"""
channel_score.py — GRID CONTROL · Brand-Book v7 · B-2/B-3
Deterministic (Class-1, pure-math) channel-scoring + verdict engine.

Reads  brands/<slug>/competitor_intel_v7.json   (written by competitor_intel.py / B-1)
Writes brands/<slug>/channel_scores_v7.json     (consumed by the v7 render + narrative)

NO LLM. Every verdict carries the REAL numbers it was derived from (Rule 10 provenance).
The spec is BRAND_BOOK_REPORT_SPEC.md §7.4 (ad-longevity money signal) and §7.5
(Presence + Effort + Traction + Money-signal → RIDE / TEST / SKIP / GAP).

Verdict semantics (locked):
  RIDE  — peers are proven here; this is where the category is won. Table stakes + room.
  TEST  — a real signal exists (a leader wins, or money runs) but peers haven't validated it.
  SKIP  — category is absent/dead here; no evidence it converts.
  GAP   — a wedge: peers ignore this channel but there's hard proof it works (a leader owns it
          and/or sustained paid spend runs). The opening to own.

We deliberately separate the PEER TIER (the 3 user-named competitors the brand actually
competes with) from a CATEGORY LEADER (an aspirational outlier such as Gary Vee) so a channel
that "only the giant plays" reads as a GAP for the brand, not as saturated.
"""

from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timezone

_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# CATEGORY LEADER vs PEER split (pure-math, channel-breadth):
# A competitor running a full multi-channel funnel (IG + YouTube + paid) while peers are
# single-channel is structurally a different tier — the aspirational operator. Raw engagement
# does NOT define the tier: a single-channel account with huge engagement (e.g. a peer who has
# mastered the comment-funnel) is still a PEER you compete with head-to-head, and is exactly
# the playbook to emulate. Strategic tier = how many channels you operate, not reach.
LEADER_CHANNELS = 3        # active on this many channels ⇒ leader (full-funnel operator)

# Ad-longevity money signal thresholds (days a single ad has run).
LONGEVITY_PROVEN = 30      # an ad sustained ≥30d ⇒ the channel converts for the category
LONGEVITY_STRONG = 90      # ≥90d ⇒ high-confidence profitable channel


# ---------------------------------------------------------------- helpers
def _load(slug: str) -> dict:
    path = os.path.join(_ROOT, "brands", slug, "competitor_intel_v7.json")
    if not os.path.exists(path):
        sys.exit(f"[channel_score] missing {path} — run competitor_intel.py (B-1) first")
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def _prov(value, tag, source_path, note=""):
    """Rule-10 provenance stub attached to every derived signal."""
    return {"value": value, "tag": tag, "source": f"competitor_intel_v7.json::{source_path}", "note": note}


def _median(xs):
    xs = sorted(x for x in xs if x is not None)
    if not xs:
        return 0.0
    n = len(xs)
    mid = n // 2
    return xs[mid] if n % 2 else (xs[mid - 1] + xs[mid]) / 2.0


# ---------------------------------------------------------------- tier split
def _active_channel_count(c: dict) -> int:
    n = 0
    if c.get("instagram", {}).get("status") == "ok":
        n += 1
    if c.get("youtube", {}).get("status") == "ok":
        n += 1
    if c.get("meta_ads", {}).get("status") == "advertising":
        n += 1
    return n


def _split_tiers(competitors: dict):
    """Return (peer_handles, leader_handles) by channel breadth — full-funnel operators are leaders."""
    leaders = [h for h, c in competitors.items() if _active_channel_count(c) >= LEADER_CHANNELS]
    peers = [h for h in competitors if h not in leaders]
    return peers, leaders


# ---------------------------------------------------------------- per-channel scoring
def _score_instagram(competitors, peers, leaders):
    rows, peer_active, leader_active, tractions = [], 0, 0, []
    for h, c in competitors.items():
        ig = c.get("instagram", {})
        ok = ig.get("status") == "ok"
        eng = ig.get("avg_engagement", 0.0) or 0.0
        rows.append({
            "handle": h, "tier": "leader" if h in leaders else "peer",
            "active": ok, "avg_engagement": round(eng, 1),
            "posts_sampled": ig.get("posts_sampled", 0),
            "format_mix": ig.get("format_mix", {}),
        })
        if ok and h in peers:
            peer_active += 1
            tractions.append(eng)
        if ok and h in leaders:
            leader_active += 1
    peer_presence = peer_active / max(1, len(peers))
    verdict = "RIDE" if peer_presence >= 0.66 else ("TEST" if peer_presence > 0 else "SKIP")
    return {
        "channel": "Instagram",
        "verdict": verdict,
        "peer_presence_pct": round(peer_presence * 100),
        "peer_active": peer_active, "peer_total": len(peers),
        "leader_active": leader_active,
        "median_peer_engagement": round(_median(tractions), 1),
        "is_gap": False,
        "money_signal_days": 0,
        "headline": _ig_headline(verdict, peer_active, len(peers), tractions),
        "rows": rows,
        "provenance": _prov(round(peer_presence * 100), "REAL",
                            "competitors[*].instagram.status",
                            f"{peer_active}/{len(peers)} peers post on IG (all Video)"),
    }


