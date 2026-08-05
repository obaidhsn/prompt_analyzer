"""Configuration for PromptAnalyzer.

Configuration priority (highest to lowest):
    1. Decorator / explicit arguments (handled by callers)
    2. Environment variables (``PROMPTANALYZER_*``, legacy ``PROMPTLOG_*``)
    3. Default values (this module)

The configuration is intentionally dependency-light so importing
:mod:`promptanalyzer` never pulls in FastAPI or a database driver.
"""

from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path

__all__ = ["Config", "get_config", "reset_config", "home_dir"]

_ENV_PREFIXES = ("PROMPTANALYZER_", "PROMPTLOG_")


def _env(name: str, default: str | None = None) -> str | None:
    """Read ``name`` under any supported prefix, preferring the canonical one."""
    for prefix in _ENV_PREFIXES:
        value = os.environ.get(prefix + name)
        if value is not None:
            return value
    return default


def _env_bool(name: str, default: bool) -> bool:
    raw = _env(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def _env_int(name: str, default: int) -> int:
    raw = _env(name)
    if raw is None:
        return default
    try:
        return int(raw)
    except ValueError:
        return default


def home_dir() -> Path:
    """Return the PromptAnalyzer home directory (``~/.promptanalyzer`` by default)."""
    raw = _env("HOME_DIR") or _env("DIR")
    base = Path(raw).expanduser() if raw else Path.home() / ".promptanalyzer"
    return base


class Config:
    """Resolved runtime configuration.

    Attributes are computed once from the environment. Use :func:`get_config`
    to obtain the cached singleton, or construct directly in tests.
    """

    def __init__(self) -> None:
        self.home: Path = home_dir()
        self.db_kind: str = (_env("DB", "sqlite") or "sqlite").lower()
        self.sqlite_path: Path = Path(
            _env("SQLITE_PATH") or str(self.home / "promptanalyzer.db")
        ).expanduser()
        self.database_url: str | None = _env("DATABASE_URL")

        self.host: str = _env("HOST", "127.0.0.1") or "127.0.0.1"
        self.port: int = _env_int("PORT", 4001)

        self.dashboard: bool = _env_bool("DASHBOARD", True)
        self.auto_start: bool = _env_bool("AUTO_START", False)
        self.open_browser: bool = _env_bool("OPEN_BROWSER", False)

        self.log_tokens: bool = _env_bool("LOG_TOKENS", True)
        self.log_cost: bool = _env_bool("LOG_COST", True)
        self.save_responses: bool = _env_bool("SAVE_RESPONSES", True)
        self.enabled: bool = _env_bool("ENABLED", True)

        self.project: str = _env("PROJECT", "default") or "default"
        self.env: str = _env("ENV", "development") or "development"

    # -- Derived helpers ---------------------------------------------------

    @property
    def logs_dir(self) -> Path:
        return self.home / "logs"

    @property
    def config_path(self) -> Path:
        return self.home / "config"

    def sqlalchemy_url(self) -> str:
        """Return the SQLAlchemy connection URL for the configured backend."""
        if self.database_url:
            return self.database_url
        if self.db_kind in {"postgres", "postgresql"}:
            raise RuntimeError(
                "PROMPTANALYZER_DB=postgres requires PROMPTANALYZER_DATABASE_URL to be set."
            )
        return f"sqlite:///{self.sqlite_path}"

    def ensure_dirs(self) -> None:
        """Create the home, logs and sqlite parent directories if missing."""
        self.home.mkdir(parents=True, exist_ok=True)
        self.logs_dir.mkdir(parents=True, exist_ok=True)
        if self.db_kind == "sqlite":
            self.sqlite_path.parent.mkdir(parents=True, exist_ok=True)

    def as_dict(self) -> dict[str, object]:
        return {
            "home": str(self.home),
            "db_kind": self.db_kind,
            "sqlite_path": str(self.sqlite_path),
            "database_url": self.database_url,
            "host": self.host,
            "port": self.port,
            "dashboard": self.dashboard,
            "auto_start": self.auto_start,
            "open_browser": self.open_browser,
            "log_tokens": self.log_tokens,
            "log_cost": self.log_cost,
            "save_responses": self.save_responses,
            "enabled": self.enabled,
            "project": self.project,
            "env": self.env,
        }


@lru_cache(maxsize=1)
def get_config() -> Config:
    """Return the process-wide cached :class:`Config`."""
    return Config()


def reset_config() -> None:
    """Clear the cached config (used by tests after mutating the environment)."""
    get_config.cache_clear()
