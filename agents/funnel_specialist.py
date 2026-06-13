"""
Funnel Specialist — OffGrid Marketing OS
Agent ID: 7 | Runs after Strategy Agent is approved.
Model: claude-sonnet-4-6
Rule 9: AutoResearch Loop — Awareness-first / Retargeting-first / Hybrid variants.
Reads:  brands/{slug}/strategy_90day.json + brand_profile.json
Writes: brands/{slug}/outputs/pending_approval/Funnel Specialist/ + Notion card
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
from agents._lib import cost_reporter


load_dotenv(override=True)

ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "").strip()
# Phase D — model sourced from the single-source-of-truth gateway
try:
    from agents._lib.model_gateway import model_for
except ImportError:
    from agents._lib.model_gateway import model_for
MODEL = model_for("funnel-specialist")
BRAND_SLUG = os.getenv("ACTIVE_BRAND", "offgrid-creatives-ai")


class FunnelSpecialist:

    def __init__(self, brand_slug: str = BRAND_SLUG):
        self.brand_slug = brand_slug
        self.log("Initialising Funnel Specialist...")

        self.ceo = CEOBrain()
        self.brand_profile = self.ceo.brand_profile
        self.brand_dir = Path(self.ceo.brand_dir)

        if not ANTHROPIC_API_KEY:
            raise ValueError("ANTHROPIC_API_KEY not found in .env")
        self.client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
        self._total_input_tokens = 0
        self._total_output_tokens = 0

    def log(self, msg: str) -> None:
        print(f"[FunnelSpecialist] {msg}")

    # ── Data loaders ──────────────────────────────────────────────────────────

    def load_strategy(self) -> dict:
        path = self.brand_dir / "strategy_90day.json"
        if not path.exists():
            raise FileNotFoundError(
                "strategy_90day.json not found. "
                "Run strategy_agent.py first."
            )
        with open(path) as f:
            return json.load(f)

    def load_approved_strategy(self) -> dict:
        """Try approved folder first, fall back to brand dir."""
        for check in [
            self.brand_dir / "outputs" / "approved" / "Strategy Agent",
            self.brand_dir / "outputs" / "pending_approval" / "Strategy Agent",
        ]:
            if check.exists():
                files = sorted(check.glob("*.json"), key=lambda f: f.stat().st_mtime, reverse=True)
                if files:
                    raw = files[0].read_text()
                    if "---" in raw:
                        raw = raw.split("---", 1)[1].strip()
                    try:
                        return json.loads(raw)
                    except Exception:
                        pass
        return {}

    # ── AutoResearch Loop — Rule 9 ────────────────────────────────────────────

    def run_autoresearch_loop(self, strategy: dict, approved_strategy: dict) -> dict:
        """
        3 funnel variants:
        A — Awareness-first (organic content → profile → DM → Google Form → payment)
        B — Retargeting-first (assume warm audience, push directly to offer)
        C — Hybrid with split entry points (cold + warm paths merged)
        Metric: which funnel architecture maximises conversion in 0-budget beta phase
        """

        brand = self.brand_profile
        price = brand.get("price", {})

        prompt = f"""You are the Funnel Specialist for OffGrid Creatives AI Marketing OS.

BRAND: {brand.get('brand_name', 'OffGrid Creatives AI')}
PRODUCT: {brand.get('product', 'AI Ad Intelligence Report')}
PRODUCT DESCRIPTION: {brand.get('product_description', '')}
TARGET AUDIENCE: {', '.join(brand.get('target_audience', brand.get('audience', [])))}
PLATFORMS: {', '.join(brand.get('platforms', ['Instagram', 'LinkedIn']))}
PHASE: {brand.get('phase', 'beta')} | GOAL: {brand.get('goal', 'Sell beta reports')}
BUDGET: {brand.get('budget_phase', 'low_budget_month_1')} — NO paid ads in beta

PRICING:
- Beta price: ₹{price.get('beta_inr', 999)} INR
- India full price: ₹{price.get('india_inr', 3500)} INR
- International: ₹{price.get('international_inr', 5000)} INR

EXISTING PIPELINE: {json.dumps(brand.get('existing_pipeline', {}), indent=2)}

90-DAY STRATEGY CONTEXT:
Strategic angle: {strategy.get('strategic_angle', 'Not available')}
North star metric: {strategy.get('north_star_metric', 'Not available')}
Phase 1 goal: {strategy.get('phase_1', {}).get('goal', 'Not available') if isinstance(strategy.get('phase_1'), dict) else 'Not available'}

TONE: {brand.get('tone', 'Bold, credible, founder-to-founder')}
ACCOUNTS: Instagram: {brand.get('accounts', {}).get('instagram_handle', '@offgrid.creatives')} | LinkedIn: {brand.get('accounts', {}).get('linkedin_url', '')}

Design 3 complete funnel architecture variants for this exact brand and offer.

VARIANT A — Awareness-first funnel (zero paid ads, cold audience):
Map every step from first content view to payment for someone who has never heard of OffGrid.
Include: content hook type → profile visit → bio action → website/form → DM exchange → payment → delivery → follow-up.

VARIANT B — Retargeting/warm audience funnel:
Map the journey for someone who has already seen 2-3 posts or visited the profile.
Shorter path, more direct offer. Different DM scripts. Different CTA copy.

VARIANT C — Hybrid funnel with split entry points:
One architecture that serves both cold and warm audiences with clear branch points.
Include the decision logic: "if person engages with post → path X; if person DMs first → path Y".

