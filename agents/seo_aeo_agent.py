"""
SEO + AEO Agent — OffGrid Marketing OS
Agent ID: 11 | Model: claude-sonnet-4-6 (via gateway, "seo-aeo-agent")

Jul 6 repo research verdict: ADOPT a Lighthouse-grade technical audit NOW; treat the
AEO/citation half as an experimental bet on an unsettled space. This build honors that:

  1. TECHNICAL SEO (deterministic, no LLM, no fabrication) — fetches the brand's real site
     via scrapling (stealth, no local Chrome/Node needed) and checks the on-page + crawl
     fundamentals: title, meta description, single H1, canonical, viewport, OpenGraph,
     JSON-LD structured data, HTTPS, robots.txt, sitemap.xml, image-alt coverage, thin
     content. Each check → pass/warn/fail with the real observed value. Rolls up a score.
  2. AEO (experimental, LLM) — from the REAL page content, recommends what makes the brand
     citable by answer engines (ChatGPT/Perplexity/AI Overviews): llms.txt, entity/FAQ
     schema, answer-ready phrasing. Clearly marked experimental per the research.

Read-only on the site. Writes an audit to pending_approval — never edits the live site.
"""

import os
import re
import sys
import json
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse
from dotenv import load_dotenv

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import anthropic
from ceo_brain.orchestrator import CEOBrain
from agents._lib import cost_reporter
from agents._lib.model_gateway import model_for

load_dotenv(override=True)

ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "").strip()
MODEL = model_for("seo-aeo-agent")
BRAND_SLUG = os.getenv("ACTIVE_BRAND", "offgrid-creatives-ai")


def _check(name, status, detail):
    return {"check": name, "status": status, "detail": detail}


