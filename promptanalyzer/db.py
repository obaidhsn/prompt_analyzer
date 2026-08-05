"""Database engine and session management.

A single lazily-initialised engine is shared per process. SQLite is configured
with WAL journaling and a busy timeout so concurrent reads (dashboard) and
writes (background logger) do not block each other.
"""

from __future__ import annotations

import threading
from collections.abc import Iterator
from contextlib import contextmanager
from typing import Any

from sqlalchemy import create_engine, event
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from .config import Config, get_config
from .logging_utils import debug
from .models import Base

__all__ = ["get_engine", "session_scope", "init_db", "reset_engine", "SessionLocal"]

_engine: Engine | None = None
_SessionFactory: sessionmaker[Session] | None = None
_lock = threading.Lock()


def _configure_sqlite(engine: Engine) -> None:
    @event.listens_for(engine, "connect")
    def _set_pragmas(dbapi_conn: Any, _record: Any) -> None:
        cursor = dbapi_conn.cursor()
        try:
            cursor.execute("PRAGMA journal_mode=WAL")
            cursor.execute("PRAGMA synchronous=NORMAL")
            cursor.execute("PRAGMA busy_timeout=5000")
            cursor.execute("PRAGMA foreign_keys=ON")
        finally:
            cursor.close()


def get_engine(config: Config | None = None) -> Engine:
    """Return the shared engine, creating it (and the schema) on first use."""
    global _engine, _SessionFactory
    if _engine is not None:
        return _engine
    with _lock:
        if _engine is not None:
            return _engine
        cfg = config or get_config()
        cfg.ensure_dirs()
        url = cfg.sqlalchemy_url()
        is_sqlite = url.startswith("sqlite")
        engine = create_engine(
            url,
            future=True,
            echo=False,
            pool_pre_ping=not is_sqlite,
            connect_args={"check_same_thread": False} if is_sqlite else {},
        )
        if is_sqlite:
            _configure_sqlite(engine)
        Base.metadata.create_all(engine)
        _engine = engine
        _SessionFactory = sessionmaker(bind=engine, expire_on_commit=False, future=True)
        debug("initialised engine for %s", url)
        return _engine


def SessionLocal() -> Session:
    """Return a new session bound to the shared engine."""
    if _SessionFactory is None:
        get_engine()
    assert _SessionFactory is not None
    return _SessionFactory()


@contextmanager
def session_scope() -> Iterator[Session]:
    """Provide a transactional session, committing on success, rolling back on error."""
    session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def init_db(config: Config | None = None) -> None:
    """Create tables if they do not exist."""
    get_engine(config)


def reset_engine() -> None:
    """Dispose the engine and clear cached factories (tests / ``reset`` command)."""
    global _engine, _SessionFactory
    with _lock:
        if _engine is not None:
            _engine.dispose()
        _engine = None
        _SessionFactory = None
