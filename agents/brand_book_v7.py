"""
agents/brand_book_v7.py — Brand-Book v7 assembly (BRAND-CENTERED onboarding audit).

The brand is the hero. We pull its OWN real connected-account numbers (brand_self.py),
benchmark them against the 3 competitors + category (competitor_intel.py), score where
the category is won (channel_score.py), and end in a prescriptive WHAT + HOW route for
THIS brand. Competitor data is the lens, never the subject.

Deterministic spine (Class-1): brand stats, brand-vs-category benchmark, channel verdicts,
the comment-funnel gap. One Class-2 Opus call writes prose around those facts — it never
invents a number or verdict. Eval v7 (mode/category aware) gates before render.

Usage: python3 agents/brand_book_v7.py [slug]
"""
from __future__ import annotations

import json
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _ROOT)
sys.path.insert(0, os.path.join(_ROOT, "agents"))

try:
    from model_gateway import complete
    from _untrusted import UNTRUSTED_POLICY
    from brand_book import _FILLER
    from brand_book_v7_renderer import render_v7
except ImportError:
    from agents.model_gateway import complete
    from agents._untrusted import UNTRUSTED_POLICY
    from agents.brand_book import _FILLER
    from agents.brand_book_v7_renderer import render_v7

AGENT_SLUG = "brand-book"
VERSION = "v7"


def _palette(slug: str) -> dict:
    if slug == "offgrid-creatives-ai":
        return {"accent": "#d98a1f", "ink": "#23211c", "paper": "#ffffff"}
    return {"accent": "#b23a2e", "ink": "#211d18", "paper": "#ffffff"}


def _load(slug: str):
    base = os.path.join(_ROOT, "brands", slug)
    with open(os.path.join(base, "brand_self_v7.json")) as f:
        brand = json.load(f)
    with open(os.path.join(base, "competitor_intel_v7.json")) as f:
        intel = json.load(f)
    with open(os.path.join(base, "channel_scores_v7.json")) as f:
        scores = json.load(f)
    with open(os.path.join(base, "brand_profile.json")) as f:
        profile = json.load(f)
    return brand, intel, scores, profile


