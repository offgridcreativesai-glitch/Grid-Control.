import os
import sys
import json
import time
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

# Add project root so supabase/db.py is importable from any agent
_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _PROJECT_ROOT)


class BaseAgent:
    def __init__(self, agent_name):
        self.agent_name = agent_name
        self.anthropic_api_key = os.getenv("ANTHROPIC_API_KEY")
        _slug = os.getenv("ACTIVE_BRAND", "")
        if _slug:
            self.output_dir = os.path.join(_PROJECT_ROOT, "brands", _slug, "outputs", "pending_approval")
        else:
            self.output_dir = os.path.join(_PROJECT_ROOT, "outputs", "pending_approval")
        self._session_context: dict | None = None
        self._session_start_time: float = time.time()

        # Supabase available flag — agents use memory only when DB is live.
        # NB: `import supabase.db` collides with the pip `supabase` package, so
        # import the local module directly with supabase/ on the path (same as
        # dashboard_api). This is what makes memory + narrative actually persist.
        try:
            _supa_dir = os.path.join(_PROJECT_ROOT, "supabase")
            if _supa_dir not in sys.path:
                sys.path.insert(0, _supa_dir)
            import db as _db
            self._db = _db
            self._db_available = True
        except Exception as _e:
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

    # ── narrative memory (story-so-far) ───────────────────────────────────────
    # Append-only timeline of decisions/actions/results across ALL agents, so a
    # run CONTINUES the brand's story instead of cold-starting (Phase A).

    def narrative_read(self, brand_slug: str, n: int = 20) -> list[dict]:
        """Return the most recent N narrative entries (oldest→newest) for this
        brand across all agents. Empty list when DB is unavailable."""
        if not self._db_available:
            return []
        brand_id = self._get_brand_id(brand_slug)
        if not brand_id:
            return []
        try:
            entries = self._db.get_narrative(brand_id, n=n)
            self.log(f"[narrative] read {len(entries)} entries")
            return entries
        except Exception as e:
            self.log(f"[narrative] read failed: {e}")
            return []

    def narrative_read_as_text(self, brand_slug: str, n: int = 20) -> str:
        """Format the story-so-far for injection into a system prompt."""
        entries = self.narrative_read(brand_slug, n=n)
        if not entries:
            return ""
        lines = [
            f"- [{(e.get('ts') or '')[:10]}] {e.get('agent','?')} · "
            f"{e.get('entry_type','?')}: {e.get('summary','')}"
            for e in entries
        ]
        return (
            "\n## Story So Far (recent decisions, actions & results — continue, don't restart)\n"
            + "\n".join(lines) + "\n"
        )

    def narrative_append(
        self,
        brand_slug: str,
        entry_type: str,
        summary: str,
        refs: dict | None = None,
    ) -> None:
        """Append one entry to the brand narrative.
        entry_type: 'decision' | 'action' | 'result'."""
        if not self._db_available:
            return
        brand_id = self._get_brand_id(brand_slug)
        if not brand_id:
            return
        try:
            self._db.append_narrative(
                brand_id, self._agent_slug(), entry_type, summary, refs=refs
            )
            self.log(f"[narrative] appended {entry_type}: {summary[:60]}")
        except Exception as e:
            self.log(f"[narrative] append failed: {e}")

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

    # ── memory persistence hooks ─────────────────────────────────────────────
    # Hook 0a from CLIENT_READY_BUILD_PLAN.md
    # SessionStart: load _state.json + recent learnings (~3KB vs 50-100KB)
    # PreCompact: save state before context compression
    # SessionEnd: persist learnings + update _state.json

    def session_start(self, brand_slug: str) -> dict:
        """Load compact brand context + recent learnings. Call at agent boot.

        Returns a dict with 'state' (compact brand summary) and 'learnings'
        (formatted text block). Agents inject these into their system prompt
        instead of loading 7+ full JSON files.
        """
        from agents._state import load_brand_state
        from agents._learnings import render_recent_for_prompt

        state = load_brand_state(brand_slug)
        learnings = render_recent_for_prompt(
            brand_slug, n=8, agent_filter=self._agent_slug()
        )
        narrative = self.narrative_read_as_text(brand_slug, n=20)
        self._session_context = {
            "state": state,
            "learnings": learnings,
            "narrative": narrative,
            "brand_slug": brand_slug,
        }
        self._session_start_time = time.time()
        self.log(
            f"[session] loaded compact state + {len(learnings)} chars learnings "
            f"+ {len(narrative)} chars narrative"
        )
        return self._session_context

    def session_save(self, brand_slug: str) -> None:
        """Save current brand state to disk. Call before context compression
        or any long pause to avoid re-deriving state."""
        from agents._state import write_brand_state
        write_brand_state(brand_slug)
        self.log("[session] state snapshot saved")

    def session_end(
        self,
        brand_slug: str,
        learnings: list[str] | None = None,
        narrative_summary: str | None = None,
        narrative_type: str = "result",
        narrative_refs: dict | None = None,
    ) -> None:
        """Persist session learnings + refresh _state.json. Call at agent completion.

        learnings: list of plain-text insight strings to persist.
        narrative_summary: one-line summary of what this run did/decided/produced,
            appended to the brand narrative so the next run continues the story.
        narrative_type: 'decision' | 'action' | 'result' (default 'result').
        """
        from agents._state import write_brand_state
        from agents._learnings import append as append_learning

        if learnings:
            slug = self._agent_slug()
            for text in learnings:
                append_learning(brand_slug, slug, text, kind="insight")
            self.log(f"[session] persisted {len(learnings)} learnings")

        if narrative_summary:
            self.narrative_append(
                brand_slug, narrative_type, narrative_summary, refs=narrative_refs
            )

        write_brand_state(brand_slug)
        elapsed = time.time() - self._session_start_time
        self.log(f"[session] ended ({elapsed:.0f}s)")

    # ── skill learning loop ────────────────────────────────────────────────────

    def _skills_dir(self, brand_slug: str) -> Path:
        return Path(f"brands/{brand_slug}/skills/{self._agent_slug()}")

    def load_skills(self, brand_slug: str, max_tokens: int = 3000) -> str:
        """Load skill metadata for this agent+brand. Returns formatted text
        for injection into the system prompt. Stays under max_tokens chars."""
        skills_dir = self._skills_dir(brand_slug)
        if not skills_dir.exists():
            return ""

        skills = []
        total_chars = 0
        for f in sorted(skills_dir.glob("*.md")):
            content = f.read_text(encoding="utf-8").strip()
            if total_chars + len(content) > max_tokens:
                break
            skills.append(content)
            total_chars += len(content)

        if not skills:
            return ""

        self.log(f"[skills] loaded {len(skills)} skills ({total_chars} chars)")
        return "\n## Learned Skills\n" + "\n---\n".join(skills) + "\n"

    def save_skill(
        self,
        brand_slug: str,
        skill_name: str,
        content: str,
        tags: list[str] | None = None,
        version: int = 1,
    ) -> Path:
        """Save or update a skill file."""
        import re

        skills_dir = self._skills_dir(brand_slug)
        skills_dir.mkdir(parents=True, exist_ok=True)

        slug = re.sub(r"[^a-z0-9-]", "", skill_name.lower().replace(" ", "-"))
        path = skills_dir / f"{slug}.md"

        tag_str = ", ".join(tags) if tags else ""
        frontmatter = (
            f"---\n"
            f"name: {skill_name}\n"
            f"version: {version}\n"
            f"tags: [{tag_str}]\n"
            f"updated: {datetime.now().isoformat()}\n"
            f"---\n\n"
        )

        path.write_text(frontmatter + content, encoding="utf-8")
        self.log(f"[skills] saved: {slug} (v{version})")
        return path

    def patch_skill(
        self,
        brand_slug: str,
        skill_name: str,
        lesson: str,
    ) -> bool:
        """Append a lesson learned to an existing skill file.
        Returns True if skill was found and patched."""
        import re

        slug = re.sub(r"[^a-z0-9-]", "", skill_name.lower().replace(" ", "-"))
        path = self._skills_dir(brand_slug) / f"{slug}.md"
        if not path.exists():
            return False

        content = path.read_text(encoding="utf-8")
        patch = f"\n\n### Lesson ({datetime.now().strftime('%Y-%m-%d')})\n{lesson}\n"
        path.write_text(content + patch, encoding="utf-8")
        self.log(f"[skills] patched: {slug}")
        return True

    def extract_skill_on_approval(
        self,
        brand_slug: str,
        skill_name: str,
        pattern: str,
        tags: list[str] | None = None,
    ) -> Path:
        """Called when an output is approved — extract the working pattern as a skill."""
        return self.save_skill(brand_slug, skill_name, pattern, tags=tags)

    def patch_skill_on_rejection(
        self,
        brand_slug: str,
        skill_name: str,
        rejection_reason: str,
    ) -> bool:
        """Called when an output is rejected — patch the skill with the lesson."""
        return self.patch_skill(brand_slug, skill_name, f"REJECTED: {rejection_reason}")

    # ── program.md (experimentation guardrails) ──────────────────────────────

    def load_program(self) -> str:
        """Load this agent's program.md — defines experimentation boundaries.
        Returns empty string if no program.md exists."""
        path = Path(f"agents/programs/{self._agent_slug()}.md")
        if not path.exists():
            return ""
        content = path.read_text(encoding="utf-8").strip()
        self.log(f"[program] loaded ({len(content)} chars)")
        return "\n## Experimentation Program\n" + content + "\n"

    # ── file I/O ──────────────────────────────────────────────────────────────

    def _brand_dir(self) -> str:
        """Return brands/{slug}/ path using ACTIVE_BRAND env var.
        Falls back to data/ for backwards compatibility."""
        slug = os.getenv("ACTIVE_BRAND", "")
        if slug:
            brand_path = os.path.join(_PROJECT_ROOT, "brands", slug)
            if os.path.isdir(brand_path):
                return brand_path
        return os.path.join(_PROJECT_ROOT, "data")

    def load_brand_profile(self):
        path = os.path.join(self._brand_dir(), "brand_profile.json")
        with open(path, "r") as f:
            return json.load(f)

    def load_session_state(self):
        path = os.path.join(self._brand_dir(), "session_state.json")
        with open(path, "r") as f:
            return json.load(f)

    def load_competitors(self):
        path = os.path.join(self._brand_dir(), "competitors_db.json")
        with open(path, "r") as f:
            return json.load(f)

    def load_trends(self):
        path = os.path.join(self._brand_dir(), "trends_live.json")
        with open(path, "r") as f:
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
        path = os.path.join(self._brand_dir(), "session_state.json")
        with open(path, "w") as f:
            json.dump(state, f, indent=2)

    def log(self, message):
        timestamp = datetime.now().strftime("%H:%M:%S")
        print(f"[{timestamp}] [{self.agent_name.upper()}] {message}")
