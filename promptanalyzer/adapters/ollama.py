"""Ollama adapter — supports both the native ``ollama`` client and its
OpenAI-compatible endpoint."""

from __future__ import annotations

from typing import Any

from ..normalize import NormalizedRecord
from .base import Adapter, _content_to_text, _get, extract_messages


class OllamaAdapter(Adapter):
    provider = "ollama"

    def matches(self, args: tuple[Any, ...], kwargs: dict[str, Any], result: Any) -> bool:
        module = getattr(type(result), "__module__", "") or ""
        if "ollama" in module:
            return True
        # Native ollama chat responses carry these fields.
        return bool(
            isinstance(result, dict)
            and "model" in result
            and ("eval_count" in result or "message" in result and "done" in result)
        )

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
        message = _get(result, "message")
        if message is not None:
            rec.response = _content_to_text(_get(message, "content"))
        else:
            rec.response = _get(result, "response")
        rec.input_tokens = _get(result, "prompt_eval_count")
        rec.output_tokens = _get(result, "eval_count")
        return rec
