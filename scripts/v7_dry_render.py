"""
scripts/v7_dry_render.py — B-4 dry render ($0, no Anthropic).
Synthesizes a placeholder narrative from the deterministic channel scores and renders
the v7 visual PDF, to prove the visual layer + image embedding before the paid B-5 run.
Usage: python3 scripts/v7_dry_render.py [slug]
"""
import json
import os
import sys
from datetime import datetime, timezone

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "agents"))

from brand_book_v7_renderer import render_v7  # noqa: E402


def _palette(slug):
    if slug == "offgrid-creatives-ai":
        return {"accent": "#d98a1f", "ink": "#23211c", "paper": "#ffffff"}
    return {"accent": "#b23a2e", "ink": "#211d18", "paper": "#ffffff"}


def synth_narrative(scores):
    """Deterministic placeholder narrative (B-5 Opus replaces the prose)."""
    chans = scores["channels"]
    snapshot = [{"verdict": c["verdict"], "channel": c["channel"], "line": c["headline"]}
                for c in chans]
    cs = scores.get("content_signals", {})
    route_steps = []
    for r in scores.get("route_order", []):
        c = next(ch for ch in chans if ch["channel"] == r["channel"])
        if c["verdict"] == "RIDE":
            action = "keep posting, but weaponise the comment-funnel"
            why = cs.get("headline", c["headline"])
        elif c["verdict"] == "GAP" and c["channel"].startswith("Meta"):
            action = "be the first peer to run paid"
            why = c["headline"]
        elif c["verdict"] == "GAP":
            action = "plant a long-form authority flag"
            why = c["headline"]
        else:
            action = "test small, watch the signal"
            why = c["headline"]
        route_steps.append({"channel": c["channel"], "verdict": c["verdict"],
                            "action": action, "why": why})
    return {
        "headline": "Everyone fights on IG. The wins are hiding off it.",
        "subhead": "Where your category actually converts — and the two lanes no peer is in.",
        "snapshot": snapshot,
        "intros": {
            "channel_map": "Every public channel, scored on who shows up, who works, and who's paying.",
            "ad": "Brands don't burn money on ads that lose. Longevity is the truth serum.",
            "content": "The category posts one way and converts another. Here's the mechanic.",
            "gap": "Two lanes have hard proof they work — and zero peers competing.",
            "route": "Do the proven thing now. Plant flags where no one else is.",
        },
        "route_steps": route_steps,
    }


def main():
    slug = sys.argv[1] if len(sys.argv) > 1 else "askgauravai"
    with open(os.path.join(ROOT, "brands", slug, "channel_scores_v7.json")) as f:
        scores = json.load(f)
    with open(os.path.join(ROOT, "brands", slug, "competitor_intel_v7.json")) as f:
        intel = json.load(f)
    narrative = synth_narrative(scores)
    ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    out = os.path.join(ROOT, "brands", slug, "outputs", "pending_approval",
                       "brand-book", f"{ts}_v7_DRYRUN.pdf")
    path = render_v7(scores, intel, narrative, _palette(slug), out)
    print(f"[v7 dry render] → {path}")


if __name__ == "__main__":
    main()
