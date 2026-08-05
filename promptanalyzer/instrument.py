"""Automatic client instrumentation.

The ``@track`` decorator can only see a function's arguments and return value.
But most LLM code builds the request *inside* the function and returns just the
answer text — so the prompts, model, and token usage are invisible to a plain
decorator.

To capture them anyway, PromptAnalyzer transparently wraps the ``create`` methods
of supported SDK clients (OpenAI, Anthropic). While a tracked function is running,
these wrappers record the real request kwargs and response object into a
context-local :class:`CallCapture`. The tracker then extracts from that capture,
so the example "call the client, return ``.content``" is fully logged.

Everything here is defensive and opt-out (``PROMPTANALYZER_INSTRUMENT=false``):
patching failures are swallowed, and if an SDK isn't installed it's simply
skipped.
"""

from __future__ import annotations

import functools
import inspect
import os
import threading
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import dataclass, field
from typing import Any

from .logging_utils import debug

__all__ = [
    "CallCapture",
    "capture_context",
    "install_all",
    "instrument_method",
    "instrumentation_enabled",
]

_PATCH_MARKER = "_promptanalyzer_patched"
_active_capture: ContextVar[CallCapture | None] = ContextVar("promptanalyzer_capture", default=None)
_install_lock = threading.Lock()
_installed = False


@dataclass
class RecordedCall:
    """A single intercepted client call."""

    request: dict[str, Any]
    result: Any
    provider: str | None = None


@dataclass
class CallCapture:
    """Collects client calls made during one tracked function invocation."""

    calls: list[RecordedCall] = field(default_factory=list)

    def record(self, request: dict[str, Any], result: Any, provider: str | None) -> None:
        self.calls.append(RecordedCall(request=dict(request), result=result, provider=provider))

    @property
    def last(self) -> RecordedCall | None:
        return self.calls[-1] if self.calls else None


def instrumentation_enabled() -> bool:
    raw = os.environ.get("PROMPTANALYZER_INSTRUMENT")
    if raw is None:
        return True
    return raw.strip().lower() in {"1", "true", "yes", "on"}


@contextmanager
def capture_context() -> Iterator[CallCapture]:
    """Arm capture for the duration of the block (context-local, nesting-safe)."""
    capture = CallCapture()
    token = _active_capture.set(capture)
    try:
        yield capture
    finally:
        _active_capture.reset(token)


def _wrap_sync(original: Callable[..., Any], provider: str) -> Callable[..., Any]:
    @functools.wraps(original)
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        result = original(*args, **kwargs)
        _maybe_record(kwargs, result, provider)
        return result

    return wrapper


def _wrap_async(original: Callable[..., Any], provider: str) -> Callable[..., Any]:
    @functools.wraps(original)
    async def wrapper(*args: Any, **kwargs: Any) -> Any:
        result = await original(*args, **kwargs)
        _maybe_record(kwargs, result, provider)
        return result

    return wrapper


def _maybe_record(kwargs: dict[str, Any], result: Any, provider: str) -> None:
    capture = _active_capture.get()
    if capture is None:
        return
    try:
        capture.record(kwargs, result, provider)
    except Exception as exc:  # never let recording break the client call
        debug("call capture failed: %s", exc)


def instrument_method(cls: type, method_name: str, provider: str) -> bool:
    """Wrap ``cls.method_name`` to record calls. Returns True if newly patched.

    Idempotent and defensive — safe to call on any class, including in tests.
    """
    try:
        original = cls.__dict__.get(method_name)
        if original is None:
            original = getattr(cls, method_name, None)
        if original is None or getattr(original, _PATCH_MARKER, False):
            return False
        if inspect.iscoroutinefunction(original):
            wrapper = _wrap_async(original, provider)
        else:
            wrapper = _wrap_sync(original, provider)
        setattr(wrapper, _PATCH_MARKER, True)
        setattr(cls, method_name, wrapper)
        return True
    except Exception as exc:  # patching must never raise
        debug("failed to instrument %s.%s: %s", getattr(cls, "__name__", cls), method_name, exc)
        return False


# Known SDK targets: (import_path, class_name, method, provider).
_TARGETS: tuple[tuple[str, str, str, str], ...] = (
    ("openai.resources.chat.completions", "Completions", "create", "openai"),
    ("openai.resources.chat.completions", "AsyncCompletions", "create", "openai"),
    ("anthropic.resources.messages", "Messages", "create", "anthropic"),
    ("anthropic.resources.messages", "AsyncMessages", "create", "anthropic"),
)


def install_all() -> None:
    """Patch every available SDK client. Runs at most once; never raises."""
    global _installed
    if _installed or not instrumentation_enabled():
        return
    with _install_lock:
        if _installed:
            return
        for module_path, class_name, method, provider in _TARGETS:
            try:
                import importlib

                module = importlib.import_module(module_path)
                cls = getattr(module, class_name, None)
                if cls is not None:
                    instrument_method(cls, method, provider)
            except Exception as exc:  # SDK not installed / layout changed
                debug("skipping %s.%s (%s)", module_path, class_name, exc)
        _installed = True
