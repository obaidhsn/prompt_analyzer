"""Adapter registry and auto-detection.

The registry maps provider names to adapter instances and provides
:func:`detect_adapter`, which picks the best adapter for a given call/result
when the user did not specify one explicitly.
"""

from __future__ import annotations

from typing import Any

from .anthropic import AnthropicAdapter
from .azure import AzureAdapter
from .base import Adapter
from .generic import GenericAdapter
from .google import GoogleAdapter
from .groq import GroqAdapter
from .litellm import LiteLLMAdapter
from .mistral import MistralAdapter
from .ollama import OllamaAdapter
from .openai import OpenAIAdapter
from .openrouter import OpenRouterAdapter
from .vllm import VLLMAdapter

__all__ = [
    "Adapter",
    "GenericAdapter",
    "get_adapter",
    "detect_adapter",
    "REGISTRY",
]

# Instantiate the stateless adapters once.
REGISTRY: dict[str, Adapter] = {
    "openai": OpenAIAdapter(),
    "anthropic": AnthropicAdapter(),
    "google": GoogleAdapter(),
    "gemini": GoogleAdapter(),
    "ollama": OllamaAdapter(),
    "litellm": LiteLLMAdapter(),
    "vllm": VLLMAdapter(),
    "openrouter": OpenRouterAdapter(),
    "groq": GroqAdapter(),
    "mistral": MistralAdapter(),
    "azure": AzureAdapter(),
    "generic": GenericAdapter(),
}

# Detection order: most specific providers first, OpenAI last (it is the
# broadest OpenAI-shaped matcher). OpenRouter/vLLM/Azure are only auto-picked
# when their narrow signals fire.
_DETECTION_ORDER: tuple[str, ...] = (
    "anthropic",
    "google",
    "ollama",
    "litellm",
    "groq",
    "mistral",
    "azure",
    "openrouter",
    "openai",
)


def get_adapter(name: str) -> Adapter | None:
    """Return the registered adapter for ``name`` (case-insensitive)."""
    return REGISTRY.get(name.lower()) if name else None


def detect_adapter(args: tuple[Any, ...], kwargs: dict[str, Any], result: Any) -> Adapter:
    """Return the best-matching adapter, defaulting to the OpenAI adapter."""
    for name in _DETECTION_ORDER:
        adapter = REGISTRY[name]
        try:
            if adapter.matches(args, kwargs, result):
                return adapter
        except Exception:  # a defensive matcher should never break detection
            continue
    return REGISTRY["openai"]
