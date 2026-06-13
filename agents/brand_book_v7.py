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
    # ROLE MODEL = the full-funnel leader to climb toward (Gary Vee), NOT a competitor.
    role_model = next((r for r in rows if not r["is_brand"] and r.get("tier") == "leader"), None)
    # COMPETITOR CEILING = the top single-channel peer to beat now (Manthan) — the near-term target.
    peer_rows = [r for r in rows if not r["is_brand"] and r.get("tier") == "peer"]
    competitor_ceiling = max(peer_rows, key=lambda r: r["engagement"], default=None)

    # the comment-funnel gap: brand's own comments vs the best peer's comment-driven posts
    cs = scores.get("content_signals", {})
    peer_comment_best = max((r["avg_comments"] for r in cs.get("rows", [])), default=0)
    brand_comments = bi.get("avg_comments") or 0

    return {
        "brand_engagement": brand_eng,
        "rows": rows,
        "category_median": median,
        "role_model": role_model,                 # Gary Vee — the aspiration
        "competitor_ceiling": competitor_ceiling,  # top peer — the near-term target
        "gap_to_median_x": round(median / brand_eng, 1) if brand_eng else None,
        "comment_funnel_gap": {
            "brand_avg_comments": brand_comments,
            "peer_best_avg_comments": round(peer_comment_best, 1),
            "brand_runs_funnel": brand_comments > (bi.get("avg_likes") or 0) and brand_comments > 0,
        },
    }


# ───────────────────────────────────────── the one Opus call (full brand audit)
def _facts(brand, benchmark, scores, profile, signals) -> str:
    bi = brand["instagram"]
    return json.dumps({
        "brand": {
            "username": bi.get("username"), "name": bi.get("name"), "bio": bi.get("biography"),
            "followers": bi.get("followers"), "posts": bi.get("media_count"),
            "avg_likes": bi.get("avg_likes"), "avg_comments": bi.get("avg_comments"),
            "avg_reach": bi.get("avg_reach"), "total_saves": bi.get("total_saves"),
            "format_mix": bi.get("format_mix"), "demographics_status": bi.get("demographics_status"),
            "on_channels": ["Instagram"],
        },
        "framing": {"role_model": signals["framing"]["role_model"],
                    "competitors": signals["framing"]["competitors"],
                    "note": "role_model = the full-funnel operator to climb toward (aspiration); "
                            "competitors = the single-channel peers to beat now."},
        "benchmark": {
            "brand_engagement": benchmark["brand_engagement"],
            "category_median": benchmark["category_median"],
            "competitor_ceiling": benchmark["competitor_ceiling"],   # top peer = near-term target
            "role_model": benchmark["role_model"],                   # Gary Vee = aspiration
            "gap_to_median_x": benchmark["gap_to_median_x"],
        },
        "brand_identity": {
            "positioning_wedge": signals["identity"]["positioning_wedge"],
            "brand_architecture": signals["identity"]["brand_architecture"],
            "tone_of_voice": signals["identity"]["tone_of_voice"],
            "external_signal": signals["identity"]["external_signal"],
            "identity_gaps": signals["identity"]["identity_gaps"],
        },
        "audience": signals["audience"],
        "the_how_playbook": {
            "the_mechanic": signals["playbook"]["the_mechanic"],
            "funnel_adoption": signals["playbook"]["funnel_adoption"],
            "keyword_cta_examples": signals["playbook"]["keyword_cta_examples"],
            "top_category_hooks": signals["playbook"]["top_category_hooks"],
            "per_competitor": signals["playbook"]["competitors"],
        },
        "channels": [{"channel": c["channel"], "verdict": c["verdict"], "is_gap": c.get("is_gap"),
                      "headline": c["headline"], "money_signal_days": c.get("money_signal_days", 0)}
                     for c in scores["channels"]],
        "triage": signals["triage"],
        "channels_absent": [c["channel"] for c in scores.get("channels_absent", [])],
    }, ensure_ascii=False, indent=2)


_SCHEMA = """Return STRICT JSON only (no code fences, no prose around it). Every figure you cite must
come from FACTS. Keys:
{
  "headline": "<=10 words. THIS BRAND's path. punchy, no hype clichés",
  "subhead": "<=20 words. what this audit decides for them",
  "exec_summary": [ "<=24 words each. 3-5 critical findings/opportunities for the founder, each tied to a real number" ],
  "starting_line": "<=45 words. honest read of where the brand is TODAY (cite real numbers). runway, not verdict",
  "where_you_stand": "<=55 words. brand vs competitor_ceiling vs category median — honest gap. cite numbers",
  "snapshot": [ {"verdict":"RIDE|GAP|TEST|SKIP","channel":"...","line":"<=22 words"} ],
  "identity": {
     "summary": "<=40 words. who the brand IS per its positioning",
     "external_image_gap": "<=45 words. the internal-identity-vs-external-image gap — cite the concrete identity_gaps"
  },
  "audience": "<=45 words. who the target follower is + the honest perception read (cite demographics_status, 0 comments)",
  "how_winners_win": "<=70 words. reverse-engineer the COMPETITORS' mechanic: the comment-keyword→DM funnel + the hook style. cite a real keyword example and a real hook",
  "role_model": "<=45 words. what the ROLE MODEL (full-funnel) proves about the destination — IG+YouTube+paid. cite real numbers",
  "your_playbook": [ "<=30 words each. 3-5 concrete moves THIS brand makes to copy the winners — specific, post-level, no vagueness" ],
  "roadmap": {
     "month_1": {"title":"<=8 words","moves":["<=24 words each — a SUGGESTED type of content to publish, framed as guidance"]},
     "month_2": {"title":"<=8 words","moves":["<=24 words each — suggested content types"]},
     "month_3": {"title":"<=8 words","moves":["<=24 words each — suggested content types"]}
  },
  "route_steps": [ {"verdict":"...","channel":"...","action":"<=10 words imperative","why":"<=34 words. cite a real number"} ],
  "intros": {"channel_map":"<=26w","how":"<=26w"}
}
One snapshot + one route_step per channel in `channels`, same order.
ROADMAP IS THE GUIDE'S CONTENT PLAN — each `moves` entry SUGGESTS a TYPE of content the brand
could publish (e.g. "A weekly carousel breaking down one automation you built", "Short Reels
demoing a tool with a comment-trigger", "Build-in-public clips showing the system working"),
phrased as recommendations a trusted guide gives — "consider…", "content like…", "a format worth
testing…" — NEVER blunt orders ("do X", "post Y"). Still ground each suggestion in a real
category signal. month_1 = quick wins, month_2 = build, month_3 = expand."""


