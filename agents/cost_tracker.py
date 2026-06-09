"""
Cost Tracker — GRID CONTROL
Agent ID: 9 | Runs on-demand (no Apify, no scraping)
Model: None — pure-math / template (Phase D: NO LLM. This agent is about saving
       money; it should not spend any. Report is built deterministically.)

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
from calendar import monthrange
from datetime import datetime
from dotenv import load_dotenv

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from ceo_brain.orchestrator import CEOBrain

load_dotenv(override=True)

# Phase D: pure-math agent. No model, no Anthropic client, no token cost.
MODEL = None


class CostTracker:

    def __init__(self, brand_slug: str = "offgrid-creatives-ai"):
        self.brand_slug = brand_slug
        self.now        = datetime.utcnow()
        self.year       = self.now.year
        self.month      = self.now.month
        self.log("Initialising Cost Tracker...")

        self.ceo = CEOBrain()
        self.brand_profile = self.ceo.brand_profile
        self.log(f"Ready (pure-math, no LLM). Brand: {self.brand_profile.get('brand_name', brand_slug)}")

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

    # ── Deterministic analysis (pure-math, no LLM) ────────────────────────────

    def _build_cost_analysis(self, cost_data: dict) -> str:
        """Build a plain-English monthly cost report from the numbers. No LLM."""
        month_name = datetime(self.year, self.month, 1).strftime("%B %Y")
        brand_name = self.brand_profile.get("brand_name", self.brand_slug)
        totals     = cost_data.get("totals", {})
        agents     = cost_data.get("agents", [])
        total      = float(totals.get("total_usd", 0) or 0)
        runs       = totals.get("total_runs", 0)
        inr        = total * 85  # USD→INR ≈ 85

        if not agents or runs == 0:
            return (
                f"No agent runs were recorded for {brand_name} in {month_name}. "
                f"Total spend: $0.00 (₹0). Nothing to optimise yet."
            )

        def agent_total(a: dict) -> float:
            return (
                float(a.get("api_cost_usd", 0) or 0)
                + float(a.get("fal_cost_usd", 0) or 0)
                + float(a.get("apify_cost_usd", 0) or 0)
            )

        top = max(agents, key=agent_total)
        services = {
            "Anthropic API": float(totals.get("api_cost_usd", 0) or 0),
            "FAL.ai":        float(totals.get("fal_cost_usd", 0) or 0),
            "Apify":         float(totals.get("apify_cost_usd", 0) or 0),
        }
        top_service = max(services, key=services.get)

        # Month-end projection: pro-rate by days elapsed.
        days_in_month = monthrange(self.year, self.month)[1]
        day_of_month  = min(self.now.day, days_in_month) or 1
        projection    = total / day_of_month * days_in_month

        # Reasonableness band (plan §8: minimal ≈ $65-75/mo, full ≈ $110-150).
        if total < 50:
            verdict = "well within the expected envelope — no action needed."
        elif total < 150:
            verdict = "in the normal full-pipeline range; keep an eye on the top driver."
        else:
            verdict = "above the expected band — review the top agent/service below."

        return (
            f"{brand_name} spent ${total:.2f} (~₹{inr:,.0f}) across {runs} agent "
            f"runs in {month_name}.\n"
            f"Most expensive agent: {top['agent_slug']} — ${agent_total(top):.2f} "
            f"over {top.get('runs', 0)} run(s).\n"
            f"Biggest cost driver: {top_service} (${services[top_service]:.2f}).\n"
            f"Assessment: this is {verdict}\n"
            f"Projection: at the current pace ({day_of_month}/{days_in_month} days "
            f"elapsed), month-end is tracking to ${projection:.2f} (~₹{projection*85:,.0f})."
        )

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
        # Pure-math agent — no LLM tokens to record.
        return out_path


if __name__ == "__main__":
    slug = sys.argv[1] if len(sys.argv) > 1 else "offgrid-creatives-ai"
    CostTracker(brand_slug=slug).run()
