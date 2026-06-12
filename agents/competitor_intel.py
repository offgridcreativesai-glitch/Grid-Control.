"""
competitor_intel.py — GRID CONTROL · Brand-Book v7 data layer (B-1)
================================================================================
Multi-platform competitor intelligence for the "WHERE + HOW to promote" report
(spec: docs/BRAND_BOOK_REPORT_SPEC.md §7).

For each user-fed competitor it scrapes the PUBLIC surfaces they actually use and
computes DETERMINISTIC, real metrics (no LLM here — Class-1):

  • Instagram      apify/instagram-scraper          → organic engagement + formats
  • Meta Ad Library brilliant_gum/facebook-ads-...  → the AD-LONGEVITY money signal
  • YouTube        streamers/youtube-channel-scraper → organic reach (best-effort)

Honesty rules (the offgrid lesson, baked in):
  • Apify error stubs (no_items / not_found / error) are NEVER counted as data.
  • Instagram hides like counts on many posts → we keep likes AND video views and
    flag coverage; a handle with only error/empty items is marked status=empty.
  • "Not active here" / "not advertising" is recorded as a real finding, not a 0.

Writes a NEW file — brands/<slug>/competitor_intel_v7.json — and touches NOTHING
else (content_calendar / voice_profile / trends_live are off-limits).

Run:  ACTIVE_BRAND=<slug> python3 agents/competitor_intel.py <slug>
"""

from __future__ import annotations
import os
import sys
import json
import time
import statistics
from datetime import datetime, timezone

import requests

APIFY_API_KEY = os.getenv("APIFY_API_KEY", "").strip()
_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Apify actor ids (REST form uses ~ instead of /)
ACTOR_IG       = "apify~instagram-scraper"
ACTOR_META_ADS = "brilliant_gum~facebook-ads-library-scraper"
ACTOR_YOUTUBE  = "streamers~youtube-channel-scraper"

# Apify items that are error stubs, never counted as real posts
_ERR_KEYS = ("error", "errorDescription")
_ERR_VALUES = ("no_items", "not_found", "not_available", "private")


def _is_error_item(it: dict) -> bool:
    if not isinstance(it, dict):
        return True
    for k in _ERR_KEYS:
        if it.get(k):
            return True
    # some actors signal an empty profile with a lone marker field
    if it.get("error") in _ERR_VALUES:
        return True
    return False


def _avg(nums: list) -> float:
    nums = [n for n in nums if isinstance(n, (int, float))]
    return round(statistics.mean(nums), 1) if nums else 0.0


# ── Apify run helpers (standalone — no CEOBrain dependency) ──────────────────
class Apify:
    def __init__(self, token: str):
        self.token = token

    def run(self, actor: str, payload: dict, *, wait_s: int = 180, poll: int = 6) -> list:
        """Start an actor run, poll to completion, return dataset items ([] on fail)."""
        if not self.token:
            print("  [apify] APIFY_API_KEY missing"); return []
        try:
            r = requests.post(
                f"https://api.apify.com/v2/acts/{actor}/runs?token={self.token}",
                json=payload, timeout=30,
            )
            if r.status_code != 201:
                print(f"  [apify] {actor} start failed http={r.status_code}"); return []
            run_id = r.json()["data"]["id"]
        except Exception as e:
            print(f"  [apify] {actor} start error: {e}"); return []

        waited = 0
        while waited < wait_s:
            time.sleep(poll); waited += poll
            try:
                s = requests.get(
                    f"https://api.apify.com/v2/actor-runs/{run_id}?token={self.token}",
                    timeout=30,
                ).json()["data"]["status"]
            except Exception:
                continue
            if s in ("SUCCEEDED", "FAILED", "ABORTED", "TIMED-OUT"):
                if s != "SUCCEEDED":
                    print(f"  [apify] {actor} run {s}"); return []
                break
        try:
            items = requests.get(
                f"https://api.apify.com/v2/actor-runs/{run_id}/dataset/items?token={self.token}",
                timeout=60,
            ).json()
            return items if isinstance(items, list) else []
        except Exception as e:
            print(f"  [apify] {actor} fetch error: {e}"); return []


