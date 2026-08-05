"""Best-effort token cost estimation.

Prices are expressed in USD per 1,000 tokens and are intentionally easy to
override or extend. Unknown models fall back to ``0.0`` cost rather than raising.
Values are approximate and can be refreshed without touching call sites.
"""

from __future__ import annotations

__all__ = ["estimate_cost", "PRICES", "register_price"]

# (input_per_1k, output_per_1k) in USD. Prefix matching is used so that dated
# model variants (e.g. ``gpt-4o-2024-08-06``) resolve to their base price.
PRICES: dict[str, tuple[float, float]] = {
    # OpenAI
    "gpt-4o-mini": (0.00015, 0.00060),
    "gpt-4o": (0.00250, 0.01000),
    "gpt-4-turbo": (0.01000, 0.03000),
    "gpt-4": (0.03000, 0.06000),
    "gpt-3.5-turbo": (0.00050, 0.00150),
    "o1-mini": (0.00110, 0.00440),
    "o1": (0.01500, 0.06000),
    "gpt-5": (0.00500, 0.01500),
    # Anthropic
    "claude-3-5-sonnet": (0.00300, 0.01500),
    "claude-3-5-haiku": (0.00080, 0.00400),
    "claude-3-opus": (0.01500, 0.07500),
    "claude-3-sonnet": (0.00300, 0.01500),
    "claude-3-haiku": (0.00025, 0.00125),
    "claude-sonnet-4": (0.00300, 0.01500),
    "claude-opus-4": (0.01500, 0.07500),
    # Google
    "gemini-1.5-pro": (0.00125, 0.00500),
    "gemini-1.5-flash": (0.00007, 0.00030),
    "gemini-2.0-flash": (0.00010, 0.00040),
    "gemini-2.5-pro": (0.00125, 0.01000),
    # Mistral
    "mistral-large": (0.00200, 0.00600),
    "mistral-small": (0.00020, 0.00060),
    # Groq (Llama)
    "llama-3.1-70b": (0.00059, 0.00079),
    "llama-3.1-8b": (0.00005, 0.00008),
    # Local / open — free to run
    "ollama": (0.0, 0.0),
    "vllm": (0.0, 0.0),
}


def register_price(model_prefix: str, input_per_1k: float, output_per_1k: float) -> None:
    """Register or override the price for a model prefix at runtime."""
    PRICES[model_prefix.lower()] = (input_per_1k, output_per_1k)


def _lookup(model: str | None) -> tuple[float, float] | None:
    if not model:
        return None
    key = model.lower()
    if key in PRICES:
        return PRICES[key]
    # Longest-prefix match so "gpt-4o-2024-..." beats "gpt-4".
    best: tuple[str, tuple[float, float]] | None = None
    for prefix, price in PRICES.items():
        if key.startswith(prefix) and (best is None or len(prefix) > len(best[0])):
            best = (prefix, price)
    return best[1] if best else None


def estimate_cost(
    model: str | None, input_tokens: int | None, output_tokens: int | None
) -> float | None:
    """Estimate USD cost for a run. Returns ``None`` when the model is unknown."""
    price = _lookup(model)
    if price is None:
        return None
    in_rate, out_rate = price
    cost = (input_tokens or 0) / 1000 * in_rate + (output_tokens or 0) / 1000 * out_rate
    return round(cost, 8)
