"""
Scrape YouTube channels for the same 5 creators we have IG data on.
Used to test new direction claims against YouTube content + monetization patterns.
"""
import json
import os
import sys
from pathlib import Path

import requests

APIFY_TOKEN = os.environ.get("APIFY_API_KEY")
if not APIFY_TOKEN:
    print("ERROR: APIFY_API_KEY not set"); sys.exit(1)

ROOT = Path("brands/askgauravai")

# YouTube searches — match by handle / brand name / topic
SEARCHES = [
    "manthan jethwani AI",
    "anushka AI claude",
    "vibefounder",
    "vaibhav sisinty",
    "non coder AI build",
    "build in public AI india",
]

ACTOR = "streamers~youtube-scraper"


def search_youtube(query, max_results=15):
    url = f"https://api.apify.com/v2/acts/{ACTOR}/run-sync-get-dataset-items?token={APIFY_TOKEN}"
    payload = {
        "searchQueries": [query],
        "maxResults": max_results,
        "maxResultsShorts": 0,
        "maxResultStreams": 0,
    }
    try:
        r = requests.post(url, json=payload, timeout=300)
        if r.status_code in (200, 201):
            return r.json()
        print(f"[yt-scrape] {query}: status {r.status_code}, {r.text[:200]}")
        return []
    except Exception as e:
        print(f"[yt-scrape] {query}: FAILED {e}")
        return []


def main():
    print(f"[yt-scrape] starting — {len(SEARCHES)} searches, 15 videos each")
    raw = {}
    for q in SEARCHES:
        print(f"[yt-scrape] {q!r}...")
        results = search_youtube(q, 15)
        if results:
            cleaned = [
                {
                    "title": v.get("title"),
                    "url": v.get("url"),
                    "channel": v.get("channelName"),
                    "channel_url": v.get("channelUrl"),
                    "views": v.get("viewCount"),
                    "likes": v.get("likes"),
                    "duration": v.get("duration"),
                    "duration_seconds": v.get("durationSeconds"),
                    "uploaded": v.get("date"),
                    "description": (v.get("text") or "")[:600],
                }
                for v in results if isinstance(v, dict)
            ]
            raw[q] = cleaned
            print(f"[yt-scrape]   got {len(cleaned)} videos")
        else:
            raw[q] = []

    out = ROOT / "youtube_scrape_raw.json"
    out.write_text(json.dumps(raw, indent=2, ensure_ascii=False))
    print(f"[yt-scrape] DONE → {out}")
    total = sum(len(v) for v in raw.values())
    print(f"[yt-scrape] total videos collected: {total}")


if __name__ == "__main__":
    main()
