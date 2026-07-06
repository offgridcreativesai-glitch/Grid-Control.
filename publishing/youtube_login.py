"""
YouTube OAuth — *web* server flow for one-click connect from Grid Control.

Unlike publishing/youtube_oauth.py (a local CLI "installed app" loopback flow),
this drives the standard Google web OAuth: the browser is redirected to Google,
consents, and Google calls our HTTPS callback with a code. We exchange it for a
durable **refresh token** and store it (plus the client id/secret) in the brand's
private .env, where _verify_youtube_oauth() mints access tokens on demand.

App credentials come from the GC Google Cloud OAuth **web** client:
  - YOUTUBE_CLIENT_ID
  - YOUTUBE_CLIENT_SECRET
(global .env). The brand's connected YOUTUBE_REFRESH_TOKEN is per-brand.

Scopes are sensitive/restricted → external clients need Google verification
(Phase B); accounts added as test users on the consent screen work now.
"""
import os
import requests

AUTH_URL  = "https://accounts.google.com/o/oauth2/v2/auth"
TOKEN_URL = "https://oauth2.googleapis.com/token"

SCOPES = [
    "https://www.googleapis.com/auth/youtube.upload",
    "https://www.googleapis.com/auth/youtube.readonly",
    "https://www.googleapis.com/auth/yt-analytics.readonly",
]


def app_credentials() -> tuple[str, str]:
    """(client_id, client_secret) for the GC YouTube web OAuth client."""
    return (
        (os.getenv("YOUTUBE_CLIENT_ID") or "").strip(),
        (os.getenv("YOUTUBE_CLIENT_SECRET") or "").strip(),
    )


def build_authorize_url(redirect_uri: str, state: str) -> str:
    """Google consent URL. offline + consent guarantee a refresh token."""
    client_id, _ = app_credentials()
    from urllib.parse import urlencode
    q = urlencode({
        "client_id":     client_id,
        "redirect_uri":  redirect_uri,
        "response_type": "code",
        "scope":         " ".join(SCOPES),
        "access_type":   "offline",
        "prompt":        "consent",
        "include_granted_scopes": "true",
        "state":         state,
    })
    return f"{AUTH_URL}?{q}"


def exchange_code(code: str, redirect_uri: str) -> dict:
    """code → {refresh_token, access_token}. Raises if no refresh token returned."""
    client_id, client_secret = app_credentials()
    r = requests.post(TOKEN_URL, data={
        "code":          code,
        "client_id":     client_id,
        "client_secret": client_secret,
        "redirect_uri":  redirect_uri,
        "grant_type":    "authorization_code",
    }, timeout=10)
    if r.status_code != 200:
        raise RuntimeError(f"token exchange failed ({r.status_code}): {r.text[:300]}")
    d = r.json()
    refresh = d.get("refresh_token")
    if not refresh:
        raise RuntimeError("no refresh_token returned — revoke prior access and retry with prompt=consent")
    return {"refresh_token": refresh, "access_token": d.get("access_token", "")}
