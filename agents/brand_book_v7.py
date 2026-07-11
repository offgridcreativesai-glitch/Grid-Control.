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

from agents._lib.model_gateway import complete
from agents._lib._untrusted import UNTRUSTED_POLICY
from agents.renderers.brand_book_v7_renderer import render_v7

AGENT_SLUG = "brand-book"
VERSION = "v7"

# AI-filler phrases — report auto-rejected if any appear (inlined from former v6).
_FILLER = (
    "in today's fast-paced", "in the ever-evolving", "navigating the landscape",
    "in conclusion", "it is important to note", "as an ai", "leverage synerg",
    "unlock the power", "in the realm of", "game-changer", "dive deep into",
)


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

    # Share of voice — % of the category's total engagement that is THIS brand's.
    # Deterministic (brand + every scraped competitor); never estimated.
    total_eng = round(sum(r["engagement"] for r in rows), 1)
    share_of_voice_pct = round(100 * brand_eng / total_eng, 1) if total_eng else None

    # White space — channels the category wins on that the brand isn't claiming yet
    # (scored gaps + channels the brand is entirely absent from).
    white_space = [c["channel"] for c in scores.get("channels", []) if c.get("is_gap")] \
        + [c["channel"] for c in scores.get("channels_absent", [])]

    return {
        "brand_engagement": brand_eng,
        "rows": rows,
        "category_median": median,
        "role_model": role_model,                 # Gary Vee — the aspiration
        "competitor_ceiling": competitor_ceiling,  # top peer — the near-term target
        "gap_to_median_x": round(median / brand_eng, 1) if brand_eng else None,
        "share_of_voice_pct": share_of_voice_pct,  # real % of category engagement
        "white_space": white_space,                # gap + absent channels
        "comment_funnel_gap": {
            "brand_avg_comments": brand_comments,
            "peer_best_avg_comments": round(peer_comment_best, 1),
            "brand_runs_funnel": brand_comments > (bi.get("avg_likes") or 0) and brand_comments > 0,
        },
    }


# ───────────────────────────────────────── the one Opus call (full brand audit)
def _competitors_detail(intel, signals, benchmark) -> list:
    """One consolidated record per COMPETITOR (peers only — the role model gets its own
    section). Merges the three scrapes into a single card-ready row: IG pull + whether
    they're paying for ads (Meta Ad Library) + their storefront price band + the one hook
    that works for them. Deterministic — Opus only writes prose around these facts."""
    peers = set(signals["framing"]["competitors"] or [])
    pb = {c["handle"]: c for c in signals["playbook"]["competitors"]}
    web = signals["website"].get("competitors", {}) or {}
    out = []
    for h, c in (intel.get("competitors") or {}).items():
        if h not in peers:
            continue
        ig = c.get("instagram", {}) or {}
        if ig.get("status") != "ok":
            continue
        ma = c.get("meta_ads", {}) or {}
        p = pb.get(h, {})
        top = (p.get("top_hooks") or [])
        out.append({
            "handle": h,
            "followers": ig.get("followers"),
            "avg_engagement": round(ig.get("avg_engagement", 0) or 0, 1),
            "cta_pattern": p.get("cta_pattern"),
            "runs_comment_funnel": p.get("runs_comment_funnel"),
            "top_hook": top[0].get("hook") if top else None,
            "advertising": ma.get("status") == "advertising",
            "active_ads": ma.get("active_ads"),
            "storefront_platform": (web.get(h) or {}).get("platform"),
            "price_band": (web.get(h) or {}).get("price_signals") or [],
        })
    return out


def _category_facts(signals, benchmark, comps_detail) -> dict:
    """Deterministic category-level rollup — the bird's-eye view before drilling into
    individual handles. All from data already scraped: format norm, the dominant winning
    mechanic's adoption, the price landscape across every storefront, the open lane."""
    prices = []
    own_web = signals["website"].get("own") or {}
    for pb in ([own_web.get("price_signals")] + [c.get("price_band") for c in comps_detail]):
        for p in (pb or []):
            prices.append(p)
    advertisers = [c["handle"] for c in comps_detail if c.get("advertising")]
    return {
        "players": [c["handle"] for c in comps_detail],
        "funnel_adoption": signals["playbook"]["funnel_adoption"],   # e.g. "2/3 run the comment→DM funnel"
        "the_mechanic": signals["playbook"]["the_mechanic"],
        "advertisers": advertisers,                                  # who's paying to play
        "price_points_seen": sorted(set(prices)),                    # every ₹ price across category stores
        "white_space_channels": benchmark["white_space"],
        "category_median_engagement": benchmark["category_median"],
    }


