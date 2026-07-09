"""
audit_signals.py — GRID CONTROL · Brand-Book v8 (full brand-audit).
Deterministic (Class-1, pure-math/regex) signal layer for the brand-audit report.

Closes the Frontify + BrandAuditors gap: beyond channel verdicts, it extracts the
brand-audit substance — role-model vs competitor framing, the reverse-engineered
"how the winners win" playbook (hooks + the comment-to-DM CTA mechanic), the
internal-identity-vs-external-image coherence gap, a target-audience profile, and an
impact/effort triage that seeds the 90-day roadmap.

NO LLM. Reads brand_self_v7.json + competitor_intel_v7.json + channel_scores_v7.json
+ brand_profile.json. Returns a dict the assembly hands to the one Opus narrative call.

Framing (locked, see memory feedback_role_model_vs_competitors):
  ROLE MODEL  = the full-funnel operator the brand climbs toward (Gary Vee).
  COMPETITORS = the single-channel peers it beats now (Manthan/Sean/Gobi).
"""
from __future__ import annotations

import re

# CTA mechanic detection — the "comment <keyword> and I'll DM you" lead funnel.
_KEYWORD_CTA = re.compile(r'comment[s]?\s+["“‘\']([A-Za-z]+)', re.I)
_GENERIC_CTA = re.compile(r'\b(comment\s+to\b|comment\s+below|dm\s+me|dm\s+to|link\s+in\s+bio)', re.I)
_PASSIVE_CTA = re.compile(r'\b(follow\s+if|follow\s+for|save\s+this|share\s+this|tag\s+a)', re.I)


def _split_tiers(scores: dict):
    """Internal structural split → audit framing. leader=ROLE MODEL, peers=COMPETITORS."""
    t = scores.get("tiers", {})
    return t.get("peers", []), (t.get("leaders", []) or [None])[0]


def _classify_cta(caption: str) -> str:
    if not caption:
        return "none"
    if _KEYWORD_CTA.search(caption):
        return "keyword_funnel"      # strongest: comment a specific word → DM
    if _GENERIC_CTA.search(caption):
        return "generic_funnel"      # comment/dm, no keyword
    if _PASSIVE_CTA.search(caption):
        return "passive"             # follow/save — no lead capture
    return "none"


# ───────────────────────────────── the HOW playbook (reverse-engineered)
def playbook(intel: dict, scores: dict) -> dict:
    competitors, _role_model = _split_tiers(scores)
    per_comp, all_hooks, keyword_examples = [], [], []
    funnel_users = 0

    for h in competitors:
        ig = (intel["competitors"].get(h, {}) or {}).get("instagram", {})
        posts = ig.get("top_posts", []) or []
        ctas, hooks = [], []
        for p in posts:
            cap = (p.get("caption") or "").strip()
            cls = _classify_cta(cap)
            ctas.append(cls)
            first = cap.split("\n")[0][:90] if cap else ""
            if first:
                hooks.append({"hook": first, "comments": p.get("comments", 0), "likes": p.get("likes", 0)})
            for kw in _KEYWORD_CTA.findall(cap):
                keyword_examples.append({"handle": h, "keyword": kw,
                                         "comments": p.get("comments", 0),
                                         "snippet": cap[:80]})
        runs_funnel = any(c in ("keyword_funnel", "generic_funnel") for c in ctas)
        if runs_funnel:
            funnel_users += 1
        per_comp.append({
            "handle": h,
            "avg_comments": round(ig.get("avg_comments", 0), 1),
            "avg_likes": round(ig.get("avg_likes", 0), 1),
            "comment_to_like": round((ig.get("avg_comments", 0) / ig.get("avg_likes", 1)), 2)
            if ig.get("avg_likes") else 0,
            "runs_comment_funnel": runs_funnel,
            "cta_pattern": max(set(ctas), key=ctas.count) if ctas else "none",
            "top_hooks": sorted(hooks, key=lambda x: x["comments"], reverse=True)[:3],
        })
        all_hooks.extend(hooks)

    return {
        "competitors": per_comp,
        "funnel_adoption": f"{funnel_users}/{len(competitors)}",
        "keyword_cta_examples": sorted(keyword_examples, key=lambda x: x["comments"], reverse=True)[:6],
        "top_category_hooks": sorted(all_hooks, key=lambda x: x["comments"], reverse=True)[:6],
        "the_mechanic": "comment a specific keyword → auto-DM the resource",
    }


