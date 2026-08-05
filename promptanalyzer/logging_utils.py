"""Internal logging helpers.

PromptAnalyzer must *never* crash a user's application. Every failure inside
the library is routed through :func:`warn` / :func:`debug`, never re-raised past
the tracking boundary.
"""

from __future__ import annotations

import logging
import os

_LOGGER_NAME = "promptanalyzer"


def get_logger() -> logging.Logger:
    logger = logging.getLogger(_LOGGER_NAME)
    if not logger.handlers:
        handler = logging.StreamHandler()
        handler.setFormatter(logging.Formatter("%(levelname)s [promptanalyzer] %(message)s"))
        logger.addHandler(handler)
        level = os.environ.get("PROMPTANALYZER_LOG_LEVEL", "WARNING").upper()
        logger.setLevel(getattr(logging, level, logging.WARNING))
        logger.propagate = False
    return logger


def warn(message: str, *args: object) -> None:
    get_logger().warning(message, *args)


def debug(message: str, *args: object) -> None:
    get_logger().debug(message, *args)


def exception(message: str) -> None:
    """Log a caught exception at WARNING level with traceback at DEBUG."""
    logger = get_logger()
    logger.warning(message)
    logger.debug("traceback", exc_info=True)
