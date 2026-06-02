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

from typing import Any

from requests_oauthlib import OAuth1Session

VERIFY_URL = "https://api.twitter.com/1.1/account/verify_credentials.json"
TWEET_URL = "https://api.twitter.com/2/tweets"
CHAR_LIMIT = 280


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
