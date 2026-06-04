"""
X / Twitter publisher — posts via API v2 (POST /2/tweets) using OAuth 1.0a user context.
The four keys come from the brand's private .env:
  TWITTER_API_KEY, TWITTER_API_SECRET, TWITTER_ACCESS_TOKEN, TWITTER_ACCESS_SECRET
(the app must be Read+Write). Text posts work today; media is a later add.

Same two-mode contract as the other publishers:
  - keys present + write access → posts for real, returns the permalink.
  - keys absent/blocked → returns a 'prepared' package so the human can post manually.

The 280-char limit is surfaced as a clear error — we never silently truncate a post.
Zero fabrication: every value traces to the approved output or a real API call.
"""
from __future__ import annotations

import os
import time
from pathlib import Path
from typing import Any

from requests_oauthlib import OAuth1Session

VERIFY_URL = "https://api.twitter.com/1.1/account/verify_credentials.json"
TWEET_URL = "https://api.twitter.com/2/tweets"
UPLOAD_URL = "https://upload.twitter.com/1.1/media/upload.json"
CHAR_LIMIT = 280
BASE_DIR = Path(__file__).resolve().parent.parent


def _session(api_key: str, api_secret: str, access_token: str, access_secret: str) -> OAuth1Session:
    return OAuth1Session(
        client_key=api_key,
        client_secret=api_secret,
        resource_owner_key=access_token,
        resource_owner_secret=access_secret,
    )


def token_status(api_key: str, api_secret: str, access_token: str, access_secret: str) -> dict[str, Any]:
    """Read-only liveness probe. verify_credentials returns the handle; the
    x-access-level header tells us whether the app can actually write."""
    if not all([api_key, api_secret, access_token, access_secret]):
        return {"live": False, "reason": "missing_keys"}
    try:
        oauth = _session(api_key, api_secret, access_token, access_secret)
        r = oauth.get(VERIFY_URL, timeout=15)
        if r.status_code == 200:
            handle = (r.json() or {}).get("screen_name", "")
            access_level = r.headers.get("x-access-level", "")
            return {
                "live": True,
                "account": f"@{handle}" if handle else "X account",
                "write": "write" in access_level,
                "access_level": access_level,
            }
        return {"live": False, "reason": f"http_{r.status_code}", "detail": r.text[:160]}
    except Exception as e:
        return {"live": False, "reason": str(e)}


def publish_text(
    api_key: str, api_secret: str, access_token: str, access_secret: str, text: str
) -> dict[str, Any]:
    """Post a tweet via API v2. Returns a result dict with the tweet id + permalink."""
    text = (text or "").strip()
    if not text:
        return {"published": False, "error": "Empty tweet text."}
    if len(text) > CHAR_LIMIT:
        return {
            "published": False,
            "error": f"Tweet is {len(text)} chars (limit {CHAR_LIMIT}). Shorten it — not truncating.",
        }
    try:
        oauth = _session(api_key, api_secret, access_token, access_secret)
        r = oauth.post(TWEET_URL, json={"text": text}, timeout=30)
    except Exception as e:
        return {"published": False, "error": str(e)}

    if r.status_code in (200, 201):
        data = (r.json() or {}).get("data", {})
        tweet_id = data.get("id", "")
        permalink = f"https://x.com/i/web/status/{tweet_id}" if tweet_id else ""
        return {"published": True, "tweet_id": tweet_id, "permalink": permalink}

    return {"published": False, "stage": "tweets", "status": r.status_code, "error": r.text[:300]}


# ── media upload (v1.1) + tweet with media (v2) ───────────────────────────────

def _resolve(path: str) -> Path:
    p = (BASE_DIR / path) if not os.path.isabs(path) else Path(path)
    if not p.exists():
        raise FileNotFoundError(f"Media not found on disk: {p}")
    return p


def _upload_image(oauth: OAuth1Session, path: str) -> str:
    with open(_resolve(path), "rb") as fh:
        r = oauth.post(UPLOAD_URL, files={"media": fh.read()}, timeout=60)
    if r.status_code not in (200, 201):
        raise RuntimeError(f"image upload {r.status_code}: {r.text[:200]}")
    return str((r.json() or {}).get("media_id_string", ""))