def _median(xs):
    xs = sorted(x for x in xs if x is not None)
    if not xs:
        return 0.0
    n = len(xs)
    return xs[n // 2] if n % 2 else (xs[n // 2 - 1] + xs[n // 2]) / 2.0


# ───────────────────────────────────────── deterministic brand-vs-category benchmark
def _benchmark(brand: dict, intel: dict, scores: dict) -> dict:
    bi = brand["instagram"]
    brand_eng = round((bi.get("avg_likes") or 0) + (bi.get("avg_comments") or 0), 1)
    peers = scores.get("tiers", {}).get("peers", [])

    rows = [{"handle": f"@{bi.get('username')}", "engagement": brand_eng,
             "followers": bi.get("followers"), "is_brand": True}]
    peer_eng = []
    for h, c in intel.get("competitors", {}).items():
        ig = c.get("instagram", {})
        if ig.get("status") != "ok":
            continue
        e = round(ig.get("avg_engagement", 0.0), 1)
        rows.append({"handle": h, "engagement": e, "is_brand": False,
                     "tier": "leader" if h not in peers else "peer"})
        if h in peers:
            peer_eng.append(e)
    rows.sort(key=lambda r: r["engagement"], reverse=True)

    median = round(_median(peer_eng), 1)
    ceiling_row = max((r for r in rows if not r["is_brand"]), key=lambda r: r["engagement"], default=None)
    # the role model = highest-engagement PEER (the realistic next ceiling, not the giant leader)
    peer_rows = [r for r in rows if not r["is_brand"] and r.get("tier") == "peer"]
    role_model = max(peer_rows, key=lambda r: r["engagement"], default=None)

    # the comment-funnel gap: brand's own comments vs the best peer's comment-driven posts
    cs = scores.get("content_signals", {})
    peer_comment_best = max((r["avg_comments"] for r in cs.get("rows", [])), default=0)
    brand_comments = bi.get("avg_comments") or 0

    return {
        "brand_engagement": brand_eng,
        "rows": rows,
        "category_median": median,
        "ceiling": ceiling_row,
        "role_model": role_model,
        "gap_to_median_x": round(median / brand_eng, 1) if brand_eng else None,
        "comment_funnel_gap": {
            "brand_avg_comments": brand_comments,
            "peer_best_avg_comments": round(peer_comment_best, 1),
            "brand_runs_funnel": brand_comments > (bi.get("avg_likes") or 0) and brand_comments > 0,
        },
    }


# ───────────────────────────────────────── the one Opus call (brand-centered)
def _facts(brand, benchmark, scores, profile) -> str:
    bi = brand["instagram"]
    return json.dumps({
        "brand": {
            "username": bi.get("username"), "name": bi.get("name"),
            "bio": bi.get("biography"),
            "followers": bi.get("followers"), "posts": bi.get("media_count"),
            "avg_likes": bi.get("avg_likes"), "avg_comments": bi.get("avg_comments"),
            "avg_reach": bi.get("avg_reach"), "total_saves": bi.get("total_saves"),
            "format_mix": bi.get("format_mix"),
            "account_insights_28d": bi.get("account_insights_28d"),
            "demographics_status": bi.get("demographics_status"),
            "on_channels": ["Instagram"],
            "positioning_wedge": profile.get("positioning_wedge"),
            "brand_architecture": profile.get("brand_architecture"),
        },
        "benchmark": {
            "brand_engagement": benchmark["brand_engagement"],
            "category_median": benchmark["category_median"],
            "ceiling": benchmark["ceiling"],
            "role_model": benchmark["role_model"],
            "gap_to_median_x": benchmark["gap_to_median_x"],
            "comment_funnel_gap": benchmark["comment_funnel_gap"],
        },
        "channels": [{"channel": c["channel"], "verdict": c["verdict"],
                      "is_gap": c.get("is_gap"), "headline": c["headline"],
                      "money_signal_days": c.get("money_signal_days", 0)}
                     for c in scores["channels"]],
        "content_signal": scores.get("content_signals", {}).get("headline"),
        "route_order": scores.get("route_order", []),
        "channels_absent": [c["channel"] for c in scores.get("channels_absent", [])],
    }, ensure_ascii=False, indent=2)


_SCHEMA = """Return STRICT JSON only (no code fences, no prose around it):
{
  "headline": "<=10 words. THIS BRAND's path, not the competitors'. punchy, no hype clichés>",
  "subhead": "<=20 words. what this audit decides for them>",
  "starting_line": "<=45 words. honest read of where the brand is TODAY (cite its real numbers). framed as a runway, not a verdict>",
  "where_you_stand": "<=55 words. the brand vs the category ceiling — honest gap + what it means. cite the real benchmark numbers>",
  "snapshot": [ {"verdict":"RIDE|GAP|TEST|SKIP","channel":"...","line":"<=22 words"} ],
  "intros": {"channel_map":"<=26w","how":"<=26w","money":"<=26w","route":"<=26w"},
  "the_how": "<=50 words. the ONE mechanic the category wins on (comment-to-DM funnel) and the brand's specific gap on it. cite the real comment numbers>",
  "route_steps": [ {"verdict":"...","channel":"...","action":"<=10 words imperative","why":"<=34 words. cite a real number, tie to THIS brand's start"} ]
}
One snapshot + one route_step per channel in `channels` / `route_order`, same order."""


def _generate(brand, benchmark, scores, profile) -> tuple[dict, dict]:
    name = brand["instagram"].get("name") or profile.get("name")
    system = (
        f"You are the lead strategist writing an onboarding brand audit for {name} — a real client "
        "who just signed with OffGrid. This is their FIRST impression of us, so it must be sharp, "
        "honest, and specific. Voice: founder-to-founder, blunt, zero hype. The BRAND is the hero of "
        "every section — competitors are only the lens that shows the route. You write PROSE around "
        "facts already proven by a deterministic engine; you NEVER invent a number, channel, or verdict. "
        "Only use figures in the FACTS block. The brand is tiny and new — never condescend; frame the "
        "gap as runway and give them the exact moves to close it."
    )
    prompt = "\n\n".join([
        UNTRUSTED_POLICY,
        "FACTS (REAL, pre-computed — the only numbers/verdicts that exist; do not add or alter any):\n"
        + _facts(brand, benchmark, scores, profile),
        "Write the audit narrative. Story arc: (1) where THIS brand stands today, honestly; (2) what the "
        "category proves works — the comment-to-DM funnel is the HOW; (3) where the openings are (channels "
        "peers ignore but the leader proves convert); (4) the exact sequenced route for a brand starting "
        "from here. Make every section about the brand's next move.",
        "HARD STYLE RULE — never use these phrases or close variants (auto-rejected if any appear): "
        + "; ".join(_FILLER) + ".",
        _SCHEMA,
    ])
    res = complete(AGENT_SLUG, [{"role": "user", "content": prompt}], system=system, max_tokens=2200)
    return _parse_json((res.get("text") or "").strip()), res


def _parse_json(text: str) -> dict:
    text = re.sub(r"^```(?:json)?\s*|\s*```$", "", text.strip(), flags=re.MULTILINE)
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        m = re.search(r"\{.*\}", text, re.DOTALL)
        if m:
            return json.loads(m.group(0))
        raise


# ───────────────────────────────────────── eval v7
def _has_filler(n: dict) -> bool:
    blob = json.dumps(n, ensure_ascii=False).lower()
    return any(f in blob for f in _FILLER)


def _eval(brand, scores, narrative) -> dict:
    bi = brand["instagram"]
    checks = {
        "brand_is_centered": bool(narrative.get("starting_line")) and bool(narrative.get("where_you_stand")),
        "has_real_brand_data": bi.get("status") == "ok" and bi.get("followers") is not None,
        "has_real_evidence": any(c.get("provenance", {}).get("tag") == "REAL" for c in scores["channels"]),
        "channel_recommendation_present": bool(narrative.get("route_steps")) and bool(narrative.get("snapshot")),
        "ad_signal_assessed": any(c["channel"].startswith("Meta Ads") for c in scores["channels"]),
        "honest_absence": bool(scores.get("channels_absent")) or bi.get("demographics_status") == "locked_under_100_followers",
        "no_ai_filler": not _has_filler(narrative),
        "all_sections_present": all([narrative.get("headline"), narrative.get("snapshot"),
                                     narrative.get("the_how"), narrative.get("route_steps")]),
    }
    return {"passed": all(checks.values()), "checks": checks}


# ───────────────────────────────────────── assembly
def generate(slug: str, render_pdf: bool = True) -> dict:
    brand, intel, scores, profile = _load(slug)
    benchmark = _benchmark(brand, intel, scores)
    narrative, res = _generate(brand, benchmark, scores, profile)
    ev = _eval(brand, scores, narrative)

    report = {
        "meta": {"brand": brand["instagram"].get("name") or slug, "slug": slug, "version": VERSION,
                 "date": datetime.now(timezone.utc).strftime("%Y-%m-%d"), "model": res.get("model"),
                 "engine": "brand_self + channel_score (Class-1) + Opus narrative (Class-2)"},
        "brand": brand, "benchmark": benchmark, "scores": scores,
        "narrative": narrative, "eval": ev,
    }

    out_dir = Path(_ROOT) / "brands" / slug / "outputs" / "pending_approval" / "brand-book"
    out_dir.mkdir(parents=True, exist_ok=True)
    ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    header = (f"LOOP: [brand-book] — report {VERSION} / GOAL onboarding-audit sign-off / "
              f"METRIC eval-v7-pass / EVAL {'PASS' if ev['passed'] else 'FAIL'}")
    (out_dir / f"{ts}_brand_book_{VERSION}.json").write_text(
        header + "\n---\n" + json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    if render_pdf:
        pdf = out_dir / f"{ts}_brand_book_{VERSION}.pdf"
        try:
            report["_pdf_path"] = str(render_v7(report, intel, _palette(slug), pdf))
        except Exception as e:
            import traceback
            report["_pdf_error"] = f"{e}\n{traceback.format_exc()[:800]}"
    return report


def main():
    slug = sys.argv[1] if len(sys.argv) > 1 else os.getenv("ACTIVE_BRAND", "askgauravai")
    rep = generate(slug)
    ev = rep["eval"]
    print(f"\n[brand_book_v7] {slug} — eval {'PASS' if ev['passed'] else 'FAIL'}")
    for k, v in ev["checks"].items():
        print(f"   {'✓' if v else '✗'} {k}")
    n = rep["narrative"]
    print(f"\n   headline: {n.get('headline')}")
    print(f"   subhead:  {n.get('subhead')}")
    print(f"   model:    {rep['meta'].get('model')}")
    if rep.get("_pdf_path"):
        print(f"   PDF →     {rep['_pdf_path']}")
    if rep.get("_pdf_error"):
        print(f"   PDF ERROR: {rep['_pdf_error']}")


if __name__ == "__main__":
    main()
