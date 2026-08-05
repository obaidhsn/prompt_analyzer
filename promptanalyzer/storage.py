"""Persistence layer: prompt versioning + a non-blocking background writer.

The public entry point is :func:`enqueue_run`, called by the tracking decorator.
Writes happen on a dedicated daemon thread so the caller's request path pays
only the cost of putting an item on a queue (sub-millisecond).

Every failure is swallowed and logged — persistence problems must never
propagate into the user's application.
"""

from __future__ import annotations

import atexit
import contextlib
import queue
import threading
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from .config import Config, get_config
from .db import session_scope
from .hashing import normalize_prompt, prompt_hash
from .logging_utils import debug, warn
from .models import Project, PromptVersion, Run

__all__ = ["RunPayload", "enqueue_run", "record_run", "get_writer", "shutdown_writer"]


@dataclass
class RunPayload:
    """A pending run to be persisted."""

    project: str
    function_name: str | None = None
    provider: str | None = None
    model: str | None = None
    system_prompt: str | None = None
    user_input: str | None = None
    response: str | None = None
    latency_ms: float | None = None
    input_tokens: int | None = None
    output_tokens: int | None = None
    total_tokens: int | None = None
    cost: float | None = None
    tags: list[str] | None = None
    metadata: dict[str, Any] | None = None
    error: str | None = None
    env: str | None = None
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


# --------------------------------------------------------------------------- #
# Versioning + write helpers (synchronous core)
# --------------------------------------------------------------------------- #


def _get_or_create_project(session: Session, name: str) -> Project:
    project = session.scalar(select(Project).where(Project.name == name))
    if project is None:
        project = Project(name=name)
        session.add(project)
        session.flush()
    return project


def _get_or_create_version(
    session: Session, project: Project, system_prompt: str | None
) -> PromptVersion | None:
    """Return the prompt version for ``system_prompt``, creating one if new.

    Returns ``None`` when there is no system prompt to version.
    """
    if system_prompt is None or normalize_prompt(system_prompt) == "":
        return None
    digest = prompt_hash(system_prompt)
    existing = session.scalar(
        select(PromptVersion).where(
            PromptVersion.project_id == project.id, PromptVersion.hash == digest
        )
    )
    if existing is not None:
        return existing
    max_version = session.scalar(
        select(func.max(PromptVersion.version)).where(PromptVersion.project_id == project.id)
    )
    version = PromptVersion(
        project_id=project.id,
        version=(max_version or 0) + 1,
        hash=digest,
        system_prompt=normalize_prompt(system_prompt),
    )
    session.add(version)
    session.flush()
    return version


def record_run(payload: RunPayload, config: Config | None = None) -> int | None:
    """Persist a run synchronously. Returns the new run id, or ``None`` on failure.

    This is the synchronous core used by the background writer and available for
    callers who want a blocking write (e.g. tests).
    """
    cfg = config or get_config()
    try:
        with session_scope() as session:
            project = _get_or_create_project(session, payload.project)
            version = _get_or_create_version(session, project, payload.system_prompt)
            run = Run(
                project_id=project.id,
                prompt_version_id=version.id if version else None,
                function_name=payload.function_name,
                provider=payload.provider,
                model=payload.model,
                system_prompt=payload.system_prompt if cfg.save_responses else None,
                user_input=payload.user_input if cfg.save_responses else None,
                response=payload.response if cfg.save_responses else None,
                latency_ms=payload.latency_ms,
                input_tokens=payload.input_tokens if cfg.log_tokens else None,
                output_tokens=payload.output_tokens if cfg.log_tokens else None,
                total_tokens=payload.total_tokens if cfg.log_tokens else None,
                cost=payload.cost if cfg.log_cost else None,
                tags=payload.tags,
                run_metadata=payload.metadata,
                error=payload.error,
                env=payload.env,
                created_at=payload.created_at,
            )
            session.add(run)
            session.flush()
            run_id = run.id
        return run_id
    except Exception as exc:
        warn("storage unavailable, continuing application execution (%s)", exc)
        debug("record_run failed: %s", exc)
        return None


# --------------------------------------------------------------------------- #
# Background writer
# --------------------------------------------------------------------------- #


class BackgroundWriter:
    """A single daemon thread draining a queue of :class:`RunPayload` objects."""

    _SENTINEL = object()

    def __init__(self, maxsize: int = 10_000) -> None:
        self._queue: queue.Queue[Any] = queue.Queue(maxsize=maxsize)
        self._thread: threading.Thread | None = None
        self._started = threading.Event()
        self._lock = threading.Lock()

    def start(self) -> None:
        with self._lock:
            if self._thread is not None and self._thread.is_alive():
                return
            self._thread = threading.Thread(
                target=self._run, name="promptanalyzer-writer", daemon=True
            )
            self._thread.start()
            self._started.set()

    def _run(self) -> None:
        while True:
            item = self._queue.get()
            try:
                if item is self._SENTINEL:
                    return
                record_run(item)
            except Exception as exc:  # defensive: never kill the writer thread
                warn("background write failed (%s)", exc)
            finally:
                self._queue.task_done()

    def submit(self, payload: RunPayload) -> None:
        self.start()
        try:
            self._queue.put_nowait(payload)
        except queue.Full:
            warn("log queue full, dropping run to protect the application")

    def flush(self, timeout: float | None = 5.0) -> None:
        """Block until the queue is drained (used by tests and CLI export)."""
        if self._thread is None:
            return
        deadline_join = self._queue.join
        if timeout is None:
            deadline_join()
        else:
            done = threading.Event()

            def _waiter() -> None:
                deadline_join()
                done.set()

            threading.Thread(target=_waiter, daemon=True).start()
            done.wait(timeout)

    def shutdown(self, timeout: float = 5.0) -> None:
        if self._thread is None:
            return
        with contextlib.suppress(queue.Full):
            self._queue.put_nowait(self._SENTINEL)
        self._thread.join(timeout)


_writer: BackgroundWriter | None = None
_writer_lock = threading.Lock()


def get_writer() -> BackgroundWriter:
    global _writer
    if _writer is None:
        with _writer_lock:
            if _writer is None:
                _writer = BackgroundWriter()
                atexit.register(_writer.shutdown)
    return _writer


def enqueue_run(payload: RunPayload) -> None:
    """Queue a run for asynchronous persistence (non-blocking, error-safe)."""
    try:
        get_writer().submit(payload)
    except Exception as exc:
        warn("could not enqueue run (%s)", exc)


def shutdown_writer() -> None:
    global _writer
    if _writer is not None:
        _writer.shutdown()
        _writer = None
