"""
Data Analyst — OffGrid Marketing OS
Agent ID: 6 | Runs every week automatically.
Model: claude-sonnet-4-6 (haiku spec, sonnet used for depth)
Rule 1: Read-only. Never modifies content files.
Rule 9: AutoResearch Loop — Raw metrics / Trend+pattern / Actionable insight variants.
Reads:  session_state.json + all pending/approved output files + brand_profile.json
Writes: brands/{slug}/outputs/pending_approval/Data Analyst/ + Notion card
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
MODEL = model_for("data-analyst")
BRAND_SLUG = os.getenv("ACTIVE_BRAND", "offgrid-creatives-ai")


def _escape_literal_newlines_in_strings(json_str: str) -> str:
    """Escape literal \\n/\\r/\\t inside JSON string values (Claude API quirk)."""
    result = []
    in_string = False
    i = 0
    while i < len(json_str):
        c = json_str[i]
        if in_string:
            if c == '\\':
                result.append(c); i += 1
                if i < len(json_str): result.append(json_str[i])
            elif c == '"':
                in_string = False; result.append(c)
            elif c == '\n': result.append('\\n')
            elif c == '\r': result.append('\\r')
            elif c == '\t': result.append('\\t')
            else: result.append(c)
        else:
            if c == '"': in_string = True
            result.append(c)
        i += 1
    return ''.join(result)


def _safe_json_loads(raw: str):
    """json.loads with literal-newline repair fallback."""
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return json.loads(_escape_literal_newlines_in_strings(raw))


class DataAnalyst:

    def __init__(self, brand_slug: str = BRAND_SLUG):
        self.brand_slug = brand_slug
        self.log("Initialising Data Analyst...")

        self.ceo = CEOBrain()
        self.brand_profile = self.ceo.brand_profile
        self.brand_dir = Path(self.ceo.brand_dir)

        if not ANTHROPIC_API_KEY:
            raise ValueError("ANTHROPIC_API_KEY not found in .env")
        self.client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
        self._total_input_tokens = 0
        self._total_output_tokens = 0

    def log(self, msg: str) -> None:
        print(f"[DataAnalyst] {msg}")

    # ── Data collection ───────────────────────────────────────────────────────

    def collect_output_inventory(self) -> dict:
        """Scan all output files across pending + approved for scoring."""
        inventory: dict = {
            "pending": {},
            "approved": {},
            "total_files": 0,
        }

        for status in ["pending_approval", "approved"]:
            base = self.brand_dir / "outputs" / status
            if not base.exists():
                continue
            for agent_dir in base.iterdir():
                if not agent_dir.is_dir():
                    continue
                files = list(agent_dir.glob("*.json"))
                inventory[status if status == "approved" else "pending"][agent_dir.name] = {
                    "count": len(files),
                    "files": [f.name for f in files],
                }
                inventory["total_files"] += len(files)

        return inventory

    def collect_session_data(self) -> dict:
        """Read session_state for agent run history and Notion card counts."""
        session_path = self.brand_dir / "session_state.json"
        if not session_path.exists():
            return {}
        with open(session_path) as f:
            return json.load(f)

    def collect_api_connection_status(self) -> dict:
        """Check which external APIs are configured."""
        return {
            "meta_graph_api":    bool(os.getenv("META_GRAPH_API_TOKEN", "").strip()),
            "ig_insights":       bool(os.getenv("META_GRAPH_API_TOKEN", "").strip()),
            "linkedin_api":      bool(os.getenv("LINKEDIN_ACCESS_TOKEN", "").strip()),
            "ga4":               bool(os.getenv("GA4_PROPERTY_ID", "").strip()),
            "search_console":    bool(os.getenv("SEARCH_CONSOLE_SITE_URL", "").strip()),
            "anthropic":         bool(ANTHROPIC_API_KEY),
            "elevenlabs":        bool(os.getenv("ELEVENLABS_API_KEY", "").strip()),
        }

    def collect_live_insights(self) -> dict:
        """Pull live IG/FB-Page insights (real data only — never fabricated).
        Returns the meta_insights structure; empty/with-errors if unconfigured."""
        try:
            from agents.intel.meta_insights import fetch_instagram_insights
        except ImportError:
            from agents.intel.meta_insights import fetch_instagram_insights
        benv = {
            "META_GRAPH_API_TOKEN": os.getenv("META_GRAPH_API_TOKEN", ""),
            "IG_USER_ID":           os.getenv("IG_USER_ID", ""),
        }
        return fetch_instagram_insights(benv)

    def collect_script_sample(self) -> list:
        """Pull a sample of script writer outputs for hook analysis."""
        scripts = []
        for status in ["pending_approval", "approved"]:
            script_dir = self.brand_dir / "outputs" / status / "Script Writer"
            if not script_dir.exists():
                continue
            for f in sorted(script_dir.glob("*.json"), key=lambda x: x.stat().st_mtime, reverse=True)[:2]:
                raw = f.read_text().strip()
                if "---" in raw:
                    raw = raw.split("---", 1)[1].strip()
                try:
                    data = _safe_json_loads(raw)
                    for item in data.get("scripts", [])[:3]:
                        s = item.get("script", {})
                        scripts.append({
                            "platform": s.get("platform"),
                            "format": s.get("format"),
                            "hook": s.get("hook", "")[:120],
                            "week": item.get("week"),
                            "requires_human_face": item.get("requires_human_face"),
                        })
                except Exception:
                    pass
        return scripts[:9]

    # ── AutoResearch Loop — Rule 9 ────────────────────────────────────────────

    def run_autoresearch_loop(self, data_package: dict) -> dict:
        """
        3 variants:
        A — Raw metrics summary (what happened)
        B — Trend + pattern read (why it happened)
        C — Actionable insight with next step recommendation (what to do next)
        Metric: which report leads to highest probability of CEO Brain adjusting strategy
        """

        prompt = f"""You are the Data Analyst for OffGrid Creatives AI Marketing OS.

