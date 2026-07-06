"""
Generate Google Ads API refresh token via Desktop OAuth flow.
Run once. Opens browser → consent → returns refresh_token.
Paste into .env as GOOGLE_ADS_REFRESH_TOKEN.
"""
import os
from dotenv import load_dotenv
from google_auth_oauthlib.flow import InstalledAppFlow

load_dotenv()

CLIENT_ID = os.getenv("GOOGLE_ADS_CLIENT_ID")
CLIENT_SECRET = os.getenv("GOOGLE_ADS_CLIENT_SECRET")
SCOPES = ["https://www.googleapis.com/auth/adwords"]

if not (CLIENT_ID and CLIENT_SECRET):
    raise SystemExit("Missing GOOGLE_ADS_CLIENT_ID / GOOGLE_ADS_CLIENT_SECRET in .env")

client_config = {
    "installed": {
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET,
        "auth_uri": "https://accounts.google.com/o/oauth2/auth",
        "token_uri": "https://oauth2.googleapis.com/token",
        "redirect_uris": ["http://localhost"],
    }
}

flow = InstalledAppFlow.from_client_config(client_config, scopes=SCOPES)
# access_type=offline forces refresh_token issuance; prompt=consent forces re-grant
creds = flow.run_local_server(port=0, access_type="offline", prompt="consent")

print()
print("=" * 60)
print("REFRESH TOKEN (paste into .env):")
print()
print(f"GOOGLE_ADS_REFRESH_TOKEN={creds.refresh_token}")
print("=" * 60)
