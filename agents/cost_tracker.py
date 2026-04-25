"""
Cost Tracker — GRID CONTROL
Agent ID: 9 | Runs on-demand (no Apify, no scraping)
Model: claude-haiku-4-5-20251001  (cheapest — this agent IS about saving money)

What it does:
  - Reads all agent_runs for this brand for the current month from Supabase
  - Calculates Anthropic API cost (per token, per model)
  - Calculates FAL.ai cost (per image/video generation)
  - Calculates Apify cost (per actor run)
  - Produces a plain-English monthly cost report per agent
  - Writes report to brands/{slug}/cost_report.json
  - Pushes summary to CEO Brain

Pricing used:
  Claude Sonnet 4-6:  $3.00 / 1M input,  $15.00 / 1M output
  Claude Opus 4-6:   $15.00 / 1M input,  $75.00 / 1M output
  Claude Haiku 4-5:   $0.80 / 1M input,   $4.00 / 1M output
  FAL.ai:            ~$0.008 per image generation
  Apify:             ~$0.35  per actor run
"""

import os
import sys
import json
from datetime import datetime
from dotenv import load_dotenv

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import anthropic
from ceo_brain.orchestrator import CEOBrain
import cost_reporter

load_dotenv(override=True)

ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "").strip()
MODEL = "claude-haiku-4-5-20251001"


