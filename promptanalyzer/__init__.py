"""PromptAnalyzer — local-first LLM observability & prompt versioning.

Git for prompts. Add one decorator, run your app, open the dashboard:

    from promptanalyzer import track

    @track("medical-chatbot")
    def ask(message):
        return client.chat.completions.create(...)

Then run ``promptanalyzer dashboard`` and open http://localhost:4001.
"""

from __future__ import annotations

from .config import Config, get_config, reset_config
from .pricing import estimate_cost, register_price
from .storage import shutdown_writer
from .tracker import track

__version__ = "0.1.0"

__all__ = [
    "track",
    "get_config",
    "reset_config",
    "Config",
    "estimate_cost",
    "register_price",
    "shutdown_writer",
    "start_dashboard",
    "__version__",
]


def start_dashboard(
    *,
    host: str | None = None,
    port: int | None = None,
    open_browser: bool = False,
    background: bool = True,
) -> None:
    """Start the local dashboard server.

    Imported lazily so the core library never hard-depends on FastAPI.
    """
    from .server.runner import start_dashboard as _start

    _start(host=host, port=port, open_browser=open_browser, background=background)


def _maybe_auto_start() -> None:
    """Start the dashboard on import when PROMPTANALYZER_AUTO_START is enabled."""
    cfg = get_config()
    if not cfg.auto_start:
        return
    try:
        start_dashboard(open_browser=cfg.open_browser, background=True)
    except Exception:  # pragma: no cover - auto-start must never crash import
        from .logging_utils import debug

        debug(
            "dashboard auto-start failed",
        )


_maybe_auto_start()
