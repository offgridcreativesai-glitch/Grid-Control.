"""
CEO Brain — OffGrid Marketing OS
Orchestrator. Dynamic router. Session state manager.
Rule 3: Nothing executes without approval.
Rule 9: AutoResearch standard — loop before output.
"""

import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import json
from datetime import datetime
from dotenv import load_dotenv
from notion_integration.notion_pusher import push_to_notion, test_notion_connection

load_dotenv()

# Brand slug — active brand being managed
ACTIVE_BRAND = os.getenv("ACTIVE_BRAND", "offgrid-creatives-ai")
BRANDS_DIR = os.path.join(os.path.dirname(__file__), "..", "brands")


class CEOBrain:

    def __init__(self):
        self.brand_slug = ACTIVE_BRAND
        self.brand_dir = os.path.join(BRANDS_DIR, self.brand_slug)
        self.brand_profile = self.load_json("brand_profile.json")
        self.session_state = self.load_json("session_state.json")
        self.log(f"CEO Brain booted for brand: {self.brand_slug}")

        # Verify Notion on every boot
        notion_live = test_notion_connection()
        if not notion_live:
            self.log("WARNING: Notion connection failed. Approval pipeline is offline.")
        else:
            self.log("Notion approval pipeline: LIVE")

    def load_json(self, filename: str) -> dict:
        """Load a JSON file from the active brand directory."""
        path = os.path.join(self.brand_dir, filename)
        if not os.path.exists(path):
            self.log(f"WARNING: {filename} not found at {path}")
            return {}
        with open(path, "r") as f:
            return json.load(f)

    def save_session_state(self):
        """Persist session state to the active brand directory."""
        path = os.path.join(self.brand_dir, "session_state.json")
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w") as f:
            json.dump(self.session_state, f, indent=2)
        self.log("Session state saved.")

    def log(self, message: str):
        """Timestamped terminal log."""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        print(f"[CEO Brain | {timestamp}] {message}")

    def get_next_agent(self) -> str:
        """
        Dynamic router. Returns the next agent to run based on session state.
        Full 15-agent roster in correct sequence.
        CEO Brain decides path based on what data is available.
        """
        completed = self.session_state.get("completed_agents", [])

        # Full agent sequence — locked roster
        sequence = [
            "trend-researcher",       # Always runs first. Real data before anything.
            "strategy-agent",         # 90-day roadmap. Needs trend data.
            "content-planner",        # 30-day calendar. Needs strategy + trends.
            "script-writer",          # Scripts + hooks. Needs content plan.
            "creative-director",      # Video + image production. Needs scripts.
            "seo-aeo-agent",          # SEO + AEO optimization. Needs content.
            "email-marketing-agent",  # Email sequences. Needs content plan.
            "community-manager",      # Community engagement. Needs brand voice.
            "dm-customer-hunter",     # DM outreach. Needs audience data.
            "funnel-specialist",      # Full funnel. Needs strategy + content.
            "ad-strategist",          # Paid ads. Activates only when budget confirmed.
            "data-analyst",           # Metrics + scoring. Reads all outputs.
            "brand-guardian",         # Brand consistency check. Reviews all outputs.
            "website-agent",          # Website builds + deploys. Needs funnel.
            "ceo-brain-review",       # Final review gate before any execution.
        ]

        for agent in sequence:
            if agent not in completed:
                # Special gate — Ad Strategist only activates with confirmed budget
                if agent == "ad-strategist":
                    budget_confirmed = self.session_state.get("paid_budget_confirmed", False)
                    if not budget_confirmed:
                        self.log("Ad Strategist skipped — no paid budget confirmed yet.")
                        continue
                self.log(f"Next agent: {agent}")
                return agent

        self.log("All agents complete for this cycle.")
        return "complete"

    def save_agent_output(
        self,
        agent_name: str,
        output_type: str,
        loop_header: dict,
        content: str,
        filename: str
    ):
        """
        Save agent output to pending_approval/ and push to Notion.
        This is the only approved method for saving agent outputs.
        Rule 3: Nothing executes without approval.
        Rule 9: Loop header required on every output.
        """
        # Save to local pending_approval folder using slug (lowercase-hyphen) not display name
        import re as _re
        agent_folder = _re.sub(r"[^a-z0-9-]", "", agent_name.lower().replace(" ", "-")).strip("-")
        output_dir = os.path.join(
            self.brand_dir, "outputs", "pending_approval", agent_folder
        )
        os.makedirs(output_dir, exist_ok=True)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filepath = os.path.join(output_dir, f"{timestamp}_{filename}")

        # Write loop header + content to file
        full_output = f"""LOOP: {agent_name} — {output_type}
GOAL: {loop_header.get('goal', '')}
METRIC: better = {loop_header.get('metric', '')}
VARIANTS TESTED: {loop_header.get('variants_tested', 3)}
WINNER: {loop_header.get('winner', '')}

---

{content}
"""
        with open(filepath, "w") as f:
            f.write(full_output)

        self.log(f"Output saved locally: {filepath}")

        # ── BUILD H — Auto-block CRITICAL contradictions ──────────────────
        # Skip self-check for the contradiction detector itself + Brand Guardian
        # (avoid infinite loop / double-audit)
        contradiction_result = {"checked": False}
        if agent_name not in ("Brand Guardian", "Contradiction Detector"):
            try:
                import sys as _sys
                from pathlib import Path as _Path
                _sys.path.insert(0, str(_Path(__file__).resolve().parent))
                from contradiction_detector import detect_contradictions, save_contradictions_report
                report = detect_contradictions(self.brand_slug)
                save_contradictions_report(self.brand_slug, report)
                contradiction_result = {
                    "checked": True,
                    "blocking": report.get("blocking", False),
                    "counts":   report.get("counts", {}),
                    "critical_findings": [
                        f for f in report.get("findings", [])
                        if f.get("severity") == "CRITICAL"
                    ],
                }
                if report.get("blocking"):
                    # Only quarantine THIS save if the current agent is named in any CRITICAL finding's
                    # agents_involved list. Otherwise the contradiction is unrelated to this output —
                    # log a warning, surface it for review, but let the save proceed.
                    current_agent_in_critical = any(
                        agent_name in (f.get("agents_involved") or [])
                        for f in contradiction_result["critical_findings"]
                    )
                    self.log(f"🚨 BUILD H — {len(contradiction_result['critical_findings'])} CRITICAL contradiction(s) detected after {agent_name} save")
                    for f in contradiction_result["critical_findings"][:3]:
                        self.log(f"   [{f.get('rule_id')}] {f.get('agents_involved')}: {f.get('proposed_fix', '')[:120]}")

                    if current_agent_in_critical:
                        # Quarantine the file by moving it to a blocked subfolder
                        blocked_dir = os.path.join(self.brand_dir, "outputs", "blocked", agent_folder)
                        os.makedirs(blocked_dir, exist_ok=True)
                        blocked_path = os.path.join(blocked_dir, f"{timestamp}_{filename}")
                        try:
                            import shutil as _shutil
                            _shutil.move(filepath, blocked_path)
                            self.log(f"🔒 {agent_name} is named in CRITICAL finding — output QUARANTINED to: {blocked_path}")
                            return {
                                "local_path": blocked_path,
                                "blocked":    True,
                                "block_reason": "CRITICAL contradictions detected (agent named in finding)",
                                "contradictions": contradiction_result,
                                "notion_result": {"success": False, "error": "Skipped — output blocked by Build H"},
                            }
                        except Exception as e:
                            self.log(f"WARNING: Could not quarantine blocked output — {e}. Falling through to normal save.")
                    else:
                        self.log(f"   {agent_name} is NOT named in any CRITICAL finding — save allowed, but flagged for review.")
            except Exception as e:
                self.log(f"WARNING: Contradiction check skipped — {e}")
                contradiction_result = {"checked": False, "error": str(e)}

        # Push to Notion for human approval
        notion_result = push_to_notion(
            agent_name=agent_name,
            brand=self.brand_slug,
            output_type=output_type,
            loop_header=loop_header,
            content=content
        )

        if notion_result["success"]:
            self.log(f"Pushed to Notion: {notion_result['notion_url']}")
            # Store Notion URL in session state for reference
            if "notion_cards" not in self.session_state:
                self.session_state["notion_cards"] = []
            self.session_state["notion_cards"].append({
                "agent": agent_name,
                "output_type": output_type,
                "notion_url": notion_result["notion_url"],
                "page_id": notion_result["page_id"],
                "timestamp": notion_result["timestamp"],
                "status": "pending_approval"
            })
            self.save_session_state()
        else:
            self.log(f"WARNING: Notion push failed — {notion_result['error']}")
            self.log("Output saved locally but NOT in Notion. Manual review required.")

        return {
            "local_path": filepath,
            "notion_result": notion_result,
            "contradictions": contradiction_result,
        }

    def mark_agent_complete(self, agent_name: str):
        """Mark an agent as complete in session state."""
        if "completed_agents" not in self.session_state:
            self.session_state["completed_agents"] = []
        if agent_name not in self.session_state["completed_agents"]:
            self.session_state["completed_agents"].append(agent_name)
        self.session_state["last_completed"] = agent_name
        self.session_state["last_updated"] = datetime.now().isoformat()
        self.save_session_state()
        self.log(f"Agent marked complete: {agent_name}")

    def status_report(self):
        """Print current system state to terminal."""
        completed = self.session_state.get("completed_agents", [])
        next_agent = self.get_next_agent()
        notion_cards = self.session_state.get("notion_cards", [])
        pending = [c for c in notion_cards if c.get("status") == "pending_approval"]

        print("\n" + "="*60)
        print(f"  CEO BRAIN STATUS — {self.brand_slug.upper()}")
        print("="*60)
        print(f"  Completed agents : {len(completed)}/15")
        print(f"  Next agent       : {next_agent}")
        print(f"  Pending approvals: {len(pending)} in Notion")
        print(f"  Last updated     : {self.session_state.get('last_updated', 'Never')}")
        print("="*60 + "\n")


if __name__ == "__main__":
    brain = CEOBrain()
    brain.status_report()
