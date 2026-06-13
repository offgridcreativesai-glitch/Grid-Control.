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
from agents.renderers.brand_book_v7_renderer import render_v7            # noqa: E402
from agents.intel import audit_signals                                    # noqa: E402


def synth(brand, benchmark, scores, signals):
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
        "subhead": "Who you are, where you stand, and the 90-day route to close the gap.",
        "exec_summary": [
            "You're at 14 followers and 0 comments — the category's whole conversion mechanic is missing from your account.",
            "Your top competitor runs a 1.52x comment-to-like ratio; you run zero. That's the #1 fix.",
            "Two channels (Meta Ads, YouTube) are wide open — but earn Instagram first.",
            "Only 33% of your posts are Reels; the category is ~100% short-video.",
        ],
        "starting_line": f"You're at {bi.get('followers')} followers, {bi.get('media_count')} posts, "
                         f"~{bi.get('avg_reach')} reach a post. Day one. The numbers are small; the runway is the point.",
        "where_you_stand": f"Your posts average {benchmark['brand_engagement']} engagement. The category median is "
                           f"{benchmark['category_median']}. That gap is the map, not a verdict.",
        "snapshot": snapshot,
        "identity": {"summary": "You're the founder building AI marketing systems in public — intelligence plus done-for-you, for solo D2C teams.",
                     "external_image_gap": "Your bio says 'no jargon, just what works' — but your 3 posts don't ask for a single action. The promise is sharp; the account doesn't deliver on it yet."},
        "audience": "Your target is the solo D2C founder drowning in dashboards. Right now 0 comments and 0 saves means perception is unformed — this audit sets the first impression deliberately.",
        "how_winners_win": "The competitors win on one mechanic: every Reel ends in 'comment a keyword, I'll DM you the resource.' Gobi's 'comment POLY' pulled 5,604 comments. Bold first-person hooks ('I gained 50,000 followers in 17 days') do the pulling.",
        "role_model": "Your role model Gary Vee proves the destination: 4.8M YouTube subs and Meta ads live 139 days. Full-funnel — but that's the climb, not the start.",
        "your_playbook": [
            "Add 'comment <keyword> → auto-DM' to every Reel — start with one lead magnet.",
            "Open every post with a bold first-person result hook, like the competitors.",
            "Move to 100% Reels; retire static carousels.",
            "Reply to every comment to train the algorithm and start the conversation.",
        ],
        "roadmap": {
            "month_1": {"title": "Fix the foundation", "moves": ["Install the comment-to-DM funnel", "Switch to 100% Reels", "Lock the hook formula"]},
            "month_2": {"title": "Build the engine", "moves": ["Post 4 funnel Reels/week", "Reply to every comment", "Ship one lead magnet"]},
            "month_3": {"title": "Open the next front", "moves": ["Test small Meta retargeting", "Plan first YouTube long-form"]},
        },
        "intros": {"channel_map": "Every channel scored on who shows up, who works, who's paying.",
                   "how": "Here's your version of the mechanic, post by post."},
        "route_steps": steps,
    }


def main():
    slug = sys.argv[1] if len(sys.argv) > 1 else "askgauravai"
    brand, intel, scores, profile = _load(slug)
    benchmark = _benchmark(brand, intel, scores)
    signals = audit_signals.build(brand, intel, scores, profile)
    narrative = synth(brand, benchmark, scores, signals)
    report = {"meta": {"brand": brand["instagram"].get("name") or slug,
                       "slug": slug, "date": datetime.now(timezone.utc).strftime("%Y-%m-%d")},
              "brand": brand, "benchmark": benchmark, "scores": scores,
              "signals": signals, "narrative": narrative}
    ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    out = os.path.join(ROOT, "brands", slug, "outputs", "pending_approval", "brand-book",
                       f"{ts}_v7_DRYRUN.pdf")
    print(f"[v7 dry render] → {render_v7(report, intel, _palette(slug), out)}")


if __name__ == "__main__":
    main()
