"""
agents/model_gateway.py — SINGLE SOURCE OF TRUTH for agent → model + effort.

Phase D (DASHBOARD_V2_BUILD_PLAN, Jun 9 2026). Kills the drift between the
hardcoded MODEL constants in agents/*.py and managed_agents/registry.json:
every agent sources its model from here instead of hardcoding a string.

Two Claude tiers + pure-math. NO Haiku, NO Ollama — Sonnet 4.6 is the floor
(decided Jun 9 2026; high-volume grunt accepts ~3x a Haiku tier for quality
consistency).

  tier "opus"   → claude-opus-4-8    (creative / decisions)
  tier "sonnet" → claude-sonnet-4-6  (floor — everything else with an LLM)
  tier "none"   → pure-math agents   (no LLM at all)

`complete()` is the go-forward call path: it wraps LiteLLM (the multi-provider
future — GPT/Gemini/Grok later) with an Anthropic-SDK fallback, and reports
per-call cost via cost_reporter so spend feeds Phase B. Existing agents keep
their tuned anthropic streaming call-sites; they only source MODEL from here.
"""
import os
import re
from typing import Optional

# ── Tier → concrete model id ──────────────────────────────────────────────────
MODELS = {
    "opus":   "claude-opus-4-8",
    "sonnet": "claude-sonnet-4-6",
}

# ── Single source of truth: agent_slug → (tier, effort) ───────────────────────
# effort is the intended reasoning level (xhigh|high|medium). It is recorded
# here and exposed via effort_for(); complete() can translate it to an
# extended-thinking budget when an agent opts in (use_thinking=True).
AGENT_ROUTING: dict[str, tuple[str, str]] = {
    # Opus 4.8 — creative / decisions
    "ceo-brain":             ("opus",   "xhigh"),
    "strategy-agent":        ("opus",   "high"),
    "script-writer":         ("opus",   "high"),
    "creative-director":     ("opus",   "medium"),
    "ad-strategist":         ("opus",   "high"),
    "brand-guardian":        ("opus",   "high"),
    "brand-book":            ("opus",   "xhigh"),  # Phase G — heavy multi-section report gen

    # Sonnet 4.6 — floor (everything else with an LLM)
    "content-planner":       ("sonnet", "medium"),
    "carousel-designer":     ("sonnet", "medium"),
    "data-analyst":          ("sonnet", "medium"),
    "funnel-specialist":     ("sonnet", "medium"),
    "trend-researcher":      ("sonnet", "medium"),
    "website-agent":         ("sonnet", "medium"),
    "seo-aeo-agent":         ("sonnet", "medium"),
    "email-marketing-agent": ("sonnet", "medium"),
    "community-manager":     ("sonnet", "medium"),
    "dm-customer-hunter":    ("sonnet", "medium"),

    # None — pure-math / template, no LLM
    "trend-sentinel":        ("none",   "none"),
    "performance-tracker":   ("none",   "none"),
    "cost-tracker":          ("none",   "none"),
}

# effort → extended-thinking budget tokens (Anthropic API). 0 = thinking off.
EFFORT_THINKING_BUDGET = {
    "xhigh":  8000,
    "high":   4000,
    "medium": 0,      # floor agents run without extended thinking
    "low":    0,
    "none":   0,
}

# Default tier for an unknown agent = the floor (never silently use Opus).
_DEFAULT = ("sonnet", "medium")


def _slugify(agent: str) -> str:
    """Normalize a display name OR slug to the canonical kebab slug.
    'CEO Brain' -> 'ceo-brain', 'DM+Customer Hunter' -> 'dmcustomer-hunter'?
    To stay aligned with base_agent._agent_slug, mirror its exact transform."""
    return re.sub(r"[^a-z0-9-]", "", agent.lower().replace(" ", "-"))


# Display-name aliases whose slugified form does not match AGENT_ROUTING keys.
_ALIASES = {
    "dmcustomer-hunter":   "dm-customer-hunter",
    "dm-customerhunter":   "dm-customer-hunter",
    "seoaeo-agent":        "seo-aeo-agent",
    "seo-aeoagent":        "seo-aeo-agent",
    "cost-tracker":        "cost-tracker",
    "ceo-brain-review":    "ceo-brain",
}