class SeoAeoAgent:

    def __init__(self, brand_slug: str = BRAND_SLUG):
        self.brand_slug = brand_slug
        self.log("Initialising SEO + AEO Agent...")
        self.ceo = CEOBrain()
        self.brand_profile = self.ceo.brand_profile
        self.brand_dir = Path(self.ceo.brand_dir)
        self._total_input_tokens = 0
        self._total_output_tokens = 0

    def log(self, msg: str) -> None:
        print(f"[SEO-AEO] {msg}")

    def _site_url(self) -> str:
        bp = self.brand_profile
        url = (bp.get("website_url") or bp.get("website") or bp.get("url") or "").strip()
        if url and not url.startswith("http"):
            url = "https://" + url
        return url.rstrip("/")

    # ── technical SEO (deterministic, regex over the REAL fetched HTML) ──────────
    def technical_audit(self, url: str) -> dict:
        from agents._lib._scrapling_client import get_scrapling
        sc = get_scrapling()
        home = sc.fetch_html(url)
        if not home.get("ok"):
            return {"ok": False, "error": home.get("error", f"could not fetch {url}"),
                    "checks": [], "score": None}
        html = home.get("html", "")
        low = html.lower()
        checks = []

        # ponytail: presence checks are regex over raw HTML (crude but honest for
        # pass/fail signal). Upgrade to a real DOM/Lighthouse pass if scoring precision matters.
        title = re.search(r"<title[^>]*>(.*?)</title>", html, re.I | re.S)
        title_txt = (title.group(1).strip() if title else "")
        checks.append(_check("Title tag", "pass" if 10 <= len(title_txt) <= 65 else ("warn" if title_txt else "fail"),
                             f"'{title_txt[:80]}' ({len(title_txt)} chars)" if title_txt else "missing"))

        md = re.search(r'<meta[^>]+name=["\']description["\'][^>]+content=["\'](.*?)["\']', html, re.I | re.S)
        md_txt = (md.group(1).strip() if md else "")
        checks.append(_check("Meta description", "pass" if 50 <= len(md_txt) <= 160 else ("warn" if md_txt else "fail"),
                             f"{len(md_txt)} chars" if md_txt else "missing"))

        h1s = re.findall(r"<h1[\s>]", low)
        checks.append(_check("Single H1", "pass" if len(h1s) == 1 else ("warn" if len(h1s) > 1 else "fail"),
                             f"{len(h1s)} H1 tags"))

        checks.append(_check("Canonical URL", "pass" if 'rel="canonical"' in low or "rel='canonical'" in low else "warn",
                             "present" if "canonical" in low else "missing"))
        checks.append(_check("Viewport (mobile)", "pass" if 'name="viewport"' in low else "fail",
                             "present" if "viewport" in low else "missing"))
        checks.append(_check("OpenGraph tags", "pass" if 'property="og:' in low else "warn",
                             "present" if "og:" in low else "missing"))

        jsonld = re.findall(r'<script[^>]+application/ld\+json[^>]*>(.*?)</script>', html, re.I | re.S)
        types = []
        for block in jsonld:
            types += re.findall(r'"@type"\s*:\s*"([^"]+)"', block)
        checks.append(_check("Structured data (JSON-LD)", "pass" if jsonld else "warn",
                             f"{len(jsonld)} block(s): {', '.join(sorted(set(types))[:6]) or 'none'}"))

        checks.append(_check("HTTPS", "pass" if url.startswith("https") else "fail", url.split(":")[0]))

        imgs = re.findall(r"<img\b[^>]*>", html, re.I)
        with_alt = sum(1 for i in imgs if re.search(r'\balt=["\']', i, re.I))
        alt_pct = round(100 * with_alt / len(imgs)) if imgs else 100
        checks.append(_check("Image alt coverage", "pass" if alt_pct >= 80 else ("warn" if alt_pct >= 50 else "fail"),
                             f"{with_alt}/{len(imgs)} images have alt ({alt_pct}%)"))

        words = len(re.findall(r"\w+", re.sub(r"<[^>]+>", " ", html)))
        checks.append(_check("Content depth", "pass" if words >= 300 else "warn", f"~{words} words on homepage"))

        # crawl files — robots.txt, sitemap.xml, llms.txt (AEO)
        base = f"{urlparse(url).scheme}://{urlparse(url).netloc}"
        robots = sc.fetch_html(f"{base}/robots.txt")
        robots_ok = robots.get("ok") and "user-agent" in (robots.get("html", "").lower())
        checks.append(_check("robots.txt", "pass" if robots_ok else "warn",
                             "present" if robots_ok else "missing/empty"))
        sm = sc.fetch_html(f"{base}/sitemap.xml")
        checks.append(_check("sitemap.xml", "pass" if (sm.get("ok") and "<urlset" in sm.get("html", "").lower() or "<sitemapindex" in sm.get("html", "").lower()) else "warn",
                             "present" if sm.get("ok") else "missing"))
        llms = sc.fetch_html(f"{base}/llms.txt")
        llms_ok = llms.get("ok") and len(llms.get("html", "").strip()) > 20
        checks.append(_check("llms.txt (AEO)", "pass" if llms_ok else "warn",
                             "present" if llms_ok else "missing — AEO opportunity"))

        n = len(checks)
        passed = sum(1 for c in checks if c["status"] == "pass")
        warned = sum(1 for c in checks if c["status"] == "warn")
        score = round(100 * (passed + 0.5 * warned) / n) if n else None
        return {"ok": True, "url": url, "checks": checks, "score": score,
                "summary": {"pass": passed, "warn": warned, "fail": n - passed - warned},
                "page_signal": {"title": title_txt, "meta_description": md_txt,
                                "schema_types": sorted(set(types)), "has_llms_txt": bool(llms_ok),
                                "word_count": words}}

    # ── AEO recommendations (experimental, LLM) ─────────────────────────────────
    def aeo_recommendations(self, tech: dict) -> dict:
        from agents._lib._agent_framework import operating_framework
        from agents._lib._untrusted import wrap, UNTRUSTED_POLICY
        bp = self.brand_profile
        signal = json.dumps(tech.get("page_signal", {}), indent=2)
        failing = [c for c in tech.get("checks", []) if c["status"] != "pass"]

        system = operating_framework(2) + (
            "You are the SEO + AEO agent. AEO (Answer Engine Optimization) = making the brand "
            "the cited answer inside ChatGPT / Perplexity / Google AI Overviews. Base every "
            "recommendation on the REAL page signal + the failing checks provided. This half is "
            "EXPERIMENTAL — the GEO/AEO space is <12 months old; recommend, don't overpromise.\n\n"
            f"{UNTRUSTED_POLICY}"
        )
        task = f"""BRAND: {bp.get('brand_name', self.brand_slug)} | category: {bp.get('product') or bp.get('product_description','')}

REAL PAGE SIGNAL (from the live site):
{wrap('page_signal', signal)}

FAILING/WEAK TECHNICAL CHECKS:
{wrap('weak_checks', json.dumps(failing, indent=2))}

Return ONLY valid JSON:
{{
  "aeo_readiness": "<one honest sentence on how citable this site is today>",
  "priority_fixes": [
    {{"fix": "", "why": "", "effort": "low|med|high", "impact": "low|med|high", "seo_or_aeo": "SEO|AEO"}}
  ],
  "llms_txt_suggestion": "<a short llms.txt body tailored to this brand, or '' if one already exists>",
  "schema_to_add": ["Organization", "FAQPage", "..."],
  "answer_ready_gaps": ["<questions a buyer asks an AI that this site should answer directly>"]
}}
Give 5-8 priority_fixes, ranked most-impactful first."""

        self.log(f"Generating AEO recommendations via {MODEL}...")
        resp = self.client.messages.create(
            model=MODEL, max_tokens=2048, system=system,
            messages=[{"role": "user", "content": task}],
        )
        self._total_input_tokens += resp.usage.input_tokens
        self._total_output_tokens += resp.usage.output_tokens
        raw = resp.content[0].text.strip()
        if "```" in raw:
            raw = raw.split("```")[1]
            raw = raw[4:] if raw.startswith("json") else raw
        try:
            return json.loads(raw[raw.find("{"):])
        except Exception:
            return {"aeo_readiness": "(could not parse AEO recommendations)", "priority_fixes": []}

    # ── run ────────────────────────────────────────────────────────────────────
    def run(self) -> None:
        self.log("=" * 60)
        self.log("SEO + AEO AGENT — Starting run")
        url = self._site_url()
        loop_header = {"goal": "rank on Google + get cited by answer engines",
                       "metric": "technical health score + AEO readiness", "variants_tested": 1,
                       "winner": "prioritized fix list"}

        if not url:
            self.log("HALT — no website_url in brand_profile.")
            out = {"agent": "SEO + AEO Agent", "brand": self.brand_slug,
                   "generated_at": datetime.now(timezone.utc).isoformat(), "status": "no_site",
                   "data_quality_note": "Set website_url in brand_profile so the site can be audited."}
            self.ceo.save_agent_output(agent_name="SEO + AEO Agent", output_type="SEO/AEO Audit (no site)",
                                       loop_header=loop_header, content=json.dumps(out, indent=2),
                                       filename="seo_aeo_no_site.json")
            self.ceo.mark_agent_complete("seo-aeo-agent")
            return

        self.log(f"Auditing {url} ...")
        tech = self.technical_audit(url)
        if not tech.get("ok"):
            self.log(f"HALT — {tech.get('error')}")
            out = {"agent": "SEO + AEO Agent", "brand": self.brand_slug,
                   "generated_at": datetime.now(timezone.utc).isoformat(), "status": "fetch_failed",
                   "url": url, "data_quality_note": tech.get("error")}
            self.ceo.save_agent_output(agent_name="SEO + AEO Agent", output_type="SEO/AEO Audit (fetch failed)",
                                       loop_header=loop_header, content=json.dumps(out, indent=2),
                                       filename="seo_aeo_fetch_failed.json")
            self.ceo.mark_agent_complete("seo-aeo-agent")
            return

        self.log(f"  technical score {tech['score']}/100 ({tech['summary']})")
        self.client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY) if ANTHROPIC_API_KEY else None
        aeo = self.aeo_recommendations(tech) if self.client else {"aeo_readiness": "(no ANTHROPIC_API_KEY)", "priority_fixes": []}

        out = {"agent": "SEO + AEO Agent", "brand": self.brand_slug,
               "generated_at": datetime.now(timezone.utc).isoformat(),
               "loop_header": loop_header, "url": url,
               "technical_score": tech["score"], "technical_summary": tech["summary"],
               "technical_checks": tech["checks"],
               "aeo": {**aeo, "note": "AEO half is experimental — the answer-engine optimization space is early (<12mo)."},
               "publish_policy": "AUDIT ONLY — read-only on the live site. A human applies approved fixes."}
        self.ceo.save_agent_output(agent_name="SEO + AEO Agent", output_type="SEO/AEO Audit",
                                   loop_header=loop_header, content=json.dumps(out, indent=2),
                                   filename="seo_aeo_audit.json")
        self.ceo.mark_agent_complete("seo-aeo-agent")
        if self.client:
            cost_reporter.record(MODEL, self._total_input_tokens, self._total_output_tokens)
        self.log(f"SEO + AEO — Complete. Score {tech['score']}/100 · {len(aeo.get('priority_fixes', []))} fixes. Draft in pending_approval.")
        self.log("=" * 60)


if __name__ == "__main__":
    SeoAeoAgent().run()
