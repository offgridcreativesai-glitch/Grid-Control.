"""
utils/scrape_cache.py — Phase E2 scrape cache.

Cuts re-scrape bleed (~80%): one scrape feeds many runs within a TTL window.
File-based, per-brand, keyed by (source, target). Read by the Trend Researcher
(and any owned-scrape path) BEFORE hitting Apify/Scrapling — on a fresh hit it
skips both the API cost AND the 90–120s actor wait.

Design:
  - Cache lives in brands/{slug}/cache/scrapes/{source}__{key_hash}.json
  - Each entry stores {fetched_at, ttl_hours, source, target, data}.
  - get(...) returns the cached `data` if present and within TTL, else None.
  - put(...) writes/overwrites the entry.
  - Disable globally with SCRAPE_CACHE_DISABLED=1 (forces every call to miss).

This is intentionally dependency-free (stdlib only) so any agent subprocess can
use it without import risk. Scrapling/Apify remain the fetch backends; this only
decides whether a fetch is needed.
"""
import os
import json
import time
import hashlib
from datetime import datetime, timezone
from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parent.parent


def _disabled() -> bool:
    return os.getenv("SCRAPE_CACHE_DISABLED", "").strip() in ("1", "true", "True")


def _cache_dir(brand_slug: str) -> Path:
    return _PROJECT_ROOT / "brands" / brand_slug / "cache" / "scrapes"


def _key_hash(target) -> str:
    """Stable short hash for a target (str, list, or dict)."""
    if isinstance(target, (list, dict)):
        raw = json.dumps(target, sort_keys=True, ensure_ascii=False)
    else:
        raw = str(target)
    return hashlib.sha1(raw.encode("utf-8")).hexdigest()[:16]


def _path(brand_slug: str, source: str, target) -> Path:
    safe_source = "".join(c for c in source if c.isalnum() or c in "-_")
    return _cache_dir(brand_slug) / f"{safe_source}__{_key_hash(target)}.json"


def get(brand_slug: str, source: str, target, ttl_hours: float = 24.0):
    """Return cached scrape `data` if present and within TTL, else None.

    source: logical source label, e.g. 'ig_hashtags', 'ig_brand_profile'.
    target: what was scraped (hashtag list, handle, url) — part of the key.
    """
    if _disabled() or not brand_slug:
        return None
    p = _path(brand_slug, source, target)
    if not p.exists():
        return None
    try:
        entry = json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return None
    fetched_at = entry.get("fetched_at_epoch", 0)
    ttl = entry.get("ttl_hours", ttl_hours)
    age_hours = (time.time() - fetched_at) / 3600.0
    if age_hours > ttl:
        return None  # stale
    return entry.get("data")


def put(brand_slug: str, source: str, target, data, ttl_hours: float = 24.0) -> None:
    """Store scrape `data` for (source, target). Best-effort; never raises."""
    if _disabled() or not brand_slug:
        return
    try:
        d = _cache_dir(brand_slug)
        d.mkdir(parents=True, exist_ok=True)
        entry = {
            "source": source,
            "target": target,
            "fetched_at": datetime.now(timezone.utc).isoformat(),
            "fetched_at_epoch": time.time(),
            "ttl_hours": ttl_hours,
            "data": data,
        }
        _path(brand_slug, source, target).write_text(
            json.dumps(entry, ensure_ascii=False, indent=2), encoding="utf-8"
        )
    except Exception as e:
        print(f"[scrape_cache] put failed ({source}): {e}")


def age_hours(brand_slug: str, source: str, target) -> float | None:
    """Return the age of a cached entry in hours, or None if absent."""
    p = _path(brand_slug, source, target)
    if not p.exists():
        return None
    try:
        entry = json.loads(p.read_text(encoding="utf-8"))
        return (time.time() - entry.get("fetched_at_epoch", 0)) / 3600.0
    except Exception:
        return None
