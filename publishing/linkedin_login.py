"""
LinkedIn OAuth 2.0 (authorization code) — one-click connect for Grid Control.

A brand authorizes via LinkedIn; we exchange the code for a ~60-day member
access token and store it as LINKEDIN_ACCESS_TOKEN in brands/<slug>/.env. The
member URN (needed to post) is captured separately from /v2/userinfo by the
connections reader, or here on exchange.

App credentials come from the GC LinkedIn Developer app (global .env):
  - LINKEDIN_CLIENT_ID
  - LINKEDIN_CLIENT_SECRET
Required products on the app: "Sign In with LinkedIn using OpenID Connect"
(openid/profile/email) + "Share on LinkedIn" (w_member_social).
"""
import os
import requests

AUTH_URL  = "https://www.linkedin.com/oauth/v2/authorization"
TOKEN_URL = "https://www.linkedin.com/oauth/v2/accessToken"

# openid/profile/email = identity; w_member_social = post as the member.
SCOPES = ["openid", "profile", "email", "w_member_social"]


def app_credentials() -> tuple[str, str]:
    return (
        (os.getenv("LINKEDIN_CLIENT_ID") or "").strip(),
        (os.getenv("LINKEDIN_CLIENT_SECRET") or "").strip(),
    )


def build_authorize_url(redirect_uri: str, state: str) -> str:
    client_id, _ = app_credentials()
    from urllib.parse import urlencode
    q = urlencode({
        "response_type": "code",
        "client_id":     client_id,
        "redirect_uri":  redirect_uri,
        "state":         state,
        "scope":         " ".join(SCOPES),
    })
    return f"{AUTH_URL}?{q}"


def exchange_code(code: str, redirect_uri: str) -> dict:
    """code → {access_token, urn}. URN resolved from /v2/userinfo (best-effort)."""
    client_id, client_secret = app_credentials()
    r = requests.post(TOKEN_URL, data={
        "grant_type":    "authorization_code",
        "code":          code,
        "redirect_uri":  redirect_uri,
        "client_id":     client_id,
        "client_secret": client_secret,
    }, headers={"Content-Type": "application/x-www-form-urlencoded"}, timeout=10)
    if r.status_code != 200:
        raise RuntimeError(f"token exchange failed ({r.status_code}): {r.text[:300]}")
    token = r.json().get("access_token")
    if not token:
        raise RuntimeError(f"no access_token in response: {r.text[:200]}")

    urn = ""
    try:
        ui = requests.get("https://api.linkedin.com/v2/userinfo",
                          headers={"Authorization": f"Bearer {token}"}, timeout=8)
        if ui.status_code == 200:
            sub = ui.json().get("sub", "")
            if sub:
                urn = sub if sub.startswith("urn:li:") else f"urn:li:person:{sub}"
    except Exception:
        pass
    return {"access_token": token, "urn": urn}
