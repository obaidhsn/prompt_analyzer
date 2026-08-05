"""Shared pytest fixtures — isolate each test in its own temporary database."""

from __future__ import annotations

import importlib
from collections.abc import Iterator
from pathlib import Path

import pytest


@pytest.fixture(autouse=True)
def isolated_home(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Iterator[Path]:
    """Point PromptAnalyzer at a fresh temp home and reset all singletons."""
    monkeypatch.setenv("PROMPTANALYZER_HOME_DIR", str(tmp_path))
    monkeypatch.setenv("PROMPTANALYZER_SQLITE_PATH", str(tmp_path / "test.db"))
    monkeypatch.delenv("PROMPTANALYZER_DATABASE_URL", raising=False)
    monkeypatch.setenv("PROMPTANALYZER_AUTO_START", "false")

    import promptanalyzer.config as config
    import promptanalyzer.db as db
    import promptanalyzer.storage as storage

    config.reset_config()
    db.reset_engine()
    # Reset the background writer so each test gets a clean queue.
    storage.shutdown_writer()
    importlib.reload  # noqa: B018 - keep import used

    db.init_db()
    yield tmp_path

    storage.shutdown_writer()
    db.reset_engine()
    config.reset_config()
