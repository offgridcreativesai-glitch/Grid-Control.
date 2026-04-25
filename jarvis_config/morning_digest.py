"""
jarvis_config/morning_digest.py
Morning briefing — reads Grid Control API and speaks a 3-sentence brief.

Run manually: python jarvis_config/morning_digest.py
Schedule via cron: 0 8 * * * cd /path/to/project && python jarvis_config/morning_digest.py
"""

import os
import sys
import json
import requests

# Allow running from project root
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

GRID_API = os.getenv("GRID_API_URL", "http://localhost:5001")
SECRET   = os.getenv("DASHBOARD_SECRET", "")
HEADERS  = {"X-Dashboard-Secret": SECRET} if SECRET else {}


def _get(path: str) -> dict:
    try:
        r = requests.get(f"{GRID_API}{path}", headers=HEADERS, timeout=10)
        return r.json() if r.ok else {}
    except Exception:
        return {}


def build_digest() -> str:
    """Build a 3-sentence spoken brief from Grid Control state."""
    # Get all brands
    brands_resp = _get("/api/brands")
    brands = brands_resp.get("data", []) if brands_resp.get("success") else []
    brand_count = len(brands)

    # Count pending approvals across all brands
    total_pending = 0
    for brand in brands[:5]:
        slug = brand.get("slug", "")
        if slug:
            outputs = _get(f"/api/outputs/pending?brand_slug={slug}")
            items = outputs.get("data", []) if outputs.get("success") else []
            total_pending += len(items)

    # Get agent status for first brand
    next_agent = "no agents queued"
    if brands:
        slug      = brands[0].get("slug", "")
        status    = _get(f"/api/agents/status?brand_slug={slug}")
        agents    = status.get("data", []) if status.get("success") else []
        for a in agents:
            if a.get("status") == "idle" and a.get("enabled"):
                next_agent = a.get("name", "unknown agent")
                break

    sentences = [
        f"Good morning. Grid Control is managing {brand_count} brand{'s' if brand_count != 1 else ''}.",
        f"You have {total_pending} output{'s' if total_pending != 1 else ''} pending your approval.",
        f"The next agent ready to run is {next_agent}." if next_agent != "no agents queued"
        else "All agents are up to date.",
    ]

    return " ".join(sentences)


if __name__ == "__main__":
    from jarvis_config.tts import speak

    brief = build_digest()
    print(f"\n[Morning Digest]\n{brief}\n")
    try:
        speak(brief, play=True)
    except ImportError as e:
        print(f"TTS skipped: {e}")
        print("Install with: pip install edge-tts")
