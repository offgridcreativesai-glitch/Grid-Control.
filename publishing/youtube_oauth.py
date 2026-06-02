"""
YouTube OAuth — one-time consent flow to mint a durable refresh token.

Reads YOUTUBE_CLIENT_ID + YOUTUBE_CLIENT_SECRET from a brand's private .env
(brands/<slug>/.env), runs the Google "installed app" consent flow in the
browser, and writes YOUTUBE_REFRESH_TOKEN back into that same .env.

The refresh token is what actually authorizes uploads/reads later — access
tokens are minted from it on demand and expire in ~1h.

Usage:
    python3 publishing/youtube_oauth.py askgauravai
    # or rely on ACTIVE_BRAND:
    ACTIVE_BRAND=askgauravai python3 publishing/youtube_oauth.py
"""
import os
import re
import sys
from pathlib import Path

from dotenv import dotenv_values
from google_auth_oauthlib.flow import InstalledAppFlow
import googleapiclient.discovery

BASE_DIR = Path(__file__).resolve().parent.parent
SCOPES = [
    "https://www.googleapis.com/auth/youtube.upload",
    "https://www.googleapis.com/auth/youtube.readonly",
]


def _brand_env_path(slug: str) -> Path:
    return BASE_DIR / "brands" / slug / ".env"


def _write_env(path: Path, key: str, value: str) -> None:
    content = path.read_text(encoding="utf-8") if path.exists() else ""
    pattern = re.compile(rf"^{re.escape(key)}\s*=.*$", re.MULTILINE)
    line = f"{key}={value}"
    if pattern.search(content):
        content = pattern.sub(line, content)
    else:
        content = content.rstrip("\n") + ("\n" if content else "") + line + "\n"
    path.write_text(content, encoding="utf-8")


def main() -> int:
    slug = (sys.argv[1] if len(sys.argv) > 1 else os.getenv("ACTIVE_BRAND", "")).strip()
    if not slug:
        print("ERROR: pass a brand slug (e.g. askgauravai) or set ACTIVE_BRAND.")
        return 1

    env_path = _brand_env_path(slug)
    if not env_path.exists():
        print(f"ERROR: {env_path} not found.")
        return 1

    env = dotenv_values(env_path)
    client_id = (env.get("YOUTUBE_CLIENT_ID") or "").strip()
    client_secret = (env.get("YOUTUBE_CLIENT_SECRET") or "").strip()
    if not client_id or not client_secret:
        print("ERROR: YOUTUBE_CLIENT_ID / YOUTUBE_CLIENT_SECRET missing in brand .env.")
        return 1

    client_config = {
        "installed": {
            "client_id": client_id,
            "client_secret": client_secret,
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
            "redirect_uris": ["http://localhost"],
        }
    }

    print(f"\n→ Starting YouTube consent for brand '{slug}'.")
    print("  A browser window will open. Sign in with the AskGauravAI channel's")
    print("  Google account and click Allow. (If you see an 'unverified app' warning,")
    print("  click Advanced → Go to … (unsafe) — it's your own app.)\n")

    flow = InstalledAppFlow.from_client_config(client_config, scopes=SCOPES)
    # access_type=offline + prompt=consent guarantees a refresh_token is returned
    creds = flow.run_local_server(
        port=0, access_type="offline", prompt="consent", open_browser=True
    )

    if not creds.refresh_token:
        print("ERROR: No refresh token returned. Re-run and ensure you fully consent.")
        return 1

    _write_env(env_path, "YOUTUBE_REFRESH_TOKEN", creds.refresh_token)

    # Confirm by fetching the channel title
    try:
        yt = googleapiclient.discovery.build("youtube", "v3", credentials=creds)
        resp = yt.channels().list(part="snippet", mine=True).execute()
        items = resp.get("items", [])
        title = items[0]["snippet"]["title"] if items else "(no channel on this account)"
        print(f"\n✅ Connected. Channel: {title}")
    except Exception as e:
        print(f"\n✅ Refresh token saved, but channel lookup failed: {e}")

    print(f"   YOUTUBE_REFRESH_TOKEN written to {env_path}")
    print("   Run the YouTube connection check in Grid Control to see it go green.\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
