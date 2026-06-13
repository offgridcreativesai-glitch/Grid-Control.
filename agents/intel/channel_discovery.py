"""
channel_discovery.py — GRID CONTROL · Brand-Book B-1 completion · zero-assumption discovery.

Channel presence VARIES per brand (Gaurav, Jun 14): some competitors are on LinkedIn/web,
some aren't. So before scraping any new channel we DISCOVER what actually exists, per
competitor, and the downstream scrapers run only against real, found URLs. Nothing assumed.

Discovery chain (free / cheap, no per-channel spend until something is found):
  1. IG profile scrape (cheap) → externalUrl + biography + follower count.
  2. If externalUrl is a link-aggregator (Linktree / Beacons / Stan / bio.link / komi …),
     fetch it and extract every outbound link, classify by host.
  3. Else treat externalUrl as the primary website/funnel link.
  4. Parse the bio for @company handles and any inline URLs.
Output → brands/<slug>/channel_discovery_v7.json : per competitor
  {website, linkedin, x, youtube, tiktok, other[], funnel_link, followers, bio}

Honest absence: a channel not found is recorded as null, never guessed.
"""
from __future__ import annotations

import json
import os
import re
import sys
import time
from datetime import datetime, timezone
from urllib.parse import urlparse, parse_qs, unquote

import requests

_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
APIFY = os.getenv("APIFY_API_KEY", "").strip()
ACTOR_IG = "apify~instagram-scraper"

_AGGREGATORS = ("linktr.ee", "beacons.ai", "stan.store", "bio.link", "komi.io",
                "linkin.bio", "lnk.bio", "campsite.bio", "tap.bio", "many.link")

_HOST_MAP = [
    ("linkedin.com", "linkedin"),
    ("twitter.com", "x"), ("x.com", "x"),
    ("youtube.com", "youtube"), ("youtu.be", "youtube"),
    ("tiktok.com", "tiktok"),
]


def _apify(actor: str, payload: dict, wait_s: int = 120, poll: int = 5):
    if not APIFY:
        return []
    try:
        r = requests.post(f"https://api.apify.com/v2/acts/{actor}/runs?token={APIFY}",
                          json=payload, timeout=30)
        if r.status_code != 201:
            return []
        rid = r.json()["data"]["id"]
    except Exception:
        return []
    waited = 0
    while waited < wait_s:
        time.sleep(poll); waited += poll
        try:
            s = requests.get(f"https://api.apify.com/v2/actor-runs/{rid}?token={APIFY}",
                             timeout=30).json()["data"]["status"]
        except Exception:
            continue
        if s in ("SUCCEEDED", "FAILED", "ABORTED", "TIMED-OUT"):
            break
    try:
        items = requests.get(
            f"https://api.apify.com/v2/actor-runs/{rid}/dataset/items?token={APIFY}",
            timeout=60).json()
        return items if isinstance(items, list) else []
    except Exception:
        return []


def _unwrap(url: str) -> str:
    """Instagram wraps outbound links via l.instagram.com/?u=<encoded>. Unwrap them."""
    try:
        p = urlparse(url)
        if "instagram.com" in p.netloc and p.path.startswith("/"):
            q = parse_qs(p.query)
            if "u" in q:
                return unquote(q["u"][0])
    except Exception:
        pass
    return url


def _classify(url: str) -> tuple[str, str]:
    """Return (channel, clean_url). channel in linkedin/x/youtube/tiktok/website."""
    url = _unwrap(url)
    host = (urlparse(url).netloc or "").lower().replace("www.", "")
    for needle, chan in _HOST_MAP:
        if needle in host:
            return chan, url
    return "website", url


def _ig_profile(handle: str) -> dict:
    items = _apify(ACTOR_IG, {"directUrls": [f"https://www.instagram.com/{handle}/"],
                              "resultsType": "details", "resultsLimit": 1})
    return items[0] if items else {}


def _extract_links_from_page(url: str) -> list[str]:
    """Fetch an aggregator page and pull outbound links (best-effort, plain HTTP)."""
    try:
        r = requests.get(url, timeout=15, headers={"User-Agent": "Mozilla/5.0"})
        if r.status_code != 200:
            return []
        return re.findall(r'href=["\'](https?://[^"\']+)["\']', r.text)
    except Exception:
        return []


def discover_one(handle: str) -> dict:
    prof = _ig_profile(handle)
    bio = prof.get("biography") or ""
    ext = _unwrap(prof.get("externalUrl") or "")
    found = {"website": None, "linkedin": None, "x": None, "youtube": None,
             "tiktok": None, "other": [], "funnel_link": ext or None,
             "followers": prof.get("followersCount"), "bio": bio[:200],
             "company_mentions": re.findall(r'@([A-Za-z0-9_.]+)', bio)}

    candidates: list[str] = []
    if ext:
        host = (urlparse(ext).netloc or "").lower().replace("www.", "")
        if any(agg in host for agg in _AGGREGATORS):
            candidates = [_unwrap(u) for u in _extract_links_from_page(ext)]
        else:
            candidates = [ext]
    # any explicit URLs in the bio
    candidates += re.findall(r'https?://[^\s]+', bio)

    for url in candidates:
        chan, clean = _classify(url)
        host = (urlparse(clean).netloc or "").lower()
        if any(agg in host for agg in _AGGREGATORS):
            continue
        if chan in ("linkedin", "x", "youtube", "tiktok"):
            if not found[chan]:
                found[chan] = clean
        elif "instagram.com" not in host and clean:
            if not found["website"]:
                found["website"] = clean
            elif clean not in found["other"]:
                found["other"].append(clean)
    return found


def discover(slug: str, handles: list[str]) -> dict:
    out = {"brand_slug": slug, "discovered_at": datetime.now(timezone.utc).isoformat(),
           "method": "ig-bio external-link + aggregator extraction (zero-assumption)",
           "competitors": {}}
    for h in handles:
        print(f"  [discover] {h} …")
        out["competitors"][h] = discover_one(h)
    return out


def main():
    slug = sys.argv[1] if len(sys.argv) > 1 else os.getenv("ACTIVE_BRAND", "askgauravai")
    intel_path = os.path.join(_ROOT, "brands", slug, "competitor_intel_v7.json")
    handles = list(json.load(open(intel_path))["competitors"].keys()) if os.path.exists(intel_path) \
        else sys.argv[2:]
    data = discover(slug, handles)
    path = os.path.join(_ROOT, "brands", slug, "channel_discovery_v7.json")
    json.dump(data, open(path, "w", encoding="utf-8"), indent=2, ensure_ascii=False)
    print(f"\n[channel_discovery] {slug}")
    for h, d in data["competitors"].items():
        present = [c for c in ("website", "linkedin", "x", "youtube", "tiktok") if d.get(c)]
        print(f"  {h}: {(', '.join(present) or 'IG-only')} "
              f"({d.get('followers')} followers) · funnel={d.get('funnel_link')}")
    print(f"  → {path}")


if __name__ == "__main__":
    main()
