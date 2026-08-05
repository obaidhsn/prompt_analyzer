"""Integration tests for the dashboard server and exporter."""

from __future__ import annotations

import json

import pytest

from promptanalyzer.exporter import export_runs
from promptanalyzer.storage import RunPayload, record_run


@pytest.fixture()
def seeded():
    record_run(
        RunPayload(
            project="medical",
            system_prompt="You are a doctor.",
            user_input="headache?",
            response="Rest and hydrate.",
            provider="openai",
            model="gpt-4o-mini",
            input_tokens=10,
            output_tokens=20,
            total_tokens=30,
            cost=0.001,
            latency_ms=120.0,
        )
    )
    record_run(
        RunPayload(
            project="medical",
            system_prompt="You are a doctor. Cite sources.",
            user_input="fever?",
            response="See a doctor.",
            provider="anthropic",
            model="claude-3-5-sonnet",
            input_tokens=8,
            output_tokens=12,
            total_tokens=20,
            cost=0.002,
            latency_ms=200.0,
        )
    )


def _client():
    from fastapi.testclient import TestClient

    from promptanalyzer.server.app import create_app

    return TestClient(create_app())


def test_home_and_pages_render(seeded):
    client = _client()
    for path in ("/", "/projects", "/runs", "/search"):
        resp = client.get(path)
        assert resp.status_code == 200
        assert "PromptAnalyzer" in resp.text


def test_api_stats(seeded):
    client = _client()
    data = client.get("/api/stats").json()
    assert data["total_runs"] == 2
    assert data["total_projects"] == 1
    assert data["total_versions"] == 2
    assert data["total_tokens"] == 50


def test_run_detail_and_versions(seeded):
    client = _client()
    projects = client.get("/api/stats").json()
    assert projects["total_versions"] == 2
    # First project id is 1; its diff page should render.
    resp = client.get("/projects/1/diff")
    assert resp.status_code == 200
    assert "diff" in resp.text.lower()


def test_search_filters(seeded):
    client = _client()
    resp = client.get("/search", params={"q": "headache"})
    assert resp.status_code == 200
    assert "headache" in resp.text


def test_export_json_csv_markdown(seeded):
    data = json.loads(export_runs("json"))
    assert len(data) == 2
    csv_text = export_runs("csv")
    assert "provider" in csv_text.splitlines()[0]
    md = export_runs("markdown")
    assert "# PromptAnalyzer Export" in md


def test_404_page():
    client = _client()
    assert client.get("/projects/9999").status_code == 404
