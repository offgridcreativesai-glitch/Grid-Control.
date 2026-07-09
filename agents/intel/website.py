"""
agents/intel/website.py — lightweight website intelligence (FREE, no Apify).

Pulls positioning signals from a brand's homepage over plain HTTP: title,
meta/OG description, H1/H2 headings, detected commerce platform, and (best-effort)
price signals. JS-heavy stores (Shopify etc.) still serve server-rendered
<title>/<meta>/OG/product-schema, which is enough for a positioning read without
paying for a headless-browser Apify run.

Zero-assumption: returns {"status": "unreachable"} / {"status": "none"} on any
failure — never raises, never fabricates. Used by brand_self (own site) and
competitor_intel (competitor sites) for the v7 brand-book.
"""
from __future__ import annotations
import re
import requests

_UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
       "(KHTML, like Gecko) Chrome/120 Safari/537.36")

_PLATFORM_SIGS = [
    ("Shopify", ("cdn.shopify.com", "shopify.com", "x-shopify")),
    ("WooCommerce", ("woocommerce", "wp-content/plugins/woocommerce")),
    ("Wix", ("wixstatic.com", "wix.com")),
    ("Squarespace", ("squarespace.com", "static1.squarespace")),
    ("BigCommerce", ("bigcommerce.com",)),
    ("Magento", ("mage-",)),
    ("Webflow", ("webflow.io", "assets-global.website-files")),
]


def _detect_platform(html_lower: str) -> str | None:
    for name, sigs in _PLATFORM_SIGS:
        if any(s in html_lower for s in sigs):
            return name
    return None


def _first(html: str, pattern: str) -> str | None:
    m = re.search(pattern, html, re.I | re.S)
    return m.group(1) if m else None


def _clean(t: str | None, n: int = 180) -> str:
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", "", t or "")).strip()[:n]


def scrape_website(url: str | None) -> dict:
    """Homepage positioning signals for `url`. Never raises."""
    if not url or not str(url).strip():
        return {"status": "none", "note": "no website on file"}
    url = str(url).strip()
    if not url.startswith(("http://", "https://")):
        url = "https://" + url
    try:
        r = requests.get(url, headers={"User-Agent": _UA}, timeout=12, allow_redirects=True)
    except Exception as e:
        return {"status": "unreachable", "url": url, "error": str(e)[:120]}
    if r.status_code >= 400:
        return {"status": "unreachable", "url": url, "http": r.status_code}
    html = r.text or ""
    hl = html.lower()

    title = _first(html, r"<title[^>]*>(.*?)</title>")
    desc = (_first(html, r'<meta[^>]+name=["\']description["\'][^>]+content=["\'](.*?)["\']')
            or _first(html, r'<meta[^>]+content=["\'](.*?)["\'][^>]+name=["\']description["\']'))
    og_desc = _first(html, r'<meta[^>]+property=["\']og:description["\'][^>]+content=["\'](.*?)["\']')
    og_title = _first(html, r'<meta[^>]+property=["\']og:title["\'][^>]+content=["\'](.*?)["\']')
    h1s = [_clean(x, 120) for x in re.findall(r"<h1[^>]*>(.*?)</h1>", html, re.I | re.S)]
    h2s = [_clean(x, 120) for x in re.findall(r"<h2[^>]*>(.*?)</h2>", html, re.I | re.S)]
    # Best-effort price signals (currency + number), deduped, first few.
    prices = re.findall(r"(?:₹|Rs\.?|INR|\$|USD|£|€)\s?[\s]?\d[\d,]*(?:\.\d{2})?", html)[:8]

    return {
        "status": "ok",
        "url": r.url,
        "http": r.status_code,
        "platform": _detect_platform(hl),
        "title": _clean(title),
        "og_title": _clean(og_title),
        "description": _clean(desc or og_desc, 300),
        "h1": [x for x in h1s if x][:3],
        "h2": [x for x in h2s if x][:5],
        "price_signals": list(dict.fromkeys(p.strip() for p in prices)),
    }


def resolve_competitor_url(handle: str, bio_link: str | None = None) -> str:
    """Best candidate website for a competitor. Prefer a captured IG bio link; else a
    domain-style handle IS the domain (owr.life, prdgy.in); else guess <handle>.com."""
    if bio_link and str(bio_link).strip():
        return str(bio_link).strip()
    h = (handle or "").strip().lstrip("@")
    if "." in h:
        return "https://" + h
    return "https://" + h + ".com"