For EACH variant, provide:
- funnel_map: array of stages with {{stage, touchpoint, action, copy, goal}}
- dm_scripts: {{instagram: "", linkedin: ""}} — real word-for-word DM scripts
- landing_page_cta: the exact headline + CTA button text for the offer page
- objection_handlers: top 3 objections with exact response scripts
- post_purchase_sequence: [day_0, day_3, day_7] follow-up messages
- conversion_trigger: the single moment that moves them from consideration to payment

Return ONLY valid JSON:
{{
  "loop_goal": "design the funnel with highest conversion probability in zero-budget beta phase",
  "loop_metric": "better = more beta report sales in first 30 days with zero ad spend",
  "variants": {{
    "A": {{
      "label": "Awareness-First — Cold Audience Funnel",
      "funnel_map": [],
      "dm_scripts": {{"instagram": "", "linkedin": ""}},
      "landing_page_cta": {{"headline": "", "subheadline": "", "cta_button": ""}},
      "objection_handlers": [],
      "post_purchase_sequence": [],
      "conversion_trigger": ""
    }},
    "B": {{
      "label": "Retargeting-First — Warm Audience Funnel",
      "funnel_map": [],
      "dm_scripts": {{"instagram": "", "linkedin": ""}},
      "landing_page_cta": {{"headline": "", "subheadline": "", "cta_button": ""}},
      "objection_handlers": [],
      "post_purchase_sequence": [],
      "conversion_trigger": ""
    }},
    "C": {{
      "label": "Hybrid — Split Entry Points",
      "funnel_map": [],
      "cold_path": {{}},
      "warm_path": {{}},
      "branch_logic": "",
      "dm_scripts": {{"instagram": "", "linkedin": ""}},
      "landing_page_cta": {{"headline": "", "subheadline": "", "cta_button": ""}},
      "objection_handlers": [],
      "post_purchase_sequence": [],
      "conversion_trigger": ""
    }}
  }},
  "winning_variant": "C",
  "winner_reason": "one line reason",
  "approval_status": "pending"
}}"""

        self.log("Running AutoResearch Loop — 3 funnel variants via Claude Sonnet...")
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
            raise ValueError(f"Could not parse funnel loop response: {raw[:200]}")

    # ── Main run ──────────────────────────────────────────────────────────────

    def run(self) -> None:
        self.log("=" * 60)
        self.log("FUNNEL SPECIALIST — Starting run")
        self.log("=" * 60)

        strategy          = self.load_strategy()
        approved_strategy = self.load_approved_strategy()

        self.log(f"Strategy loaded. Strategic angle: {strategy.get('strategic_angle', 'N/A')[:80]}")

        loop_result      = self.run_autoresearch_loop(strategy, approved_strategy)
        winning_variant  = loop_result.get("winning_variant", "C")
        winner_reason    = loop_result.get("winner_reason", "")
        variants         = loop_result.get("variants", {})
        winning_data     = variants.get(winning_variant, {})

        self.log(f"Loop complete. Winner: Variant {winning_variant} — {winner_reason}")

        loop_header = {
            "goal":            loop_result.get("loop_goal", ""),
            "metric":          loop_result.get("loop_metric", ""),
            "variants_tested": 3,
            "winner":          f"Variant {winning_variant} — {winner_reason}",
        }

        output = {
            "agent":            "Funnel Specialist",
            "brand":            self.brand_slug,
            "generated_at":     datetime.now().isoformat(),
            "loop_header":      loop_header,
            "winning_variant":  winning_variant,
            "winning_funnel":   winning_data,
            "all_variants":     variants,
            "funnel_map":       winning_data.get("funnel_map", []),
            "dm_scripts":       winning_data.get("dm_scripts", {}),
            "landing_page_cta": winning_data.get("landing_page_cta", {}),
            "objection_handlers": winning_data.get("objection_handlers", []),
            "post_purchase_sequence": winning_data.get("post_purchase_sequence", []),
            "conversion_trigger": winning_data.get("conversion_trigger", ""),
            "approval_status":  "pending",
        }

        output_dir = self.brand_dir / "outputs" / "pending_approval" / "Funnel Specialist"
        output_dir.mkdir(parents=True, exist_ok=True)
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{ts}_funnel.json"
        output_path = output_dir / filename

        header_text = (
            f"LOOP: Funnel Specialist — Conversion Funnel Architecture\n"
            f"GOAL: {loop_header['goal']}\n"
            f"METRIC: better = {loop_header['metric']}\n"
            f"VARIANTS TESTED: 3\n"
            f"WINNER: {loop_header['winner']}\n"
            f"---\n"
        )
        output_path.write_text(header_text + json.dumps(output, indent=2))
        self.log(f"✅ Funnel saved: {filename}")

        self.log("Pushing to Notion approval pipeline...")
        self.ceo.save_agent_output(
            agent_name="Funnel Specialist",
            output_type="Conversion Funnel Architecture",
            loop_header=loop_header,
            content=json.dumps(output, indent=2),
            filename=filename,
        )

        self.ceo.mark_agent_complete("funnel-specialist")

        self.log("=" * 60)
        self.log("FUNNEL SPECIALIST — Run complete")
        self.log(f"Winning variant : Variant {winning_variant}")
        self.log(f"Notion card     : ✅ Pushed")
        self.log(f"Output file     : {filename}")
        self.log("=" * 60)
        cost_reporter.record(MODEL, self._total_input_tokens, self._total_output_tokens)


if __name__ == "__main__":
    specialist = FunnelSpecialist()
    specialist.run()
