"""
agents/intel/social_listening.py — GRID CONTROL social listening (gap #4, Jul 11 2026).

"What is the internet saying about this brand?" — the capability GC was missing. Searches the
brand's name + handle across the open web via Bright Data's SERP API (parsed Google results),
then classifies each mention by source type and a light, deterministic sentiment read, and rolls
it up into counts the cockpit can show.

Zero-assumption / Rule 10: REAL search results only (Bright Data SERP), never invented. Sentiment
is a transparent keyword lexicon (Class-1 pure-math — no LLM cost, no fabrication); a richer
LLM theme/sentiment pass can layer on later. Cost-gated by paid_ops (SERP is a paid call; free
tier 5K/mo covers our volume).

Writes brands/<slug>/social_listening.json. Usage: python3 agents/intel/social_listening.py [slug]
"""
from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timezone

_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

# Transparent sentiment lexicon — deterministic, honest, no LLM.
_POS = {"love", "loved", "best", "great", "amazing", "excellent", "quality", "premium",
        "comfortable", "recommend", "recommended", "worth", "perfect", "awesome", "favourite",
        "favorite", "beautiful", "stylish", "fast", "reliable", "happy", "impressed"}
_NEG = {"bad", "worst", "scam", "fake", "cheap", "disappointed", "disappointing", "avoid",
        "poor", "terrible", "awful", "refund", "broke", "broken", "waste", "delay", "delayed",
        "overpriced", "rude", "never", "problem", "issue", "defective", "cancel"}

_SOCIAL = ("instagram.com", "twitter.com", "x.com", "tiktok.com", "facebook.com",
           "youtube.com", "linkedin.com", "threads.net", "pinterest.com", "snapchat.com")
_FORUM = ("reddit.com", "quora.com")
_REVIEW = ("trustpilot", "g2.com", "yelp", "capterra", "ambitionbox", "mouthshut",
           "sitejabber", "glassdoor")
_NEWS = ("news", "times", "herald", "post", "reuters", "bloomberg", "forbes", "yourstory",
         "inc42", "economictimes", "hindustantimes")


def _sentiment(text: str) -> str:
    t = (text or "").lower()
    pos = sum(1 for w in _POS if w in t)
    neg = sum(1 for w in _NEG if w in t)
    if pos > neg:
        return "positive"
    if neg > pos:
        return "negative"
    return "neutral"


def _source_type(domain: str, own_domain: str) -> str:
    d = (domain or "").lower()
    if own_domain and own_domain in d:
        return "own"
    if any(s in d for s in _SOCIAL):
        return "social"
    if any(s in d for s in _FORUM):
        return "forum"
    if any(s in d for s in _REVIEW):
        return "review"
    if any(s in d for s in _NEWS):
        return "news"
    return "web"


def _profile(slug: str) -> dict:
    path = os.path.join(_ROOT, "brands", slug, "brand_profile.json")
    try:
        raw = open(path, encoding="utf-8").read()
        body = raw.split("\n---\n", 1)[1] if "\n---\n" in raw else raw
        return json.loads(body)
    except Exception:
        return {}


def _own_domain(bp: dict) -> str:
    site = (bp.get("website") or bp.get("website_url") or bp.get("url") or "").strip()
    if not site:
        return ""
    from urllib.parse import urlparse
    try:
        net = urlparse(site if site.startswith("http") else "https://" + site).netloc
        return net.replace("www.", "")
    except Exception:
        return ""


def run(slug: str, per_query: int = 15) -> dict:
    bp = _profile(slug)
    name = (bp.get("brand_name") or bp.get("name") or "").strip()
    handle = (bp.get("handle") or bp.get("instagram_handle") or "").strip().lstrip("@")
    if not name and not handle:
        return {"status": "no_brand_identity", "note": "brand_profile has no name/handle to search"}

    # Cost gate — SERP is a paid call (free tier covers our volume, but honor the kill-switch).
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

    queries = []
    if name:
        queries += [f'"{name}"', f'"{name}" review', f'"{name}" reddit']
    if handle:
        queries += [f"{handle} instagram"]
    seen_q: set = set()
    queries = [q for q in queries if not (q in seen_q or seen_q.add(q))]

    own = _own_domain(bp)
    mentions: dict[str, dict] = {}   # keyed by link (dedupe)
    for q in queries:
        res = bd.serp_search(q, num=per_query)
        if not res.get("ok"):
            continue
        for item in (res.get("results") or []) + (res.get("news") or []):
            link = item.get("link")
            if not link or link in mentions:
                continue
            domain = item.get("source_domain") or _dom(link)
            stype = _source_type(domain, own)
            if stype == "own":
                continue  # the brand's own pages aren't "what people are saying"
            text = f"{item.get('title','')} {item.get('snippet','')}"
            mentions[link] = {
                "title": item.get("title", ""),
                "link": link,
                "snippet": item.get("snippet", ""),
                "source": item.get("source") or domain,
                "source_type": stype,
                "sentiment": _sentiment(text),
                "found_via": q,
            }

    items = list(mentions.values())
    by_type: dict[str, int] = {}
    by_sentiment = {"positive": 0, "neutral": 0, "negative": 0}
    for m in items:
        by_type[m["source_type"]] = by_type.get(m["source_type"], 0) + 1
        by_sentiment[m["sentiment"]] += 1

    return {
        "status": "ok",
        "brand_slug": slug,
        "collected_at": datetime.now(timezone.utc).isoformat(),
        "source": "Bright Data SERP API (real Google results)",
        "queries": queries,
        "total_mentions": len(items),
        "by_source_type": by_type,
        "by_sentiment": by_sentiment,
        "mentions": sorted(items, key=lambda m: (m["sentiment"] != "negative", m["sentiment"] != "positive")),
    }


def _dom(url: str) -> str:
    from urllib.parse import urlparse
    try:
        return urlparse(url).netloc.replace("www.", "")
    except Exception:
        return ""


def main():
    slug = sys.argv[1] if len(sys.argv) > 1 else os.getenv("ACTIVE_BRAND", "")
    if not slug:
        sys.exit("usage: social_listening.py <brand_slug>")
    data = run(slug)
    if data.get("status") != "ok":
        print(f"[social_listening] {slug}: {data.get('status')} — {data.get('note','')}")
        return
    path = os.path.join(_ROOT, "brands", slug, "social_listening.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    print(f"[social_listening] {slug}: {data['total_mentions']} mentions · "
          f"{data['by_sentiment']} · sources {data['by_source_type']}")
    print(f"  → brands/{slug}/social_listening.json")


if __name__ == "__main__":
    main()
