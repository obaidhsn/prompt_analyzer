"""The normalized inference record shared by every adapter.

All provider-specific responses are converted into a :class:`NormalizedRecord`.
The rest of the system (versioning, storage, dashboard) only ever sees this
shape, keeping the core provider-agnostic.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

__all__ = ["NormalizedRecord"]


@dataclass
class NormalizedRecord:
    """Provider-agnostic representation of a single LLM inference."""

    provider: str | None = None
    model: str | None = None
    system_prompt: str | None = None
    user_prompt: str | None = None
    response: str | None = None
    input_tokens: int | None = None
    output_tokens: int | None = None
    total_tokens: int | None = None
    latency_ms: float | None = None
    cost: float | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def merge(self, other: NormalizedRecord) -> None:
        """Fill in any missing fields on ``self`` from ``other`` (non-destructive)."""
        for f in (
            "provider",
            "model",
            "system_prompt",
            "user_prompt",
            "response",
            "input_tokens",
            "output_tokens",
            "total_tokens",
            "latency_ms",
            "cost",
        ):
            if getattr(self, f) in (None, "") and getattr(other, f) not in (None, ""):
                setattr(self, f, getattr(other, f))
        for key, value in other.metadata.items():
            self.metadata.setdefault(key, value)

    def finalize(self) -> None:
        """Derive ``total_tokens`` when the provider only gave the split."""
        if self.total_tokens is None and (
            self.input_tokens is not None or self.output_tokens is not None
        ):
            self.total_tokens = (self.input_tokens or 0) + (self.output_tokens or 0)
