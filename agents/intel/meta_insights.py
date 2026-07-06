"""
meta_insights.py — Live Instagram insights via the Instagram Login API.

Real-data only. Every value here comes from a live Meta call. Nothing is
fabricated. When a metric is unavailable (low follower count, missing scope,
deprecated metric), the field is omitted and a note is recorded in `errors` —
callers must treat absence as "no data", never invent a number.

Auth model (Instagram Login API — the SAME token that publishes):
  META_GRAPH_API_TOKEN — Instagram Login token (IGAA…) for the brand's IG
                         professional account, with scope
                         `instagram_business_manage_insights` added.
  IG_USER_ID           — the IG business/creator account id (already in .env).

Endpoint: https://graph.instagram.com/<version>/...  (NOT graph.facebook.com).
This keeps one auth per brand for both publishing and insights — fewer moving
parts, nothing to silently break (no Facebook-Page link dependency).

Demographics (follower_demographics) require 100+ followers; below that Meta
returns an error which we capture gracefully (empty, with a note).

Usage:
    from agents.intel.meta_insights import fetch_instagram_insights
    data = fetch_instagram_insights(brand_env_dict)
"""
from __future__ import annotations

import os
from datetime import datetime, timedelta
from typing import Any

import requests

GRAPH = "https://graph.instagram.com/v21.0"
TIMEOUT = 8


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


def fetch_instagram_insights(benv: dict) -> dict[str, Any]:
    """Pull live IG insights for the brand via the Instagram Login API.
    Returns a structured dict: a `connected` flag, the metrics that succeeded,
    and an `errors` list for the ones that did not. Caller feeds this straight
    into the Data Analyst package.
    """
    token = (benv.get("META_GRAPH_API_TOKEN") or "").strip()
    ig_id = (benv.get("IG_USER_ID") or "").strip()

    out: dict[str, Any] = {
        "source": "instagram_login_api",
        "fetched_at": datetime.now().isoformat(),
        "connected": False,
        "ig_user_id": ig_id or None,
        "account": {},
        "audience": {},
        "errors": [],
    }

    if not token:
        out["errors"].append("META_GRAPH_API_TOKEN not set — connect Instagram first.")
        return out
    if not ig_id:
        out["errors"].append("IG_USER_ID not set — cannot query IG insights.")
        return out

    # ── 0. Identity / follower count (also confirms the token works) ──────────
    prof, err = _get(ig_id, {
        "fields": "username,followers_count,follows_count,media_count",
        "access_token": token,
    })
    if err:
        out["errors"].append(f"profile: {err}")
        return out  # token bad / no access → stop, return honest empty
    out["connected"] = True
    out["account"]["username"] = prof.get("username")
    out["account"]["followers_count"] = prof.get("followers_count")
    out["account"]["follows_count"] = prof.get("follows_count")
    out["account"]["media_count"] = prof.get("media_count")
    followers = prof.get("followers_count") or 0

    # ── 1. Account reach (last 28d, total_value form) ────────────────────────
    #     Requires instagram_business_manage_insights. If the scope is missing
    #     the error is captured here (telling us the token needs regenerating).
    since = (datetime.now() - timedelta(days=28)).strftime("%Y-%m-%d")
    reach, err = _get(f"{ig_id}/insights", {
        "metric": "reach",
        "period": "day",
        "metric_type": "total_value",
        "since": since,
        "access_token": token,
    })
    if err:
        out["errors"].append(f"reach: {err}")
    elif reach and reach.get("data"):
        try:
            tv = reach["data"][0].get("total_value", {}).get("value")
            out["account"]["reach_28d"] = tv
        except Exception:
            out["errors"].append("reach: unexpected shape")

    # ── 2. Audience demographics (needs 100+ followers) ──────────────────────
    if followers >= 100:
        for breakdown in ("country", "age", "gender"):
            demo, err = _get(f"{ig_id}/insights", {
                "metric": "follower_demographics",
                "period": "lifetime",
                "metric_type": "total_value",
                "timeframe": "last_30_days",
                "breakdown": breakdown,
                "access_token": token,
            })
            if err:
                out["errors"].append(f"demographics[{breakdown}]: {err}")
                continue
            try:
                results = demo["data"][0]["total_value"]["breakdowns"][0]["results"]
                out["audience"][breakdown] = {
                    r["dimension_values"][0]: r["value"] for r in results
                }
            except Exception:
                out["errors"].append(f"demographics[{breakdown}]: unexpected shape")
    else:
        out["audience"]["_note"] = (
            f"Audience demographics unlock at 100 followers "
            f"(currently {followers}). Plumbing verified; data will populate as the account grows."
        )

    return out


if __name__ == "__main__":
    # Standalone probe: ACTIVE_BRAND=askgauravai python3 agents/meta_insights.py
    from pathlib import Path

    from agents._lib import token_crypto

    slug = os.getenv("ACTIVE_BRAND", "askgauravai")
    env_path = Path(__file__).resolve().parent.parent.parent / "brands" / slug / ".env"
    benv: dict[str, str] = {}
    if env_path.exists():
        for line in env_path.read_text().splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                benv[k.strip()] = token_crypto.decrypt(v.strip())
    result = fetch_instagram_insights(benv)
    # Print connection + metric KEYS and error notes only — never raw token.
    print(f"connected   : {result['connected']}")
    print(f"account     : {result['account']}")
    print(f"audience    : {list(result['audience'].keys())}")
    print(f"errors      : {result['errors']}")