BRAND: {self.brand_profile.get('brand_name', 'OffGrid Creatives AI')}
PRODUCT: {self.brand_profile.get('product', 'AI Ad Intelligence Report')}
PHASE: {self.brand_profile.get('phase', 'beta')}
PLATFORMS: {', '.join(self.brand_profile.get('platforms', ['Instagram', 'LinkedIn']))}
GOAL: {self.brand_profile.get('goal', 'Sell beta reports')}

SYSTEM STATE THIS WEEK:
{json.dumps(data_package, indent=2)}

IMPORTANT CONTEXT:
- Meta Graph API is {'CONNECTED' if data_package['api_status']['meta_graph_api'] else 'NOT CONNECTED — no live Instagram metrics available'}
- LinkedIn API is {'CONNECTED' if data_package['api_status']['linkedin_api'] else 'NOT CONNECTED — no live LinkedIn metrics available'}
- GA4 is {'CONNECTED' if data_package['api_status']['ga4'] else 'NOT CONNECTED'}
- Total output files in system: {data_package['output_inventory']['total_files']}
- Completed agents: {', '.join(data_package['session'].get('completed_agents', []))}
- Notion cards pending: {len([c for c in data_package['session'].get('notion_cards', []) if c.get('status') == 'pending_approval'])}
- Notion cards approved: {len([c for c in data_package['session'].get('notion_cards', []) if c.get('status') == 'approved'])}

Generate 3 analysis variants for this week's performance report.

VARIANT A — Raw metrics summary:
Report exactly what the system produced this week — output counts by agent, approval status, what's been run vs not run yet. No inference. Just facts.

VARIANT B — Trend + pattern read:
Based on what agents have run and what scripts have been produced, identify any patterns. Which content formats dominate? What hooks are being used? What does the production pipeline look like? Are there gaps?

VARIANT C — Actionable insight with next step recommendation:
Lead with the single most important insight from this week's data, then give 3 specific next actions the CEO Brain should take to maximise beta sales this week. Be specific — not "post more content" but exactly what to do and why.

