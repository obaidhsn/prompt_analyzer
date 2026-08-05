"""Integration tests for the @track decorator."""

from __future__ import annotations

import asyncio
from types import SimpleNamespace

import pytest

from promptanalyzer import track
from promptanalyzer.db import session_scope
from promptanalyzer.models import Run
from promptanalyzer.storage import get_writer


def _flush():
    get_writer().flush(timeout=5.0)


def _fake_openai(content="Hi", model="gpt-4o-mini"):
    return SimpleNamespace(
        model=model,
        choices=[SimpleNamespace(message=SimpleNamespace(content=content))],
        usage=SimpleNamespace(prompt_tokens=10, completion_tokens=20, total_tokens=30),
    )


def test_track_records_a_run():
    @track("support")
    def chat(message):
        return _fake_openai("Hello!")

    chat("hi there")
    _flush()
    with session_scope() as session:
        run = session.query(Run).one()
        assert run.function_name == "chat"
        assert run.provider == "openai"
        assert run.model == "gpt-4o-mini"
        assert run.response == "Hello!"
        assert run.total_tokens == 30
        assert run.cost is not None and run.cost > 0
        assert run.latency_ms is not None


def test_track_never_swallows_user_result():
    @track("passthrough")
    def echo(x):
        return x

    assert echo(42) == 42


def test_track_records_errors_and_reraises():
    @track("boom")
    def broken():
        raise ValueError("kaboom")

    with pytest.raises(ValueError, match="kaboom"):
        broken()
    _flush()
    with session_scope() as session:
        run = session.query(Run).one()
        assert "kaboom" in (run.error or "")


def test_tracking_failure_does_not_break_function(monkeypatch):
    # Force enqueue to blow up; the wrapped function must still return.
    import promptanalyzer.tracker as tracker

    def boom(_payload):
        raise RuntimeError("db exploded")

    monkeypatch.setattr(tracker, "enqueue_run", boom)

    @track("resilient")
    def chat():
        return _fake_openai()

    assert chat() is not None  # no exception propagated


def test_async_tracking():
    @track("async-bot")
    async def chat():
        await asyncio.sleep(0)
        return _fake_openai("async hi")

    result = asyncio.run(chat())
    assert result is not None
    _flush()
    with session_scope() as session:
        run = session.query(Run).one()
        assert run.response == "async hi"


def test_custom_extractors_with_track():
    @track(
        name="custom",
        provider="mylib",
        system=lambda a, k: k["system"],
        user=lambda a, k: k["prompt"],
        response=lambda r: r,
    )
    def llm(system, prompt):
        return "the answer"

    llm(system="be terse", prompt="2+2?")
    _flush()
    with session_scope() as session:
        run = session.query(Run).one()
        assert run.provider == "mylib"
        assert run.system_prompt == "be terse"
        assert run.user_input == "2+2?"
        assert run.response == "the answer"
