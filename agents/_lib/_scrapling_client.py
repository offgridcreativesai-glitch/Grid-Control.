"""
Scrapling client — Phase 2a (Jun 18 2026).

Adaptive web-scraping wrapper for COMPETITOR WEBSITE positioning signal.
Complements Apify (IG/YT/social) — Apify stays canonical for social platforms;
Scrapling fills the gap where Apify is overkill (public web pages).

Public API:
    sc = get_scrapling()
    page = sc.scrape_homepage("https://manthan.com")
    # → { url, title, meta_description, h1_h2_h3, nav_links, body_snippet, ok }
"""
import os
import re
from typing import Optional
from urllib.parse import urlparse, urljoin


class ScraplingClient:
    """Thin wrapper. Silent no-op when scrapling missing."""

    def __init__(self):
        self._ok = False
        try:
            from scrapling.fetchers import Fetcher
            self._Fetcher = Fetcher
            self._ok = True
        except Exception as e:
            print(f"[scrapling] init skipped: {e}")

    @property
    def enabled(self) -> bool:
        return self._ok

    def fetch_html(self, url: str, timeout: int = 20) -> dict:
        """Raw stealth HTML fetch — for callers that run their own extraction (e.g.
        website.py's platform/price/OG regex). Uses scrapling's anti-bot Fetcher so
        sites that block plain `requests` (e.g. owr.life) still resolve. Never raises.
        Returns {ok, status, url, html}."""
        if not self._ok:
            return {"ok": False, "url": url, "error": "scrapling not installed"}
        try:
            r = self._Fetcher.get(url, stealthy_headers=True, follow_redirects=True, timeout=timeout)
        except Exception as e:
            return {"ok": False, "url": url, "error": f"fetch failed: {e}"}
        return {
            "ok": r.status < 400,
            "status": int(r.status),
            "url": str(getattr(r, "url", url) or url),
            "html": str(r.html_content or ""),
        }

    def scrape_homepage(self, url: str, timeout: int = 20) -> dict:
        """Scrape a competitor homepage. Returns structured positioning signal.
        Never raises — returns {ok: False, error: ...} on failure."""
        if not self._ok:
            return {"url": url, "ok": False, "error": "scrapling not installed"}

        try:
            r = self._Fetcher.get(
                url,
                stealthy_headers=True,
                follow_redirects=True,
                timeout=timeout,
            )
        except Exception as e:
            return {"url": url, "ok": False, "error": f"fetch failed: {e}"}

        if r.status >= 400:
            return {"url": url, "ok": False, "error": f"http {r.status}", "status": r.status}

        try:
            return self._extract(url, r)
        except Exception as e:
            return {"url": url, "ok": False, "error": f"parse failed: {e}"}

    # ── internals ───────────────────────────────────────────────

    def _extract(self, url: str, r) -> dict:
        title = self._first_text(r, "title")
        meta_desc = ""
        meta = r.css('meta[name="description"]')
        if meta:
            meta_desc = (meta[0].attrib.get("content") or "").strip()
        if not meta_desc:
            og = r.css('meta[property="og:description"]')
            if og:
                meta_desc = (og[0].attrib.get("content") or "").strip()

        h1 = [self._clean(h.text) for h in r.css("h1")[:5] if self._clean(h.text)]
        h2 = [self._clean(h.text) for h in r.css("h2")[:10] if self._clean(h.text)]
        h3 = [self._clean(h.text) for h in r.css("h3")[:10] if self._clean(h.text)]

        # Nav-ish links — likely the brand's product taxonomy / value props
        nav_links = []
        seen = set()
        for a in r.css("nav a, header a")[:25]:
            txt = self._clean(a.text)
            href = a.attrib.get("href") or ""
            if not txt or len(txt) > 60 or txt.lower() in seen:
                continue
            seen.add(txt.lower())
            nav_links.append({"text": txt, "href": self._abs(url, href)})

        body_snippet = self._body_text(r)[:1200]

        return {
            "url": url,
            "ok": True,
            "title": (title or "").strip(),
            "meta_description": meta_desc,
            "h1": h1,
            "h2": h2,
            "h3": h3,
            "nav_links": nav_links,
            "body_snippet": body_snippet,
            "scraped_at": _now_iso(),
        }

    @staticmethod
    def _first_text(r, sel: str) -> str:
        nodes = r.css(sel)
        if not nodes:
            return ""
        return (nodes[0].text or "").strip()

    @staticmethod
    def _clean(text: Optional[str]) -> str:
        return re.sub(r"\s+", " ", (text or "")).strip()

    @staticmethod
    def _abs(base: str, href: str) -> str:
        try:
            return urljoin(base, href) if href else ""
        except Exception:
            return href

    @staticmethod
    def _body_text(r) -> str:
        try:
            paras = [ScraplingClient._clean(p.text) for p in r.css("p")[:25]]
            return " ".join(p for p in paras if p and len(p) > 20)
        except Exception:
            return ""


def _now_iso() -> str:
    from datetime import datetime, timezone
    return datetime.now(timezone.utc).isoformat()


_singleton: Optional[ScraplingClient] = None


def get_scrapling() -> ScraplingClient:
    global _singleton
    if _singleton is None:
        _singleton = ScraplingClient()
    return _singleton