Return ONLY valid JSON:
{{
  "report_week": "{datetime.now().strftime('%Y-W%U')}",
  "loop_goal": "produce the analysis variant most likely to drive CEO Brain strategy adjustment",
  "loop_metric": "better = more specific, more actionable, higher probability of producing a paying beta client",
  "variants": {{
    "A": {{
      "label": "Raw Metrics Summary",
      "agents_run_this_cycle": [],
      "agents_not_yet_run": [],
      "output_counts": {{}},
      "approval_pipeline": {{}},
      "api_connections": {{}},
      "summary": ""
    }},
    "B": {{
      "label": "Trend + Pattern Read",
      "content_format_distribution": {{}},
      "hook_frameworks_detected": [],
      "production_pipeline_health": "",
      "gaps_identified": [],
      "pattern_insights": []
    }},
    "C": {{
      "label": "Actionable Insight + Next Steps",
      "lead_insight": "",
      "confidence": "high/medium/low",
      "next_actions": [
        {{"action": "", "reason": "", "expected_outcome": "", "priority": 1}},
        {{"action": "", "reason": "", "expected_outcome": "", "priority": 2}},
        {{"action": "", "reason": "", "expected_outcome": "", "priority": 3}}
      ],
      "repurposing_candidates": [],
      "anomalies_detected": []
    }}
  }},
  "winning_variant": "C",
  "winner_reason": "Actionable insight variant directly serves CEO Brain's routing decisions"
}}"""

        self.log("Running AutoResearch Loop — 3 analysis variants via Claude Sonnet...")
        response = self.client.messages.create(
            model=MODEL,
            max_tokens=4096,
            messages=[{"role": "user", "content": self.ceo.story_so_far_block() + prompt}]
        )
        self._total_input_tokens += response.usage.input_tokens
        self._total_output_tokens += response.usage.output_tokens
        raw = response.content[0].text.strip()
        if "```" in raw:
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
        try:
            return _safe_json_loads(raw)
        except json.JSONDecodeError:
            idx = raw.find("{")
            if idx >= 0:
                try:
                    return _safe_json_loads(raw[idx:])
                except Exception:
                    pass
            raise ValueError(f"Could not parse loop response: {raw[:200]}")

    # ── Main run ──────────────────────────────────────────────────────────────

    def run(self) -> None:
        self.log("=" * 60)
        self.log("DATA ANALYST — Starting weekly run")
        self.log("=" * 60)

        # Collect all data (READ ONLY — never modify anything)
        self.log("Collecting system state data...")
        inventory   = self.collect_output_inventory()
        session     = self.collect_session_data()
        api_status  = self.collect_api_connection_status()
        scripts     = self.collect_script_sample()
        live_insights = self.collect_live_insights()

        if not api_status["meta_graph_api"]:
            self.log("⚠️  META_GRAPH_API_TOKEN not set — live Instagram metrics unavailable.")
            self.log("   Report will be based on system output inventory only.")
        if not api_status["ig_insights"]:
            self.log("⚠️  META_GRAPH_API_TOKEN not set — IG insights unavailable.")
        elif live_insights.get("connected"):
            acct = live_insights.get("account", {})
            self.log(f"✅ Live IG insights: @{acct.get('username','?')} · "
                     f"{acct.get('followers_count','?')} followers · "
                     f"reach_28d={acct.get('reach_28d','n/a')}")
            for e in live_insights.get("errors", []):
                self.log(f"   · insight note: {e}")
        if not api_status["linkedin_api"]:
            self.log("⚠️  LINKEDIN_ACCESS_TOKEN not set — live LinkedIn metrics unavailable.")

        data_package = {
            "output_inventory": inventory,
            "session":          session,
            "api_status":       api_status,
            "live_insights":    live_insights,
            "script_sample":    scripts,
            "report_generated": datetime.now().isoformat(),
        }

        # Run AutoResearch Loop
        loop_result = self.run_autoresearch_loop(data_package)
        winning_variant = loop_result.get("winning_variant", "C")
        winner_reason   = loop_result.get("winner_reason", "")
        variants        = loop_result.get("variants", {})
        winning_data    = variants.get(winning_variant, {})

        self.log(f"Loop complete. Winner: Variant {winning_variant} — {winner_reason}")

        # Build loop header
        loop_header = {
            "goal":             loop_result.get("loop_goal", ""),
            "metric":           loop_result.get("loop_metric", ""),
            "variants_tested":  3,
            "winner":           f"Variant {winning_variant} — {winner_reason}",
        }

        # Assemble final output
        output = {
            "agent":             "Data Analyst",
            "brand":             self.brand_slug,
            "report_week":       loop_result.get("report_week", ""),
            "generated_at":      datetime.now().isoformat(),
            "loop_header":       loop_header,
            "winning_analysis":  winning_data,
            "all_variants":      variants,
            "raw_data_snapshot": {
                "output_inventory":  inventory,
                "api_status":        api_status,
                "live_insights":     live_insights,
                "completed_agents":  session.get("completed_agents", []),
                "notion_card_count": len(session.get("notion_cards", [])),
            },
            "data_quality_note": (
                "LIVE API DATA: Not available — Meta Graph API and LinkedIn API tokens not set. "
                "Report based on system output inventory. Connect APIs via Brand Onboarding to unlock live metrics."
                if not api_status["meta_graph_api"] and not api_status["linkedin_api"]
                else f"LIVE API DATA: {'IG insights active' if live_insights.get('connected') else 'Partial'} — "
                     f"reach/audience via Instagram Login API."
            )
        }

        # Save output
        output_dir = self.brand_dir / "outputs" / "pending_approval" / "Data Analyst"
        output_dir.mkdir(parents=True, exist_ok=True)
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{ts}_weekly_report.json"
        output_path = output_dir / filename

        header_text = (
            f"LOOP: Data Analyst — Weekly Performance Report\n"
            f"GOAL: {loop_header['goal']}\n"
            f"METRIC: better = {loop_header['metric']}\n"
            f"VARIANTS TESTED: 3\n"
            f"WINNER: {loop_header['winner']}\n"
            f"---\n"
        )
        output_path.write_text(header_text + json.dumps(output, indent=2))
        self.log(f"✅ Report saved: {filename}")

        # Push to Notion
        self.log("Pushing to Notion approval pipeline...")
        self.ceo.save_agent_output(
            agent_name="Data Analyst",
            output_type="Weekly Performance Report",
            loop_header=loop_header,
            content=json.dumps(output, indent=2),
            filename=filename,
        )

        self.ceo.mark_agent_complete("data-analyst")

        self.log("=" * 60)
        self.log("DATA ANALYST — Run complete")
        self.log(f"Report week     : {loop_result.get('report_week', 'N/A')}")
        self.log(f"Winning variant : Variant {winning_variant}")
        self.log(f"API data live   : {'❌ Not connected' if not api_status['meta_graph_api'] else '✅ Meta connected'}")
        self.log(f"Notion card     : ✅ Pushed")
        cost_reporter.record(MODEL, self._total_input_tokens, self._total_output_tokens)
        self.log(f"Output file     : {filename}")
        self.log("=" * 60)


if __name__ == "__main__":
    analyst = DataAnalyst()
    analyst.run()