# ───────────────────────────────── identity coherence (internal vs external)
def identity(profile: dict, brand: dict) -> dict:
    bi = brand["instagram"]
    bio = bi.get("biography") or ""
    posts = bi.get("posts", []) or []
    # external signal = what the live account actually does
    cta_classes = [_classify_cta(p.get("caption", "")) for p in posts]
    runs_funnel = any(c in ("keyword_funnel", "generic_funnel") for c in cta_classes)
    fmt = bi.get("format_mix", {}) or {}
    video_share = fmt.get("VIDEO", 0) / max(1, sum(fmt.values()))

    gaps = []
    if not runs_funnel:
        gaps.append("No comment-to-DM funnel on any live post — the category's core conversion mechanic is absent.")
    if video_share < 0.5:
        gaps.append(f"Only {round(video_share*100)}% of posts are video; the category is ~100% Reels.")
    if (bi.get("avg_comments") or 0) == 0:
        gaps.append("Zero comments across all posts — no two-way conversation started yet.")
    return {
        "positioning_wedge": profile.get("positioning_wedge"),
        "brand_architecture": profile.get("brand_architecture"),
        "tone_of_voice": profile.get("tone_of_voice"),
        "what_to_never_say": profile.get("what_to_never_say"),
        "bio": bio,
        "external_signal": {
            "post_cta_patterns": cta_classes,
            "runs_funnel": runs_funnel,
            "video_share_pct": round(video_share * 100),
        },
        "identity_gaps": gaps,
    }


# ───────────────────────────────── target audience profile
def audience(profile: dict, brand: dict) -> dict:
    bi = brand["instagram"]
    return {
        "demographics_status": bi.get("demographics_status"),
        "real_demographics": bi.get("demographics") or {},
        "stated_target": profile.get("target_audience"),
        "perception_read": {
            "own_comments": bi.get("avg_comments"),
            "own_saves": bi.get("total_saves"),
            "signal": "No audience conversation yet (0 comments, 0 saves) — perception is unformed; "
                      "this audit sets the first impression deliberately."
            if not (bi.get("avg_comments") or bi.get("total_saves")) else "Early engagement signal present.",
        },
    }


# ───────────────────────────────── impact/effort triage → 90-day seed
def triage(scores: dict, identity_sig: dict) -> dict:
    """Impact/Effort matrix (BrandAuditors Phase 1) over the concrete moves."""
    quick_wins, strategic, later = [], [], []
    # quick win: add the keyword CTA (low effort, high impact — fixes the #1 gap)
    if not identity_sig["external_signal"]["runs_funnel"]:
        quick_wins.append("Add a 'comment <keyword> → I DM you' CTA to every Reel — the category's proven lead mechanic.")
    if identity_sig["external_signal"]["video_share_pct"] < 100:
        quick_wins.append("Shift all posts to Reels — the category is ~100% short-video.")
    # strategic: the GAP channels (high effort, high impact, sequence-gated)
    for c in scores.get("channels", []):
        if c.get("is_gap") and c["channel"].startswith("Meta"):
            strategic.append("Add paid retargeting on Meta once the organic funnel converts — uncontested by peers.")
        elif c.get("is_gap"):
            later.append("Open a YouTube long-form channel later — the role-model's lane, but only after Instagram traction.")
    return {"quick_wins": quick_wins, "strategic_shifts": strategic, "later": later}


def website(brand: dict, intel: dict) -> dict:
    """Website positioning signals — own site vs competitors (platform, tagline,
    positioning line, price band). Feeds the narrative so the report compares where
    each brand sells and how it's priced, not just its social presence."""
    def _sig(w: dict) -> dict | None:
        if not isinstance(w, dict) or w.get("status") != "ok":
            return None
        tagline = next((h for h in (w.get("h1") or []) if h and "root" not in h.lower()
                        and "{" not in h), "")
        return {
            "url": w.get("url"),
            "platform": w.get("platform"),
            "tagline": tagline[:120],
            "positioning": (w.get("description") or w.get("og_title") or w.get("title") or "")[:220],
            "price_signals": (w.get("price_signals") or [])[:5],
        }
    own = _sig(((brand.get("other_channels") or {}).get("website") or {}))
    comps = {}
    for h, c in (intel.get("competitors") or {}).items():
        s = _sig(c.get("website"))
        if s:
            comps[h] = s
    return {"own": own, "competitors": comps,
            "note": "homepage signals (title/meta/H1/price) — free HTTP, no headless render"}


def build(brand: dict, intel: dict, scores: dict, profile: dict) -> dict:
    competitors, role_model = _split_tiers(scores)
    ident = identity(profile, brand)
    return {
        "framing": {"role_model": role_model, "competitors": competitors},
        "playbook": playbook(intel, scores),
        "identity": ident,
        "audience": audience(profile, brand),
        "triage": triage(scores, ident),
        "website": website(brand, intel),
    }
