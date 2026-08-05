"""Dashboard server package (FastAPI + Jinja2, ships inside the wheel)."""

from __future__ import annotations

from .app import create_app

__all__ = ["create_app"]
