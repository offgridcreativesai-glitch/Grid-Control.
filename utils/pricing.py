"""
Single source of truth for model pricing (USD per 1M tokens, May 2026).
Both agents/tracing.py and supabase/db.py import from here.
"""

# Short aliases → full Claude model names both resolve here
MODEL_COSTS: dict[str, dict[str, float]] = {
    # Short aliases (used by agents/tracing.py)
    "opus-4-6":                   {"input": 15.00, "output": 75.00},
    "sonnet-4-6":                 {"input": 3.00,  "output": 15.00},
    "haiku":                      {"input": 0.80,  "output": 4.00},
    # Full model names (used by supabase/db.py / Anthropic API responses)
    "claude-opus-4-6":            {"input": 15.00, "output": 75.00},
    "claude-sonnet-4-6":          {"input": 3.00,  "output": 15.00},
    "claude-haiku-4-5-20251001":  {"input": 0.80,  "output": 4.00},
}

DEFAULT_COSTS = {"input": 3.00, "output": 15.00}  # Sonnet fallback

# Non-LLM costs
FAL_COST_PER_IMAGE = 0.008
APIFY_COST_PER_RUN = 0.35


def estimate_cost(model: str, input_tokens: int, output_tokens: int) -> float:
    """Estimate USD cost for a single API call."""
    costs = MODEL_COSTS.get(model, DEFAULT_COSTS)
    return (input_tokens * costs["input"] + output_tokens * costs["output"]) / 1_000_000
