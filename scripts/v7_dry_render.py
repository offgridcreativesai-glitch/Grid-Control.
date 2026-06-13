"""
scripts/v7_dry_render.py — B-4 dry render ($0, no Anthropic) for the BRAND-CENTERED audit.
Synthesizes a placeholder narrative from the deterministic data and renders the premium
visual PDF, to prove the layout before the paid Opus run.
Usage: python3 scripts/v7_dry_render.py [slug]
"""
import json
import os
import sys
from datetime import datetime, timezone

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "agents"))

from brand_book_v7 import _load, _benchmark, _palette  # noqa: E402
from brand_book_v7_renderer import render_v7            # noqa: E402


def synth(brand, benchmark, scores):
    bi = brand["instagram"]
    chans = scores["channels"]
    snapshot = [{"verdict": c["verdict"], "channel": c["channel"], "line": c["headline"]} for c in chans]
    steps = []
    for r in scores.get("route_order", []):
        c = next(ch for ch in chans if ch["channel"] == r["channel"])
        act = ("ship comment-to-DM Reels weekly" if c["verdict"] == "RIDE"
               else "be the first peer to run paid" if c["channel"].startswith("Meta")
               else "plant a long-form authority flag" if c["verdict"] == "GAP"
               else "test small, watch the signal")
        steps.append({"verdict": c["verdict"], "channel": c["channel"], "action": act, "why": c["headline"]})
    return {
        "headline": "14 followers today. Here's the exact climb.",
        "subhead": "Where you stand against your category, and the sequenced route to close the gap.",
        "starting_line": f"You're at {bi.get('followers')} followers, {bi.get('media_count')} posts, "
                         f"~{bi.get('avg_reach')} reach a post. Day one. The numbers are small; the runway is the point.",
        "where_you_stand": f"Your posts average {benchmark['brand_engagement']} engagement. The category median is "
                           f"{benchmark['category_median']}. That gap is the map, not a verdict.",
        "snapshot": snapshot,
        "intros": {"channel_map": "Every channel scored on who shows up, who works, who's paying.",
                   "how": "The category posts one way and converts another.",
                   "money": "Brands don't burn money on ads that lose.",
                   "route": "Do the proven thing now; plant flags where no one is."},
        "the_how": "The category wins on comment-to-DM funnels. You average 0 comments — you're not running it yet. "
                   "That's the single highest-leverage change.",
        "route_steps": steps,
    }


def main():
    slug = sys.argv[1] if len(sys.argv) > 1 else "askgauravai"
    brand, intel, scores, profile = _load(slug)
    benchmark = _benchmark(brand, intel, scores)
    narrative = synth(brand, benchmark, scores)
    report = {"meta": {"brand": brand["instagram"].get("name") or slug,
                       "slug": slug, "date": datetime.now(timezone.utc).strftime("%Y-%m-%d")},
              "brand": brand, "benchmark": benchmark, "scores": scores, "narrative": narrative}
    ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    out = os.path.join(ROOT, "brands", slug, "outputs", "pending_approval", "brand-book",
                       f"{ts}_v7_DRYRUN.pdf")
    print(f"[v7 dry render] → {render_v7(report, intel, _palette(slug), out)}")


if __name__ == "__main__":
    main()
