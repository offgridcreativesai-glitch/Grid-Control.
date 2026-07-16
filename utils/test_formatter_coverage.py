"""Pins the NO-RAW-JSON rule mechanically (regressed 3+ times, worst on Jul 14:
brand-book fell to the generic key-dumper and the vault showed `Meta: Brand: Slug:...`).

Enforces two things:
1. EVERY agent in the roster has a dedicated format_for_notion branch — none may
   fall to the generic `## <name> Output` key-dump. Both the display name (Supabase
   path) and the pending_approval folder slug (disk path) must resolve.
2. Formatted output is human markdown: no raw JSON syntax, and for realistic
   payloads the human narrative text actually appears.

ADDING A NEW AGENT? Add its name+slug here AND its formatter branch in the same
commit — this test is what makes forgetting impossible.

Run: `python3 utils/test_formatter_coverage.py` or pytest.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from utils.output_formatter import format_for_notion

# (display name as stored in Supabase / AGENTS, folder slug on disk).
# ceo-brain is the orchestrator/saver — it never writes a vault folder of its own.
ROSTER = [
    ("Strategy Agent", "strategy-agent"),
    ("Content Planner", "content-planner"),
    ("Script Writer", "script-writer"),
    ("Creative Director", "creative-director"),
    ("Ad Strategist", "ad-strategist"),
    ("Data Analyst", "data-analyst"),
    ("Funnel Specialist", "funnel-specialist"),
    ("Trend Researcher", "trend-researcher"),
    ("Website Agent", "website-agent"),
    ("Brand Guardian", "brand-guardian"),
    ("SEO + AEO Agent", "seo--aeo-agent"),  # '+' strips to a double hyphen
    ("Email Marketing Agent", "email-marketing-agent"),
    ("Community Manager", "community-manager"),
    ("DM Customer Hunter", "dm-customer-hunter"),
    ("Carousel Designer", "carousel-designer"),
    ("Trend Sentinel", "trend-sentinel"),
    ("Performance Tracker", "performance-tracker"),
    ("Brand Book", "brand-book"),
    ("Weekly Program", "weekly-program"),
    ("Monthly Program", "monthly-program"),
]

MARKER_PAYLOAD = {"meta": {"brand": "x", "slug": "y"}, "followers": 123}


def _is_generic_dump(name: str, out: str) -> bool:
    return out.startswith(f"## {name} Output")


def test_every_roster_agent_has_a_branch():
    misses = []
    for display, slug in ROSTER:
        for name in (display, slug):
            out = format_for_notion(name, dict(MARKER_PAYLOAD))
            if _is_generic_dump(name, out):
                misses.append(name)
    assert not misses, (
        f"These roster agents fall to the generic key-dumper (the raw-JSON bug): {misses}. "
        "Add a dedicated branch in utils/output_formatter.format_for_notion."
    )


REALISTIC = {
    "Creative Director": {
        "scripts_processed": 2,
        "winning_variant": {"concept": "Founder unboxing at golden hour", "format": "reel"},
        "production_notes": "Shoot vertical, natural light, no logo watermark.",
    },
    "Ad Strategist": {
        "competitor_read": "Competitors lean on discount hooks; whitespace is story-led UGC.",
        "ad_angles": [{"angle": "Heritage story", "why": "no competitor owns it"}],
        "budget_note": "Suggested starting split pending owner budget confirmation.",
    },
    "Brand Guardian": {
        "overall_grade": "B+",
        "scripts_evaluated": 4,
        "agents_audited": ["script-writer"],
        "voice_findings": [{"finding": "Tone drifts formal in CTA", "fix": "Use spoken-word phrasing"}],
    },
    "SEO + AEO Agent": {
        "url": "https://example.com",
        "technical_score": 72,
        "technical_summary": "Site is indexable; largest gaps are missing schema and slow LCP.",
        "aeo": {"readiness": "partial", "priority_fixes": ["Add FAQ schema"]},
    },
    "Carousel Designer": {
        "topic": "3 myths about organic cotton",
        "platform": "instagram",
        "slide_count": 7,
        "post_caption": "Myth 1: organic means expensive...",
        "save_prompt": "Save this for your next fabric shop run.",
    },
    "Performance Tracker": {
        "posts_total": 12,
        "winning_patterns": [{"pattern": "carousel + question hook", "reason": "2.1x saves"}],
        "dead_patterns": [{"pattern": "text-only quote posts", "reason": "0 saves in 30 days"}],
    },
    "Monthly Program": {
        "window": "June 2026",
        "scale_next_month": [{"pattern": "reels with founder voiceover", "why": "top reach"}],
        "keep": [{"pattern": "weekly carousel", "why": "steady saves"}],
        "cut": [],
        "budget_split_reason": "No real ad spend data yet — budget split activates once ads run.",
    },
}


def test_realistic_payloads_render_human_text_not_json():
    for name, payload in REALISTIC.items():
        out = format_for_notion(name, payload)
        assert not _is_generic_dump(name, out), name
        assert '{"' not in out and '":' not in out, f"{name}: JSON syntax leaked:\n{out}"
        # the human narrative must actually surface, not just a header
        human_bits = [v for v in payload.values() if isinstance(v, str) and len(v) > 20]
        for bit in human_bits:
            assert bit[:20] in out, f"{name}: human text missing from render:\n{out}"


def test_machine_scaffolding_keys_stay_hidden():
    out = format_for_notion("Performance Tracker", {
        "run_at": "2026-07-15T00:00:00", "brand_slug": "third-gen-tribe",
        "decision_engine": "pure_math", "posts_total": 3,
        "winning_patterns": [{"pattern": "reels", "reason": "reach"}],
    })
    for leaked in ("Run At", "Brand Slug", "Decision Engine", "run_at", "decision_engine"):
        assert leaked not in out, f"machine key leaked: {leaked}\n{out}"


if __name__ == "__main__":
    test_every_roster_agent_has_a_branch()
    test_realistic_payloads_render_human_text_not_json()
    test_machine_scaffolding_keys_stay_hidden()
    print("formatter-coverage tests passed")