def _canonical(agent: str) -> str:
    slug = _slugify(agent)
    return _ALIASES.get(slug, slug)


def config_for(agent: str) -> dict:
    """Return the full routing config for an agent (slug or display name)."""
    slug = _canonical(agent)
    tier, effort = AGENT_ROUTING.get(slug, _DEFAULT)
    return {
        "slug": slug,
        "tier": tier,
        "effort": effort,
        "model": MODELS.get(tier),                       # None for pure-math
        "thinking_budget": EFFORT_THINKING_BUDGET.get(effort, 0),
    }


def model_for(agent: str) -> Optional[str]:
    """Return the concrete model id for an agent. None for pure-math agents."""
    return config_for(agent)["model"]


def effort_for(agent: str) -> str:
    """Return the intended effort level for an agent."""
    return config_for(agent)["effort"]


def is_pure_math(agent: str) -> bool:
    """True when the agent uses no LLM (decision_engine = pure_math)."""
    return config_for(agent)["tier"] == "none"


# ── Go-forward unified call path ──────────────────────────────────────────────

def complete(
    agent: str,
    messages: list[dict],
    system: Optional[str] = None,
    max_tokens: int = 4096,
    temperature: float = 1.0,
    use_thinking: bool = False,
    report_cost: bool = True,
) -> dict:
    """Run a completion for `agent` using its routed model.

    LiteLLM-first (multi-provider future), Anthropic-SDK fallback. Returns
    {text, input_tokens, output_tokens, model}. Reports cost via cost_reporter
    (which reads GRID_RUN_ID) unless report_cost=False.

    NB: existing agents keep their own tuned anthropic streaming call-sites;
    this is for new code (Wave 2 F1–F4) and anything wanting central cost
    capture without re-implementing the client.
    """
    cfg = config_for(agent)
    model = cfg["model"]
    if model is None:
        raise ValueError(f"Agent '{agent}' is pure-math (no LLM). Do not call complete().")

    thinking_budget = cfg["thinking_budget"] if use_thinking else 0
    text, in_tok, out_tok = "", 0, 0

    # 1) LiteLLM path
    try:
        import litellm  # noqa
        lm_messages = []
        if system:
            lm_messages.append({"role": "system", "content": system})
        lm_messages.extend(messages)
        kwargs: dict = {
            "model": f"anthropic/{model}",
            "messages": lm_messages,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "api_key": os.getenv("ANTHROPIC_API_KEY"),
        }
        if thinking_budget:
            kwargs["thinking"] = {"type": "enabled", "budget_tokens": thinking_budget}
        resp = litellm.completion(**kwargs)
        text = resp.choices[0].message.content or ""
        usage = getattr(resp, "usage", None)
        if usage:
            in_tok = getattr(usage, "prompt_tokens", 0) or 0
            out_tok = getattr(usage, "completion_tokens", 0) or 0
    except ImportError:
        # 2) Anthropic SDK fallback
        import anthropic
        client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
        create_kwargs: dict = {
            "model": model,
            "max_tokens": max_tokens,
            "messages": messages,
        }
        if system:
            create_kwargs["system"] = system
        if thinking_budget:
            create_kwargs["thinking"] = {"type": "enabled", "budget_tokens": thinking_budget}
        resp = client.messages.create(**create_kwargs)
        text = "".join(
            block.text for block in resp.content if getattr(block, "type", "") == "text"
        )
        in_tok = resp.usage.input_tokens
        out_tok = resp.usage.output_tokens

    if report_cost:
        try:
            from agents._lib import cost_reporter

            cost_reporter.record(model, in_tok, out_tok)
        except Exception:
            pass

    return {"text": text, "input_tokens": in_tok, "output_tokens": out_tok, "model": model}


if __name__ == "__main__":
    # Quick self-check of the routing table.
    print("agent_slug                tier     effort   model")
    print("-" * 64)
    for slug in AGENT_ROUTING:
        c = config_for(slug)
        print(f"{slug:24} {c['tier']:8} {c['effort']:8} {c['model'] or '(none)'}")
