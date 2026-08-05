"""Generic / custom adapter driven by user-supplied extractor callables.

This is the escape hatch that lets *any* Python LLM library integrate:

    @track(
        name="custom-model",
        system=lambda args, kwargs: kwargs["system"],
        user=lambda args, kwargs: kwargs["prompt"],
        response=lambda result: result,
    )
    def my_llm():
        ...

Each extractor is optional and defensively invoked — a raising extractor simply
yields ``None`` for that field.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from ..logging_utils import debug
from ..normalize import NormalizedRecord
from .base import Adapter, _content_to_text, _get, extract_messages
from .openai import OpenAIAdapter

SystemExtractor = Callable[[tuple[Any, ...], dict[str, Any]], Any]
UserExtractor = Callable[[tuple[Any, ...], dict[str, Any]], Any]
ResponseExtractor = Callable[[Any], Any]
ModelExtractor = Callable[[tuple[Any, ...], dict[str, Any], Any], Any]


def _safe(fn: Callable[..., Any] | None, *call_args: Any) -> Any:
    if fn is None:
        return None
    try:
        return fn(*call_args)
    except Exception as exc:  # never let a user extractor break tracking
        debug("generic extractor failed: %s", exc)
        return None


class GenericAdapter(Adapter):
    """Adapter built from user-provided extractor callables.

    Any field left unspecified falls back to best-effort OpenAI-style extraction
    so partial configuration still yields useful data.
    """

    provider = "custom"

    def __init__(
        self,
        *,
        provider: str | None = None,
        system: SystemExtractor | None = None,
        user: UserExtractor | None = None,
        response: ResponseExtractor | None = None,
        model: ModelExtractor | None = None,
    ) -> None:
        self.provider = provider or "custom"
        self._system = system
        self._user = user
        self._response = response
        self._model = model
        self._fallback = OpenAIAdapter()

    def matches(self, args: tuple[Any, ...], kwargs: dict[str, Any], result: Any) -> bool:
        return True

    def from_call(self, args: tuple[Any, ...], kwargs: dict[str, Any]) -> NormalizedRecord:
        system = _safe(self._system, args, kwargs)
        user = _safe(self._user, args, kwargs)
        model = _safe(self._model, args, kwargs, None)
        if system is None or user is None:
            fb_system, fb_user = extract_messages(kwargs)
            system = system if system is not None else fb_system
            user = user if user is not None else fb_user
        if model is None:
            model = kwargs.get("model")
        return NormalizedRecord(
            provider=self.provider,
            model=model if isinstance(model, str) else None,
            system_prompt=_to_text(system),
            user_prompt=_to_text(user),
        )

    def from_response(self, result: Any) -> NormalizedRecord:
        rec = NormalizedRecord(provider=self.provider)
        if self._response is not None:
            rec.response = _to_text(_safe(self._response, result))
        # Try to enrich with token usage from a structured result.
        usage = _get(result, "usage")
        if usage is not None:
            rec.input_tokens = _get(usage, "prompt_tokens", "input_tokens")
            rec.output_tokens = _get(usage, "completion_tokens", "output_tokens")
            rec.total_tokens = _get(usage, "total_tokens")
        if rec.response is None:
            rec.response = _content_to_text(result) or (result if isinstance(result, str) else None)
        if not isinstance(rec.response, str):
            rec.response = None
        return rec


def _to_text(value: Any) -> str | None:
    if value is None:
        return None
    if isinstance(value, str):
        return value
    return _content_to_text(value)
