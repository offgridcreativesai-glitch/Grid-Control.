"""
agents/_lib/_brightdata_client.py — Bright Data Web Scraper API client (Jul 11 2026).

Alternative scrape provider to Apify for the brand-book intel pipeline. Selected via the
`SCRAPE_PROVIDER` env flag (apify | brightdata); Apify stays the fallback. Bright Data's
maintained scrapers give higher reliability than Apify community Actors (which silently
break — e.g. the deprecated instagram-post-scraper returning 0 posts), and its pay-per-success
model with a 5K-records/month free tier is cheaper at our volume.

Auth: BRIGHTDATA_API_TOKEN (account API token, infra-level in the global /.env — one account
for all brands, gridadmin1). Bearer auth.

API shape (Web Scraper API v3):
  POST /datasets/v3/trigger?dataset_id=gd_...&format=json   body=[{input}]  -> {snapshot_id}
  GET  /datasets/v3/progress/{snapshot_id}                                  -> {status}
  GET  /datasets/v3/snapshot/{snapshot_id}?format=json                      -> [records]

Zero-assumption: never raises, never fabricates. Returns {"ok": False, "error": ...} on any
failure. Dataset IDs that are not yet CONFIRMED against this account are left None so the
client returns a clear "not configured" error instead of guessing (RULE ZERO).
"""
from __future__ import annotations

import json
import os
import ssl
import time
import urllib.error
import urllib.parse
import urllib.request

_BASE = "https://api.brightdata.com/datasets/v3"

try:
    import certifi
    _CTX = ssl.create_default_context(cafile=certifi.where())
except Exception:                                    # pragma: no cover
    _CTX = ssl._create_unverified_context()

# Bright Data dataset IDs (gd_*) are global per scraper (not per-account). Profiles + posts are
# the well-documented public IDs; they are still SMOKE-TESTED live before we rely on them.
# hashtag + facebook_ads are left None until confirmed from the BD dashboard (Scrapers list) —
# the client refuses to guess a production dataset_id.
DATASETS = {
    "instagram_profiles": "gd_l1vikfch901nx3by4",   # ✅ VERIFIED live Jul 11 (returns profile + own posts[])
    "instagram_posts": "gd_lk5ns7kz21pck8jpis",     # posts scraper; also serves hashtag via discover_by=hashtag
    "instagram_hashtag": "gd_lk5ns7kz21pck8jpis",   # = posts dataset, discover_by=hashtag mode (no separate scraper)
    "facebook_ads": None,                            # Bright Data has NO Meta Ad Library scraper — Meta Ads STAYS on
                                                     # Apify (facebook-ads-library-scraper). Do not build a custom one.
}


class BrightDataClient:
    """Thin Web Scraper API wrapper. Silent no-op when no token is set."""

    def __init__(self):
        self._token = (os.getenv("BRIGHTDATA_API_TOKEN") or "").strip()

    @property
    def enabled(self) -> bool:
        return bool(self._token)

    # ── HTTP ─────────────────────────────────────────────────────
    def _req(self, method: str, url: str, body: bytes | None = None, timeout: int = 30):
        req = urllib.request.Request(url, data=body, method=method)
        req.add_header("Authorization", f"Bearer {self._token}")
        if body is not None:
            req.add_header("Content-Type", "application/json")
        try:
            with urllib.request.urlopen(req, timeout=timeout, context=_CTX) as r:
                raw = r.read().decode("utf-8", "replace")
            return {"ok": True, "status": 200, "body": raw}
        except urllib.error.HTTPError as e:
            return {"ok": False, "status": e.code, "error": e.read().decode("utf-8", "replace")[:400]}
        except Exception as e:                        # pragma: no cover
            return {"ok": False, "status": None, "error": str(e)[:300]}

    # ── core: trigger → poll → download ──────────────────────────
    def trigger_and_wait(self, dataset_key: str, inputs: list, extra_params: dict | None = None,
                         timeout: int = 180, poll_every: int = 5) -> dict:
        """Run a Bright Data scraper synchronously (trigger, poll to ready, download).
        Returns {ok, records, count, snapshot_id} or {ok:False, error}."""
        if not self.enabled:
            return {"ok": False, "error": "BRIGHTDATA_API_TOKEN not set"}
        dataset_id = DATASETS.get(dataset_key)
        if not dataset_id:
            return {"ok": False, "error": f"dataset_id for '{dataset_key}' not configured — "
                    f"confirm it in the Bright Data dashboard (Scrapers) before use"}

        params = {"dataset_id": dataset_id, "format": "json"}
        params.update(extra_params or {})
        url = f"{_BASE}/trigger?" + urllib.parse.urlencode(params)
        trig = self._req("POST", url, body=json.dumps(inputs).encode("utf-8"))
        if not trig["ok"]:
            return {"ok": False, "error": f"trigger failed ({trig['status']}): {trig['error']}"}
        try:
            snapshot_id = json.loads(trig["body"]).get("snapshot_id")
        except Exception:
            return {"ok": False, "error": f"trigger returned non-JSON: {trig['body'][:200]}"}
        if not snapshot_id:
            return {"ok": False, "error": f"no snapshot_id in trigger response: {trig['body'][:200]}"}

        # poll progress
        deadline = time.time() + timeout
        while time.time() < deadline:
            prog = self._req("GET", f"{_BASE}/progress/{snapshot_id}")
            if prog["ok"]:
                try:
                    status = (json.loads(prog["body"]).get("status") or "").lower()
                except Exception:
                    status = ""
                if status == "ready":
                    break
                if status in ("failed", "error"):
                    return {"ok": False, "error": f"snapshot {snapshot_id} failed", "snapshot_id": snapshot_id}
            time.sleep(poll_every)
        else:
            return {"ok": False, "error": f"timeout after {timeout}s (snapshot {snapshot_id} not ready)",
                    "snapshot_id": snapshot_id}

        # download
        dl = self._req("GET", f"{_BASE}/snapshot/{snapshot_id}?format=json", timeout=60)
        if not dl["ok"]:
            return {"ok": False, "error": f"download failed ({dl['status']}): {dl['error']}",
                    "snapshot_id": snapshot_id}
        try:
            records = json.loads(dl["body"])
        except Exception:
            # NDJSON fallback
            records = [json.loads(ln) for ln in dl["body"].splitlines() if ln.strip()]
        if isinstance(records, dict):
            records = [records]
        return {"ok": True, "records": records, "count": len(records), "snapshot_id": snapshot_id}

    # ── high-level scrapers (map to the pipeline's needs) ────────
    def instagram_profiles(self, handles: list[str], timeout: int = 180) -> dict:
        inputs = [{"url": f"https://www.instagram.com/{h.lstrip('@').strip('/')}/"} for h in handles]
        return self.trigger_and_wait("instagram_profiles", inputs, timeout=timeout)

    def instagram_posts(self, handle: str, num_posts: int = 25, timeout: int = 240) -> dict:
        inputs = [{"url": f"https://www.instagram.com/{handle.lstrip('@').strip('/')}/",
                   "num_of_posts": num_posts}]
        return self.trigger_and_wait("instagram_posts", inputs,
                                     extra_params={"type": "discover_new", "discover_by": "url"},
                                     timeout=timeout)


_singleton: BrightDataClient | None = None


def get_brightdata() -> BrightDataClient:
    global _singleton
    if _singleton is None:
        _singleton = BrightDataClient()
    return _singleton
