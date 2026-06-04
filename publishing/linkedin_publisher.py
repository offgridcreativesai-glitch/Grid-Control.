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

import os
from pathlib import Path
from typing import Any

import requests

API = "https://api.linkedin.com"
BASE_DIR = Path(__file__).resolve().parent.parent


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


# ── media upload (register → PUT binary → asset URN) ──────────────────────────

def _resolve(path: str) -> Path:
    p = (BASE_DIR / path) if not os.path.isabs(path) else Path(path)
    if not p.exists():
        raise FileNotFoundError(f"Media not found on disk: {p}")
    return p


def _register_and_upload(token: str, author_urn: str, file_path: str, recipe: str) -> str:
    """Register an upload, PUT the binary, return the LinkedIn asset URN."""
    p = _resolve(file_path)
    reg = requests.post(
        f"{API}/v2/assets?action=registerUpload",
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json",
                 "X-Restli-Protocol-Version": "2.0.0"},
        json={"registerUploadRequest": {
            "recipes": [recipe], "owner": author_urn,
            "serviceRelationships": [{"relationshipType": "OWNER",
                                      "identifier": "urn:li:userGeneratedContent"}]}},
        timeout=30,
    )
    if reg.status_code not in (200, 201):
        raise RuntimeError(f"registerUpload {reg.status_code}: {reg.text[:200]}")
    val = (reg.json() or {}).get("value", {})
    asset = val.get("asset", "")
    upload_url = (val.get("uploadMechanism", {})
                  .get("com.linkedin.digitalmedia.uploading.MediaUploadHttpRequest", {})
                  .get("uploadUrl", ""))
    if not asset or not upload_url:
        raise RuntimeError(f"registerUpload missing asset/uploadUrl: {reg.text[:200]}")
    with open(p, "rb") as fh:
        up = requests.put(upload_url, headers={"Authorization": f"Bearer {token}"},
                          data=fh.read(), timeout=300)
    if up.status_code not in (200, 201):
        raise RuntimeError(f"binary upload {up.status_code}: {up.text[:200]}")
    return asset


def _ugc_media_post(token: str, author_urn: str, text: str, category: str, media_assets: list[str]) -> dict[str, Any]:
    media = [{"status": "READY", "media": a} for a in media_assets]
    payload = {
        "author": author_urn, "lifecycleState": "PUBLISHED",
        "specificContent": {"com.linkedin.ugc.ShareContent": {
            "shareCommentary": {"text": text},
            "shareMediaCategory": category, "media": media}},
        "visibility": {"com.linkedin.ugc.MemberNetworkVisibility": "PUBLIC"},
    }
    r = requests.post(f"{API}/v2/ugcPosts",
        headers={"Authorization": f"Bearer {token}", "X-Restli-Protocol-Version": "2.0.0",
                 "Content-Type": "application/json"}, json=payload, timeout=60)
    if r.status_code in (200, 201):
        post_urn = r.headers.get("x-restli-id") or (r.json() or {}).get("id") or ""
        return {"published": True, "post_urn": post_urn,
                "permalink": f"https://www.linkedin.com/feed/update/{post_urn}" if post_urn else ""}
    return {"published": False, "stage": "ugcPosts_media", "status": r.status_code, "error": r.text[:300]}


def publish_images(token: str, author_urn: str, text: str, image_paths: list[str]) -> dict[str, Any]:
    """Multi-image member post (carousel-style). Up to ~9 images."""
    if not author_urn:
        return {"published": False, "error": "LINKEDIN_URN missing."}
    try:
        assets = [_register_and_upload(token, author_urn, p, "urn:li:digitalmediaRecipe:feedshare-image")
                  for p in image_paths]
        return _ugc_media_post(token, author_urn, text, "IMAGE", assets)
    except Exception as e:
        return {"published": False, "stage": "images", "error": str(e)[:300]}


def publish_video(token: str, author_urn: str, text: str, video_path: str) -> dict[str, Any]:
    """Native video member post (the reel)."""
    if not author_urn:
        return {"published": False, "error": "LINKEDIN_URN missing."}
    try:
        asset = _register_and_upload(token, author_urn, video_path, "urn:li:digitalmediaRecipe:feedshare-video")
        return _ugc_media_post(token, author_urn, text, "VIDEO", [asset])
    except Exception as e:
        return {"published": False, "stage": "video", "error": str(e)[:300]}