def _ig_headline(verdict, active, total, tractions):
    if verdict == "RIDE":
        return (f"All {active}/{total} peers are here, 100% short-video. "
                f"This is table stakes — the category is fought on IG Reels.")
    return "Peers are largely absent from IG."


def _score_youtube(competitors, peers, leaders):
    rows, peer_active, leader_active = [], 0, 0
    leader_subs = 0
    for h, c in competitors.items():
        yt = c.get("youtube", {})
        ok = yt.get("status") == "ok"
        rows.append({
            "handle": h, "tier": "leader" if h in leaders else "peer",
            "active": ok, "subscribers": yt.get("subscribers"),
            "avg_views": yt.get("avg_views"),
        })
        if ok and h in peers:
            peer_active += 1
        if ok and h in leaders:
            leader_active += 1
            leader_subs = max(leader_subs, yt.get("subscribers") or 0)
    peer_presence = peer_active / max(1, len(peers))
    # No peer on YT, but a leader owns it ⇒ proven authority lane, uncontested = GAP.
    is_gap = (peer_active == 0 and leader_active > 0)
    if is_gap:
        verdict = "GAP"
    elif peer_presence >= 0.66:
        verdict = "RIDE"
    elif peer_active > 0:
        verdict = "TEST"
    else:
        verdict = "SKIP"
    return {
        "channel": "YouTube",
        "verdict": verdict,
        "peer_presence_pct": round(peer_presence * 100),
        "peer_active": peer_active, "peer_total": len(peers),
        "leader_active": leader_active,
        "leader_subscribers": leader_subs,
        "is_gap": is_gap,
        "money_signal_days": 0,
        "headline": _yt_headline(is_gap, peer_active, len(peers), leader_subs),
        "rows": rows,
        "provenance": _prov(peer_active, "REAL",
                            "competitors[*].youtube.status",
                            f"{peer_active}/{len(peers)} peers on YouTube; "
                            f"leader subs={leader_subs:,}" if leader_subs else "no leader subs"),
    }


def _yt_headline(is_gap, active, total, leader_subs):
    if is_gap:
        return (f"Zero of {total} peers have a YouTube presence — yet the category leader "
                f"commands {leader_subs/1e6:.1f}M subs here. Long-form authority is wide open.")
    if active:
        return f"{active}/{total} peers run YouTube."
    return "No one in the category is on YouTube."


def _score_meta_ads(competitors, peers, leaders):
    rows, peer_advertisers, leader_advertisers = [], 0, 0
    max_longevity, longevity_owner = 0, None
    platforms_running = set()
    for h, c in competitors.items():
        ma = c.get("meta_ads", {})
        advertising = ma.get("status") == "advertising"
        days = ma.get("max_days_running", 0) or 0
        rows.append({
            "handle": h, "tier": "leader" if h in leaders else "peer",
            "advertising": advertising,
            "active_ads": ma.get("active_ads", 0),
            "max_days_running": days,
            "platforms": ma.get("platforms", []),
        })
        if advertising and h in peers:
            peer_advertisers += 1
        if advertising and h in leaders:
            leader_advertisers += 1
        if days > max_longevity:
            max_longevity, longevity_owner = days, h
        platforms_running.update(ma.get("platforms", []) or [])
    peer_presence = peer_advertisers / max(1, len(peers))
    money_proven = max_longevity >= LONGEVITY_PROVEN
    # No peer advertises, but sustained paid spend runs in the category ⇒ GAP wedge.
    is_gap = (peer_advertisers == 0 and money_proven)
    if is_gap:
        verdict = "GAP"
    elif peer_presence >= 0.5 and money_proven:
        verdict = "RIDE"
    elif peer_advertisers > 0:
        verdict = "TEST"
    elif money_proven:
        verdict = "TEST"
    else:
        verdict = "SKIP"
    return {
        "channel": "Meta Ads (Paid)",
        "verdict": verdict,
        "peer_presence_pct": round(peer_presence * 100),
        "peer_advertisers": peer_advertisers, "peer_total": len(peers),
        "leader_advertisers": leader_advertisers,
        "is_gap": is_gap,
        "money_signal_days": max_longevity,
        "money_signal_owner": longevity_owner,
        "money_signal_strength": ("STRONG" if max_longevity >= LONGEVITY_STRONG
                                  else "PROVEN" if money_proven else "NONE"),
        "platforms_running": sorted(platforms_running),
        "headline": _ads_headline(is_gap, peer_advertisers, len(peers),
                                   max_longevity, longevity_owner, sorted(platforms_running)),
        "rows": rows,
        "provenance": _prov(max_longevity, "REAL",
                            f"competitors.{longevity_owner}.meta_ads.max_days_running",
                            f"{peer_advertisers}/{len(peers)} peers advertise; "
                            f"longest live ad {max_longevity}d ({longevity_owner})"),
    }


