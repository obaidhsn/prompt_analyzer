"""Read-side query helpers shared by the dashboard and the exporter.

Keeping queries here (rather than in route handlers) keeps the web layer thin
and makes the same analytics reusable from the CLI.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy import String, cast, func, or_, select
from sqlalchemy.orm import Session

from .models import Project, PromptVersion, Run

__all__ = [
    "Page",
    "overview_stats",
    "runs_over_time",
    "list_projects",
    "project_detail",
    "list_versions",
    "version_detail",
    "list_runs",
    "get_run",
    "distinct_models",
    "distinct_providers",
]


@dataclass
class Page:
    """A paginated result set."""

    items: list[Any]
    total: int
    page: int
    page_size: int

    @property
    def pages(self) -> int:
        return max(1, (self.total + self.page_size - 1) // self.page_size)

    @property
    def has_prev(self) -> bool:
        return self.page > 1

    @property
    def has_next(self) -> bool:
        return self.page < self.pages


def overview_stats(session: Session) -> dict[str, Any]:
    """Aggregate headline metrics for the home dashboard."""
    total_projects = session.scalar(select(func.count(Project.id))) or 0
    total_versions = session.scalar(select(func.count(PromptVersion.id))) or 0
    total_runs = session.scalar(select(func.count(Run.id))) or 0
    total_tokens = session.scalar(select(func.coalesce(func.sum(Run.total_tokens), 0))) or 0
    total_cost = session.scalar(select(func.coalesce(func.sum(Run.cost), 0.0))) or 0.0
    avg_latency = session.scalar(select(func.avg(Run.latency_ms)))
    error_count = session.scalar(select(func.count(Run.id)).where(Run.error.is_not(None))) or 0
    return {
        "total_projects": total_projects,
        "total_versions": total_versions,
        "total_runs": total_runs,
        "total_tokens": int(total_tokens),
        "total_cost": float(total_cost or 0.0),
        "avg_latency": float(avg_latency) if avg_latency is not None else 0.0,
        "error_count": error_count,
    }


def runs_over_time(session: Session, days: int = 14) -> dict[str, list]:
    """Return per-day series for runs, tokens, cost and average latency."""
    since = datetime.now(timezone.utc) - timedelta(days=days)
    day = func.date(Run.created_at)
    rows = session.execute(
        select(
            day.label("day"),
            func.count(Run.id),
            func.coalesce(func.sum(Run.total_tokens), 0),
            func.coalesce(func.sum(Run.cost), 0.0),
            func.coalesce(func.avg(Run.latency_ms), 0.0),
        )
        .where(Run.created_at >= since)
        .group_by(day)
        .order_by(day)
    ).all()
    return {
        "labels": [str(r[0]) for r in rows],
        "runs": [int(r[1]) for r in rows],
        "tokens": [int(r[2]) for r in rows],
        "cost": [round(float(r[3]), 6) for r in rows],
        "latency": [round(float(r[4]), 2) for r in rows],
    }


def list_projects(session: Session) -> list[dict[str, Any]]:
    """List projects with per-project run/version counts and totals."""
    rows = session.execute(
        select(
            Project.id,
            Project.name,
            Project.created_at,
            func.count(func.distinct(Run.id)),
            func.coalesce(func.sum(Run.total_tokens), 0),
            func.coalesce(func.sum(Run.cost), 0.0),
        )
        .outerjoin(Run, Run.project_id == Project.id)
        .group_by(Project.id)
        .order_by(Project.name)
    ).all()
    version_counts: dict[int, int] = {  # noqa: C416 - annotated; Row isn't a plain tuple
        pid: count
        for pid, count in session.execute(
            select(PromptVersion.project_id, func.count(PromptVersion.id)).group_by(
                PromptVersion.project_id
            )
        ).all()
    }
    return [
        {
            "id": r[0],
            "name": r[1],
            "created_at": r[2],
            "runs": int(r[3]),
            "tokens": int(r[4]),
            "cost": float(r[5]),
            "versions": int(version_counts.get(r[0], 0)),
        }
        for r in rows
    ]


def project_detail(session: Session, project_id: int) -> Project | None:
    return session.get(Project, project_id)


def list_versions(session: Session, project_id: int) -> list[dict[str, Any]]:
    """Return prompt versions for a project with aggregate run metrics."""
    rows = session.execute(
        select(
            PromptVersion.id,
            PromptVersion.version,
            PromptVersion.hash,
            PromptVersion.system_prompt,
            PromptVersion.created_at,
            func.count(Run.id),
            func.coalesce(func.avg(Run.latency_ms), 0.0),
            func.coalesce(func.avg(Run.cost), 0.0),
            func.coalesce(func.sum(Run.total_tokens), 0),
        )
        .outerjoin(Run, Run.prompt_version_id == PromptVersion.id)
        .where(PromptVersion.project_id == project_id)
        .group_by(PromptVersion.id)
        .order_by(PromptVersion.version.desc())
    ).all()
    return [
        {
            "id": r[0],
            "version": r[1],
            "hash": r[2],
            "system_prompt": r[3],
            "created_at": r[4],
            "runs": int(r[5]),
            "avg_latency": float(r[6]),
            "avg_cost": float(r[7]),
            "tokens": int(r[8]),
        }
        for r in rows
    ]


def version_detail(session: Session, version_id: int) -> dict[str, Any] | None:
    version = session.get(PromptVersion, version_id)
    if version is None:
        return None
    stats = session.execute(
        select(
            func.count(Run.id),
            func.coalesce(func.avg(Run.latency_ms), 0.0),
            func.coalesce(func.avg(Run.cost), 0.0),
            func.coalesce(func.sum(Run.total_tokens), 0),
        ).where(Run.prompt_version_id == version_id)
    ).one()
    return {
        "version": version,
        "runs": int(stats[0]),
        "avg_latency": float(stats[1]),
        "avg_cost": float(stats[2]),
        "tokens": int(stats[3]),
    }


def list_runs(
    session: Session,
    *,
    page: int = 1,
    page_size: int = 25,
    project_id: int | None = None,
    version_id: int | None = None,
    model: str | None = None,
    provider: str | None = None,
    search: str | None = None,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
    tag: str | None = None,
) -> Page:
    """List runs with pagination and the full set of dashboard filters."""
    conditions = []
    if project_id is not None:
        conditions.append(Run.project_id == project_id)
    if version_id is not None:
        conditions.append(Run.prompt_version_id == version_id)
    if model:
        conditions.append(Run.model == model)
    if provider:
        conditions.append(Run.provider == provider)
    if date_from is not None:
        conditions.append(Run.created_at >= date_from)
    if date_to is not None:
        conditions.append(Run.created_at <= date_to)
    if tag:
        conditions.append(cast(Run.tags, String).like(f'%"{tag}"%'))
    if search:
        like = f"%{search}%"
        conditions.append(
            or_(
                Run.system_prompt.like(like),
                Run.user_input.like(like),
                Run.response.like(like),
            )
        )

    base = select(Run)
    if conditions:
        base = base.where(*conditions)

    total = session.scalar(select(func.count()).select_from(base.order_by(None).subquery())) or 0
    page = max(1, page)
    items = list(
        session.scalars(
            base.order_by(Run.created_at.desc(), Run.id.desc())
            .limit(page_size)
            .offset((page - 1) * page_size)
        )
    )
    return Page(items=items, total=int(total), page=page, page_size=page_size)


def get_run(session: Session, run_id: int) -> Run | None:
    return session.get(Run, run_id)


def distinct_models(session: Session) -> list[str]:
    rows = session.scalars(
        select(Run.model).where(Run.model.is_not(None)).distinct().order_by(Run.model)
    )
    return [r for r in rows if r]


def distinct_providers(session: Session) -> list[str]:
    rows = session.scalars(
        select(Run.provider).where(Run.provider.is_not(None)).distinct().order_by(Run.provider)
    )
    return [r for r in rows if r]
