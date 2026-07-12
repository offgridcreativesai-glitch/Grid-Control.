"""
agents/intel/reputation.py — GRID CONTROL reputation engine (gap #5, Jul 12 2026).

"What's this brand's star rating, and where are the bad reviews?" — the reputation/reviews
capability GC was missing (Birdeye's whole game, scoped to our D2C/founder wedge). Reuses the
already-wired Bright Data SERP feed (no new data source, no dataset_id to guess — RULE ZERO):
runs review-focused Google queries, reads the rich-snippet star rating + review count Google
surfaces for review pages (Trustpilot / G2 / Google / MouthShut / AmbitionBox / Yelp ...),
falls back to parsing them out of the snippet text, and rolls it up into an overall rating,
a per-platform breakdown, and the negative reviews that need a response.

Zero-assumption / Rule 10: REAL SERP data only, never invented. Rating parse is transparent
regex (Class-1 pure-math, no LLM). Cost-gated by paid_ops (SERP is a paid call; free tier
5K/mo covers our volume).

ponytail: reads ratings from SERP rich snippets, not a dedicated per-platform reviews scraper.
Ceiling: no individual review text / per-review response drafting. Upgrade path = add a BD
reviews dataset (Trustpilot/Google Maps) once a dataset_id is confirmed from the dashboard.

Writes brands/<slug>/reputation.json. Usage: python3 agents/intel/reputation.py [slug]
"""
from __future__ import annotations

import json
import os
import re
import sys
from datetime import datetime, timezone

_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from agents.intel.social_listening import _profile, _sentiment, _dom, _own_domain  # reuse

# Review platforms we recognize + a friendly label for the cockpit.
_PLATFORMS = {
    "trustpilot": "Trustpilot", "g2.com": "G2", "yelp": "Yelp", "capterra": "Capterra",
    "ambitionbox": "AmbitionBox", "mouthshut": "MouthShut", "sitejabber": "Sitejabber",
    "glassdoor": "Glassdoor", "google.com": "Google", "productreview": "ProductReview",
    "amazon.": "Amazon", "flipkart": "Flipkart", "play.google": "Play Store",
    "apps.apple": "App Store", "facebook.com": "Facebook",
}

# "4.3 out of 5", "4.3/5", "Rated 4.5", "4.2 ★", "4,1 stars"
_RATING_RE = re.compile(r"(\d(?:[.,]\d)?)\s*(?:out of\s*5|/\s*5|stars?|★|of 5)", re.I)
# "1,234 reviews", "based on 512 reviews", "(89 ratings)"
_COUNT_RE = re.compile(r"([\d,]{1,9})\s*(?:reviews?|ratings?)", re.I)


def _platform_of(domain: str) -> str | None:
    d = (domain or "").lower()
    for key, label in _PLATFORMS.items():
        if key in d:
            return label
    return None


def _num(v):
    """Coerce a rating/count field or matched string to a float, or None."""
    if v is None:
        return None
    try:
        return float(str(v).replace(",", "").strip())
    except (TypeError, ValueError):
        return None


def _parse_rating(item: dict) -> float | None:
    r = _num(item.get("rating"))
    if r is not None and 0 < r <= 5:
        return round(r, 1)
    m = _RATING_RE.search(f"{item.get('title','')} {item.get('snippet','')}")
    if m:
        r = _num(m.group(1))
        if r is not None and 0 < r <= 5:
            return round(r, 1)
    return None


def _parse_count(item: dict) -> int | None:
    c = _num(item.get("reviews_cnt"))
    if c is not None and c >= 0:
        return int(c)
    m = _COUNT_RE.search(f"{item.get('title','')} {item.get('snippet','')}")
    if m:
        c = _num(m.group(1))
        if c is not None:
            return int(c)
    return None


