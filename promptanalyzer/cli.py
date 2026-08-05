"""Command-line interface for PromptAnalyzer.

Commands:
    promptanalyzer init        Create ~/.promptanalyzer and the database.
    promptanalyzer dashboard   Launch the local dashboard (blocking).
    promptanalyzer migrate     Create/upgrade the database schema.
    promptanalyzer export      Export runs to json / csv / markdown.
    promptanalyzer doctor      Diagnose the installation and environment.
    promptanalyzer reset       Delete all stored data (with confirmation).
"""

from __future__ import annotations

import argparse
import sys
from collections.abc import Sequence

from . import __version__
from .config import Config, get_config

_BANNER = "🧬 PromptAnalyzer"


def _cmd_init(args: argparse.Namespace) -> int:
    from .db import init_db

    cfg = get_config()
    cfg.ensure_dirs()
    init_db(cfg)
    print(f"{_BANNER}: initialised")
    print(f"  home:     {cfg.home}")
    print(f"  database: {cfg.sqlalchemy_url()}")
    print('\nAdd @track("my-project") to an LLM function, then run:')
    print("  promptanalyzer dashboard")
    return 0


def _cmd_dashboard(args: argparse.Namespace) -> int:
    try:
        from .server.runner import start_dashboard
    except ImportError:
        print(
            "Dashboard dependencies are missing. Install them with:\n"
            "  pip install 'promptanalyzer[dashboard]'",
            file=sys.stderr,
        )
        return 1
    cfg = get_config()
    host = args.host or cfg.host
    port = args.port or cfg.port
    print(f"{_BANNER}: dashboard at http://{host}:{port}  (Ctrl+C to stop)")
    try:
        start_dashboard(host=host, port=port, open_browser=not args.no_browser, background=False)
    except KeyboardInterrupt:
        print("\nStopped.")
    return 0


def _cmd_migrate(args: argparse.Namespace) -> int:
    from .db import init_db

    init_db()
    print(f"{_BANNER}: schema is up to date.")
    return 0


def _cmd_export(args: argparse.Namespace) -> int:
    from .exporter import export_runs

    text = export_runs(args.format, project=args.project, limit=args.limit, output=args.output)
    if args.output:
        print(f"{_BANNER}: exported to {args.output}")
    else:
        print(text)
    return 0


def _cmd_doctor(args: argparse.Namespace) -> int:
    cfg = get_config()
    print(f"{_BANNER} doctor")
    print(f"  version:        {__version__}")
    print(f"  python:         {sys.version.split()[0]}")
    print(f"  home:           {cfg.home}  ({'exists' if cfg.home.exists() else 'missing'})")
    print(f"  db kind:        {cfg.db_kind}")
    print(f"  db url:         {_safe_url(cfg)}")
    print(f"  host:port:      {cfg.host}:{cfg.port}")
    print(f"  project/env:    {cfg.project} / {cfg.env}")

    ok = True
    for name in ("fastapi", "uvicorn", "jinja2", "sqlalchemy"):
        present = _has_module(name)
        ok = ok and (present or name == "fastapi")
        print(f"  dep {name:<12} {'✓' if present else '✗ (missing)'}")

    try:
        from .db import session_scope
        from .queries import overview_stats

        with session_scope() as session:
            stats = overview_stats(session)
        print(
            f"  database:       reachable — {stats['total_runs']} runs, "
            f"{stats['total_projects']} projects"
        )
    except Exception as exc:
        print(f"  database:       ERROR — {exc}")
        ok = False

    print("\nStatus:", "healthy ✓" if ok else "issues found ✗")
    return 0 if ok else 1


def _cmd_reset(args: argparse.Namespace) -> int:
    cfg = get_config()
    if not args.yes:
        reply = input(
            f"This will DELETE all PromptAnalyzer data at {cfg.sqlite_path}. "
            "Type 'yes' to continue: "
        )
        if reply.strip().lower() != "yes":
            print("Aborted.")
            return 1
    from .db import init_db, reset_engine
    from .models import Base

    reset_engine()
    from .db import get_engine

    engine = get_engine()
    Base.metadata.drop_all(engine)
    reset_engine()
    init_db()
    print(f"{_BANNER}: all data reset.")
    return 0


def _safe_url(cfg: Config) -> str:
    try:
        url = cfg.sqlalchemy_url()
    except Exception as exc:
        return f"<error: {exc}>"
    if "@" in url:  # hide credentials in postgres URLs
        scheme, _, rest = url.partition("://")
        _, _, host = rest.partition("@")
        return f"{scheme}://***@{host}"
    return url


def _has_module(name: str) -> bool:
    import importlib.util

    return importlib.util.find_spec(name) is not None


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="promptanalyzer",
        description="Local-first LLM observability & prompt versioning.",
    )
    parser.add_argument("--version", action="version", version=f"promptanalyzer {__version__}")
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("init", help="Create the home directory and database.").set_defaults(
        func=_cmd_init
    )

    d = sub.add_parser("dashboard", help="Launch the local dashboard.")
    d.add_argument("--host", default=None)
    d.add_argument("--port", type=int, default=None)
    d.add_argument("--no-browser", action="store_true", help="Do not open a browser.")
    d.set_defaults(func=_cmd_dashboard)

    sub.add_parser("migrate", help="Create/upgrade the database schema.").set_defaults(
        func=_cmd_migrate
    )

    e = sub.add_parser("export", help="Export runs.")
    e.add_argument("format", nargs="?", default="json", choices=["json", "csv", "markdown", "md"])
    e.add_argument("--project", default=None)
    e.add_argument("--limit", type=int, default=None)
    e.add_argument("-o", "--output", default=None, help="Write to a file instead of stdout.")
    e.set_defaults(func=_cmd_export)

    sub.add_parser("doctor", help="Diagnose the installation.").set_defaults(func=_cmd_doctor)

    r = sub.add_parser("reset", help="Delete all stored data.")
    r.add_argument("-y", "--yes", action="store_true", help="Skip the confirmation prompt.")
    r.set_defaults(func=_cmd_reset)

    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
