"""OpenRouter adapter.

OpenRouter is accessed through the OpenAI SDK pointed at ``openrouter.ai``, so
the response shape is identical to OpenAI. Detection is by base URL when it is
discoverable, otherwise this adapter is selected explicitly via ``provider=``.
"""

from __future__ import annotations

from typing import Any

from .openai import OpenAIAdapter


class OpenRouterAdapter(OpenAIAdapter):
    provider = "openrouter"

    def matches(self, args: tuple[Any, ...], kwargs: dict[str, Any], result: Any) -> bool:
        model = kwargs.get("model")
        # OpenRouter models are namespaced, e.g. "anthropic/claude-3.5-sonnet".
        return isinstance(model, str) and "/" in model
