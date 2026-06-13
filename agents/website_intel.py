"""
website_intel.py — GRID CONTROL · Brand-Book B-1 completion · Website/SEO channel.

Scrapes each competitor's DISCOVERED website (from channel_discovery_v7.json) and extracts
deterministic funnel + SEO/GEO signals — what they sell, how they price, the CTA, and how
search/AI-ready the page is. Uses Scrapling (D4Vinci) for robust fetch (HTTP first, stealth
browser fallback for JS/anti-bot pages).

Per the SEO/GEO comparison (Jun 14): the Website/SEO channel data layer is deterministic
signal extraction here; the richer GEO audit (our geo-seo-claude suite, which beat the
seo-geo-tracker link 8-5) can layer on top later. Real data only; honest-empty on failure.

Output → brands/<slug>/website_intel_v7.json
"""
from __future__ import annotations

import json
import os
import re
import sys
from datetime import datetime, timezone
from urllib.parse import urlparse

import requests

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

_PRICE_RE = re.compile(r'(?:[$₹€£]\s?\d[\d,]*(?:\.\d+)?|\b\d+\s?(?:USD|INR|EUR|/mo|per month|/month)\b)', re.I)
_CTA_WORDS = ("book a call", "book now", "get started", "start free", "sign up", "subscribe",
              "join", "buy now", "get access", "apply now", "schedule", "download", "work with me")


def _fetch(url: str):
    """Scrapling HTTP fetch, stealth-browser fallback. Returns (page_obj, html) or (None, '')."""
    try:
        from scrapling.fetchers import Fetcher
        page = Fetcher.get(url, timeout=20, follow_redirects=True)
        html = getattr(page, "html_content", "") or str(page)
        if len(html) > 1500:
            return page, html
    except Exception:
        page = None
    # fallback: stealth browser for JS/anti-bot pages
    try:
        from scrapling.fetchers import StealthyFetcher
        page = StealthyFetcher.fetch(url, headless=True, network_idle=True, timeout=40000)
        html = getattr(page, "html_content", "") or str(page)
        return page, html
    except Exception:
        return None, ""


def _text(html: str) -> str:
    t = re.sub(r"<script[\s\S]*?</script>|<style[\s\S]*?</style>", " ", html, flags=re.I)
    t = re.sub(r"<[^>]+>", " ", t)
    return re.sub(r"\s+", " ", t).strip()


def _meta(html: str, name: str) -> str:
    m = re.search(rf'<meta[^>]+(?:name|property)=["\']{re.escape(name)}["\'][^>]+content=["\']([^"\']+)', html, re.I)
    return m.group(1).strip() if m else ""


def _title(html: str) -> str:
    m = re.search(r"<title[^>]*>([^<]+)</title>", html, re.I)
    return m.group(1).strip() if m else ""


def _headings(html: str, tag: str, n: int) -> list[str]:
    out = [re.sub(r"\s+", " ", _text(h)).strip()
           for h in re.findall(rf"<{tag}[^>]*>([\s\S]*?)</{tag}>", html, re.I)]
    return [h for h in out if h][:n]


def _llms_txt(url: str) -> bool:
    try:
        base = f"{urlparse(url).scheme}://{urlparse(url).netloc}"
        r = requests.get(base + "/llms.txt", timeout=8, headers={"User-Agent": "Mozilla/5.0"})
        return r.status_code == 200 and "#" in r.text[:200]
    except Exception:
        return False


def scrape_site(url: str) -> dict:
    page, html = _fetch(url)
    if not html:
        return {"status": "unreachable", "url": url}
    text = _text(html)
    prices = list(dict.fromkeys(_PRICE_RE.findall(html)))[:6]
    low = text.lower()
    ctas = [c for c in _CTA_WORDS if c in low]
    has_schema = bool(re.search(r'application/ld\+json', html, re.I))
    return {
        "status": "ok",
        "url": url,
        "title": _title(html),
        "meta_description": _meta(html, "description") or _meta(html, "og:description"),
        "h1": _headings(html, "h1", 3),
        "h2": _headings(html, "h2", 6),
        "pricing_signals": prices,
        "has_pricing": bool(prices),
        "ctas": ctas,
        "primary_cta": ctas[0] if ctas else None,
        "word_count": len(text.split()),
        "seo_geo": {
            "has_jsonld_schema": has_schema,        # AI/SEO structured-data signal
            "has_meta_description": bool(_meta(html, "description")),
            "has_llms_txt": _llms_txt(url),          # GEO (AI-search) readiness signal
            "title_len": len(_title(html)),
        },
        "positioning_excerpt": text[:280],
    }


def run(slug: str) -> dict:
    disc_path = os.path.join(_ROOT, "brands", slug, "channel_discovery_v7.json")
    disc = json.load(open(disc_path))["competitors"]
    out = {"brand_slug": slug, "scraped_at": datetime.now(timezone.utc).isoformat(),
           "tool": "Scrapling (D4Vinci) HTTP+stealth", "competitors": {}}
    for h, d in disc.items():
        site = d.get("website")
        if not site:
            out["competitors"][h] = {"status": "no_website"}
            print(f"  [website] {h}: no website discovered"); continue
        print(f"  [website] {h}: scraping {site} …")
        out["competitors"][h] = scrape_site(site)
    return out


def main():
    slug = sys.argv[1] if len(sys.argv) > 1 else os.getenv("ACTIVE_BRAND", "askgauravai")
    data = run(slug)
    path = os.path.join(_ROOT, "brands", slug, "website_intel_v7.json")
    json.dump(data, open(path, "w", encoding="utf-8"), indent=2, ensure_ascii=False)
    print(f"\n[website_intel] {slug}")
    for h, w in data["competitors"].items():
        if w.get("status") == "ok":
            print(f"  {h}: “{(w.get('title') or '')[:50]}” · pricing={w['has_pricing']} "
                  f"· cta={w.get('primary_cta')} · schema={w['seo_geo']['has_jsonld_schema']} "
                  f"· llms.txt={w['seo_geo']['has_llms_txt']}")
        else:
            print(f"  {h}: {w.get('status')}")
    print(f"  → {path}")


if __name__ == "__main__":
    main()
