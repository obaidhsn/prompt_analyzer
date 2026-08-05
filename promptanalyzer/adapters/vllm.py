"""vLLM adapter — served through an OpenAI-compatible API."""

from __future__ import annotations

from typing import Any

from .openai import OpenAIAdapter


class VLLMAdapter(OpenAIAdapter):
    provider = "vllm"

    def matches(self, args: tuple[Any, ...], kwargs: dict[str, Any], result: Any) -> bool:
        # vLLM is OpenAI-shaped; selected explicitly via provider="vllm".
        return False
