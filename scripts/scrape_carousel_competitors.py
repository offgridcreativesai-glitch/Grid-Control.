"""
One-off scrape: pull recent carousel posts from carousel-style competitors
to study visual design patterns before building HTML/CSS templates.

Output: brands/askgauravai/competitor_carousel_pattern_raw.json
"""

import os
import sys
import json
from pathlib import Path
from datetime import datetime
from dotenv import load_dotenv

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from apify_client import ApifyClient

load_dotenv()
APIFY_API_KEY = os.getenv("APIFY_API_KEY", "").strip()
if not APIFY_API_KEY:
    raise SystemExit("APIFY_API_KEY missing from .env")

BRAND_DIR = Path(__file__).resolve().parent.parent / "brands" / "askgauravai"
OUT_RAW = BRAND_DIR / "competitor_carousel_pattern_raw.json"

CAROUSEL_REFERENCE_HANDLES = [
    "thevibefounder",
    "vaibhavsisinty",
]
POSTS_PER_HANDLE = 12

client = ApifyClient(APIFY_API_KEY)

print(f"Scraping {len(CAROUSEL_REFERENCE_HANDLES)} handles, {POSTS_PER_HANDLE} posts each…")

run_input = {
    "directUrls": [f"https://www.instagram.com/{h}/" for h in CAROUSEL_REFERENCE_HANDLES],
    "resultsType": "posts",
    "resultsLimit": POSTS_PER_HANDLE,
    "addParentData": False,
}

run = client.actor("apify/instagram-scraper").call(run_input=run_input, timeout_secs=180)
items = list(client.dataset(run["defaultDatasetId"]).iterate_items())

print(f"Got {len(items)} raw items.")

# Filter to carousels (Sidecar = multi-image post). Keep ImageUrl(s) + caption + counts.
carousels = []
for it in items:
    if it.get("type") != "Sidecar":
        # Also keep Image (single-image post — sometimes designed posts)
        if it.get("type") not in ("Image",):
            continue
    carousels.append({
        "owner": it.get("ownerUsername"),
        "shortCode": it.get("shortCode"),
        "url": it.get("url"),
        "type": it.get("type"),
        "timestamp": it.get("timestamp"),
        "caption": (it.get("caption") or "")[:1500],
        "likes": it.get("likesCount"),
        "comments": it.get("commentsCount"),
        "image_urls": it.get("images") or ([it.get("displayUrl")] if it.get("displayUrl") else []),
        "first_image": it.get("displayUrl"),
        "child_posts_count": len(it.get("childPosts") or []),
        "child_image_urls": [c.get("displayUrl") for c in (it.get("childPosts") or []) if c.get("displayUrl")],
    })

# Save raw
OUT_RAW.write_text(json.dumps({
    "scraped_at": datetime.utcnow().isoformat(),
    "handles": CAROUSEL_REFERENCE_HANDLES,
    "total_carousels": len(carousels),
    "posts": carousels,
}, indent=2, ensure_ascii=False))

print(f"\nSaved {len(carousels)} posts → {OUT_RAW}")
print(f"\nBy handle:")
from collections import Counter
for owner, n in Counter([c["owner"] for c in carousels]).most_common():
    print(f"  {owner}: {n} posts")
