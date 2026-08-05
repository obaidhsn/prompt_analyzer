"""Groq adapter — OpenAI-compatible chat completions."""

from __future__ import annotations

from typing import Any

from .openai import OpenAIAdapter


class GroqAdapter(OpenAIAdapter):
    provider = "groq"
    _module_markers = ("groq",)

    def matches(self, args: tuple[Any, ...], kwargs: dict[str, Any], result: Any) -> bool:
        module = getattr(type(result), "__module__", "") or ""
        return "groq" in module