class CostTracker:

    def __init__(self, brand_slug: str = "offgrid-creatives-ai"):
        self.brand_slug = brand_slug
        self.now        = datetime.utcnow()
        self.year       = self.now.year
        self.month      = self.now.month
        self.log("Initialising Cost Tracker...")

        self.ceo = CEOBrain()
        self.brand_profile = self.ceo.brand_profile

        if not ANTHROPIC_API_KEY:
            raise ValueError("ANTHROPIC_API_KEY not found in .env")
        self.client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
        self.log(f"Ready. Brand: {self.brand_profile.get('brand_name', brand_slug)}")
        self._total_input_tokens = 0
        self._total_output_tokens = 0

    def log(self, msg: str):
        ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        print(f"[Cost Tracker | {ts}] {msg}")

    # ── Supabase data pull ────────────────────────────────────────────────────

    def _pull_monthly_costs(self) -> dict:
        """Pull aggregated cost data from Supabase for this month."""
        try:
            sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "supabase"))
            import db as _db

            # Resolve brand_id
            brand_row = _db.get_brand(self.brand_slug)
            if not brand_row:
                self.log(f"Brand '{self.brand_slug}' not found in Supabase — using empty data")
                return {"year": self.year, "month": self.month, "agents": [], "totals": {}}

            brand_id = brand_row["id"]
            data = _db.get_brand_monthly_costs(brand_id, self.year, self.month)
            self.log(f"Pulled {len(data.get('agents', []))} agent records from Supabase")
            return data
        except Exception as e:
            self.log(f"Supabase pull failed: {e} — returning empty data")
            return {"year": self.year, "month": self.month, "agents": [], "totals": {}}

    # ── Claude analysis ───────────────────────────────────────────────────────

    def _build_cost_analysis(self, cost_data: dict) -> str:
        """Ask Claude Haiku to interpret the cost data into a plain-English report."""
        month_name = datetime(self.year, self.month, 1).strftime("%B %Y")
        brand_name = self.brand_profile.get("brand_name", self.brand_slug)
        totals     = cost_data.get("totals", {})
        agents     = cost_data.get("agents", [])

        # Format agent table for the prompt
        agent_lines = []
        for a in agents:
            agent_lines.append(
                f"  {a['agent_slug']}: {a['runs']} runs | "
                f"{a['input_tokens']:,} input tokens | {a['output_tokens']:,} output tokens | "
                f"API ${a['api_cost_usd']:.4f} | "
                f"FAL {a['fal_generations']} imgs ${a['fal_cost_usd']:.4f} | "
                f"Apify {a['apify_runs']} runs ${a['apify_cost_usd']:.4f}"
            )
        agent_block = "\n".join(agent_lines) if agent_lines else "  No agent runs recorded this month."

        prompt = f"""You are the Cost Tracker for {brand_name}'s GRID CONTROL marketing OS.

Month: {month_name}

RAW COST DATA:
{agent_block}

TOTALS:
  Anthropic API:  ${totals.get('api_cost_usd', 0):.4f}
  FAL.ai images:  ${totals.get('fal_cost_usd', 0):.4f}
  Apify scraping: ${totals.get('apify_cost_usd', 0):.4f}
  TOTAL THIS MONTH: ${totals.get('total_usd', 0):.4f}
  Total agent runs: {totals.get('total_runs', 0)}

Write a concise cost report in plain English with:
1. One-sentence summary of total spend this month
2. Which agent cost the most and why (if data available)
3. Which service (Anthropic / FAL.ai / Apify) is the biggest cost driver
4. Simple recommendation: is this cost reasonable for the value it creates? What to watch.
5. Monthly projection if usage stays the same

Keep it under 200 words. No JSON. No code blocks. Direct and practical."""

        resp = self.client.messages.create(
            model=MODEL,
            max_tokens=512,
            messages=[{"role": "user", "content": prompt}],
        )
        self._total_input_tokens += resp.usage.input_tokens
        self._total_output_tokens += resp.usage.output_tokens
        return resp.content[0].text.strip()

    # ── Save output ───────────────────────────────────────────────────────────

    def _save_report(self, cost_data: dict, analysis: str) -> str:
        """Write cost report to brands/{slug}/cost_report.json."""
        brand_dir = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "brands", self.brand_slug
        )
        os.makedirs(brand_dir, exist_ok=True)

        report = {
            "generated_at": datetime.utcnow().isoformat() + "Z",
            "brand_slug":   self.brand_slug,
            "brand_name":   self.brand_profile.get("brand_name", self.brand_slug),
            "period":       f"{self.year}-{self.month:02d}",
            "cost_data":    cost_data,
            "analysis":     analysis,
        }

        out_path = os.path.join(brand_dir, "cost_report.json")
        with open(out_path, "w") as f:
            json.dump(report, f, indent=2)

        self.log(f"Report saved → {out_path}")
        return out_path

    def _push_to_supabase(self, cost_data: dict, analysis: str) -> None:
        """Save output to agent_outputs via CEO Brain."""
        try:
            totals = cost_data.get("totals", {})
            self.ceo.save_agent_output(
                agent_name="Cost Tracker",
                output_type="Monthly Cost Report",
                loop_header={
                    "month":      f"{self.year}-{self.month:02d}",
                    "total_usd":  totals.get("total_usd", 0),
                    "total_runs": totals.get("total_runs", 0),
                },
                content={
                    "analysis":  analysis,
                    "cost_data": cost_data,
                },
            )
            self.log("Output pushed to CEO Brain / Notion")
        except Exception as e:
            self.log(f"CEO Brain push failed (non-fatal): {e}")

    # ── Main ──────────────────────────────────────────────────────────────────

    def run(self):
        self.log(f"Running cost analysis for {self.year}-{self.month:02d}...")

        cost_data = self._pull_monthly_costs()
        analysis  = self._build_cost_analysis(cost_data)
        out_path  = self._save_report(cost_data, analysis)
        self._push_to_supabase(cost_data, analysis)

        totals = cost_data.get("totals", {})
        self.log(f"Done. Total this month: ${totals.get('total_usd', 0):.4f}")
        print(f"\n{'='*60}")
        print(f"COST REPORT — {self.brand_profile.get('brand_name', self.brand_slug)}")
        print(f"{'='*60}")
        print(analysis)
        print(f"{'='*60}")
        print(f"Anthropic API:  ${totals.get('api_cost_usd', 0):.4f}")
        print(f"FAL.ai images:  ${totals.get('fal_cost_usd', 0):.4f}")
        print(f"Apify scraping: ${totals.get('apify_cost_usd', 0):.4f}")
        print(f"TOTAL:          ${totals.get('total_usd', 0):.4f}")
        print(f"Report saved:   {out_path}")
        cost_reporter.record(MODEL, self._total_input_tokens, self._total_output_tokens)
        return out_path


if __name__ == "__main__":
    slug = sys.argv[1] if len(sys.argv) > 1 else "offgrid-creatives-ai"
    CostTracker(brand_slug=slug).run()