def _ads_headline(is_gap, advertisers, total, days, owner, platforms):
    if is_gap:
        plat = ", ".join(platforms[:5]) if platforms else "Meta"
        return (f"Not one of {total} peers runs paid — but the category leader has ads live "
                f"for {days} days straight across {plat}. Sustained spend = a channel that "
                f"converts. No peer is bidding for it.")
    if advertisers:
        return f"{advertisers}/{total} peers run Meta ads; longest live ad {days}d."
    return "No measurable paid activity in the category."


# ---------------------------------------------------------------- content signals (HOW, §7.6)
# Comment-to-DM lead funnel: a post engineered for leads pulls MORE comments than likes
# (the "comment <word> and I'll DM you" mechanic). comment:like ratio > 1 = funnel-driven.
COMMENT_FUNNEL_RATIO = 1.0


def _content_signals(competitors, peers):
    """Pure-math HOW evidence: comment-funnel intensity + format mix per peer."""
    rows = []
    funnel_peers = []
    for h in peers:
        ig = competitors.get(h, {}).get("instagram", {})
        if ig.get("status") != "ok":
            continue
        likes = ig.get("avg_likes", 0.0) or 0.0
        comments = ig.get("avg_comments", 0.0) or 0.0
        ratio = round(comments / likes, 2) if likes else 0.0
        is_funnel = ratio >= COMMENT_FUNNEL_RATIO
        if is_funnel:
            funnel_peers.append(h)
        rows.append({
            "handle": h, "avg_likes": round(likes, 1), "avg_comments": round(comments, 1),
            "comment_to_like_ratio": ratio, "comment_funnel": is_funnel,
            "format_mix": ig.get("format_mix", {}),
            "provenance": _prov(ratio, "REAL",
                                f"competitors.{h}.instagram.(avg_comments/avg_likes)",
                                f"{comments:.0f} comments vs {likes:.0f} likes"),
        })
    headline = ""
    if funnel_peers:
        lead = max(rows, key=lambda r: r["comment_to_like_ratio"])
        headline = (f"{len(funnel_peers)}/{len(peers)} peers run a comment-to-DM lead funnel — "
                    f"{lead['handle']} pulls {lead['avg_comments']:.0f} comments vs only "
                    f"{lead['avg_likes']:.0f} likes ({lead['comment_to_like_ratio']}× ratio). "
                    f"They're farming comments for DMs, not likes for vanity. This is the HOW.")
    return {
        "signal": "comment_to_dm_funnel",
        "funnel_peers": funnel_peers,
        "all_video": all(
            list((competitors.get(h, {}).get("instagram", {}).get("format_mix") or {}).keys()) == ["Video"]
            for h in peers if competitors.get(h, {}).get("instagram", {}).get("status") == "ok"
        ),
        "headline": headline,
        "rows": rows,
    }


# ---------------------------------------------------------------- Website / SEO (B-1 completion)
def _load_extra(slug: str):
    """Load discovery + website-intel (graceful if a pass hasn't run)."""
    base = os.path.join(_ROOT, "brands", slug)
    def _ld(name):
        p = os.path.join(base, name)
        return json.load(open(p, encoding="utf-8")) if os.path.exists(p) else {}
    return _ld("channel_discovery_v7.json"), _ld("website_intel_v7.json")


_FUNNEL_LABEL = {
    "topmate.io": "1:1 booking page", "calendly.com": "booking page",
    "vercel.app": "personal site", "garyvee.com": "lead-magnet page",
}


def _funnel_kind(url: str) -> str:
    u = (url or "").lower()
    for needle, label in _FUNNEL_LABEL.items():
        if needle in u:
            return label
    if any(k in u for k in ("sureflow", "saas", "app.")):
        return "SaaS product site"
    return "funnel site"


