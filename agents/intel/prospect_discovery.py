"""
prospect_discovery.py — Real prospect sourcing for the DM Hunter (F2).

Real-data only. The IG Hashtag *API* strips owner identity, so prospect discovery
MUST use Apify (which returns ownerUsername). Two sources, same normalized shape:

  1. Apify `apify/instagram-hashtag-scraper` over the brand's ICP hashtags →
     unique post-owners + the caption that surfaced them (the intent signal).
     Gated on APIFY_API_KEY; costs Apify credits + ~poll wait. OFF without the key.

  2. Paste-in files at `brands/{slug}/prospects/*.json` — a manual list of handles
     to research (list of {handle, platform, bio, recent_post, ...} or {"prospects":[...]}).
     $0, explicit, the default for testing. Tried FIRST.

Normalized prospect shape (every field traceable to a real source):
  {
    "platform":     "instagram" | "linkedin" | ...,
    "handle":       str,
    "profile_url":  str | None,
    "bio":          str | None,
    "signal_text":  str,          # the post/caption/quote that flagged them (raw — caller wraps via _untrusted)
    "signal_source":str | None,   # permalink / where the signal came from
    "source":       str,          # "apify:instagram-hashtag-scraper" | "prospect_file:<name>"
  }

Nothing here calls an LLM. Nothing here logs the token.
"""
from __future__ import annotations

import os
import time
import json
from pathlib import Path

import requests

APIFY_BASE = "https://api.apify.com/v2"
HASHTAG_ACTOR = "apify~instagram-hashtag-scraper"


def _icp_hashtags(brand_profile: dict) -> list[str]:
    for key in ("icp_hashtags", "niche_hashtags", "hashtags", "target_hashtags"):
        v = brand_profile.get(key)
        if isinstance(v, list) and v:
            return [str(t).lstrip("#") for t in v][:5]
    return []


def _apify_run_sync(actor_id: str, input_body: dict, limit: int = 50,
                    max_wait_s: int = 150, poll_s: int = 10) -> tuple[list, str | None]:
    """Start an actor, poll to terminal, fetch items. Returns (items, error)."""
    token = (os.getenv("APIFY_API_KEY") or "").strip()
    if not token:
        return [], "APIFY_API_KEY not set"
    try:
        r = requests.post(f"{APIFY_BASE}/acts/{actor_id}/runs?token={token}",
                          json=input_body, timeout=30)
        if r.status_code != 201:
            return [], f"start HTTP {r.status_code}: {r.text[:160]}"
        run_id = r.json()["data"]["id"]
    except Exception as e:
        return [], f"start exception: {type(e).__name__}"

    waited = 0
    while waited < max_wait_s:
        time.sleep(poll_s)
        waited += poll_s
        try:
            sr = requests.get(f"{APIFY_BASE}/actor-runs/{run_id}?token={token}", timeout=20)
            status = sr.json().get("data", {}).get("status") if sr.status_code == 200 else None
        except Exception:
            status = None
        if status in ("SUCCEEDED", "FAILED", "ABORTED", "TIMED-OUT"):
            break
    try:
        dr = requests.get(
            f"{APIFY_BASE}/actor-runs/{run_id}/dataset/items?token={token}&limit={limit}",
            timeout=30)
        if dr.status_code == 200:
            return dr.json(), None
        return [], f"fetch HTTP {dr.status_code}"
    except Exception as e:
        return [], f"fetch exception: {type(e).__name__}"


def discover_via_hashtags(hashtags: list[str], limit: int = 50) -> tuple[list[dict], list[str]]:
    """Apify hashtag scrape → unique owners + the caption that surfaced them."""
    if not hashtags:
        return [], ["no ICP hashtags in brand_profile — Apify discovery skipped."]
    items, err = _apify_run_sync(HASHTAG_ACTOR, {
        "hashtags": hashtags, "resultsType": "posts", "resultsLimit": limit,
    }, limit=limit)
    if err:
        return [], [f"apify hashtag scrape: {err}"]

    seen: set[str] = set()
    prospects: list[dict] = []
    for p in items:
        owner = p.get("ownerUsername") or p.get("ownerUserName")
        if not owner or owner in seen:
            continue
        seen.add(owner)
        prospects.append({
            "platform":      "instagram",
            "handle":        owner,
            "profile_url":   f"https://www.instagram.com/{owner}/",
            "bio":           None,
            "signal_text":   (p.get("caption") or "")[:400],
            "signal_source": p.get("url") or p.get("permalink"),
            "source":        "apify:instagram-hashtag-scraper",
        })
    return prospects, [f"apify: {len(prospects)} unique owner(s) from {len(hashtags)} hashtag(s)"]


def _normalize_file_prospect(platform_default: str, item) -> dict | None:
    if not isinstance(item, dict):
        return None
    handle = item.get("handle") or item.get("username") or item.get("profile") or item.get("name")
    if not handle:
        return None
    signal = (item.get("recent_post") or item.get("signal") or item.get("signal_text")
              or item.get("post") or item.get("bio") or "").strip()
    return {
        "platform":      item.get("platform") or platform_default,
        "handle":        str(handle),
        "profile_url":   item.get("profile_url") or item.get("url") or item.get("link"),
        "bio":           item.get("bio"),
        "signal_text":   signal,
        "signal_source": item.get("signal_source") or item.get("url"),
        "source":        "prospect_file",
    }


def read_prospect_files(brand_dir: str | Path) -> tuple[list[dict], list[str]]:
    pdir = Path(brand_dir) / "prospects"
    prospects: list[dict] = []
    notes: list[str] = []
    if not pdir.exists():
        return [], ["no prospects/ dir — paste-in prospect list unavailable."]
    for fp in sorted(pdir.glob("*.json")):
        platform = fp.stem.lower()
        try:
            data = json.loads(fp.read_text())
        except Exception as e:
            notes.append(f"{fp.name}: parse error ({type(e).__name__})")
            continue
        items = data.get("prospects", []) if isinstance(data, dict) else data
        if not isinstance(items, list):
            notes.append(f"{fp.name}: expected a list or {{'prospects': [...]}}")
            continue
        kept = 0
        for it in items:
            norm = _normalize_file_prospect(platform, it)
            if norm:
                norm["source"] = f"prospect_file:{fp.name}"
                prospects.append(norm)
                kept += 1
        notes.append(f"{fp.name}: {kept} prospect(s)")
    return prospects, notes


def collect_prospects(brand_profile: dict, brand_dir: str | Path) -> dict:
    """Paste-in first (cheap/explicit); else live Apify hashtag discovery. Caller wraps via _untrusted."""
    file_prospects, file_notes = read_prospect_files(brand_dir)
    if file_prospects:
        prospects, notes, source = file_prospects, file_notes, "prospect_files"
    else:
        prospects, notes = discover_via_hashtags(_icp_hashtags(brand_profile))
        notes = file_notes + notes
        source = "apify_hashtags"

    # Dedupe on (platform, handle)
    seen: set[tuple] = set()
    deduped: list[dict] = []
    for p in prospects:
        key = (p["platform"], p["handle"].lower())
        if key in seen:
            continue
        seen.add(key)
        deduped.append(p)

    return {
        "prospects": deduped,
        "count": len(deduped),
        "discovery_source": source,
        "notes": notes,
    }
