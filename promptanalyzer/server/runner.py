"""Launch the dashboard with uvicorn, either blocking or on a background thread."""

from __future__ import annotations

import contextlib
import threading
import webbrowser
from typing import Any

from ..config import get_config
from ..logging_utils import get_logger, warn

__all__ = ["start_dashboard", "run_blocking"]

_server_thread: threading.Thread | None = None


def _build() -> tuple[Any, str, int]:
    from .app import create_app

    cfg = get_config()
    app = create_app()
    return app, cfg.host, cfg.port


def run_blocking(host: str | None = None, port: int | None = None) -> None:
    """Run the dashboard in the foreground (used by ``promptanalyzer dashboard``)."""
    import uvicorn

    app, cfg_host, cfg_port = _build()
    uvicorn.run(app, host=host or cfg_host, port=port or cfg_port, log_level="warning")


def start_dashboard(
    *,
    host: str | None = None,
    port: int | None = None,
    open_browser: bool = False,
    background: bool = True,
) -> None:
    """Start the dashboard. When ``background`` is True, return immediately."""
    global _server_thread
    cfg = get_config()
    host = host or cfg.host
    port = port or cfg.port
    url = f"http://{host}:{port}"

    if not background:
        if open_browser:
            _open_later(url)
        run_blocking(host, port)
        return

    if _server_thread is not None and _server_thread.is_alive():
        return

    def _serve() -> None:
        try:
            import uvicorn

            app, _, _ = _build()
            uvicorn.run(app, host=host, port=port, log_level="warning")
        except Exception as exc:  # pragma: no cover
            warn("dashboard failed to start (%s)", exc)

    _server_thread = threading.Thread(target=_serve, name="promptanalyzer-dashboard", daemon=True)
    _server_thread.start()
    get_logger().info("dashboard starting at %s", url)
    if open_browser:
        _open_later(url)


def _open_later(url: str, delay: float = 1.0) -> None:
    def _open() -> None:
        with contextlib.suppress(Exception):  # pragma: no cover
            webbrowser.open(url)

    threading.Timer(delay, _open).start()
