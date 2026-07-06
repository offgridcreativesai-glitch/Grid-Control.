"""Real-time handle resolution for the onboarding validation gate.

Cheap-first, zero-assumption:
  - YouTube / X / LinkedIn  → free HTTP probe (200 = valid, 404 = not_found).
  - Instagram               → reuse the report's proven Apify scraper
                              (agents.intel.competitor_intel), which is already
                              paid_ops cost-gated and flags `empty` for a handle
                              that doesn't exist / is private. The scrape doubles
                              as report data, so it is never wasted.
  - TikTok / other          → best-effort HTTP; 'unknown' if the platform blocks
                              server IPs (we never assume a handle is real).

A handle is 'valid' ONLY when verified live. Anything we cannot confirm is
'not_found' (clear 404 / empty) or 'unknown' (bot-wall / rate-limit). The caller
blocks the paid Opus synthesis on any 'not_found'; 'unknown' does NOT block
(avoids false-positives stopping the flow), but is surfaced to the user.
"""
from __future__ import annotations
import requests

_UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
       "(KHTML, like Gecko) Chrome/120 Safari/537.36")

# Platforms where a plain logged-out GET reliably distinguishes real vs missing.
# (Instagram is deliberately NOT here — it serves an identical 200 login wall for
# both real and fake handles, verified empirically. It goes via Apify instead.)
_HTTP_URL = {
    "youtube":  "https://www.youtube.com/@{h}",
    "x":        "https://x.com/{h}",
    "twitter":  "https://x.com/{h}",
    "linkedin": "https://www.linkedin.com/in/{h}",
    "tiktok":   "https://www.tiktok.com/@{h}",
}


def _http_probe(platform: str, handle: str) -> dict:
    url = _HTTP_URL[platform].format(h=handle)
    try:
        r = requests.get(url, headers={"User-Agent": _UA}, allow_redirects=True, timeout=8)
        code = r.status_code
        if code == 404:
            return {"status": "not_found", "http": code, "url": url}
        if code == 200:
            return {"status": "valid", "http": code, "url": url}
        # 403 / 429 / 5xx / blocked → can't tell; don't block the flow
        return {"status": "unknown", "http": code, "url": url}
    except Exception as e:
        return {"status": "unknown", "http": 0, "url": url, "error": str(e)[:80]}


def _ig_probe(slug: str, handle: str) -> dict:
    """Reuse the report's IG scraper. status 'ok' → valid; 'empty' → not found/private.
    Returns the raw scrape so the caller can cache it for report reuse (no double-pull)."""
    try:
        from agents.intel.competitor_intel import CompetitorIntel
        res = CompetitorIntel(slug).instagram(handle)
    except Exception as e:
        return {"status": "unknown", "via": "apify", "error": str(e)[:120]}
    if res.get("status") == "ok":
        return {"status": "valid", "via": "apify", "scrape": res}
    return {"status": "not_found", "via": "apify", "note": res.get("note", "no public posts")}


def resolve_handles(slug: str, handles: list[dict]) -> list[dict]:
    """handles: [{platform, handle}, ...] → [{platform, handle, status, ...}, ...].
    status ∈ {valid, not_found, unknown}. IG hits Apify (cost); call sparingly."""
    out: list[dict] = []
    seen: set[tuple[str, str]] = set()
    for item in handles:
        platform = (item.get("platform") or "").strip().lower()
        handle = (item.get("handle") or "").strip().lstrip("@")
        if not handle:
            continue
        key = (platform, handle.lower())
        if key in seen:
            continue
        seen.add(key)
        if platform == "instagram":
            r = _ig_probe(slug, handle)
        elif platform in _HTTP_URL:
            r = _http_probe(platform, handle)
        else:
            r = {"status": "unknown", "note": f"no validator for '{platform}'"}
        out.append({"platform": platform, "handle": handle, **r})
    return out
