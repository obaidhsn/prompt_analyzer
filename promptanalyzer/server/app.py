"""FastAPI application factory for the PromptAnalyzer dashboard.

Server-side rendered with Jinja2. HTMX drives partial updates; Alpine.js powers
small client interactions; Chart.js renders analytics. No Node build step — all
templates and static assets ship inside the Python package.
"""

from __future__ import annotations

import difflib
import json
from datetime import datetime
from pathlib import Path
from typing import Any

from fastapi import FastAPI, Query, Request
from fastapi.responses import HTMLResponse, JSONResponse, PlainTextResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from ..db import session_scope
from ..logging_utils import debug

_HERE = Path(__file__).parent
TEMPLATES_DIR = _HERE / "templates"
STATIC_DIR = _HERE / "static"


def create_app() -> Any:
    """Build and return the FastAPI application."""
    from .. import __version__
    from ..exporter import export_runs
    from ..queries import (
        distinct_models,
        distinct_providers,
        get_run,
        list_projects,
        list_runs,
        list_versions,
        overview_stats,
        project_detail,
        runs_over_time,
        version_detail,
    )

    app = FastAPI(title="PromptAnalyzer", version=__version__, docs_url="/api/docs")
    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")
    templates = Jinja2Templates(directory=str(TEMPLATES_DIR))
    _register_filters(templates)

    def ctx(request: Request, **kwargs: Any) -> dict[str, Any]:
        base = {"request": request, "version": __version__, "nav": kwargs.pop("nav", "")}
        base.update(kwargs)
        return base

    def render(name: str, context: dict[str, Any], status_code: int = 200) -> Any:
        return templates.TemplateResponse(
            context["request"], name, context, status_code=status_code
        )

    # --- Pages ---------------------------------------------------------------

    @app.get("/", response_class=HTMLResponse)
    def home(request: Request) -> Any:
        with session_scope() as session:
            stats = overview_stats(session)
            series = runs_over_time(session, days=14)
            projects = list_projects(session)[:6]
        return render(
            "index.html",
            ctx(request, nav="home", stats=stats, series=json.dumps(series), projects=projects),
        )

    @app.get("/projects", response_class=HTMLResponse)
    def projects_page(request: Request) -> Any:
        with session_scope() as session:
            projects = list_projects(session)
        return render("projects.html", ctx(request, nav="projects", projects=projects))

    @app.get("/projects/{project_id}", response_class=HTMLResponse)
    def project_page(request: Request, project_id: int) -> Any:
        with session_scope() as session:
            project = project_detail(session, project_id)
            if project is None:
                return _not_found(templates, request)
            versions = list_versions(session, project_id)
            recent = list_runs(session, project_id=project_id, page_size=10)
            name = project.name
        return render(
            "project_detail.html",
            ctx(
                request,
                nav="projects",
                project_id=project_id,
                project_name=name,
                versions=versions,
                runs=recent,
            ),
        )

    @app.get("/versions/{version_id}", response_class=HTMLResponse)
    def version_page(request: Request, version_id: int) -> Any:
        with session_scope() as session:
            detail = version_detail(session, version_id)
            if detail is None:
                return _not_found(templates, request)
            version = detail["version"]
            all_versions = list_versions(session, version.project_id)
            recent = list_runs(session, version_id=version_id, page_size=10)
            data = {
                "version_id": version.id,
                "project_id": version.project_id,
                "number": version.version,
                "hash": version.hash,
                "system_prompt": version.system_prompt,
                "created_at": version.created_at,
                "runs": detail["runs"],
                "avg_latency": detail["avg_latency"],
                "avg_cost": detail["avg_cost"],
                "tokens": detail["tokens"],
            }
        return render(
            "version_detail.html",
            ctx(request, nav="projects", v=data, all_versions=all_versions, runs=recent),
        )

    @app.get("/projects/{project_id}/diff", response_class=HTMLResponse)
    def diff_page(
        request: Request,
        project_id: int,
        a: int | None = Query(None),
        b: int | None = Query(None),
    ) -> Any:
        with session_scope() as session:
            project = project_detail(session, project_id)
            if project is None:
                return _not_found(templates, request)
            versions = list_versions(session, project_id)
            by_id = {v["id"]: v for v in versions}
            left = by_id.get(a) if a else (versions[-1] if versions else None)
            right = by_id.get(b) if b else (versions[0] if versions else None)
            diff_html = ""
            if left and right:
                diff_html = _render_diff(
                    left["system_prompt"],
                    right["system_prompt"],
                    f"v{left['version']}",
                    f"v{right['version']}",
                )
            name = project.name
        return render(
            "diff.html",
            ctx(
                request,
                nav="projects",
                project_id=project_id,
                project_name=name,
                versions=versions,
                left=left,
                right=right,
                diff_html=diff_html,
            ),
        )

    @app.get("/runs", response_class=HTMLResponse)
    def runs_page(
        request: Request,
        page: int = 1,
        model: str | None = None,
        provider: str | None = None,
        q: str | None = None,
        project_id: int | None = None,
    ) -> Any:
        with session_scope() as session:
            result = list_runs(
                session,
                page=page,
                model=model,
                provider=provider,
                search=q,
                project_id=project_id,
            )
            project_map = {p["id"]: p["name"] for p in list_projects(session)}
            models = distinct_models(session)
            providers = distinct_providers(session)
            rows = [_run_row(r, project_map) for r in result.items]
        template = "partials/runs_table.html" if request.headers.get("HX-Request") else "runs.html"
        return render(
            template,
            ctx(
                request,
                nav="runs",
                rows=rows,
                page=result,
                models=models,
                providers=providers,
                filters={"model": model, "provider": provider, "q": q, "project_id": project_id},
            ),
        )

    @app.get("/runs/{run_id}", response_class=HTMLResponse)
    def run_page(request: Request, run_id: int) -> Any:
        with session_scope() as session:
            run = get_run(session, run_id)
            if run is None:
                return _not_found(templates, request)
            project = project_detail(session, run.project_id)
            data = _run_full(run, project.name if project else "")
        return render("run_detail.html", ctx(request, nav="runs", run=data))

    @app.get("/search", response_class=HTMLResponse)
    def search_page(
        request: Request,
        q: str | None = None,
        model: str | None = None,
        provider: str | None = None,
        page: int = 1,
    ) -> Any:
        with session_scope() as session:
            result = list_runs(session, page=page, search=q, model=model, provider=provider)
            project_map = {p["id"]: p["name"] for p in list_projects(session)}
            models = distinct_models(session)
            providers = distinct_providers(session)
            rows = [_run_row(r, project_map) for r in result.items]
        template = (
            "partials/runs_table.html" if request.headers.get("HX-Request") else "search.html"
        )
        return render(
            template,
            ctx(
                request,
                nav="search",
                rows=rows,
                page=result,
                q=q or "",
                models=models,
                providers=providers,
                filters={"model": model, "provider": provider, "q": q},
            ),
        )

    # --- JSON / data API -----------------------------------------------------

    @app.get("/api/stats")
    def api_stats() -> Any:
        with session_scope() as session:
            return JSONResponse(overview_stats(session))

    @app.get("/api/series")
    def api_series(days: int = 14) -> Any:
        with session_scope() as session:
            return JSONResponse(runs_over_time(session, days=days))

    @app.get("/api/export")
    def api_export(fmt: str = "json", project: str | None = None) -> Any:
        text = export_runs(fmt, project=project)
        media = {"json": "application/json", "csv": "text/csv"}.get(fmt, "text/markdown")
        return PlainTextResponse(text, media_type=media)

    @app.get("/api/health")
    def api_health() -> Any:
        return {"status": "ok", "version": __version__}

    return app


