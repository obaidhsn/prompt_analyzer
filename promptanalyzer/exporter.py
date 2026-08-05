"""Export runs to JSON, CSV or Markdown."""

from __future__ import annotations

import csv
import io
import json
from typing import Any

from sqlalchemy import select

from .db import session_scope
from .models import Project, Run

__all__ = ["export_runs", "FORMATS"]

FORMATS = ("json", "csv", "markdown", "md")

_FIELDS = [
    "id",
    "created_at",
    "project",
    "function_name",
    "provider",
    "model",
    "system_prompt",
    "user_input",
    "response",
    "latency_ms",
    "input_tokens",
    "output_tokens",
    "total_tokens",
    "cost",
    "tags",
    "error",
]


def _run_to_dict(run: Run, project_name: str) -> dict[str, Any]:
    return {
        "id": run.id,
        "created_at": run.created_at.isoformat() if run.created_at else None,
        "project": project_name,
        "function_name": run.function_name,
        "provider": run.provider,
        "model": run.model,
        "system_prompt": run.system_prompt,
        "user_input": run.user_input,
        "response": run.response,
        "latency_ms": run.latency_ms,
        "input_tokens": run.input_tokens,
        "output_tokens": run.output_tokens,
        "total_tokens": run.total_tokens,
        "cost": run.cost,
        "tags": run.tags,
        "error": run.error,
    }


def _collect(project: str | None, limit: int | None) -> list[dict[str, Any]]:
    with session_scope() as session:
        names: dict[int, str] = {  # noqa: C416 - annotated; Row isn't a plain tuple for mypy
            pid: name for pid, name in session.execute(select(Project.id, Project.name)).all()
        }
        stmt = select(Run).order_by(Run.created_at.desc())
        if project:
            stmt = stmt.join(Project, Run.project_id == Project.id).where(Project.name == project)
        if limit:
            stmt = stmt.limit(limit)
        return [_run_to_dict(r, names.get(r.project_id, "")) for r in session.scalars(stmt)]


def _to_json(rows: list[dict[str, Any]]) -> str:
    return json.dumps(rows, indent=2, default=str)


def _to_csv(rows: list[dict[str, Any]]) -> str:
    buf = io.StringIO()
    writer = csv.DictWriter(buf, fieldnames=_FIELDS, extrasaction="ignore")
    writer.writeheader()
    for row in rows:
        serialised = dict(row)
        if isinstance(serialised.get("tags"), (list, dict)):
            serialised["tags"] = json.dumps(serialised["tags"])
        writer.writerow(serialised)
    return buf.getvalue()


def _to_markdown(rows: list[dict[str, Any]]) -> str:
    lines = ["# PromptAnalyzer Export", "", f"Total runs: {len(rows)}", ""]
    for row in rows:
        lines.append(f"## Run #{row['id']} — {row.get('model') or 'unknown model'}")
        lines.append("")
        lines.append(f"- **Project:** {row.get('project')}")
        lines.append(f"- **Provider:** {row.get('provider')}")
        lines.append(f"- **Time:** {row.get('created_at')}")
        lines.append(
            f"- **Latency:** {row.get('latency_ms')} ms · "
            f"**Tokens:** {row.get('total_tokens')} · **Cost:** ${row.get('cost')}"
        )
        if row.get("system_prompt"):
            lines += ["", "**System prompt**", "", "```", str(row["system_prompt"]), "```"]
        if row.get("user_input"):
            lines += ["", "**User input**", "", "```", str(row["user_input"]), "```"]
        if row.get("response"):
            lines += ["", "**Response**", "", "```", str(row["response"]), "```"]
        if row.get("error"):
            lines += ["", f"> ⚠️ Error: {row['error']}"]
        lines += ["", "---", ""]
    return "\n".join(lines)


def export_runs(
    fmt: str = "json",
    *,
    project: str | None = None,
    limit: int | None = None,
    output: str | None = None,
) -> str:
    """Export runs in ``fmt``; write to ``output`` if given, and return the text."""
    fmt = fmt.lower()
    if fmt not in FORMATS:
        raise ValueError(f"Unknown format {fmt!r}. Choose from {', '.join(FORMATS)}.")
    rows = _collect(project, limit)
    if fmt == "json":
        text = _to_json(rows)
    elif fmt == "csv":
        text = _to_csv(rows)
    else:  # markdown / md
        text = _to_markdown(rows)
    if output:
        with open(output, "w", encoding="utf-8") as fh:
            fh.write(text)
    return text
