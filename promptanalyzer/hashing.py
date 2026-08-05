"""Deterministic hashing used by the prompt-versioning system."""

from __future__ import annotations

import hashlib

__all__ = ["prompt_hash", "normalize_prompt"]


def normalize_prompt(text: str | None) -> str:
    """Normalize a system prompt before hashing.

    Trailing whitespace on each line and surrounding blank lines are stripped so
    that cosmetically-identical prompts collapse to the same version, while
    meaningful edits produce a new hash.
    """
    if not text:
        return ""
    lines = [line.rstrip() for line in text.replace("\r\n", "\n").split("\n")]
    return "\n".join(lines).strip()


def prompt_hash(text: str | None) -> str:
    """Return the SHA-256 hex digest of the normalized prompt text."""
    normalized = normalize_prompt(text)
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()
