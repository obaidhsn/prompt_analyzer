"""Mistral adapter — OpenAI-compatible chat completions."""

from __future__ import annotations

from typing import Any

from .openai import OpenAIAdapter


class MistralAdapter(OpenAIAdapter):
    provider = "mistral"
    _module_markers = ("mistralai", "mistral")

    def matches(self, args: tuple[Any, ...], kwargs: dict[str, Any], result: Any) -> bool:
        module = getattr(type(result), "__module__", "") or ""
        return "mistral" in module
