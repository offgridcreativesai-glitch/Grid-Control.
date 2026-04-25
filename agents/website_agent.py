"""
Website Agent — OffGrid Marketing OS
Agent ID: 9 | Runs after Funnel Specialist is approved.
Model: claude-sonnet-4-6
Rule 9: AutoResearch Loop — Conversion-optimized / Trust-optimized / Story-led variants.
Reads:  brands/{slug}/brand_profile.json + pending_approval/Funnel Specialist/
Writes: brands/{slug}/outputs/pending_approval/Website Agent/ + Notion card
NOTE:   Does NOT deploy. All output goes to pending_approval/ for human review first.
"""

import os
import sys
import json
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import anthropic
from ceo_brain.orchestrator import CEOBrain
import cost_reporter

load_dotenv(override=True)

ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "").strip()
MODEL = "claude-sonnet-4-6"
BRAND_SLUG = os.getenv("ACTIVE_BRAND", "offgrid-creatives-ai")

# Reference competitor/inspiration sites to analyse
REFERENCE_SITES = [
    "https://www.hotjar.com",
    "https://www.similarweb.com",
    "https://semrush.com",
]


class WebsiteAgent:

    def __init__(self, brand_slug: str = BRAND_SLUG):
        self.brand_slug = brand_slug
        self.log("Initialising Website Agent...")

        self.ceo = CEOBrain()
        self.brand_profile = self.ceo.brand_profile
        self.brand_dir = Path(self.ceo.brand_dir)

        if not ANTHROPIC_API_KEY:
            raise ValueError("ANTHROPIC_API_KEY not found in .env")
        self.client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
        self._total_input_tokens = 0
        self._total_output_tokens = 0

    def log(self, msg: str) -> None:
        print(f"[WebsiteAgent] {msg}")

    # ── Data loaders ──────────────────────────────────────────────────────────

    def load_funnel_output(self) -> dict:
        """Load most recent Funnel Specialist output for CTA + copy context."""
        for status in ["pending_approval", "approved"]:
            funnel_dir = self.brand_dir / "outputs" / status / "Funnel Specialist"
            if funnel_dir.exists():
                files = sorted(funnel_dir.glob("*.json"), key=lambda f: f.stat().st_mtime, reverse=True)
                if files:
                    raw = files[0].read_text()
                    if "---" in raw:
                        raw = raw.split("---", 1)[1].strip()
                    try:
                        data = json.loads(raw)
                        self.log(f"Loaded funnel output: {files[0].name}")
                        return data
                    except Exception:
                        pass
        self.log("⚠️  No Funnel Specialist output found — proceeding with brand_profile only.")
        return {}

    # ── AutoResearch Loop — Rule 9 ────────────────────────────────────────────

    def run_autoresearch_loop(self, funnel_data: dict) -> dict:
        """
        3 website variants:
        A — Conversion-optimized layout (CRO-first, minimal friction)
        B — Trust-optimized layout (proof-heavy, authority signals)
        C — Story-led layout (founder narrative, problem-solution arc)
        Metric: which layout maximises Google Form fills from organic traffic
        """

        brand = self.brand_profile
        price = brand.get("price", {})

        # Extract CTA from funnel if available
        landing_cta = funnel_data.get("landing_page_cta", {})
        funnel_headline = landing_cta.get("headline", "")
        funnel_cta_btn  = landing_cta.get("cta_button", "")
        objections      = funnel_data.get("objection_handlers", [])

        prompt = f"""You are the Website Agent for OffGrid Creatives AI Marketing OS.

BRAND: {brand.get('brand_name', 'OffGrid Creatives AI')}
PRODUCT: {brand.get('product', 'AI Ad Intelligence Report')}
PRODUCT DESCRIPTION: {brand.get('product_description', '')}
TARGET AUDIENCE: {', '.join(brand.get('target_audience', brand.get('audience', [])))}
TONE: {brand.get('tone', 'Bold, credible, founder-to-founder, disruptive but educational')}
PHASE: {brand.get('phase', 'beta')}
GOAL: {brand.get('goal', 'Sell beta reports')}

PRICING:
- Beta: ₹{price.get('beta_inr', 999)}
- India: ₹{price.get('india_inr', 3500)}
- International: ₹{price.get('international_inr', 5000)}

EXISTING PIPELINE: Google Forms → Make.com → Apify → Claude API → Railway Flask → Gmail PDF
RAILWAY URL: {brand.get('existing_pipeline', {}).get('railway_url', 'https://web-production-175d5.up.railway.app')}
GA4 PROPERTY: {os.getenv('GA4_PROPERTY_ID', 'Not yet connected')}

FUNNEL CTA (from Funnel Specialist):
Headline: {funnel_headline or 'Not yet generated'}
CTA button: {funnel_cta_btn or 'Not yet generated'}

TOP OBJECTIONS TO ADDRESS ON SITE:
{json.dumps(objections[:3], indent=2) if objections else 'Not yet available from Funnel Specialist'}

VISUAL DIRECTION:
- Mood: Dark, premium, data-driven
- Primary: Deep black (#0A0A0A) or navy (#0D1117)
- Accent: Electric green (#00C853) or amber (#F5A623)
- Typography: Inter Bold or Space Grotesk
- Themes: Report mockups, data visualizations, founder on camera

REFERENCE COMPETITOR SITES TO ANALYSE STYLE FROM:
{', '.join(REFERENCE_SITES)}
(Note: Actual scraping not yet connected — analyse based on known industry patterns)

REQUIRED WEBSITE SECTIONS (per spec):
1. Hero — headline, subheadline, CTA button
2. Problem — what happens without ad intelligence
3. Solution — what the report covers (17 sections)
4. Sample — blurred report preview description
5. How It Works — 3 steps (Form → AI scrapes → PDF to inbox)
6. Proof — testimonials placeholder + social proof
7. Pricing — ₹999 beta / ₹3500 India / ₹5000 International
8. FAQ — 5 common objections answered

Generate 3 complete website blueprint variants.

VARIANT A — Conversion-optimized layout:
CRO-first. Minimal friction. Every element exists to drive form fills.
Above-fold has one headline, one subheadline, one CTA only.
Price visible before the fold on mobile.
Proof before pricing.

VARIANT B — Trust-optimized layout:
Proof-heavy. Authority signals first. Founder story early.
Demo/sample report as primary CTA ("See what you'll get first").
Price revealed after value is established.

VARIANT C — Story-led layout:
Opens with the problem the founder personally faced.
Narrative arc: problem → failed attempts → discovery → solution → proof → offer.
Emotional journey before rational argument.

For EACH variant provide:
- layout_philosophy: one sentence
- sections: array of {{section_name, purpose, headline, body_copy, cta, visual_note}}
- hero: {{headline, subheadline, cta_primary, cta_secondary, visual}}
- above_fold_test: what a visitor sees in first 3 seconds
- tech_stack: recommended (given Railway deployment + existing pipeline)
- deployment_plan: steps to get live on Railway
- ga4_tracking_events: which events to track
- seo_title: the meta title
- seo_description: meta description

Return ONLY valid JSON:
{{
  "loop_goal": "design website that maximises Google Form fills from zero-paid organic traffic",
  "loop_metric": "better = higher form fill rate per 100 visitors, faster decision",
  "competitor_websites_analysed": {json.dumps(REFERENCE_SITES)},
  "recommended_tech": {{}},
  "variants": {{
    "A": {{
      "label": "Conversion-Optimized Layout",
      "layout_philosophy": "",
      "hero": {{}},
      "above_fold_test": "",
      "sections": [],
      "tech_stack": {{}},
      "deployment_plan": [],
      "ga4_tracking_events": [],
      "seo_title": "",
      "seo_description": ""
    }},
    "B": {{
      "label": "Trust-Optimized Layout",
      "layout_philosophy": "",
      "hero": {{}},
      "above_fold_test": "",
      "sections": [],
      "tech_stack": {{}},
      "deployment_plan": [],
      "ga4_tracking_events": [],
      "seo_title": "",
      "seo_description": ""
    }},
    "C": {{
      "label": "Story-Led Layout",
      "layout_philosophy": "",
      "hero": {{}},
      "above_fold_test": "",
      "sections": [],
      "tech_stack": {{}},
      "deployment_plan": [],
      "ga4_tracking_events": [],
      "seo_title": "",
      "seo_description": ""
    }}
  }},
  "winning_variant": "A",
  "winner_reason": "one line reason",
  "approval_status": "pending"
}}"""

        self.log("Running AutoResearch Loop — 3 website variants via Claude Sonnet...")
        response = self.client.messages.create(
            model=MODEL,
            max_tokens=6000,
            messages=[{"role": "user", "content": prompt}]
        )
        self._total_input_tokens += response.usage.input_tokens
        self._total_output_tokens += response.usage.output_tokens
        raw = response.content[0].text.strip()
        if "```" in raw:
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            idx = raw.find("{")
            if idx >= 0:
                try:
                    return json.loads(raw[idx:])
                except Exception:
                    pass
            raise ValueError(f"Could not parse website loop response: {raw[:200]}")

    # ── Main run ──────────────────────────────────────────────────────────────

    def run(self) -> None:
        self.log("=" * 60)
        self.log("WEBSITE AGENT — Starting run")
        self.log("=" * 60)

        funnel_data = self.load_funnel_output()
        loop_result = self.run_autoresearch_loop(funnel_data)

        winning_variant = loop_result.get("winning_variant", "A")
        winner_reason   = loop_result.get("winner_reason", "")
        variants        = loop_result.get("variants", {})
        winning_data    = variants.get(winning_variant, {})

        self.log(f"Loop complete. Winner: Variant {winning_variant} — {winner_reason}")

        loop_header = {
            "goal":            loop_result.get("loop_goal", ""),
            "metric":          loop_result.get("loop_metric", ""),
            "variants_tested": 3,
            "winner":          f"Variant {winning_variant} — {winner_reason}",
        }

        output = {
            "agent":                       "Website Agent",
            "brand":                       self.brand_slug,
            "generated_at":                datetime.now().isoformat(),
            "loop_header":                 loop_header,
            "winning_variant":             winning_variant,
            "competitor_websites_analysed": loop_result.get("competitor_websites_analysed", REFERENCE_SITES),
            "recommended_structure":       winning_data,
            "recommended_tech":            loop_result.get("recommended_tech", {}),
            "page_sections":               winning_data.get("sections", []),
            "hero":                        winning_data.get("hero", {}),
            "deployment_plan":             winning_data.get("deployment_plan", []),
            "ga4_tracking_events":         winning_data.get("ga4_tracking_events", []),
            "all_variants":                variants,
            "approval_status":             "pending",
            "deploy_note":                 "APPROVAL REQUIRED before deployment. Review blueprint, approve in Notion, then run deploy step.",
        }

        output_dir = self.brand_dir / "outputs" / "pending_approval" / "Website Agent"
        output_dir.mkdir(parents=True, exist_ok=True)
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{ts}_blueprint.json"
        output_path = output_dir / filename

        header_text = (
            f"LOOP: Website Agent — Website Blueprint\n"
            f"GOAL: {loop_header['goal']}\n"
            f"METRIC: better = {loop_header['metric']}\n"
            f"VARIANTS TESTED: 3\n"
            f"WINNER: {loop_header['winner']}\n"
            f"---\n"
        )
        output_path.write_text(header_text + json.dumps(output, indent=2))
        self.log(f"✅ Blueprint saved: {filename}")

        self.log("Pushing to Notion approval pipeline...")
        self.ceo.save_agent_output(
            agent_name="Website Agent",
            output_type="Website Blueprint",
            loop_header=loop_header,
            content=json.dumps(output, indent=2),
            filename=filename,
        )

        self.ceo.mark_agent_complete("website-agent")

        self.log("=" * 60)
        self.log("WEBSITE AGENT — Run complete")
        self.log(f"Winning variant : Variant {winning_variant}")
        self.log(f"Notion card     : ✅ Pushed")
        self.log(f"Output file     : {filename}")
        self.log(f"Deploy status   : ⏸  Awaiting approval in Notion before deploy")
        self.log("=" * 60)
        cost_reporter.record(MODEL, self._total_input_tokens, self._total_output_tokens)


if __name__ == "__main__":
    agent = WebsiteAgent()
    agent.run()
