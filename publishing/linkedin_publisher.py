"""
LinkedIn publisher — posts as the member (Gaurav's personal /in/ profile) using the
w_member_social permission. The access token + author URN come from the brand's private
.env (LINKEDIN_ACCESS_TOKEN, LINKEDIN_URN). Text posts work today; images are a later add.

Mirrors the same two-mode contract as the IG publisher:
  - token live  → posts for real via the UGC Posts API, returns the permalink.
  - token absent/blocked → returns a 'prepared' package (the exact text) so the human
    can post it manually; flips to auto the moment the token works.

Zero fabrication: every value traces to the approved output or a real API call.
"""
from __future__ import annotations

from typing import Any

import requests

API = "https://api.linkedin.com"


def token_status(token: str, urn: str | None = None) -> dict[str, Any]:
    """Read-only liveness probe. /v2/userinfo (OpenID) returns the member identity
    that the w_member_social token can post as."""
    if not token:
        return {"live": False, "reason": "no_token"}
    try:
        r = requests.get(
            f"{API}/v2/userinfo",
            headers={"Authorization": f"Bearer {token}"},
            timeout=15,
        )
        if r.status_code == 200:
            j = r.json() or {}
            return {
                "live": True,
                "account": j.get("name") or j.get("given_name") or "LinkedIn member",
                "sub": j.get("sub"),
                "has_urn": bool(urn),
            }
        return {"live": False, "reason": f"http_{r.status_code}", "detail": r.text[:160]}
    except Exception as e:
        return {"live": False, "reason": str(e)}


def publish_text(token: str, author_urn: str, text: str) -> dict[str, Any]:
    """Create a PUBLIC text share via the UGC Posts API. Returns a result dict with
    the ugcPost URN + a public permalink on success."""
    if not author_urn:
        return {"published": False, "error": "LINKEDIN_URN missing — required to attribute the post."}
    payload = {
        "author": author_urn,
        "lifecycleState": "PUBLISHED",
        "specificContent": {
            "com.linkedin.ugc.ShareContent": {
                "shareCommentary": {"text": text},
                "shareMediaCategory": "NONE",
            }
        },
        "visibility": {"com.linkedin.ugc.MemberNetworkVisibility": "PUBLIC"},
    }
    try:
        r = requests.post(
            f"{API}/v2/ugcPosts",
            headers={
                "Authorization": f"Bearer {token}",
                "X-Restli-Protocol-Version": "2.0.0",
                "Content-Type": "application/json",
            },
            json=payload,
            timeout=30,
        )
    except Exception as e:
        return {"published": False, "error": str(e)}

    if r.status_code in (200, 201):
        post_urn = r.headers.get("x-restli-id") or (r.json() or {}).get("id") or ""
        permalink = f"https://www.linkedin.com/feed/update/{post_urn}" if post_urn else ""
        return {"published": True, "post_urn": post_urn, "permalink": permalink}

    # Surface the real API error — never pretend success.
    detail = r.text[:300]
    return {"published": False, "stage": "ugcPosts", "status": r.status_code, "error": detail}
