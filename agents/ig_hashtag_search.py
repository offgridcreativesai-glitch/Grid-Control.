"""
agents/ig_hashtag_search.py — Phase E3.

Official Instagram Hashtag Search API as a zero-cost, no-ban-risk alternative to
the Apify hashtag scraper for TREND research. Saves Apify spend and avoids the
scraping-ban risk on owned trend pulls.

IMPORTANT (zero-assumption note):
  `ig_hashtag_search` + `{hashtag-id}/top_media|recent_media` live on the
  **graph.facebook.com (FB-Page-linked IG)** flow, requiring `instagram_basic`
  + `pages_read_engagement` and an IG account linked to a Facebook Page. The
  brand's current token may be the Instagram Login type (graph.instagram.com),
  which does NOT serve these endpoints. So this path is OFF by default and only
  activates when IG_HASHTAG_API_ENABLED=1. On any failure it returns an error
  dict and the caller falls back to Apify — existing behavior is unchanged.

  The Hashtag API also STRIPS post-owner identity (no ownerUsername), which is
  why DM-Hunter prospecting must stay on Apify; this is for trends only.

Env (per-brand, via brand_env overlay):
  META_GRAPH_API_TOKEN — access token with hashtag-search scopes
  IG_USER_ID           — the IG business account id
  IG_HASHTAG_API_ENABLED — "1" to use this path (default off → Apify)

Rate limit: 30 unique hashtags / 7 days / user — pair with scrape_cache (E2).
"""
import os
import requests

GRAPH_BASE = "https://graph.facebook.com/v21.0"


def enabled() -> bool:
    return os.getenv("IG_HASHTAG_API_ENABLED", "").strip() in ("1", "true", "True")


def _creds() -> tuple[str, str]:
    token = (os.getenv("META_GRAPH_API_TOKEN") or "").strip()
    ig_id = (os.getenv("IG_USER_ID") or "").strip()
    return token, ig_id


def _search_hashtag_id(hashtag: str, ig_id: str, token: str) -> str | None:
    """Resolve a hashtag string to its IG hashtag id."""
    try:
        r = requests.get(
            f"{GRAPH_BASE}/ig_hashtag_search",
            params={"user_id": ig_id, "q": hashtag.lstrip("#"), "access_token": token},
            timeout=20,
        )
        if r.status_code != 200:
            return None
        data = r.json().get("data", [])
        return data[0]["id"] if data else None
    except Exception:
        return None


def _hashtag_media(hashtag_id: str, ig_id: str, token: str, edge: str = "top_media",
                   limit: int = 30) -> list:
    """Fetch top_media (or recent_media) for a hashtag id. No owner identity."""
    try:
        r = requests.get(
            f"{GRAPH_BASE}/{hashtag_id}/{edge}",
            params={
                "user_id": ig_id,
                "fields": "id,caption,media_type,comments_count,like_count,permalink,timestamp",
                "access_token": token,
                "limit": limit,
            },
            timeout=25,
        )
        if r.status_code != 200:
            return []
        return r.json().get("data", []) or []
    except Exception:
        return []


def scrape_hashtags(hashtags: list[str], per_tag_limit: int = 30) -> dict:
    """Official-API analogue of TrendResearcher.scrape_instagram_hashtags().

    Returns the SAME shape so it is a drop-in: {status, posts_scraped,
    top_posts[...], hashtags_scraped, source}. On any problem returns
    {status: 'FAILED', error, source} so the caller falls back to Apify.
    """
    if not enabled():
        return {"status": "FAILED", "error": "IG Hashtag API disabled", "source": "ig_hashtag_api"}

    token, ig_id = _creds()
    if not token or not ig_id:
        return {"status": "FAILED",
                "error": "META_GRAPH_API_TOKEN / IG_USER_ID not set",
                "source": "ig_hashtag_api"}

    all_posts: list[dict] = []
    tags_done: list[str] = []
    for tag in hashtags[:5]:  # cap to protect the 30/7d quota
        hid = _search_hashtag_id(tag, ig_id, token)
        if not hid:
            continue
        media = _hashtag_media(hid, ig_id, token, edge="top_media", limit=per_tag_limit)
        tags_done.append(tag)
        for post in media:
            caption = (post.get("caption") or "")[:300]
            all_posts.append({
                "caption_snippet": caption,
                "likes": post.get("like_count", 0) or 0,
                "comments": post.get("comments_count", 0) or 0,
                "videoViewCount": 0,  # not exposed by the Hashtag API
                "type": post.get("media_type", "unknown"),
                "hashtags": [t for t in [tag] if t],
                "owner_username": "",        # API strips owner identity (trends only)
                "url": post.get("permalink", ""),
                "timestamp": post.get("timestamp", ""),
                "latestComments": [],        # not exposed by the Hashtag API
            })

    if not all_posts:
        return {"status": "FAILED",
                "error": "No media returned (token may lack hashtag scopes)",
                "source": "ig_hashtag_api"}

    all_posts.sort(key=lambda x: x["likes"] + x["comments"], reverse=True)
    return {
        "status": "OK",
        "posts_scraped": len(all_posts),
        "top_posts": all_posts[:10],
        "hashtags_scraped": tags_done,
        "source": "ig_hashtag_api",
    }
