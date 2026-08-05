"""Azure OpenAI adapter — same response shape as OpenAI."""

from __future__ import annotations

from typing import Any

from .openai import OpenAIAdapter


class AzureAdapter(OpenAIAdapter):
    provider = "azure"

    def matches(self, args: tuple[Any, ...], kwargs: dict[str, Any], result: Any) -> bool:
        module = getattr(type(result), "__module__", "") or ""
        # AzureOpenAI client lives in the openai package; distinguished by the
        # deployment-style kwargs. Selected explicitly via provider="azure".
        return "azure" in module
