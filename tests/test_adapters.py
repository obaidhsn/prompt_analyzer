"""Unit tests for provider adapters and auto-detection."""

from __future__ import annotations

from types import SimpleNamespace

from promptanalyzer.adapters import detect_adapter, get_adapter
from promptanalyzer.adapters.generic import GenericAdapter


def _openai_response():
    return SimpleNamespace(
        model="gpt-4o-mini",
        choices=[SimpleNamespace(message=SimpleNamespace(content="Hello!"))],
        usage=SimpleNamespace(prompt_tokens=10, completion_tokens=5, total_tokens=15),
    )


def _anthropic_response():
    return SimpleNamespace(
        type="message",
        model="claude-3-5-sonnet-20241022",
        content=[SimpleNamespace(text="Hi there", type="text")],
        usage=SimpleNamespace(input_tokens=12, output_tokens=8),
    )


def test_openai_adapter_extracts_response_and_usage():
    adapter = get_adapter("openai")
    kwargs = {
        "model": "gpt-4o-mini",
        "messages": [
            {"role": "system", "content": "You are helpful."},
            {"role": "user", "content": "Hi"},
        ],
    }
    call = adapter.from_call((), kwargs)
    resp = adapter.from_response(_openai_response())
    assert call.system_prompt == "You are helpful."
    assert call.user_prompt == "Hi"
    assert resp.response == "Hello!"
    assert resp.input_tokens == 10
    assert resp.output_tokens == 5


def test_anthropic_detection_and_extraction():
    result = _anthropic_response()
    adapter = detect_adapter((), {"model": "claude-3-5-sonnet"}, result)
    assert adapter.provider == "anthropic"
    resp = adapter.from_response(result)
    assert resp.response == "Hi there"
    assert resp.input_tokens == 12
    assert resp.output_tokens == 8


def test_detect_defaults_to_openai():
    adapter = detect_adapter((), {}, _openai_response())
    assert adapter.provider == "openai"


def test_generic_adapter_uses_extractors():
    adapter = GenericAdapter(
        provider="custom",
        system=lambda a, k: k["system"],
        user=lambda a, k: k["prompt"],
        response=lambda r: r["text"],
    )
    call = adapter.from_call((), {"system": "S", "prompt": "U"})
    resp = adapter.from_response({"text": "R"})
    assert call.system_prompt == "S"
    assert call.user_prompt == "U"
    assert resp.response == "R"


def test_generic_extractor_failure_is_swallowed():
    adapter = GenericAdapter(system=lambda a, k: k["missing"])  # KeyError inside
    call = adapter.from_call((), {})
    assert call.system_prompt is None  # no crash
