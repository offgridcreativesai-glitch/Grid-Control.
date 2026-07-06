"""
agents/_lib/phases.py — GC proactive-program phase definitions.

WHY: post-onboarding gap (GRIDLOCK-PROGRAM-01JUL) — GC has all 18 agents but no
"named phase" that scopes which ones run and at what content:ads ratio. Real
agencies flip the mix as a brand grows (docs/AGENCY_OPERATING_MODEL_RESEARCH.md
§3): content supports ads at launch, ads support content at scale.

Generic + brand-agnostic. Every value here is a phase-level default keyed only
by phase name — never by brand_slug. Per-brand state (which phase a brand is
actually in) lives in brands/<slug>/brand_profile.json ("phase" field) and
_state.json; this module only defines what each phase means.

Agent slugs match agents/_lib/model_gateway.AGENT_ROUTING (single source of
truth for the agent roster).
"""
from __future__ import annotations

PHASES: tuple[str, ...] = ("foundation", "launch", "growth", "scale")
DEFAULT_PHASE = "launch"

# docs/AGENCY_OPERATING_MODEL_RESEARCH.md §3 table:
#   Pre-launch -> foundation, Launch -> launch, Growth -> growth, Scale -> scale
PHASE_PLANS: dict[str, dict] = {
    "foundation": {
        "label": "Foundation",
        "monthly_rev_range": "₹0",
        "goal": "Test messaging, build initial awareness",
        "content_ads_ratio": None,  # no paid budget yet
        "weekly_volume": {"long_form": 1, "social": 3, "creator_seeds": 0},
        "active_agents": [
            "brand-guardian", "strategy-agent", "content-planner", "script-writer",
            "trend-researcher", "trend-sentinel", "performance-tracker",
        ],
    },
    "launch": {
        "label": "Launch",
        "monthly_rev_range": "₹0–25L",
        "goal": "Organic traction + social proof",
        "content_ads_ratio": "75:25",  # midpoint of researched 70-80:20-30
        "weekly_volume": {"long_form": 2, "social": 5, "creator_seeds": 10},
        "active_agents": [
            "brand-guardian", "strategy-agent", "content-planner", "script-writer",
            "creative-director", "trend-researcher", "trend-sentinel",
            "data-analyst", "performance-tracker", "community-manager",
        ],
    },
    "growth": {
        "label": "Growth",
        "monthly_rev_range": "₹25L–1Cr",
        "goal": "20% organic traffic, 20%+ email revenue",
        "content_ads_ratio": "55:45",
        "weekly_volume": {"long_form": 3, "social": 7, "creator_seeds": 40},
        "active_agents": [
            "brand-guardian", "strategy-agent", "content-planner", "script-writer",
            "creative-director", "ad-strategist", "trend-researcher", "trend-sentinel",
            "data-analyst", "performance-tracker", "funnel-specialist",
            "email-marketing-agent", "community-manager", "dm-customer-hunter",
            "seo-aeo-agent",
        ],
    },
    "scale": {
        "label": "Scale",
        "monthly_rev_range": "₹1Cr+",
        "goal": "30%+ revenue from owned channels",
        "content_ads_ratio": "40:60",
        "weekly_volume": {"long_form": 5, "social": 7, "creator_seeds": 100},
        "active_agents": [
            "ceo-brain", "brand-guardian", "strategy-agent", "content-planner",
            "script-writer", "creative-director", "ad-strategist", "data-analyst",
            "funnel-specialist", "trend-researcher", "website-agent", "seo-aeo-agent",
            "email-marketing-agent", "community-manager", "dm-customer-hunter",
            "carousel-designer", "trend-sentinel", "performance-tracker",
        ],
    },
}


def is_valid_phase(phase: str | None) -> bool:
    return phase in PHASES


def normalize_phase(phase: str | None) -> str:
    """Coerce any input into a valid phase, defaulting to DEFAULT_PHASE when
    missing or unrecognized (e.g. a brand's old free-text 'phase' description)."""
    p = (phase or "").strip().lower()
    return p if p in PHASES else DEFAULT_PHASE


def get_phase_plan(phase: str | None) -> dict:
    """Return the phase-plan profile for `phase`, falling back to DEFAULT_PHASE."""
    return PHASE_PLANS[normalize_phase(phase)]