# ── per-platform scrape + deterministic metrics ──────────────────────────────
class CompetitorIntel:
    def __init__(self, slug: str):
        self.slug = slug
        self.api = Apify(APIFY_API_KEY)
        self.scraped_at = datetime.now(timezone.utc).isoformat()

    # Instagram — organic engagement + formats (hidden-likes aware)
    def instagram(self, handle: str) -> dict:
        items = self.api.run(ACTOR_IG, {
            "directUrls": [f"https://www.instagram.com/{handle}/"],
            "resultsType": "posts", "resultsLimit": 24,
        })
        posts = [it for it in items if not _is_error_item(it)]
        if not posts:
            return {"status": "empty", "note": "no public posts returned (private / not found / hidden)"}
        likes  = [p.get("likesCount", 0) or 0 for p in posts]
        comm   = [p.get("commentsCount", 0) or 0 for p in posts]
        views  = [p.get("videoViewCount", 0) or 0 for p in posts if p.get("videoViewCount")]
        fmts   = {}
        for p in posts:
            fmts[p.get("type", "unknown")] = fmts.get(p.get("type", "unknown"), 0) + 1
        likes_hidden = sum(1 for l in likes if l == 0) > len(likes) * 0.5
        top = sorted(posts, key=lambda p: (p.get("likesCount", 0) or 0) + (p.get("commentsCount", 0) or 0),
                     reverse=True)[:5]
        return {
            "status": "ok",
            "posts_sampled": len(posts),
            "avg_likes": _avg(likes),
            "avg_comments": _avg(comm),
            "avg_engagement": round(_avg(likes) + _avg(comm), 1),
            "avg_video_views": _avg(views) if views else None,
            "likes_hidden": likes_hidden,
            "format_mix": fmts,
            "followers": next((p.get("ownerFollowersCount") for p in posts if p.get("ownerFollowersCount")), None),
            "top_posts": [{
                "url": p.get("url"), "type": p.get("type"),
                "likes": p.get("likesCount"), "comments": p.get("commentsCount"),
                "views": p.get("videoViewCount"),
                "thumbnail": p.get("displayUrl"),
                "caption": (p.get("caption") or "")[:160],
            } for p in top],
        }

    # Meta Ad Library — the AD-LONGEVITY money signal
    def meta_ads(self, search_term: str, page_match: str, countries=("US",)) -> dict:
        items = self.api.run(ACTOR_META_ADS, {
            "searchTerms": [search_term],
            "countries": list(countries),
            "adActiveStatus": "ACTIVE",
            "maxAds": 30,
            "resolveSnapshotUrls": True,
        })
        ads = [it for it in items if isinstance(it, dict) and it.get("adArchiveId")]
        # keep only ads from the competitor's OWN page (fuzzy match) — the rest are
        # category ads that merely mention the term
        pm = page_match.lower().replace(" ", "")
        own = [a for a in ads if pm in (a.get("pageName", "").lower().replace(" ", ""))]
        if not own:
            return {"status": "not_advertising",
                    "note": f"no ACTIVE Meta ads found under a page matching '{page_match}'",
                    "category_ads_mentioning_term": len(ads)}
        days = [a.get("daysRunning", 0) or 0 for a in own]
        platforms = sorted({p for a in own for p in (a.get("publisherPlatforms") or [])})
        creatives = []
        for a in sorted(own, key=lambda a: a.get("daysRunning", 0) or 0, reverse=True)[:5]:
            cr = (a.get("creatives") or [{}])[0] if a.get("creatives") else {}
            creatives.append({
                "days_running": a.get("daysRunning"),
                "page": a.get("pageName"),
                "media_type": a.get("mediaType"),
                "platforms": a.get("publisherPlatforms"),
                "snapshot": a.get("snapshotUrl"),
                "image": cr.get("imageUrl") or cr.get("originalImageUrl"),
                "body": (cr.get("body") or cr.get("adText") or "")[:200],
                "cta": cr.get("ctaText"),
                "link": cr.get("linkUrl"),
            })
        return {
            "status": "advertising",
            "active_ads": len(own),
            "max_days_running": max(days) if days else 0,
            "avg_days_running": _avg(days),
            "long_runners_30d_plus": sum(1 for d in days if d >= 30),
            "platforms": platforms,
            "top_ads": creatives,
        }

    # YouTube — organic reach (best-effort; handle may not resolve)
    def youtube(self, channel_handle: str) -> dict:
        items = self.api.run(ACTOR_YOUTUBE, {
            "startUrls": [{"url": f"https://www.youtube.com/@{channel_handle}"}],
            "maxResults": 12, "sortVideosBy": "POPULAR",
        }, wait_s=150)
        vids = [it for it in items if isinstance(it, dict) and (it.get("title") or it.get("id"))
                and not _is_error_item(it)]
        if not vids:
            return {"status": "empty", "note": "channel not found at @%s or no videos" % channel_handle}
        views = [v.get("viewCount", 0) or 0 for v in vids]
        subs = next((v.get("numberOfSubscribers") or v.get("channelSubscriberCount") for v in vids
                     if v.get("numberOfSubscribers") or v.get("channelSubscriberCount")), None)
        top = sorted(vids, key=lambda v: v.get("viewCount", 0) or 0, reverse=True)[:5]
        return {
            "status": "ok",
            "videos_sampled": len(vids),
            "subscribers": subs,
            "avg_views": _avg(views),
            "top_videos": [{"title": (v.get("title") or "")[:120], "views": v.get("viewCount"),
                            "url": v.get("url"), "thumbnail": v.get("thumbnailUrl")} for v in top],
        }