def _upload_video_chunked(oauth: OAuth1Session, path: str) -> str:
    p = _resolve(path)
    total = p.stat().st_size
    # INIT
    r = oauth.post(UPLOAD_URL, data={"command": "INIT", "total_bytes": total,
                   "media_type": "video/mp4", "media_category": "tweet_video"}, timeout=60)
    if r.status_code not in (200, 201, 202):
        raise RuntimeError(f"INIT {r.status_code}: {r.text[:200]}")
    media_id = str((r.json() or {}).get("media_id_string", ""))
    # APPEND in ~4MB chunks
    chunk = 4 * 1024 * 1024; idx = 0
    with open(p, "rb") as fh:
        while True:
            buf = fh.read(chunk)
            if not buf:
                break
            ra = oauth.post(UPLOAD_URL, data={"command": "APPEND", "media_id": media_id,
                            "segment_index": idx}, files={"media": buf}, timeout=120)
            if ra.status_code not in (200, 201, 204):
                raise RuntimeError(f"APPEND {idx} {ra.status_code}: {ra.text[:200]}")
            idx += 1
    # FINALIZE
    rf = oauth.post(UPLOAD_URL, data={"command": "FINALIZE", "media_id": media_id}, timeout=60)
    if rf.status_code not in (200, 201):
        raise RuntimeError(f"FINALIZE {rf.status_code}: {rf.text[:200]}")
    info = (rf.json() or {}).get("processing_info")
    # poll STATUS until succeeded
    waited = 0
    while info and info.get("state") in ("pending", "in_progress"):
        wait = min(int(info.get("check_after_secs", 5)), 15)
        time.sleep(wait); waited += wait
        if waited > 180:
            raise RuntimeError("video processing timeout")
        rs = oauth.get(UPLOAD_URL, params={"command": "STATUS", "media_id": media_id}, timeout=30)
        info = (rs.json() or {}).get("processing_info")
    if info and info.get("state") == "failed":
        raise RuntimeError(f"video processing failed: {info}")
    return media_id


def _tweet_with_media(oauth: OAuth1Session, text: str, media_ids: list[str]) -> dict[str, Any]:
    r = oauth.post(TWEET_URL, json={"text": text, "media": {"media_ids": media_ids}}, timeout=60)
    if r.status_code in (200, 201):
        tid = ((r.json() or {}).get("data", {})).get("id", "")
        return {"published": True, "tweet_id": tid,
                "permalink": f"https://x.com/i/web/status/{tid}" if tid else ""}
    return {"published": False, "stage": "tweets_media", "status": r.status_code, "error": r.text[:300]}


def publish_images(api_key, api_secret, access_token, access_secret, text, image_paths) -> dict[str, Any]:
    """Tweet with up to 4 images. Extra images beyond 4 are dropped (X hard limit)."""
    text = (text or "").strip()
    if len(text) > CHAR_LIMIT:
        return {"published": False, "error": f"Tweet is {len(text)} chars (limit {CHAR_LIMIT})."}
    try:
        oauth = _session(api_key, api_secret, access_token, access_secret)
        ids = [_upload_image(oauth, p) for p in image_paths[:4]]
        return _tweet_with_media(oauth, text, ids)
    except Exception as e:
        return {"published": False, "stage": "images", "error": str(e)[:300]}


def publish_video(api_key, api_secret, access_token, access_secret, text, video_path) -> dict[str, Any]:
    """Tweet with native video (the reel)."""
    text = (text or "").strip()
    if len(text) > CHAR_LIMIT:
        return {"published": False, "error": f"Tweet is {len(text)} chars (limit {CHAR_LIMIT})."}
    try:
        oauth = _session(api_key, api_secret, access_token, access_secret)
        mid = _upload_video_chunked(oauth, video_path)
        return _tweet_with_media(oauth, text, [mid])
    except Exception as e:
        return {"published": False, "stage": "video", "error": str(e)[:300]}
