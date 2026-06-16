"""
inbound_comments.py — Real inbound ingestion for the Community Manager (F1).

Real-data only. Two sources, both returning the SAME normalized shape:

  1. Live Instagram comments via the Instagram Login API (graph.instagram.com) —
     the SAME token that publishes/insights (META_GRAPH_API_TOKEN + IG_USER_ID).
     Needs the `instagram_manage_comments` scope; if absent Meta returns an error
     which we capture gracefully (empty, with a note) — never fabricate.

  2. Paste-in / Chrome-MCP files at `brands/{slug}/inbound/{platform}.json` for
     platforms without a live read path here (YouTube, LinkedIn, X). Each file is
     a list of comment objects (or {"comments": [...]}). The filename stem is the
     platform label.

Normalized comment shape (every field traceable to a real source):
  {
    "platform":   "instagram" | "youtube" | "linkedin" | "x" | ...,
    "comment_id": str,                 # platform id, or a stable hash fallback
    "media_ref":  str | None,          # post/media id or permalink the comment is on
    "author":     str | None,          # username / handle
    "text":       str,                 # the comment body (raw — caller MUST wrap via _untrusted)
    "timestamp":  str | None,
    "permalink":  str | None,
    "source":     str,                 # "instagram_login_api" | "inbound_file:<name>"
  }

Nothing here calls an LLM. Nothing here logs the token.
"""
from __future__ import annotations

import json
import hashlib
from pathlib import Path
from typing import Any

import requests

GRAPH = "https://graph.instagram.com/v21.0"
TIMEOUT = 8


def _stable_id(platform: str, author: str | None, text: str) -> str:
    """Deterministic id when the source doesn't supply one (dedupe-safe)."""
    h = hashlib.sha1(f"{platform}|{author or ''}|{text}".encode("utf-8")).hexdigest()[:16]
    return f"{platform}_{h}"


def _get(path: str, params: dict) -> tuple[dict | None, str | None]:
    """GET helper. Returns (json, error_str). Never raises. Never logs token."""
    try:
        r = requests.get(f"{GRAPH}/{path}", params=params, timeout=TIMEOUT)
        if r.status_code == 200:
            return r.json(), None
        try:
            msg = r.json().get("error", {}).get("message", "")
        except Exception:
            msg = r.text[:160]
        return None, f"HTTP {r.status_code}: {msg}"
    except Exception as e:
        return None, f"{type(e).__name__}: {e}"


def fetch_recent_ig_comments(benv: dict, max_media: int = 8, max_comments_per: int = 25) -> tuple[list[dict], list[str]]:
    """Pull comments on the brand's recent IG media. Returns (comments, errors).

    Defensive: any failure (bad token, missing scope, no media) returns whatever
    succeeded plus an error note — never raises, never invents data.
    """
    token = (benv.get("META_GRAPH_API_TOKEN") or "").strip()
    ig_id = (benv.get("IG_USER_ID") or "").strip()
    errors: list[str] = []
    comments: list[dict] = []

    if not token:
        return [], ["META_GRAPH_API_TOKEN not set — connect Instagram first."]
    if not ig_id:
        return [], ["IG_USER_ID not set — cannot query IG comments."]

    media, err = _get(f"{ig_id}/media", {
        "fields": "id,permalink,timestamp",
        "limit": max_media,
        "access_token": token,
    })
    if err:
        return [], [f"media list: {err}"]

    for m in (media or {}).get("data", []):
        media_id = m.get("id")
        permalink = m.get("permalink")
        if not media_id:
            continue
        cdata, cerr = _get(f"{media_id}/comments", {
            "fields": "id,text,username,timestamp",
            "limit": max_comments_per,
            "access_token": token,
        })
        if cerr:
            errors.append(f"comments on {media_id}: {cerr}")
            continue
        for c in (cdata or {}).get("data", []):
            text = (c.get("text") or "").strip()
            if not text:
                continue
            comments.append({
                "platform":   "instagram",
                "comment_id": c.get("id") or _stable_id("instagram", c.get("username"), text),
                "media_ref":  media_id,
                "author":     c.get("username"),
                "text":       text,
                "timestamp":  c.get("timestamp"),
                "permalink":  permalink,
                "source":     "instagram_login_api",
            })

    return comments, errors


def _normalize_file_item(platform: str, item: Any) -> dict | None:
    """Coerce one paste-in record into the normalized shape. None if no text."""
    if isinstance(item, str):
        text = item.strip()
        if not text:
            return None
        return {
            "platform": platform, "comment_id": _stable_id(platform, None, text),
            "media_ref": None, "author": None, "text": text,
            "timestamp": None, "permalink": None, "source": f"inbound_file:{platform}",
        }
    if not isinstance(item, dict):
        return None
    text = (item.get("text") or item.get("message") or item.get("comment") or item.get("body") or "").strip()
    if not text:
        return None
    author = item.get("author") or item.get("username") or item.get("from") or item.get("user")
    return {
        "platform":   platform,
        "comment_id": str(item.get("id") or item.get("comment_id") or _stable_id(platform, author, text)),
        "media_ref":  item.get("media_ref") or item.get("post") or item.get("post_id") or item.get("video_id"),
        "author":     author,
        "text":       text,
        "timestamp":  item.get("timestamp") or item.get("time") or item.get("created_at"),
        "permalink":  item.get("permalink") or item.get("url") or item.get("link"),
        "source":     f"inbound_file:{platform}",
    }


def read_inbound_files(brand_dir: str | Path) -> tuple[list[dict], list[str]]:
    """Read brands/{slug}/inbound/*.json paste-in files. Returns (comments, notes)."""
    inbound_dir = Path(brand_dir) / "inbound"
    comments: list[dict] = []
    notes: list[str] = []
    if not inbound_dir.exists():
        return [], ["no inbound/ dir — paste-in comments unavailable for non-IG platforms."]

    for fp in sorted(inbound_dir.glob("*.json")):
        platform = fp.stem.lower()
        try:
            data = json.loads(fp.read_text())
        except Exception as e:
            notes.append(f"{fp.name}: parse error ({type(e).__name__})")
            continue
        items = data.get("comments", []) if isinstance(data, dict) else data
        if not isinstance(items, list):
            notes.append(f"{fp.name}: expected a list or {{'comments': [...]}}")
            continue
        kept = 0
        for it in items:
            norm = _normalize_file_item(platform, it)
            if norm:
                comments.append(norm)
                kept += 1
        notes.append(f"{fp.name}: {kept} comment(s)")

    return comments, notes


def collect_all_inbound(benv: dict, brand_dir: str | Path) -> dict:
    """Top-level ingestion: live IG + paste-in files. Caller wraps text via _untrusted."""
    ig_comments, ig_errors = fetch_recent_ig_comments(benv)
    file_comments, file_notes = read_inbound_files(brand_dir)

    all_comments = ig_comments + file_comments
    # Dedupe on (platform, comment_id)
    seen: set[tuple] = set()
    deduped: list[dict] = []
    for c in all_comments:
        key = (c["platform"], c["comment_id"])
        if key in seen:
            continue
        seen.add(key)
        deduped.append(c)

    return {
        "comments": deduped,
        "count": len(deduped),
        "by_platform": {p: sum(1 for c in deduped if c["platform"] == p)
                        for p in sorted({c["platform"] for c in deduped})},
        "ig_errors": ig_errors,
        "file_notes": file_notes,
    }
