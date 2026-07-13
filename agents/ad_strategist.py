"""
Ad Strategist — OffGrid Marketing OS
Agent ID: 5 | Model: claude-opus-4-8 (via gateway, "ad-strategist")

BUDGET-GATED: only runs when the brand confirms a paid budget (brand_profile
paid_budget_confirmed / budget_confirmed / ad_budget). Otherwise it halts with an
honest note and spends nothing — paid strategy for a brand with no budget is fiction.

What it does (Jul 6 repo research → ADOPT apify/facebook-ads-scraper, already wired via
agents/intel/competitor_intel.meta_ads):
  1. Pull REAL competitor Meta ads (Ad Library via Apify) for the brand's competitor_handles.
  2. From that real ad data + brand context, build: ad angles, 3 copy variants per angle
     (Rule 9 loop → winner), a targeting brief, and an A/B test structure.
  3. Every recommendation carries provenance to the real ad data or brand_profile. Never
     invents competitor ad claims. Writes drafts to pending_approval — NEVER launches ads.

Cost: the Meta Ad Library scrape is a paid Apify call, gated by paid_ops (GRID_PAID_OPS).
"""

import os
import sys
import json
from datetime import datetime, timezone
from pathlib import Path
from dotenv import load_dotenv

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import anthropic
from ceo_brain.orchestrator import CEOBrain
from agents._lib import cost_reporter
from agents._lib._untrusted import wrap, UNTRUSTED_POLICY
from agents._lib.model_gateway import model_for

load_dotenv(override=True)

ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "").strip()
MODEL = model_for("ad-strategist")
BRAND_SLUG = os.getenv("ACTIVE_BRAND", "offgrid-creatives-ai")
MAX_COMPETITORS = int(os.getenv("GRID_AD_MAX_COMPETITORS", "4"))  # bound the paid scrape


def _safe_json_loads(raw: str):
    raw = raw.strip()
    if "```" in raw:
        for part in raw.split("```"):
            part = part.strip()
            if part.startswith("json"):
                part = part[4:].strip()
            if part.startswith("{"):
                raw = part
                break
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        idx = raw.find("{")
        if idx >= 0:
            return json.loads(raw[idx:])
        raise