def _generate(brand, benchmark, scores, profile, signals) -> tuple[dict, dict]:
    name = brand["instagram"].get("name") or profile.get("name")
    system = (
        f"You are the lead brand strategist writing an onboarding BRAND AUDIT for {name} — a real client "
        "who just signed with OffGrid. You are their TRUSTED GROWTH GUIDE — they're relying on you to help "
        "them grow, so be generous, specific, and encouraging. It must read like a real brand audit (identity "
        "+ perception + competitive benchmark + a concrete how-to playbook + a 90-day plan), not a metrics "
        "dump. Voice: founder-to-founder and specific. The DIAGNOSIS is honest and direct; the RECOMMENDATIONS "
        "(especially the roadmap) are framed as a guide's SUGGESTIONS — 'consider…', 'a format worth testing…', "
        "'content like…' — not blunt orders. RULES: the BRAND is the "
        "hero of every section. ROLE MODEL = the full-funnel operator to climb toward; COMPETITORS = the peers "
        "to beat now — never confuse them. You write PROSE around facts already proven by a deterministic "
        "engine; NEVER invent a number, keyword, channel, or verdict — only use what's in FACTS. No vague "
        "advice like 'be more authentic' — every recommendation must be concrete and tied to a real number "
        "or a real competitor example. The brand is tiny and new — frame gaps as runway, never condescend."
    )
    prompt = "\n\n".join([
        UNTRUSTED_POLICY,
        "FACTS (REAL, pre-computed — the only numbers/verdicts/keywords that exist; do not add or alter):\n"
        + _facts(brand, benchmark, scores, profile, signals),
        "Write the full brand-audit narrative per the schema. Arc: exec summary → where they stand → who they "
        "ARE (identity + the external-image gap) → who their audience is → how the COMPETITORS win (the "
        "comment-keyword→DM funnel, reverse-engineered with real examples) → what the ROLE MODEL proves about "
        "the destination → the brand's own concrete playbook → a 90-day roadmap. Make every line actionable.",
        "HARD STYLE RULE — never use these phrases or close variants (auto-rejected if any appear): "
        + "; ".join(_FILLER) + ".",
        _SCHEMA,
    ])
    res = complete(AGENT_SLUG, [{"role": "user", "content": prompt}], system=system, max_tokens=3200)
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
        # brand-audit completeness (Frontify + BrandAuditors)
        "exec_summary_present": isinstance(narrative.get("exec_summary"), list) and len(narrative["exec_summary"]) >= 3,
        "brand_identity_audited": bool((narrative.get("identity") or {}).get("external_image_gap")),
        "audience_assessed": bool(narrative.get("audience")),
        "how_playbook_present": bool(narrative.get("how_winners_win")) and bool(narrative.get("your_playbook")),
        "role_model_framed": bool(narrative.get("role_model")),
        "roadmap_present": all(k in (narrative.get("roadmap") or {}) for k in ("month_1", "month_2", "month_3")),
        # data integrity
        "brand_is_centered": bool(narrative.get("starting_line")) and bool(narrative.get("where_you_stand")),
        "has_real_brand_data": bi.get("status") == "ok" and bi.get("followers") is not None,
        "has_real_evidence": any(c.get("provenance", {}).get("tag") == "REAL" for c in scores["channels"]),
        "ad_signal_assessed": any(c["channel"].startswith("Meta Ads") for c in scores["channels"]),
        "honest_absence": bool(scores.get("channels_absent")) or bi.get("demographics_status") == "locked_under_100_followers",
        "no_ai_filler": not _has_filler(narrative),
    }
    return {"passed": all(checks.values()), "checks": checks}


# ───────────────────────────────────────── assembly
def generate(slug: str, render_pdf: bool = True) -> dict:
    import audit_signals
    brand, intel, scores, profile = _load(slug)
    benchmark = _benchmark(brand, intel, scores)
    signals = audit_signals.build(brand, intel, scores, profile)
    narrative, res = _generate(brand, benchmark, scores, profile, signals)
    ev = _eval(brand, scores, narrative)

    report = {
        "meta": {"brand": brand["instagram"].get("name") or slug, "slug": slug, "version": VERSION,
                 "date": datetime.now(timezone.utc).strftime("%Y-%m-%d"), "model": res.get("model"),
                 "engine": "brand_self + channel_score + audit_signals (Class-1) + Opus narrative (Class-2)"},
        "brand": brand, "benchmark": benchmark, "scores": scores, "signals": signals,
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
