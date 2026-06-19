"""
Supadata.ai client — Phase 2b (Jun 18 2026).

Hosted video → transcript. Replaces the local Whisper + yt_dlp pipeline that
silently breaks in prod (Railway has neither, local Mac is missing yt_dlp).
Supports YouTube, TikTok, Instagram, X, Facebook.

Endpoint: https://api.supadata.ai/v1/transcript?url=<video_url>
Auth: x-api-key header.
Free tier: 100 requests, no card.

Public API:
    sd = get_supadata()
    out = sd.transcript("https://www.youtube.com/watch?v=...")
    # → { ok, content, lang, source }
"""
import os
from typing import Optional
from dotenv import load_dotenv

_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
load_dotenv(os.path.join(_PROJECT_ROOT, ".env"))


class SupadataClient:
    """Thin wrapper. Silent no-op without key."""

    BASE = "https://api.supadata.ai/v1/transcript"

    def __init__(self):
        self._key = os.getenv("SUPADATA_API_KEY") or ""
        self._ok = bool(self._key)
        if not self._ok:
            return
        try:
            import requests
            self._requests = requests
        except Exception as e:
            print(f"[supadata] requests missing: {e}")
            self._ok = False

    @property
    def enabled(self) -> bool:
        return self._ok

    def transcript(self, video_url: str, timeout: int = 30) -> dict:
        """Return {ok, content, lang, source, error?}. Never raises."""
        if not self._ok:
            return {"ok": False, "error": "SUPADATA_API_KEY not set", "url": video_url}
        try:
            r = self._requests.get(
                self.BASE,
                params={"url": video_url, "text": "true"},
                headers={"x-api-key": self._key},
                timeout=timeout,
            )
            if r.status_code != 200:
                return {"ok": False, "error": f"http {r.status_code}", "body": r.text[:200], "url": video_url}
            data = r.json()
            content = data.get("content") or data.get("transcript") or ""
            if isinstance(content, list):
                content = " ".join(seg.get("text", "") for seg in content if isinstance(seg, dict))
            return {
                "ok": bool(content),
                "content": content,
                "lang": data.get("lang") or data.get("language") or "",
                "source": "supadata",
                "url": video_url,
            }
        except Exception as e:
            return {"ok": False, "error": str(e), "url": video_url}


_singleton: Optional[SupadataClient] = None


def get_supadata() -> SupadataClient:
    global _singleton
    if _singleton is None:
        _singleton = SupadataClient()
    return _singleton