class AdStrategist:

    def __init__(self, brand_slug: str = BRAND_SLUG):
        self.brand_slug = brand_slug
        self.log("Initialising Ad Strategist...")
        self.ceo = CEOBrain()
        self.brand_profile = self.ceo.brand_profile
        self.brand_dir = Path(self.ceo.brand_dir)
        if not ANTHROPIC_API_KEY:
            raise ValueError("ANTHROPIC_API_KEY not found in .env")
        self.client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
        from agents._lib.brand_archetype import classify_brand
        self.archetype = classify_brand(self.brand_slug, self.brand_profile)
        self._total_input_tokens = 0
        self._total_output_tokens = 0

    def log(self, msg: str) -> None:
        print(f"[AdStrategist] {msg}")

    # ── budget gate ────────────────────────────────────────────────────────────
    def _budget_confirmed(self) -> bool:
        bp = self.brand_profile
        return bool(bp.get("paid_budget_confirmed") or bp.get("budget_confirmed") or bp.get("ad_budget"))

    # ── real competitor ad intel (paid, cost-gated) ────────────────────────────
    def _competitors(self) -> list[str]:
        raw = self.brand_profile.get("competitor_handles") or self.brand_profile.get("competitors") or []
        if isinstance(raw, str):
            raw = [x.strip() for x in raw.replace(",", "\n").splitlines() if x.strip()]
        out = []
        for c in raw:
            name = c.get("name") or c.get("handle") if isinstance(c, dict) else c
            if name:
                out.append(str(name).lstrip("@").strip())
        return out[:MAX_COMPETITORS]

    def gather_ad_intel(self) -> dict:
        competitors = self._competitors()
        if not competitors:
            return {"ads": [], "note": "no competitor_handles in brand_profile — cannot pull competitor ads"}
        # Cost gate — the Ad Library scrape is a paid Apify call.
        try:
            from agents._lib import paid_ops
            ok, reason = paid_ops.check("apify:meta_ads")
        except Exception as e:
            ok, reason = False, f"paid_ops unavailable ({e})"
        if not ok:
            return {"ads": [], "note": f"paid-ops off — competitor ad scrape skipped ({reason})"}
        try:
            from agents.intel.competitor_intel import CompetitorIntel
            ci = CompetitorIntel(self.brand_slug)
        except Exception as e:
            return {"ads": [], "note": f"competitor_intel unavailable ({e})"}
        ads = []
        for name in competitors:
            try:
                res = ci.meta_ads(search_term=name, page_match=name)
                res["competitor"] = name
                ads.append(res)
                self.log(f"  {name}: {res.get('status')} ({res.get('active_ads', 0)} active ads)")
            except Exception as e:
                ads.append({"competitor": name, "status": "error", "note": str(e)[:160]})
        return {"ads": ads, "note": None, "competitors_checked": competitors}

    # ── strategy synthesis ─────────────────────────────────────────────────────
    def build_strategy(self, ad_intel: dict) -> dict:
        from agents._lib._agent_framework import operating_framework
        from agents._lib.brand_archetype import directive_block
        bp = self.brand_profile
        brand_ctx = json.dumps({
            "brand_name": bp.get("brand_name"), "product": bp.get("product") or bp.get("product_description"),
            "target_audience": bp.get("target_audience") or bp.get("audience_primary"),
            "price": bp.get("price_india") or bp.get("price"), "offer": bp.get("entry_offer"),
            "unique_tension": bp.get("unique_tension"), "platforms": bp.get("platforms"),
            "ad_budget": bp.get("ad_budget"), "north_star": bp.get("north_star_metric"),
        }, indent=2)

        system = operating_framework(2) + (
            f"You are the Ad Strategist for {bp.get('brand_name', self.brand_slug)}. Build a paid-ads "
            f"plan grounded ONLY in the real competitor ad data provided + the brand context. Do not "
            f"invent competitor ad claims. If the ad data is thin, say so and lean on brand context, "
            f"flagging what needs validation once ads run.\n"
            f"{directive_block(self.archetype, agent='ad-strategist')}\n\n{UNTRUSTED_POLICY}"
        )
        task = f"""BRAND CONTEXT:
{brand_ctx}

REAL COMPETITOR AD DATA (Meta Ad Library via Apify — analyze only, never fabricate):
{wrap("competitor_ads", json.dumps(ad_intel.get("ads", []), indent=2)[:6000])}

Build the paid-ads plan. Return ONLY valid JSON:
{{
  "loop_header": {{"agent": "Ad Strategist", "output_type": "Paid Ads Plan",
    "goal": "highest-ROAS entry-offer acquisition within budget",
    "metric": "better = clearest angle + strongest hook + testable structure, grounded in real ad data",
    "variants_tested": 3, "winner": "<which angle won + one-line reason>"}},
  "competitor_read": "<2-3 sentences: what competitors are actually running, from the real data>",
  "ad_angles": [
    {{"angle": "", "why_now": "", "funnel_stage": "TOF|MOF|BOF",
      "copy_variants": ["", "", ""], "copy_winner": "", "primary_platform": ""}}
  ],
  "targeting_brief": {{"audiences": [], "geos": [], "placements": [], "exclusions": []}},
  "ab_test_plan": {{"hypothesis": "", "variable": "", "control": "", "variant": "",
    "primary_metric": "", "min_spend_note": ""}},
  "data_provenance": [
    {{"claim": "", "source": "competitor_ads|brand_profile", "detail": "verbatim/near-verbatim snippet"}}
  ],
  "budget_note": "how to phase spend given the confirmed budget"
}}
Give 3 ad_angles, each with exactly 3 copy_variants and a winner."""

        self.log(f"Synthesizing ads plan via {MODEL}...")
        resp = self.client.messages.create(
            model=MODEL, max_tokens=4096, system=system,
            messages=[{"role": "user", "content": self.ceo.story_so_far_block() + task}],
        )
        self._total_input_tokens += resp.usage.input_tokens
        self._total_output_tokens += resp.usage.output_tokens
        return _safe_json_loads(resp.content[0].text)

    # ── run ────────────────────────────────────────────────────────────────────
    def run(self) -> None:
        self.log("=" * 60)
        self.log("AD STRATEGIST — Starting run")

        loop_header = {"goal": "highest-ROAS acquisition within confirmed budget",
                       "metric": "grounded, testable ad plan", "variants_tested": 3,
                       "winner": "top ad angle"}

        if not self._budget_confirmed():
            self.log("HALT — no confirmed paid budget. Ad Strategist stays dormant (spends nothing).")
            output = {"agent": "Ad Strategist", "brand": self.brand_slug,
                      "generated_at": datetime.now(timezone.utc).isoformat(),
                      "status": "dormant_no_budget",
                      "data_quality_note": ("Ad Strategist is budget-gated. Set paid_budget_confirmed: true "
                                            "(+ ad_budget) in brand_profile once a paid budget exists. No paid work runs until then.")}
            self.ceo.save_agent_output(agent_name="Ad Strategist", output_type="Paid Ads Plan (dormant)",
                                       loop_header=loop_header, content=json.dumps(output, indent=2),
                                       filename="ads_plan_dormant.json")
            self.ceo.mark_agent_complete("ad-strategist")
            return

        ad_intel = self.gather_ad_intel()
        if ad_intel.get("note"):
            self.log(f"  ad intel: {ad_intel['note']}")
        plan = self.build_strategy(ad_intel)

        output = {"agent": "Ad Strategist", "brand": self.brand_slug,
                  "generated_at": datetime.now(timezone.utc).isoformat(),
                  "loop_header": plan.get("loop_header", loop_header),
                  "competitor_read": plan.get("competitor_read", ""),
                  "ad_angles": plan.get("ad_angles", []),
                  "targeting_brief": plan.get("targeting_brief", {}),
                  "ab_test_plan": plan.get("ab_test_plan", {}),
                  "data_provenance": plan.get("data_provenance", []),
                  "budget_note": plan.get("budget_note", ""),
                  "competitor_ad_intel": ad_intel.get("ads", []),
                  "ad_intel_note": ad_intel.get("note"),
                  "publish_policy": "DRAFT ONLY — never auto-launched. Approve in Grid Control, then a human sets up the campaign."}

        self.ceo.save_agent_output(agent_name="Ad Strategist", output_type="Paid Ads Plan",
                                   loop_header=output["loop_header"], content=json.dumps(output, indent=2),
                                   filename="ads_plan.json")
        self.ceo.mark_agent_complete("ad-strategist")
        cost_reporter.record(MODEL, self._total_input_tokens, self._total_output_tokens)
        self.log(f"AD STRATEGIST — Complete ({len(output['ad_angles'])} angles). Drafts in pending_approval (never auto-launched).")
        self.log("=" * 60)


if __name__ == "__main__":
    AdStrategist().run()
