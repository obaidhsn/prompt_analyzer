"""Adapter interface and shared extraction helpers.

An *adapter* knows how to read a specific provider's request arguments and
response object and turn them into a :class:`~promptanalyzer.normalize.NormalizedRecord`.
Adapters are deliberately defensive: any extraction failure returns ``None`` for
that field rather than raising.
"""

from __future__ import annotations

from typing import Any

from ..normalize import NormalizedRecord

__all__ = ["Adapter", "extract_messages"]


class Adapter:
    """Base class for provider adapters.

    Subclasses set :attr:`provider` and implement :meth:`matches`,
    :meth:`from_call` and :meth:`from_response`.
    """

    provider: str = "generic"

    def matches(self, args: tuple[Any, ...], kwargs: dict[str, Any], result: Any) -> bool:
        """Return ``True`` if this adapter recognises the call/result."""
        return False

    def from_call(self, args: tuple[Any, ...], kwargs: dict[str, Any]) -> NormalizedRecord:
        """Extract system/user prompts and the model from call arguments."""
        return NormalizedRecord(provider=self.provider)

    def from_response(self, result: Any) -> NormalizedRecord:
        """Extract the response text and token usage from the result object."""
        return NormalizedRecord(provider=self.provider)


def _get(obj: Any, *names: str) -> Any:
    """Return the first present attribute or mapping key from ``names``."""
    for name in names:
        if isinstance(obj, dict) and name in obj:
            return obj[name]
        if hasattr(obj, name):
            return getattr(obj, name)
    return None


def extract_messages(
    kwargs: dict[str, Any],
) -> tuple[str | None, str | None]:
    """Extract (system_prompt, last_user_prompt) from a chat ``messages`` list.

    Works for the OpenAI-style ``messages=[{"role": ..., "content": ...}]``
    convention shared by most providers. Falls back to top-level ``system`` /
    ``prompt`` keys when no message list is present.
    """
    messages = kwargs.get("messages")
    system = kwargs.get("system")
    user: str | None = None

    if isinstance(messages, list):
        for msg in messages:
            role = _get(msg, "role")
            content = _content_to_text(_get(msg, "content"))
            if role == "system" and content:
                system = content if system is None else system
            elif role == "user" and content:
                user = content  # keep last user message
    if user is None:
        prompt = kwargs.get("prompt") or kwargs.get("input") or kwargs.get("query")
        if isinstance(prompt, str):
            user = prompt
    if isinstance(system, list):
        system = _content_to_text(system)
    return system, user


def _content_to_text(content: Any) -> str | None:
    """Flatten a message ``content`` value (str or list of parts) to text."""
    if content is None:
        return None
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts: list[str] = []
        for part in content:
            if isinstance(part, str):
                parts.append(part)
            else:
                text = _get(part, "text", "content")
                if isinstance(text, str):
                    parts.append(text)
        return "\n".join(parts) if parts else None
    text = _get(content, "text")
    return text if isinstance(text, str) else None
