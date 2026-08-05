"""Tests for automatic client instrumentation.

These simulate the real-world pattern the plain decorator can't see: the LLM
request is built *inside* the function and the function returns only the answer
text. Instrumentation must still capture prompts, model, tokens and cost.
"""

from __future__ import annotations

from types import SimpleNamespace

from promptanalyzer import track
from promptanalyzer.db import session_scope
from promptanalyzer.instrument import instrument_method
from promptanalyzer.models import PromptVersion, Run
from promptanalyzer.storage import get_writer


def _flush():
    get_writer().flush(timeout=5.0)


class FakeCompletions:
    """Stands in for openai ...chat.completions.Completions."""

    def create(self, *, model, messages):  # noqa: A002 - mirror the real signature
        return SimpleNamespace(
            model=model,
            choices=[SimpleNamespace(message=SimpleNamespace(content="Reset it in Settings."))],
            usage=SimpleNamespace(prompt_tokens=42, completion_tokens=8, total_tokens=50),
        )


def test_instrumented_call_is_captured_even_when_returning_content_string():
    # Instrument the fake client exactly like install_all() would for openai.
    instrument_method(FakeCompletions, "create", "openai")
    client = SimpleNamespace(chat=SimpleNamespace(completions=FakeCompletions()))

    @track("customer-support")
    def answer(question: str) -> str:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are a friendly support agent."},
                {"role": "user", "content": question},
            ],
        )
        return response.choices[0].message.content  # returns a STRING, like the example

    out = answer("How do I reset my password?")
    assert out == "Reset it in Settings."
    _flush()

    with session_scope() as session:
        run = session.query(Run).one()
        # response text, model, tokens and cost are all captured
        assert run.response == "Reset it in Settings."
        assert run.model == "gpt-4o-mini"
        assert run.provider == "openai"
        assert run.input_tokens == 42
        assert run.output_tokens == 8
        assert run.total_tokens == 50
        assert run.cost is not None and run.cost > 0
        # prompts are captured from the intercepted request
        assert run.system_prompt == "You are a friendly support agent."
        assert run.user_input == "How do I reset my password?"
        # and the system prompt was versioned
        assert session.query(PromptVersion).count() == 1


def test_no_capture_falls_back_to_return_value():
    # A function that returns the response object directly still works with no
    # instrumentation in play.
    @track("direct")
    def call():
        return SimpleNamespace(
            model="gpt-4o-mini",
            choices=[SimpleNamespace(message=SimpleNamespace(content="hi"))],
            usage=SimpleNamespace(prompt_tokens=1, completion_tokens=1, total_tokens=2),
        )

    call()
    _flush()
    with session_scope() as session:
        run = session.query(Run).one()
        assert run.response == "hi"
        assert run.total_tokens == 2