def _facts(brand, benchmark, scores, profile, signals, comps_detail, cat) -> str:
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
        "activity": bi.get("activity", {}),  # posting cadence + DORMANCY read (drives `situation`)
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
            "share_of_voice_pct": benchmark["share_of_voice_pct"],   # real % of category engagement
            "white_space_channels": benchmark["white_space"],        # gap + absent channels
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
        "website_positioning": signals.get("website", {}),
        "category_overview": cat,
        "competitors_detail": comps_detail,
    }, ensure_ascii=False, indent=2)


_SCHEMA = """Return STRICT JSON only (no code fences, no prose around it). Every figure you cite must
come from FACTS. Keys:
{
  "headline": "<=10 words. THIS BRAND's path. punchy, no hype clichés",
  "subhead": "<=20 words. what this audit decides for them",
  "situation": {
     "type": "ONE of GROWTH|REACTIVATION|LAUNCH|REPOSITION — read it from `activity` + the numbers. If activity.status is 'dormant' (dark for months) it is REACTIVATION. If a brand-new tiny account posting now, LAUNCH/GROWTH. Never mislabel.",
     "read": "<=40 words. the single most important business context that changes how the WHOLE report should be read — plain words. e.g. 'this account has been quiet ~10 months, so step one is a restart: rebuild trust and a posting rhythm before chasing growth'. This is the founder's 30-second truth — lead with it."
  },
  "exec_summary": [ "<=24 words each. 3-5 critical findings/opportunities for the founder, each tied to a real number. If situation.type is REACTIVATION, the FIRST item names the dormancy and the restart" ],
  "starting_line": "<=45 words. honest read of where the brand is TODAY (cite real numbers). runway, not verdict",
  "where_you_stand": "<=55 words. brand vs competitor_ceiling vs category median — honest gap. cite numbers",
  "share_of_voice": "<=24 words. cite the REAL share_of_voice_pct in plain words — e.g. 'of all the buzz in your niche right now, about X% of it is yours'. honest, not spun",
  "white_space": "<=28 words. the lane NO competitor owns that you could grab (use white_space_channels). name the concrete opening, not a platitude",
  "snapshot": [ {"verdict":"RIDE|GAP|TEST|SKIP","channel":"...","line":"<=22 words"} ],
  "category_overview": {
     "the_category": "<=40 words. what this niche IS and who plays in it (use category_overview.players), plain words a non-marketer gets",
     "how_they_win": "<=45 words. the format norm + the one move most of them use to win (cite funnel_adoption in plain words, e.g. '2 of the 3 do X')",
     "price_landscape": "<=30 words. the price range across the category's stores (cite real ₹ numbers from price_points_seen)",
     "the_opening": "<=30 words. the lane in this category nobody owns yet (use white_space_channels) — the concrete gap, not a platitude"
  },
  "your_instagram": {
     "read": "<=45 words. the honest state of THEIR OWN account — followers, post count, what formats they post, what's landing. cite real numbers. NOTE: format_mix counts only the recent posts SAMPLED, not all media_count — say 'of the last N posts' if you cite the video/image split, never imply it covers every post",
     "whats_working": "<=30 words. the format or post doing best (cite a real number) OR an honest 'too early to tell' if the account is tiny",
     "the_fix": "<=30 words. the single biggest change to make on Instagram, concrete and post-level"
  },
  "storefront": {
     "read": "<=45 words. audit THEIR OWN website on its own: what the homepage promises + what it's built on + the price ladder (cite website_positioning.own real ₹). plain words",
     "coherence": "<=35 words. does the website's message match their Instagram voice? name the match or the honest gap",
     "fixes": [ "2-3 concrete fixes to the storefront — <=20 words each, specific" ]
  },
  "competitor_cards": [
     {"handle":"<must equal a handle in competitors_detail>",
      "one_liner":"<=18 words. who they are in plain words",
      "winning_move":"<=30 words. the ONE thing that works for them — cite their real top_hook or their comment→DM habit",
      "steal_this":"<=24 words. what THIS brand should copy or counter, concrete"}
  ],
  "identity": {
     "summary": "<=40 words. who the brand IS per its positioning",
     "external_image_gap": "<=45 words. the internal-identity-vs-external-image gap — cite the concrete identity_gaps"
  },
  "audience": "<=45 words. who the target follower is + the honest perception read (cite demographics_status, 0 comments)",
  "how_winners_win": "<=70 words. reverse-engineer the COMPETITORS' mechanic: the comment-keyword→DM funnel + the hook style. cite a real keyword example and a real hook",
  "role_model": "<=45 words. what the ROLE MODEL (full-funnel) proves about the destination — IG+YouTube+paid. cite real numbers. OMIT THIS KEY ENTIRELY if framing.role_model is null — never invent a role model",
  "your_playbook": [ "<=30 words each. 3-5 concrete moves THIS brand makes to copy the winners — specific, post-level, no vagueness" ],
  "roadmap": {
     "month_1": {
        "title":"<=8 words — the theme of the month",
        "goal":"<=40 words — what this month is really about and WHY it comes first, plain words a founder gets. tie to a real gap/number from FACTS",
        "moves":["3-4 items, <=36 words each — a SUGGESTED content type/action framed as a guide's advice ('consider…','a format worth testing…'), EACH followed by the plain reason it helps and, where possible, a real competitor example or number"],
        "success_metric":"<=26 words — the concrete signal this month worked (a number they can watch, e.g. 'first Reels with a comment-ask get any comments at all'). honest for a tiny account"
     },
     "month_2": {"title":"<=8 words","goal":"<=40 words — the build phase, why it follows month 1","moves":["3-4 items, <=36 words each — suggested content type/action + the reason + a real example/number"],"success_metric":"<=26 words — the watchable signal month 2 worked"},
     "month_3": {"title":"<=8 words","goal":"<=40 words — the expand phase, why it comes last","moves":["3-4 items, <=36 words each — suggested content type/action + the reason + a real example/number"],"success_metric":"<=26 words — the watchable signal month 3 worked"}
  },
  "route_steps": [ {"verdict":"...","channel":"...","action":"<=10 words imperative","why":"<=34 words. cite a real number"} ],
  "intros": {"channel_map":"<=26w","how":"<=26w"},
  "foundation": {
     "purpose": "<=22 words. the WHY — why this brand exists for its people, beyond making money. human and plain, no mission-statement clichés",
     "positioning_statement": "<=30 words. the ONE prescriptive sentence: what this brand IS and for whom. sign-off-ready, grounded in positioning_wedge",
     "value_prop": "<=25 words. the core promise to the audience — concrete, no hype",
     "pillars": [ "3-4 content pillars this brand should OWN — <=6 words each, drawn from your_playbook + category signals" ],
     "pillars_explained": [ {"pillar":"<=6 words — MUST match a pillar above","proof":"<=16 words — why it's THIS brand's to own, tied to a real signal"} ],
     "icp": "<=30 words. the ideal follower/customer in one precise line (use audience + demographics)",
     "north_star": "<=20 words. the single 90-day goal that matters most (tie to roadmap month_3)",
     "voice": {
        "personality": "<=20 words. the brand's voice in a phrase (use tone_of_voice)",
        "do": [ "2-4 voice do's — <=8 words each" ],
        "dont": [ "2-4 voice don'ts — <=8 words each" ],
        "vocab_use": [ "3-6 words/phrases this brand uses — the clean term ONLY, no parentheticals, notes, or '(empty)'-style annotations" ],
        "vocab_avoid": [ "3-6 words/phrases this brand avoids — the clean term ONLY, no parentheticals, notes, or '(empty)'-style annotations" ]
     }
  }
}
One snapshot + one route_step per channel in `channels`, same order.
One competitor_card for EVERY handle in competitors_detail, same order — never skip one, never invent one.
FOUNDATION is the SIGN-OFF PAYLOAD — the prescriptive "WHAT" the founder approves to seed their
brand_profile + voice_profile. It is the audit's conclusion: the PURPOSE (the why behind the brand),
positioning, value prop, the 3-4 pillars they should own (each with a one-line proof in
pillars_explained), ICP, the 90-day north star, and voice DNA. Synthesize it from the identity
(positioning_wedge, tone_of_voice), the playbook, and audience — prescriptive, not diagnostic, and
concrete enough to brief a content team. pillars_explained MUST cover the same pillars as `pillars`.
ROADMAP IS THE HEART OF THE REPORT — the client reads this to know exactly what to do, so make it
DEEP, not a bullet list. For EACH month write: a `goal` (what the month is really about and WHY it
comes now, tied to a real gap/number), 3-4 `moves` where each move is a SUGGESTED type of content
(e.g. "A weekly Reel styling one tee on a real person, captioned in your 'Wear It Loud' voice")
FOLLOWED BY the plain reason it helps and, where you can, a real competitor example or number, and a
`success_metric` — the concrete watchable signal that month worked (honest for a tiny account, e.g.
"your first Reels with a comment-ask start pulling any comments at all"). Moves are a trusted guide's
advice — "consider…", "a format worth testing…", "content like…" — NEVER blunt orders. Ground every
suggestion in a real signal from FACTS. month_1 = quick wins, month_2 = build, month_3 = expand.
ROLE MODEL is OPTIONAL — if framing.role_model is null (no role model set for this brand), OMIT the
`role_model` key entirely and do not reference a role model anywhere; never invent one."""


