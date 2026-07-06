"""
X (Twitter) OAuth 2.0 with PKCE — one-click connect for Grid Control.

Per the standing rule, X *publishing stays manual* — so we request READ scopes
only (profile + read + offline) for insights/community context, NOT tweet.write.
The user access token is stored as TWITTER_BEARER_TOKEN in brands/<slug>/.env
(it validates on /2/users/me exactly like a bearer), plus a refresh token.

PKCE uses the `plain` method so the verifier can be carried in our signed
state — keeps the flow stateless (no server-side verifier store). X is a
confidential client here: the token call uses HTTP Basic (client_id:secret).

App credentials come from the GC X Developer app (global .env):
  - TWITTER_OAUTH_CLIENT_ID
  - TWITTER_OAUTH_CLIENT_SECRET
"""
import os
import base64
import requests

AUTH_URL  = "https://twitter.com/i/oauth2/authorize"
TOKEN_URL = "https://api.twitter.com/2/oauth2/token"

# Read-only: publishing on X is manual by standing rule.
SCOPES = ["tweet.read", "users.read", "offline.access"]


def app_credentials() -> tuple[str, str]:
    return (
        (os.getenv("TWITTER_OAUTH_CLIENT_ID") or "").strip(),
        (os.getenv("TWITTER_OAUTH_CLIENT_SECRET") or "").strip(),
    )


def build_authorize_url(redirect_uri: str, state: str, verifier: str) -> str:
    """`verifier` doubles as the PKCE challenge (plain method)."""
    client_id, _ = app_credentials()
    from urllib.parse import urlencode
    q = urlencode({
        "response_type":         "code",
        "client_id":             client_id,
        "redirect_uri":          redirect_uri,
        "scope":                 " ".join(SCOPES),
        "state":                 state,
        "code_challenge":        verifier,
        "code_challenge_method": "plain",
    })
    return f"{AUTH_URL}?{q}"


def exchange_code(code: str, redirect_uri: str, verifier: str) -> dict:
    """code → {access_token, refresh_token}."""
    client_id, client_secret = app_credentials()
    basic = base64.b64encode(f"{client_id}:{client_secret}".encode()).decode()
    r = requests.post(TOKEN_URL, data={
        "grant_type":    "authorization_code",
        "code":          code,
        "redirect_uri":  redirect_uri,
        "code_verifier": verifier,
        "client_id":     client_id,
    }, headers={
        "Authorization": f"Basic {basic}",
        "Content-Type":  "application/x-www-form-urlencoded",
    }, timeout=10)
    if r.status_code != 200:
        raise RuntimeError(f"token exchange failed ({r.status_code}): {r.text[:300]}")
    d = r.json()
    token = d.get("access_token")
    if not token:
        raise RuntimeError(f"no access_token in response: {r.text[:200]}")
    return {"access_token": token, "refresh_token": d.get("refresh_token", "")}