def run(slug: str, per_query: int = 15) -> dict:
    bp = _profile(slug)
    name = (bp.get("brand_name") or bp.get("name") or "").strip()
    if not name:
        return {"status": "no_brand_identity", "note": "brand_profile has no name to search reviews for"}

    # Cost gate — SERP is a paid call.
    try:
        from agents._lib import paid_ops
        _ok, _reason = paid_ops.check("brightdata:serp")
    except Exception as e:
        _ok, _reason = False, f"paid_ops unavailable ({e})"
    if not _ok:
        return {"status": "blocked", "note": f"paid-ops off — {_reason}", "brand_slug": slug}

    from agents._lib._brightdata_client import get_brightdata
    bd = get_brightdata()
    if not bd.enabled:
        return {"status": "no_provider", "note": "BRIGHTDATA_API_TOKEN not set"}

    queries = [f'"{name}" reviews', f'"{name}" trustpilot',
               f'"{name}" google reviews', f'"{name}" rating']
    own = _own_domain(bp)

    # One entry per review platform (best/most-reviewed hit wins for that platform).
    platforms: dict[str, dict] = {}
    needs_response: list[dict] = []
    seen_links: set[str] = set()
    for q in queries:
        res = bd.serp_search(q, num=per_query)
        if not res.get("ok"):
            continue
        for item in (res.get("results") or []):
            link = item.get("link") or ""
            if not link or link in seen_links:
                continue
            seen_links.add(link)
            domain = _dom(link)
            if own and own in domain:
                continue  # the brand's own site isn't third-party reputation
            label = _platform_of(domain)
            if not label:
                continue
            rating = _parse_rating(item)
            count = _parse_count(item)
            sent = _sentiment(f"{item.get('title','')} {item.get('snippet','')}")
            row = {"platform": label, "domain": domain, "url": link,
                   "rating": rating, "reviews": count, "sentiment": sent,
                   "title": item.get("title", ""), "snippet": item.get("snippet", "")}
            prev = platforms.get(label)
            # keep the entry with the most reviews (most authoritative listing)
            if prev is None or (count or 0) > (prev.get("reviews") or 0):
                platforms[label] = row
            if sent == "negative" or (rating is not None and rating < 3.0):
                needs_response.append(row)

    plist = list(platforms.values())
    rated = [p for p in plist if p.get("rating") is not None]
    # weighted by review count where known, else simple mean of found ratings
    wsum = sum(p["rating"] * ((p.get("reviews") or 1)) for p in rated)
    wcnt = sum((p.get("reviews") or 1) for p in rated)
    overall = round(wsum / wcnt, 1) if wcnt else None
    total_reviews = sum(p.get("reviews") or 0 for p in plist)

    return {
        "status": "ok",
        "brand_slug": slug,
        "collected_at": datetime.now(timezone.utc).isoformat(),
        "source": "Bright Data SERP API (review-site rich snippets)",
        "queries": queries,
        "overall_rating": overall,
        "platforms_found": len(plist),
        "total_reviews": total_reviews,
        "platforms": sorted(plist, key=lambda p: (p.get("rating") is None, -(p.get("reviews") or 0))),
        "needs_response": needs_response[:20],
    }


def _selfcheck():  # ponytail: offline check of the rating/count parsers
    assert _parse_rating({"snippet": "Rated 4.5 out of 5 based on 200 reviews"}) == 4.5
    assert _parse_rating({"rating": "4.2"}) == 4.2
    assert _parse_rating({"snippet": "no rating here"}) is None
    assert _parse_count({"snippet": "based on 1,234 reviews"}) == 1234
    assert _parse_count({"reviews_cnt": "89"}) == 89
    assert _platform_of("uk.trustpilot.com") == "Trustpilot"
    assert _platform_of("randomsite.com") is None
    print("reputation self-check ok")


def main():
    if len(sys.argv) > 1 and sys.argv[1] == "selftest":
        return _selfcheck()
    slug = sys.argv[1] if len(sys.argv) > 1 else os.getenv("ACTIVE_BRAND", "")
    if not slug:
        sys.exit("usage: reputation.py <brand_slug>")
    data = run(slug)
    if data.get("status") != "ok":
        print(f"[reputation] {slug}: {data.get('status')} — {data.get('note','')}")
        return
    path = os.path.join(_ROOT, "brands", slug, "reputation.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    print(f"[reputation] {slug}: overall={data['overall_rating']} across "
          f"{data['platforms_found']} platforms · {data['total_reviews']} reviews · "
          f"{len(data['needs_response'])} need response")
    print(f"  → brands/{slug}/reputation.json")


if __name__ == "__main__":
    main()