# --------------------------------------------------------------------------- #
# Rendering helpers
# --------------------------------------------------------------------------- #


def _run_row(run: Any, project_map: dict[int, str]) -> dict[str, Any]:
    return {
        "id": run.id,
        "created_at": run.created_at,
        "project": project_map.get(run.project_id, ""),
        "user_input": run.user_input,
        "response": run.response,
        "model": run.model,
        "provider": run.provider,
        "latency_ms": run.latency_ms,
        "total_tokens": run.total_tokens,
        "cost": run.cost,
        "error": run.error,
    }


def _run_full(run: Any, project_name: str) -> dict[str, Any]:
    data = _run_row(run, {run.project_id: project_name})
    data.update(
        {
            "function_name": run.function_name,
            "system_prompt": run.system_prompt,
            "input_tokens": run.input_tokens,
            "output_tokens": run.output_tokens,
            "tags": run.tags,
            "metadata": run.run_metadata,
            "env": run.env,
            "prompt_version_id": run.prompt_version_id,
        }
    )
    return data


def _render_diff(a: str, b: str, a_name: str, b_name: str) -> str:
    """Render a GitHub-style side-by-side diff using difflib (no JS needed)."""
    differ = difflib.HtmlDiff(wrapcolumn=80)
    table = differ.make_table(
        (a or "").splitlines(),
        (b or "").splitlines(),
        fromdesc=a_name,
        todesc=b_name,
        context=False,
    )
    return table


def _not_found(templates: Any, request: Any) -> Any:
    try:
        return templates.TemplateResponse(
            request,
            "not_found.html",
            {"request": request, "nav": "", "version": ""},
            status_code=404,
        )
    except Exception as exc:  # pragma: no cover
        debug("not_found render failed: %s", exc)
        return HTMLResponse("<h1>404 &mdash; Not found</h1>", status_code=404)


def _register_filters(templates: Any) -> None:
    env = templates.env

    def dt(value: datetime | None, fmt: str = "%Y-%m-%d %H:%M") -> str:
        return value.strftime(fmt) if isinstance(value, datetime) else ""

    def ago(value: datetime | None) -> str:
        if not isinstance(value, datetime):
            return ""
        now = datetime.now(value.tzinfo) if value.tzinfo else datetime.now()
        seconds = (now - value).total_seconds()
        for unit, size in (("d", 86400), ("h", 3600), ("m", 60)):
            if seconds >= size:
                return f"{int(seconds // size)}{unit} ago"
        return "just now"

    def money(value: float | None) -> str:
        if value is None:
            return "—"
        if value == 0:
            return "$0"
        if value < 0.01:
            return f"${value:.5f}"
        return f"${value:,.2f}"

    def num(value: Any) -> str:
        try:
            return f"{int(value):,}"
        except (TypeError, ValueError):
            return "0"

    def ms(value: float | None) -> str:
        return f"{value:,.0f} ms" if value is not None else "—"

    def truncate(value: str | None, length: int = 80) -> str:
        if not value:
            return ""
        text = str(value).replace("\n", " ")
        return text if len(text) <= length else text[:length] + "…"

    env.filters["dt"] = dt
    env.filters["ago"] = ago
    env.filters["money"] = money
    env.filters["num"] = num
    env.filters["ms"] = ms
    env.filters["truncate_text"] = truncate