def _generate(brand, benchmark, scores, profile, signals, comps_detail, cat) -> tuple[dict, dict]:
    name = brand["instagram"].get("name") or profile.get("name")
    from agents._lib._agent_framework import operating_framework as _operating_framework
    system = _operating_framework(2) + (
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
        "or a real competitor example. The brand is tiny and new — frame gaps as runway, never condescend. "
        "VOICE — write like a sharp friend who runs marketing explaining it to the founder over coffee: short "
        "plain sentences, warm and direct, zero MBA-speak or agency jargon. Whenever you use a metric or term "
        "(share of voice, engagement, funnel), explain it in plain words in the same breath the first time "
        "(e.g. 'share of voice — how much of the chatter in your niche is about you'). A smart 16-year-old "
        "should understand every line. Never sound like a template or a robot. "
        "HARD JARGON BAN — never use these insider terms at all; say them the plain way: 'positioning wedge' "
        "→ 'the angle that's yours'; 'impact/effort triage' / 'impact-effort' → 'quick wins vs bigger bets'; "
        "'brand architecture' → 'how the brand is set up'; 'external-image gap' → 'the gap between how you see "
        "yourself and how you come across'; 'CTA' → 'the ask'; 'funnel' → 'the path from a post to a sale'; "
        "'ICP' → 'the exact person you're for'. Write like you're talking to a smart shop owner, not pitching "
        "a boardroom."
    )
    prompt = "\n\n".join([
        UNTRUSTED_POLICY,
        "FACTS (REAL, pre-computed — the only numbers/verdicts/keywords that exist; do not add or alter):\n"
        + _facts(brand, benchmark, scores, profile, signals, comps_detail, cat),
        "Write the full brand-audit narrative per the schema. This report is READ BY THE CLIENT — a founder, "
        "their team, or their agency — who are NOT marketers. Every section stands on its own. FIRST, read the "
        "`activity` signal and decide the SITUATION: if the account has been dark for months (activity.status "
        "'dormant'), this is a REACTIVATION audit, NOT a growth audit — say so plainly up top and make the whole "
        "plan a restart (rebuild trust, a steady posting rhythm, and audience memory) before chasing reach. This "
        "is the most important context; it changes how every later section reads. Arc: SITUATION (the one truth "
        "that reframes everything) → exec summary → CATEGORY OVERVIEW (the bird's-eye read of the whole niche BEFORE any single brand: who plays "
        "in it, how they all win, the price landscape, the open lane) → where THEY stand vs the category → "
        "YOUR INSTAGRAM (their own account, its own read) → YOUR STOREFRONT (their website audited on its own: "
        "what the homepage promises, how it's built, the price ladder, does it match the Instagram voice, 2-3 "
        "fixes) → who they ARE (identity + the external-image gap) → who their audience is → THE COMPETITORS "
        "(one tight card per competitor in competitors_detail: who they are, the ONE move that works for them, "
        "what this brand should steal or counter) → the winning move decoded (the comment-keyword→DM funnel, "
        "with real examples) → (ONLY if framing.role_model is set) what the ROLE MODEL proves about the "
        "destination — if it's null, skip the role-model beat entirely → the brand's own playbook → a DEEP "
        "90-day roadmap (per month: goal + why, 3-4 moves each with its reason, and a success signal) → and "
        "CLOSE with the FOUNDATION (purpose, positioning, value prop, pillars + proofs, "
        "ICP, north star, voice DNA). Use website_positioning + competitors_detail for the storefront and "
        "competitor cards. Make every line actionable and plain.",
        "HARD STYLE RULE — never use these phrases or close variants (auto-rejected if any appear): "
        + "; ".join(_FILLER) + ".",
        _SCHEMA,
    ])
    # 8192: the v8 schema (category overview + own-IG + storefront + a card per competitor)
    # roughly doubled the JSON length; 4096 truncated it mid-`foundation` and broke parsing.
    res = complete(AGENT_SLUG, [{"role": "user", "content": prompt}], system=system, max_tokens=8192)
    return _parse_json((res.get("text") or "").strip()), res