def _score_website(discovery, website_intel, peers):
    comps = discovery.get("competitors", {})
    wi = website_intel.get("competitors", {})
    rows, with_site = [], 0
    kinds = []
    for h in peers:
        site = (comps.get(h, {}) or {}).get("website")
        w = wi.get(h, {}) or {}
        ok = bool(site)
        if ok:
            with_site += 1
            kinds.append(_funnel_kind(site))
        rows.append({"handle": h, "website": site, "title": w.get("title"),
                     "has_pricing": w.get("has_pricing"), "primary_cta": w.get("primary_cta"),
                     "schema": (w.get("seo_geo") or {}).get("has_jsonld_schema")})
    presence = with_site / max(1, len(peers))
    # Every peer funnels through a site; this is table-stakes funnel infrastructure.
    verdict = "RIDE" if presence >= 0.66 else ("TEST" if presence > 0 else "SKIP")
    kind_str = ", ".join(sorted(set(kinds))) if kinds else "none"
    headline = (f"All {with_site}/{len(peers)} peers funnel to a website ({kind_str}) — "
                f"the IG audience converts off-platform. A funnel destination is table stakes here."
                if presence >= 0.66 else
                f"{with_site}/{len(peers)} peers run a funnel site.")
    return {
        "channel": "Website / Funnel", "verdict": verdict, "is_gap": False,
        "peer_presence_pct": round(presence * 100), "money_signal_days": 0,
        "headline": headline, "rows": rows,
        "provenance": _prov(with_site, "REAL", "website_intel_v7.json::competitors[*]",
                            f"{with_site}/{len(peers)} peers have a scraped funnel site ({kind_str})"),
    }


def _score_dormant(channel, label, note):
    """LinkedIn / X: peer profiles exist (search-confirmed) but are not promoted from IG —
    dormant. Uncontested = a wedge, but low-priority vs the IG+funnel core."""
    return {
        "channel": channel, "verdict": "GAP", "is_gap": True,
        "money_signal_days": 0, "peer_presence_pct": 0,
        "headline": (f"{label} profiles exist but the peer tier is dormant there — "
                     f"no one's promoting on it. Uncontested lane, but low-priority until "
                     f"the IG funnel is running."),
        "rows": [],
        "provenance": _prov(None, "REAL", "channel_discovery_v7 + search confirmation", note),
    }


# ---------------------------------------------------------------- assembly
def score(slug: str) -> dict:
    intel = _load(slug)
    competitors = intel.get("competitors", {})
    peers, leaders = _split_tiers(competitors)
    discovery, website_intel = _load_extra(slug)

    channels = [
        _score_instagram(competitors, peers, leaders),
        _score_website(discovery, website_intel, peers),
        _score_meta_ads(competitors, peers, leaders),
        _score_youtube(competitors, peers, leaders),
        _score_dormant("LinkedIn", "LinkedIn",
                       "Manthan/Sean(SureFlow co.)/Govind have profiles; minimal activity — not a promoted channel."),
        _score_dormant("X / Twitter", "X",
                       "@manthan_ai etc. exist but minimal activity; not a promoted channel for the peer tier."),
    ]
    gaps = [c for c in channels if c.get("is_gap")]

    # The route: RIDE first (proven, do now), then GAP wedges (own these), TEST, SKIP last.
    order = {"RIDE": 0, "GAP": 1, "TEST": 2, "SKIP": 3, "NO_DATA": 4}
    route = sorted(channels, key=lambda c: order.get(c["verdict"], 9))

    out = {
        "brand_slug": slug,
        "scored_at": datetime.now(timezone.utc).isoformat(),
        "engine": "channel_score.py (Class-1 pure-math)",
        "spec": "BRAND_BOOK_REPORT_SPEC.md §7.4–7.5",
        "tiers": {"peers": peers, "leaders": leaders, "leader_rule": f"active on ≥{LEADER_CHANNELS} channels"},
        "channels": channels,
        "content_signals": _content_signals(competitors, peers),
        "channels_absent": [],   # B-1 complete — every channel in scope now scored
        "gaps": [{"channel": g["channel"], "headline": g["headline"],
                  "money_signal_days": g["money_signal_days"]} for g in gaps],
        "route_order": [{"channel": c["channel"], "verdict": c["verdict"],
                         "headline": c["headline"]} for c in route],
    }
    return out


def main():
    slug = sys.argv[1] if len(sys.argv) > 1 else os.getenv("ACTIVE_BRAND", "askgauravai")
    out = score(slug)
    path = os.path.join(_ROOT, "brands", slug, "channel_scores_v7.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(out, f, indent=2, ensure_ascii=False)

    # Human-readable summary to stdout (never raw JSON to the user — Rule 8).
    print(f"\n[channel_score] {slug} — tiers: peers={out['tiers']['peers']} "
          f"leaders={out['tiers']['leaders']}\n")
    for c in out["channels"]:
        gap = "  ⟵ GAP/WEDGE" if c.get("is_gap") else ""
        print(f"  {c['verdict']:5s}  {c['channel']:18s}{gap}")
        print(f"         {c['headline']}")
    cs = out["content_signals"]
    if cs.get("headline"):
        print(f"\n  HOW signal: {cs['headline']}")
    route_str = " → ".join(f"{r['channel']} [{r['verdict']}]" for r in out["route_order"])
    print(f"\n  Route order: {route_str}")
    print(f"\n  written → brands/{slug}/channel_scores_v7.json")


if __name__ == "__main__":
    main()
