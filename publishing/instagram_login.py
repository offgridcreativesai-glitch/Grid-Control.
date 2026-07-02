"""
Instagram API *with Instagram Login* — OAuth helpers.

This is the modern (2024+) path that lets an Instagram **Professional**
(Business/Creator) account authorize directly, WITHOUT a Facebook account or a
linked Facebook Page. Used by Grid Control so any client can click-connect their
own Instagram for insights + publishing.

Credentials come from the Meta app's "Instagram → API setup with Instagram login"
screen:
  - INSTAGRAM_APP_ID      (a.k.a. "Instagram app ID" — DIFFERENT from the FB App ID)
  - INSTAGRAM_APP_SECRET  (a.k.a. "Instagram app secret")
We fall back to META_APP_ID / META_APP_SECRET if the IG-specific ones are unset.

Flow:
  1. build_authorize_url()  → send the browser to instagram.com to consent
  2. exchange_code()        → code → short-lived token (+ ig user id)
  3. long_lived_token()     → short-lived → 60-day long-lived token
The 60-day token is what we store as META_GRAPH_API_TOKEN in brands/<slug>/.env;
_verify_social() already validates IGAA… tokens on graph.instagram.com.

Docs: https://developers.facebook.com/docs/instagram-platform/instagram-api-with-instagram-login
"""
import os
import requests

AUTHORIZE_URL   = "https://www.instagram.com/oauth/authorize"
TOKEN_URL       = "https://api.instagram.com/oauth/access_token"
LONG_LIVED_URL  = "https://graph.instagram.com/access_token"
REFRESH_URL     = "https://graph.instagram.com/refresh_access_token"

# Everything Grid Control's agents will eventually need. All available to
# testers in dev; each is justified individually at App Review (Phase B).
SCOPES = [
    "instagram_business_basic",
    "instagram_business_manage_insights",
    "instagram_business_content_publish",
    "instagram_business_manage_comments",
    "instagram_business_manage_messages",
]


def app_credentials() -> tuple[str, str]:
    """(app_id, app_secret) for Instagram Login — IG-specific first, FB fallback."""
    app_id = (os.getenv("INSTAGRAM_APP_ID") or os.getenv("META_APP_ID") or "").strip()
    secret = (os.getenv("INSTAGRAM_APP_SECRET") or os.getenv("META_APP_SECRET") or "").strip()
    return app_id, secret


def build_authorize_url(redirect_uri: str, state: str) -> str:
    """Construct the Instagram consent URL the browser is sent to."""
    app_id, _ = app_credentials()
    from urllib.parse import urlencode
    q = urlencode({
        "client_id":     app_id,
        "redirect_uri":  redirect_uri,
        "response_type": "code",
        "scope":         ",".join(SCOPES),
        "state":         state,
    })
    return f"{AUTHORIZE_URL}?{q}"


def exchange_code(code: str, redirect_uri: str) -> dict:
    """code → short-lived token. Returns {access_token, user_id} or raises."""
    app_id, secret = app_credentials()
    r = requests.post(TOKEN_URL, data={
        "client_id":     app_id,
        "client_secret": secret,
        "grant_type":    "authorization_code",
        "redirect_uri":  redirect_uri,
        "code":          code,
    }, timeout=10)
    if r.status_code != 200:
        raise RuntimeError(f"code exchange failed ({r.status_code}): {r.text[:300]}")
    data = r.json()
    # New API returns {access_token, user_id, permissions} at top level; some
    # responses nest under data[0]. Handle both.
    if "access_token" not in data and isinstance(data.get("data"), list) and data["data"]:
        data = data["data"][0]
    token = data.get("access_token")
    if not token:
        raise RuntimeError(f"no access_token in response: {str(data)[:300]}")
    return {"access_token": token, "user_id": str(data.get("user_id") or "")}


def long_lived_token(short_token: str) -> dict:
    """short-lived → 60-day long-lived token. Returns {access_token, expires_in}."""
    _, secret = app_credentials()
    r = requests.get(LONG_LIVED_URL, params={
        "grant_type":    "ig_exchange_token",
        "client_secret": secret,
        "access_token":  short_token,
    }, timeout=10)
    if r.status_code != 200:
        raise RuntimeError(f"long-lived exchange failed ({r.status_code}): {r.text[:300]}")
    d = r.json()
    return {"access_token": d.get("access_token", short_token),
            "expires_in":   d.get("expires_in", 0)}


def refresh_long_lived(token: str) -> dict:
    """Refresh a 60-day token (call before it expires). Returns {access_token, expires_in}."""
    r = requests.get(REFRESH_URL, params={
        "grant_type":   "ig_refresh_token",
        "access_token": token,
    }, timeout=10)
    if r.status_code != 200:
        raise RuntimeError(f"refresh failed ({r.status_code}): {r.text[:300]}")
    d = r.json()
    return {"access_token": d.get("access_token", token),
            "expires_in":   d.get("expires_in", 0)}