def _escape_literal_newlines_in_strings(json_str: str) -> str:
    """Escape literal newline/CR/tab inside JSON string values (Claude API quirk
    that surfaces as 'Expecting , delimiter' / 'Invalid control character')."""
    result = []
    in_string = False
    i = 0
    while i < len(json_str):
        c = json_str[i]
        if in_string:
            if c == '\\':
                result.append(c); i += 1
                if i < len(json_str): result.append(json_str[i])
            elif c == '"':
                in_string = False; result.append(c)
            elif c == '\n': result.append('\\n')
            elif c == '\r': result.append('\\r')
            elif c == '\t': result.append('\\t')
            else: result.append(c)
        else:
            if c == '"': in_string = True
            result.append(c)
        i += 1
    return ''.join(result)


def _parse_json(text: str) -> dict:
    text = re.sub(r"^```(?:json)?\s*|\s*```$", "", text.strip(), flags=re.MULTILINE)
    m = re.search(r"\{.*\}", text, re.DOTALL)
    candidate = m.group(0) if m else text
    # 1) direct  2) literal-newline repair (the common LLM glitch)
    for attempt in (candidate, _escape_literal_newlines_in_strings(candidate)):
        try:
            return json.loads(attempt)
        except json.JSONDecodeError:
            continue
    # Hard failure: persist the raw text so it can be diagnosed WITHOUT re-spending
    # an API call, then raise with a pointer to it.
    hint = ""
    try:
        dbg = Path("/tmp/brand_book_v7_parse_fail.json")
        dbg.write_text(text, encoding="utf-8")
        hint = f" — raw model output saved to {dbg} for diagnosis"
    except Exception:
        pass
    raise ValueError(f"brand_book_v7: could not parse model JSON after repair{hint}")


