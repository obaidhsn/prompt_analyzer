"""LiteLLM adapter.

LiteLLM normalizes every provider to the OpenAI response schema, so the OpenAI
extraction logic applies directly. The provider label is taken from the model
namespace when present.
"""

from __future__ import annotations

from typing import Any

from ..normalize import NormalizedRecord
from .openai import OpenAIAdapter


class LiteLLMAdapter(OpenAIAdapter):
    provider = "litellm"

    def matches(self, args: tuple[Any, ...], kwargs: dict[str, Any], result: Any) -> bool:
        module = getattr(type(result), "__module__", "") or ""
        return "litellm" in module

    def from_response(self, result: Any) -> NormalizedRecord:
        rec = super().from_response(result)
        rec.provider = self.provider
        return rec
