"""
YouTube publisher — uploads a REAL video file via youtube.upload, authorized by the
brand's OAuth refresh token (minted once by publishing/youtube_oauth.py). Client id/secret
+ refresh token come from the brand's private .env.

Hard constraint (zero fabrication): YouTube needs an actual video file on disk. We never
generate, stub, or substitute a placeholder. If no real video_path is provided, the caller
gets a clear 'needs_video' signal — nothing is uploaded.

Two-mode contract:
  - refresh token live + video file present → uploads for real, returns the watch URL.
  - token absent/blocked → 'prepared' (title/description ready, awaiting a working token).
"""
from __future__ import annotations

import os
from typing import Any

from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

SCOPES = ["https://www.googleapis.com/auth/youtube.upload",
          "https://www.googleapis.com/auth/youtube.readonly"]
TOKEN_URI = "https://oauth2.googleapis.com/token"


def _credentials(client_id: str, client_secret: str, refresh_token: str) -> Credentials:
    return Credentials(
        token=None,
        refresh_token=refresh_token,
        token_uri=TOKEN_URI,
        client_id=client_id,
        client_secret=client_secret,
        scopes=SCOPES,
    )


def token_status(client_id: str, client_secret: str, refresh_token: str) -> dict[str, Any]:
    """Read-only liveness probe — refresh the token and read the channel title."""
    if not all([client_id, client_secret, refresh_token]):
        return {"live": False, "reason": "missing_oauth_keys"}
    try:
        creds = _credentials(client_id, client_secret, refresh_token)
        yt = build("youtube", "v3", credentials=creds, cache_discovery=False)
        resp = yt.channels().list(part="snippet", mine=True).execute()
        items = resp.get("items", [])
        if not items:
            return {"live": True, "account": "(no channel on this account)"}
        return {"live": True, "account": items[0]["snippet"]["title"]}
    except Exception as e:
        return {"live": False, "reason": str(e)[:200]}


def upload_video(
    client_id: str,
    client_secret: str,
    refresh_token: str,
    video_path: str,
    title: str,
    description: str = "",
    tags: list[str] | None = None,
    privacy: str = "public",
) -> dict[str, Any]:
    """Upload a real video file. Returns a result dict with the video id + watch URL.
    Returns mode 'needs_video' if the file is missing — never fabricates an upload."""
    if not video_path or not os.path.isfile(video_path):
        return {
            "published": False,
            "mode": "needs_video",
            "error": f"No real video file found at: {video_path or '(none provided)'}",
            "note": "YouTube requires an actual founder-recorded video. Add video_path to the approved output; nothing was uploaded.",
        }
    try:
        creds = _credentials(client_id, client_secret, refresh_token)
        yt = build("youtube", "v3", credentials=creds, cache_discovery=False)
        body = {
            "snippet": {"title": title or "Untitled", "description": description or "", "tags": tags or []},
            "status": {"privacyStatus": privacy if privacy in ("public", "unlisted", "private") else "public"},
        }
        media = MediaFileUpload(video_path, resumable=True, chunksize=-1)
        request = yt.videos().insert(part="snippet,status", body=body, media_body=media)
        response = None
        while response is None:
            _, response = request.next_chunk()
        video_id = response.get("id", "")
        return {"published": True, "video_id": video_id, "permalink": f"https://youtu.be/{video_id}"}
    except Exception as e:
        return {"published": False, "stage": "videos.insert", "error": str(e)[:300]}
