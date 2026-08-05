"""Unit tests for prompt hashing and versioning."""

from __future__ import annotations

from promptanalyzer.db import session_scope
from promptanalyzer.hashing import normalize_prompt, prompt_hash
from promptanalyzer.models import PromptVersion
from promptanalyzer.storage import (
    RunPayload,
    _get_or_create_project,
    _get_or_create_version,
    record_run,
)


def test_normalize_collapses_trailing_whitespace():
    assert normalize_prompt("hello   \nworld  ") == "hello\nworld"
    assert prompt_hash("a\n") == prompt_hash("a")


def test_identical_prompts_share_a_version():
    for _ in range(3):
        record_run(RunPayload(project="bot", system_prompt="You are a doctor.", user_input="hi"))
    with session_scope() as session:
        versions = session.query(PromptVersion).all()
        assert len(versions) == 1
        assert versions[0].version == 1


def test_changed_prompt_creates_new_version():
    record_run(RunPayload(project="bot", system_prompt="v one"))
    record_run(RunPayload(project="bot", system_prompt="v two"))
    record_run(RunPayload(project="bot", system_prompt="v one"))  # reuse v1
    with session_scope() as session:
        versions = {v.version: v.system_prompt for v in session.query(PromptVersion).all()}
        assert versions == {1: "v one", 2: "v two"}


def test_version_increments_are_per_project():
    with session_scope() as session:
        p1 = _get_or_create_project(session, "a")
        p2 = _get_or_create_project(session, "b")
        v1 = _get_or_create_version(session, p1, "prompt a")
        v2 = _get_or_create_version(session, p2, "prompt b")
        assert v1.version == 1
        assert v2.version == 1


def test_empty_system_prompt_has_no_version():
    run_id = record_run(RunPayload(project="bot", system_prompt=None, user_input="hi"))
    assert run_id is not None
    with session_scope() as session:
        assert session.query(PromptVersion).count() == 0
