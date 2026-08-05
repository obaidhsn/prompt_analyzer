"""Anthropic Claude Messages API adapter."""

from __future__ import annotations

from typing import Any

from ..normalize import NormalizedRecord
from .base import Adapter, _content_to_text, _get, extract_messages


class AnthropicAdapter(Adapter):
    provider = "anthropic"

    def matches(self, args: tuple[Any, ...], kwargs: dict[str, Any], result: Any) -> bool:
        cls = type(result)
        module = getattr(cls, "__module__", "") or ""
        if "anthropic" in module:
            return True
        # Anthropic messages have type == "message" and a content block list.
        return bool(_get(result, "type") == "message" and isinstance(_get(result, "content"), list))

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
        content = _get(result, "content")
        rec.response = _content_to_text(content)
        usage = _get(result, "usage")
        if usage is not None:
            rec.input_tokens = _get(usage, "input_tokens")
            rec.output_tokens = _get(usage, "output_tokens")
        return rec