# ───────────────────────────────────────── eval v7
def _has_filler(n: dict) -> bool:
    blob = json.dumps(n, ensure_ascii=False).lower()
    return any(f in blob for f in _FILLER)


def _eval(brand, scores, narrative) -> dict:
    bi = brand["instagram"]
    checks = {
        # brand-audit completeness (Frontify + BrandAuditors)
        "exec_summary_present": isinstance(narrative.get("exec_summary"), list) and len(narrative["exec_summary"]) >= 3,
        # Humanized judgment: the audit must NAME the situation type (growth/reactivation/launch/reposition)
        # and, when the account is dormant, correctly reframe as a reactivation — not a generic growth read.
        "situation_named": bool((narrative.get("situation") or {}).get("read"))
        and ((bi.get("activity", {}).get("status") != "dormant")
             or (narrative.get("situation", {}).get("type") == "REACTIVATION")),
        "brand_identity_audited": bool((narrative.get("identity") or {}).get("external_image_gap")),
        "category_overview_present": bool((narrative.get("category_overview") or {}).get("the_category")),
        "own_instagram_sectioned": bool((narrative.get("your_instagram") or {}).get("read")),
        "storefront_audited": bool((narrative.get("storefront") or {}).get("read")),
        "competitor_cards_present": isinstance(narrative.get("competitor_cards"), list) and len(narrative["competitor_cards"]) >= 1,
        "audience_assessed": bool(narrative.get("audience")),
        "how_playbook_present": bool(narrative.get("how_winners_win")) and bool(narrative.get("your_playbook")),
        # Role model is OPTIONAL — passes if there's genuinely no role model set (leaders tier
        # empty) OR the narrative framed one. Never fail a brand for correctly omitting it.
        "role_model_framed": (not (scores.get("tiers", {}) or {}).get("leaders")) or bool(narrative.get("role_model")),
        "roadmap_present": all(k in (narrative.get("roadmap") or {}) for k in ("month_1", "month_2", "month_3")),
        # Phase H sign-off payload: the prescriptive Foundation the founder approves
        "foundation_present": all((narrative.get("foundation") or {}).get(k) for k in
                                  ("positioning_statement", "value_prop", "pillars", "icp", "north_star"))
                              and bool((narrative.get("foundation") or {}).get("voice", {}).get("personality")),
        # data integrity
        "brand_is_centered": bool(narrative.get("starting_line")) and bool(narrative.get("where_you_stand")),
        "has_real_brand_data": bi.get("status") == "ok" and bi.get("followers") is not None,
        "has_real_evidence": any(c.get("provenance", {}).get("tag") == "REAL" for c in scores["channels"]),
        "ad_signal_assessed": any(c["channel"].startswith("Meta Ads") for c in scores["channels"]),
        # Honest-absence: the report surfaces at least one real gap rather than papering over it —
        # an absent channel, locked demographics (tiny account), OR a named empty/white-space lane.
        "honest_absence": bool(scores.get("channels_absent"))
        or bi.get("demographics_status") == "locked_under_100_followers"
        or bool(narrative.get("white_space")),
        "no_ai_filler": not _has_filler(narrative),
    }
    return {"passed": all(checks.values()), "checks": checks}


