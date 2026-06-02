"""
ASKGauravAI competitor + reference pattern scrape.
Pulls last 30 IG posts from 6 handles, saves raw + summary.
Used to inform Strategy Agent regeneration (volume / format / freebie / hook patterns).
"""
import json
import os
import sys
import time
from pathlib import Path

import requests

APIFY_TOKEN = os.environ.get("APIFY_API_KEY")
if not APIFY_TOKEN:
    print("ERROR: APIFY_API_KEY not set in env")
    sys.exit(1)

HANDLES = {
    "competitors": ["manthanjethwani", "aiwithanushka", "shivam.ai.data"],
    "references": ["garyvee", "thevibefounder", "vaibhavsisinty"],
}

OUTPUT_DIR = Path("/Users/gauravoffgrid/offgrid-marketing-os/brands/askgauravai")
RAW_FILE = OUTPUT_DIR / "competitor_pattern_raw.json"
SUMMARY_FILE = OUTPUT_DIR / "competitor_pattern_summary.json"

ACTOR_ID = "apify~instagram-scraper"
RESULTS_PER_HANDLE = 30


def run_actor(direct_urls: list, results_limit: int) -> list:
    """Sync run-and-wait against apify/instagram-scraper."""
    url = f"https://api.apify.com/v2/acts/{ACTOR_ID}/run-sync-get-dataset-items?token={APIFY_TOKEN}"
    payload = {
        "directUrls": direct_urls,
        "resultsType": "posts",
        "resultsLimit": results_limit,
        "addParentData": False,
    }
    r = requests.post(url, json=payload, timeout=300)
    r.raise_for_status()
    return r.json()


def summarize_post(p: dict) -> dict:
    return {
        "id": p.get("id") or p.get("shortCode"),
        "url": p.get("url"),
        "type": p.get("type"),
        "caption": (p.get("caption") or "")[:600],
        "caption_full_len": len(p.get("caption") or ""),
        "hashtags": p.get("hashtags") or [],
        "mentions": p.get("mentions") or [],
        "likes": p.get("likesCount"),
        "comments": p.get("commentsCount"),
        "video_views": p.get("videoViewCount") or p.get("videoPlayCount"),
        "video_duration": p.get("videoDuration"),
        "is_video": bool(p.get("videoUrl")),
        "is_carousel": p.get("type") == "Sidecar" or len(p.get("childPosts") or []) > 1,
        "carousel_count": len(p.get("childPosts") or []) or None,
        "timestamp": p.get("timestamp"),
        "owner_username": p.get("ownerUsername"),
    }


def aggregate_handle(posts: list) -> dict:
    """Per-handle pattern stats."""
    if not posts:
        return {"post_count": 0}
    types = {}
    durations = []
    captions_long = 0
    captions_med = 0
    captions_short = 0
    likes = []
    comments = []
    views = []
    for p in posts:
        t = "carousel" if p["is_carousel"] else ("video" if p["is_video"] else "image")
        types[t] = types.get(t, 0) + 1
        if p["video_duration"]:
            durations.append(p["video_duration"])
        cl = p["caption_full_len"]
        if cl > 800:
            captions_long += 1
        elif cl > 200:
            captions_med += 1
        else:
            captions_short += 1
        if p["likes"]:
            likes.append(p["likes"])
        if p["comments"]:
            comments.append(p["comments"])
        if p["video_views"]:
            views.append(p["video_views"])

    def med(arr):
        if not arr:
            return None
        s = sorted(arr)
        return s[len(s) // 2]

    return {
        "post_count": len(posts),
        "type_mix": types,
        "video_duration_seconds_median": med(durations),
        "video_duration_long_form_count": sum(1 for d in durations if d > 60),
        "caption_length_distribution": {"short_<200": captions_short, "medium_200_800": captions_med, "long_>800": captions_long},
        "median_likes": med(likes),
        "median_comments": med(comments),
        "median_video_views": med(views),
        "engagement_rate_proxy": round(((med(likes) or 0) + (med(comments) or 0)) / max(med(views) or med(likes) or 1, 1), 4),
    }


def main():
    print(f"[scrape] starting — {len(HANDLES['competitors']) + len(HANDLES['references'])} handles, {RESULTS_PER_HANDLE} posts each")
    raw = {"competitors": {}, "references": {}}
    summary = {"competitors": {}, "references": {}}

    for category, handles in HANDLES.items():
        for handle in handles:
            url = f"https://www.instagram.com/{handle}/"
            print(f"[scrape] {category}/{handle} ...")
            try:
                posts = run_actor([url], RESULTS_PER_HANDLE)
            except Exception as e:
                print(f"[scrape] FAILED {handle}: {e}")
                raw[category][handle] = {"error": str(e)}
                continue
            posts_clean = [summarize_post(p) for p in posts if isinstance(p, dict)]
            raw[category][handle] = posts_clean
            summary[category][handle] = aggregate_handle(posts_clean)
            print(f"[scrape]   got {len(posts_clean)} posts. sleeping 3s.")
            time.sleep(3)

    RAW_FILE.write_text(json.dumps(raw, indent=2, ensure_ascii=False))
    SUMMARY_FILE.write_text(json.dumps(summary, indent=2, ensure_ascii=False))
    print(f"[scrape] DONE. raw → {RAW_FILE}")
    print(f"[scrape] DONE. summary → {SUMMARY_FILE}")


if __name__ == "__main__":
    main()