# Per-handle overrides — Meta Ad Library search/page names and YouTube handles
# rarely match the IG handle. Calibrated against real Ad-Library page names so the
# "advertising vs organic" signal is true, not a search-term artdefact.
_OVERRIDES: dict[str, dict] = {
    "manthanjethwani": {"ad_search": "Manthan Jethwani", "page_match": "Manthan Jethwani"},
    "seanpurvis.ai":   {"ad_search": "Sean Purvis",      "page_match": "Sean Purvis"},
    "gobi_automates":  {"ad_search": "Gobi Automates",   "page_match": "Gobi Automates"},
    "garyvee":         {"ad_search": "GaryVee",          "page_match": "Gary Vaynerchuk", "yt": "garyvee"},
}


# competitor config — handle → search/display mapping
def _competitor_config(slug: str) -> list[dict]:
    """Resolve fed competitor handles into per-platform search keys."""
    bp_path = os.path.join(_ROOT, "brands", slug, "brand_profile.json")
    raw = open(bp_path).read()
    body = raw.split("\n---\n", 1)[1] if "\n---\n" in raw else raw
    handles = json.loads(body).get("competitor_handles", [])
    out = []
    for h in handles:
        clean = h.replace("@", "").strip()
        display = clean.replace(".ai", "").replace("_", " ").replace(".", " ").title()
        cfg = {"handle": clean, "ig": clean, "yt": clean,
               "ad_search": display, "page_match": display}
        cfg.update(_OVERRIDES.get(clean, {}))
        out.append(cfg)
    return out


def run(slug: str) -> dict:
    cfg = _competitor_config(slug)
    ci = CompetitorIntel(slug)
    print(f"[competitor_intel] {slug}: {len(cfg)} competitors across IG + Meta Ads + YouTube")
    result = {"brand_slug": slug, "scraped_at": ci.scraped_at,
              "spec": "BRAND_BOOK_REPORT_SPEC.md §7 (v7)", "competitors": {}}
    for c in cfg:
        h = c["handle"]
        print(f"\n── @{h} ──")
        print("  instagram…");   ig = ci.instagram(c["ig"])
        print(f"    {ig.get('status')} | eng={ig.get('avg_engagement')} posts={ig.get('posts_sampled')}")
        print("  meta ads…");    ads = ci.meta_ads(c["ad_search"], c["page_match"])
        print(f"    {ads.get('status')} | active={ads.get('active_ads')} max_days={ads.get('max_days_running')}")
        print("  youtube…");     yt = ci.youtube(c["yt"])
        print(f"    {yt.get('status')} | subs={yt.get('subscribers')} avg_views={yt.get('avg_views')}")
        result["competitors"][h] = {"instagram": ig, "meta_ads": ads, "youtube": yt}
    out_path = os.path.join(_ROOT, "brands", slug, "competitor_intel_v7.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    print(f"\n[competitor_intel] wrote → {out_path}")
    return result


if __name__ == "__main__":
    slug = sys.argv[1] if len(sys.argv) > 1 else os.getenv("ACTIVE_BRAND", "askgauravai")
    run(slug)