# ───────────────────────────────────────── assembly
def generate(slug: str, render_pdf: bool = True) -> dict:
    from agents.intel import audit_signals

    brand, intel, scores, profile = _load(slug)
    benchmark = _benchmark(brand, intel, scores)
    signals = audit_signals.build(brand, intel, scores, profile)
    # per-competitor + category rollups: computed once, fed to BOTH the Opus facts and the
    # renderer (stashed in signals) so the deterministic chips match the prose exactly.
    comps_detail = _competitors_detail(intel, signals, benchmark)
    cat = _category_facts(signals, benchmark, comps_detail)
    signals["competitors_detail"] = comps_detail
    signals["category_facts"] = cat
    narrative, res = _generate(brand, benchmark, scores, profile, signals, comps_detail, cat)
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
    json_path = out_dir / f"{ts}_brand_book_{VERSION}.json"
    report["_output_path"] = str(json_path)  # consumed by the Phase-H gate plumbing

    # Render the PDF BEFORE persisting the JSON so _pdf_path/_output_path end up IN the
    # written file — the /brand-book/pdf route reads _pdf_path from it. Writing the JSON
    # first left _pdf_path=None on disk → "PDF not available" even though it rendered fine.
    if render_pdf:
        pdf = out_dir / f"{ts}_brand_book_{VERSION}.pdf"
        try:
            report["_pdf_path"] = str(render_v7(report, intel, _palette(slug), pdf))
        except Exception as e:
            import traceback
            report["_pdf_error"] = f"{e}\n{traceback.format_exc()[:800]}"

    json_path.write_text(
        header + "\n---\n" + json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
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
