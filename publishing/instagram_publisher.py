"""
Instagram carousel publisher — the "agents post it" step.

Two responsibilities:
  1. Host approved slide PNGs at public HTTPS URLs (Instagram's publish API fetches
     images from a URL — it never accepts local file bytes). We use Supabase Storage
     (public bucket), which we already have wired.
  2. Run the Instagram Graph API carousel flow:
        child container per slide → CAROUSEL parent container → media_publish.

Designed so the SAME path serves two modes:
  - token live  → publishes for real, returns the permalink.
  - token absent/blocked → returns a "prepared" package (public slide URLs + caption)
    so the human can post it manually tonight; flips to auto the moment the token works.

Zero fabrication: every value traces to the approved carousel output or a real API call.
"""
from __future__ import annotations

import os
import time
import mimetypes
from pathlib import Path
from typing import Any

import requests

BASE_DIR = Path(__file__).resolve().parent.parent
GRAPH_VERSION = os.getenv("IG_GRAPH_VERSION", "v21.0")
GRAPH_HOST = "https://graph.instagram.com"
STORAGE_BUCKET = os.getenv("PUBLISH_BUCKET", "published-media")


# ── Supabase Storage (public hosting for slide images) ────────────────────────

def _supabase() -> tuple[str, str]:
    url = os.getenv("SUPABASE_URL", "").rstrip("/")
    key = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "") or os.getenv("SUPABASE_ANON_KEY", "")
    if not url or not key:
        raise RuntimeError("SUPABASE_URL / SUPABASE_SERVICE_ROLE_KEY not configured")
    return url, key


def _ensure_bucket(url: str, key: str) -> None:
    """Create the public bucket once (idempotent — ignores 'already exists')."""
    r = requests.post(
        f"{url}/storage/v1/bucket",
        headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
        json={"id": STORAGE_BUCKET, "name": STORAGE_BUCKET, "public": True},
        timeout=15,
    )
    if r.status_code in (200, 201):
        return
    # 400/409 with "already exists" is fine.
    if r.status_code in (400, 409) and "exist" in r.text.lower():
        return
    # Some Supabase versions return 200 with error body; tolerate and let upload surface real errors.


def upload_slides_to_storage(brand_slug: str, slide_paths: list[str], post_id: str) -> list[str]:
    """Upload each slide PNG to the public bucket. Returns public HTTPS URLs in order."""
    url, key = _supabase()
    _ensure_bucket(url, key)
    public_urls: list[str] = []
    for idx, rel in enumerate(slide_paths, start=1):
        p = (BASE_DIR / rel) if not os.path.isabs(rel) else Path(rel)
        if not p.exists():
            raise FileNotFoundError(f"Slide image not found on disk: {p}")
        ctype = mimetypes.guess_type(str(p))[0] or "image/png"
        object_path = f"{brand_slug}/{post_id}/slide_{idx:02d}{p.suffix}"
        with open(p, "rb") as fh:
            data = fh.read()
        up = requests.post(
            f"{url}/storage/v1/object/{STORAGE_BUCKET}/{object_path}",
            headers={
                "Authorization": f"Bearer {key}",
                "Content-Type": ctype,
                "x-upsert": "true",
            },
            data=data,
            timeout=60,
        )
        if up.status_code not in (200, 201):
            raise RuntimeError(f"Storage upload failed for {object_path}: {up.status_code} {up.text[:200]}")
        public_urls.append(f"{url}/storage/v1/object/public/{STORAGE_BUCKET}/{object_path}")
    return public_urls


# ── Instagram Graph API carousel publish ──────────────────────────────────────

def _ig_node() -> str:
    """The publishing node. Instagram-Login tokens can use 'me'; an explicit
    IG_USER_ID overrides if provided."""
    return os.getenv("IG_USER_ID", "").strip() or "me"


def _wait_container_ready(container_id: str, token: str, tries: int = 8, delay: float = 2.0) -> str:
    """Poll a container's status_code until FINISHED (carousel parents need processing)."""
    for _ in range(tries):
        r = requests.get(
            f"{GRAPH_HOST}/{GRAPH_VERSION}/{container_id}",
            params={"fields": "status_code", "access_token": token},
            timeout=15,
        )
        status = (r.json() or {}).get("status_code")
        if status == "FINISHED":
            return "FINISHED"
        if status == "ERROR":
            return "ERROR"
        time.sleep(delay)
    return "TIMEOUT"


def publish_carousel(image_urls: list[str], caption: str, token: str) -> dict[str, Any]:
    """Run child containers → CAROUSEL parent → media_publish. Returns a result dict."""
    node = _ig_node()

    # 1. One child container per slide
    child_ids: list[str] = []
    for img in image_urls:
        r = requests.post(
            f"{GRAPH_HOST}/{GRAPH_VERSION}/{node}/media",
            data={"image_url": img, "is_carousel_item": "true", "access_token": token},
            timeout=30,
        )
        j = r.json() or {}
        if "id" not in j:
            return {"published": False, "stage": "child_container", "error": j.get("error", j), "image": img}
        child_ids.append(j["id"])

    # 2. Parent CAROUSEL container
    r = requests.post(
        f"{GRAPH_HOST}/{GRAPH_VERSION}/{node}/media",
        data={
            "media_type": "CAROUSEL",
            "children": ",".join(child_ids),
            "caption": caption or "",
            "access_token": token,
        },
        timeout=30,
    )
    j = r.json() or {}
    if "id" not in j:
        return {"published": False, "stage": "parent_container", "error": j.get("error", j)}
    parent_id = j["id"]

    # 2b. Wait for the parent to finish processing
    ready = _wait_container_ready(parent_id, token)
    if ready != "FINISHED":
        return {"published": False, "stage": "container_ready", "error": f"container status {ready}", "container_id": parent_id}

    # 3. Publish
    r = requests.post(
        f"{GRAPH_HOST}/{GRAPH_VERSION}/{node}/media_publish",
        data={"creation_id": parent_id, "access_token": token},
        timeout=30,
    )
    j = r.json() or {}
    if "id" not in j:
        return {"published": False, "stage": "media_publish", "error": j.get("error", j)}
    media_id = j["id"]

    # 4. Fetch permalink (best-effort)
    permalink = ""
    try:
        pr = requests.get(
            f"{GRAPH_HOST}/{GRAPH_VERSION}/{media_id}",
            params={"fields": "permalink", "access_token": token},
            timeout=15,
        )
        permalink = (pr.json() or {}).get("permalink", "")
    except Exception:
        pass

    return {"published": True, "media_id": media_id, "permalink": permalink}


def token_status(token: str) -> dict[str, Any]:
    """Read-only liveness probe for the IG token. Used by the publish endpoint to
    decide auto-publish vs prepare-only, and by a /api/publish/check route."""
    if not token:
        return {"live": False, "reason": "no_token"}
    try:
        r = requests.get(
            f"{GRAPH_HOST}/{GRAPH_VERSION}/me",
            params={"fields": "id,user_id,username,account_type", "access_token": token},
            timeout=15,
        )
        j = r.json() or {}
        if "error" in j:
            err = j["error"]
            return {"live": False, "reason": err.get("message", "error"), "code": err.get("code")}
        return {"live": True, "username": j.get("username"), "account_type": j.get("account_type"),
                "id": j.get("id"), "user_id": j.get("user_id")}
    except Exception as e:
        return {"live": False, "reason": str(e)}
