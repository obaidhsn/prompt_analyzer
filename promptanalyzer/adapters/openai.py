"""OpenAI (and OpenAI-compatible) chat completions adapter."""

from __future__ import annotations

from typing import Any

from ..normalize import NormalizedRecord
from .base import Adapter, _content_to_text, _get, extract_messages


class OpenAIAdapter(Adapter):
    provider = "openai"

    # Class name fragments that identify an OpenAI-style response object.
    _result_markers: tuple[str, ...] = ("ChatCompletion", "Completion")
    _module_markers: tuple[str, ...] = ("openai",)

    def matches(self, args: tuple[Any, ...], kwargs: dict[str, Any], result: Any) -> bool:
        cls = type(result)
        module = getattr(cls, "__module__", "") or ""
        name = cls.__name__
        if any(m in module for m in self._module_markers):
            return True
        return bool(any(m in name for m in self._result_markers) and _get(result, "choices"))

    def from_call(self, args: tuple[Any, ...], kwargs: dict[str, Any]) -> NormalizedRecord:
        system, user = extract_messages(kwargs)
        return NormalizedRecord(
            provider=self.provider,
            model=kwargs.get("model"),
            system_prompt=system,
            user_prompt=user,
        )

    def from_response(self, result: Any) -> NormalizedRecord:
        rec = NormalizedRecord(provider=self.provider, model=_get(result, "model"))
        choices = _get(result, "choices")
        if isinstance(choices, list) and choices:
            first = choices[0]
            message = _get(first, "message")
            if message is not None:
                rec.response = _content_to_text(_get(message, "content"))
            else:  # legacy completion endpoint
                rec.response = _get(first, "text")
        usage = _get(result, "usage")
        if usage is not None:
            rec.input_tokens = _get(usage, "prompt_tokens", "input_tokens")
            rec.output_tokens = _get(usage, "completion_tokens", "output_tokens")
            rec.total_tokens = _get(usage, "total_tokens")
        return rec
