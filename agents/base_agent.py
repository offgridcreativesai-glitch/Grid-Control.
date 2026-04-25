import os
import sys
import json
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

# Add project root so supabase/db.py is importable from any agent
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class BaseAgent:
    def __init__(self, agent_name):
        self.agent_name = agent_name
        self.anthropic_api_key = os.getenv("ANTHROPIC_API_KEY")
        self.output_dir = "outputs/pending_approval"

        # Supabase available flag — agents use memory only when DB is live
        try:
            import supabase.db as _db
            self._db = _db
            self._db_available = True
        except Exception:
            self._db = None
            self._db_available = False

        # Resolved at first call to _get_brand_id()
        self._brand_id_cache: str | None = None

    # ── brand helpers ─────────────────────────────────────────────────────────

    def _get_brand_id(self, brand_slug: str) -> str | None:
        if not self._db_available:
            return None
        if self._brand_id_cache:
            return self._brand_id_cache
        try:
            row = self._db.get_brand(brand_slug)
            if row:
                self._brand_id_cache = row["id"]
                return self._brand_id_cache
        except Exception as e:
            self.log(f"[memory] brand_id lookup failed: {e}")
        return None

    def _agent_slug(self) -> str:
        import re
        return re.sub(r"[^a-z0-9-]", "", self.agent_name.lower().replace(" ", "-"))

    # ── persistent memory API ─────────────────────────────────────────────────

    def remember(self, brand_slug: str, key: str, value: str) -> None:
        """
        Save a memory entry for this agent + brand.
        key: short label (e.g. "best_hashtag_q1", "top_competitor_march")
        value: plain-text summary (keep under 1000 chars for retrieval quality)
        """
        if not self._db_available:
            return
        brand_id = self._get_brand_id(brand_slug)
        if not brand_id:
            return
        try:
            self._db.save_brand_memory(
                brand_id  = brand_id,
                agent_slug = self._agent_slug(),
                memory_key = key,
                content    = value,
            )
            self.log(f"[memory] saved: {key}")
        except Exception as e:
            self.log(f"[memory] save failed ({key}): {e}")

    def recall(self, brand_slug: str) -> list[dict]:
        """
        Return all memory entries for this agent + brand.
        Returns list of { memory_key, content, updated_at }.
        Agents should call this at startup and inject into their system prompt.
        """
        if not self._db_available:
            return []
        brand_id = self._get_brand_id(brand_slug)
        if not brand_id:
            return []
        try:
            entries = self._db.get_brand_memory(brand_id, self._agent_slug())
            self.log(f"[memory] recalled {len(entries)} entries")
            return entries
        except Exception as e:
            self.log(f"[memory] recall failed: {e}")
            return []

    def recall_as_text(self, brand_slug: str) -> str:
        """
        Return memory as a formatted string ready to inject into a system prompt.
        Example output:
            ## Agent Memory (from previous runs)
            - best_hashtag_q1: #ethnicwear drove 3x ER vs generic hashtags (Jan–Mar)
            - top_competitor: Biba dominated organic content in Feb with daily Reels
        """
        entries = self.recall(brand_slug)
        if not entries:
            return ""
        lines = [f"- {e['memory_key']}: {e['content']}" for e in entries]
        return "\n## Agent Memory (from previous runs)\n" + "\n".join(lines) + "\n"

    # ── cost reporting ────────────────────────────────────────────────────────

    def report_costs(
        self,
        brand_slug: str,
        run_id: str,
        model: str,
        input_tokens: int,
        output_tokens: int,
        fal_generations: int = 0,
        apify_runs: int = 0,
    ) -> None:
        """
        Call this at the end of every agent run to record cost data.
        run_id comes from the Supabase agent_runs row created by dashboard_api.py.
        If run_id is empty (direct script run), cost is logged but not stored.
        """
        if not self._db_available or not run_id:
            cost = self._db.calc_api_cost(model, input_tokens, output_tokens) if self._db_available else 0
            self.log(
                f"[cost] API=${cost:.4f} | tokens in={input_tokens:,} out={output_tokens:,} | "
                f"fal={fal_generations} apify={apify_runs}"
            )
            return
        try:
            self._db.update_agent_run_costs(
                run_id, model, input_tokens, output_tokens, fal_generations, apify_runs
            )
            cost = self._db.calc_api_cost(model, input_tokens, output_tokens)
            self.log(f"[cost] recorded — API=${cost:.4f} fal={fal_generations} apify={apify_runs}")
        except Exception as e:
            self.log(f"[cost] record failed: {e}")

    # ── file I/O ──────────────────────────────────────────────────────────────

    def load_brand_profile(self):
        with open("data/brand_profile.json", "r") as f:
            return json.load(f)

    def load_session_state(self):
        with open("data/session_state.json", "r") as f:
            return json.load(f)

    def load_competitors(self):
        with open("data/competitors_db.json", "r") as f:
            return json.load(f)

    def load_trends(self):
        with open("data/trends_live.json", "r") as f:
            return json.load(f)

    def save_output(self, output_dict, subfolder):
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{self.agent_name}_{timestamp}.json"
        filepath = f"{self.output_dir}/{subfolder}/{filename}"
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        with open(filepath, "w") as f:
            json.dump(output_dict, f, indent=2)
        print(f"Output saved to {filepath}")
        return filepath

    def update_session_state(self, key, value):
        state = self.load_session_state()
        state[key] = value
        state["last_run"] = datetime.now().isoformat()
        with open("data/session_state.json", "w") as f:
            json.dump(state, f, indent=2)

    def log(self, message):
        timestamp = datetime.now().strftime("%H:%M:%S")
        print(f"[{timestamp}] [{self.agent_name.upper()}] {message}")
