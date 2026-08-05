"""Google Gemini adapter (google-generativeai / google-genai)."""

from __future__ import annotations

from typing import Any

from ..normalize import NormalizedRecord
from .base import Adapter, _get


class GoogleAdapter(Adapter):
    provider = "google"

    def matches(self, args: tuple[Any, ...], kwargs: dict[str, Any], result: Any) -> bool:
        cls = type(result)
        module = getattr(cls, "__module__", "") or ""
        if "google" in module and ("genai" in module or "generativeai" in module):
            return True
        # GenerateContentResponse exposes .candidates and .text.
        return bool(_get(result, "candidates") is not None and hasattr(result, "text"))

    def from_call(self, args: tuple[Any, ...], kwargs: dict[str, Any]) -> NormalizedRecord:
        system = kwargs.get("system_instruction") or kwargs.get("system")
        user = kwargs.get("contents") or kwargs.get("prompt")
        if isinstance(user, list):
            user = "\n".join(str(u) for u in user)
        return NormalizedRecord(
            provider=self.provider,
            model=kwargs.get("model"),
            system_prompt=system if isinstance(system, str) else None,
            user_prompt=str(user) if user is not None else None,
        )

    def from_response(self, result: Any) -> NormalizedRecord:
        rec = NormalizedRecord(provider=self.provider, model=_get(result, "model_version"))
        text = _get(result, "text")
        if isinstance(text, str):
            rec.response = text
        usage = _get(result, "usage_metadata")
        if usage is not None:
            rec.input_tokens = _get(usage, "prompt_token_count")
            rec.output_tokens = _get(usage, "candidates_token_count")
            rec.total_tokens = _get(usage, "total_token_count")
        return rec
