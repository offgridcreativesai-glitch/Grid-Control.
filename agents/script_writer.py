"""
Script Writer — OffGrid Marketing OS
Agent ID: 3 | Sequence position: 4 (runs after content-planner is approved)
Model: claude-sonnet-4-6
Rule 1: Zero assumptions. Reads real calendar + trend data only.
Rule 9: AutoResearch Loop — Pain-first / Result-first / Curiosity variants per piece.
Reads:  brands/{slug}/content_calendar.json + trends_live.json + brand_profile.json
Writes: pending_approval/ only (scripts are not shared between agents)
Pushes: Notion via CEO Brain save_agent_output()
Flags:  when human face or voice is required for a piece
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
import cost_reporter
# Rule 10 — Source Citation Enforcement
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _provenance import (
    build_source_index,
    validate_citations,
    build_violation_message,
    MAX_RERUN_ATTEMPTS,
)

load_dotenv(override=True)

ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "").strip()
MODEL = "claude-sonnet-4-6"
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


class ScriptWriter:

    def __init__(self, brand_slug: str = BRAND_SLUG):
        self.brand_slug = brand_slug
        self.log("Initialising Script Writer...")

        self.ceo = CEOBrain()
        self.brand_profile = self.ceo.brand_profile

        if not ANTHROPIC_API_KEY:
            raise ValueError("ANTHROPIC_API_KEY not found in .env")
        self.client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

        self.brands_dir = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "brands", self.brand_slug
        )
        self.voice_profile = None
        self.winning_hooks: list = []   # BUILD C — top hook patterns from past performance
        self.dead_hooks: list    = []   # BUILD C — hook patterns that historically flopped
        self.log(f"Ready. Brand: {self.brand_profile.get('brand_name', 'Unknown')}")
        self._load_voice_profile()
        self._load_performance_history()
        self._total_input_tokens = 0
        self._total_output_tokens = 0

    def log(self, message: str):
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        print(f"[Script Writer | {timestamp}] {message}")

    def _load_voice_profile(self):
        """Load voice_profile.json for this brand if it exists. Sets self.voice_profile."""
        vp_path = os.path.join(self.brands_dir, "voice_profile.json")
        if os.path.exists(vp_path):
            try:
                with open(vp_path) as f:
                    self.voice_profile = json.load(f)
                self.log("Voice profile loaded.")
            except Exception as e:
                self.log(f"WARNING: Could not load voice_profile.json — {e}")
                self.voice_profile = None
        else:
            self.voice_profile = None

    def _load_performance_history(self):
        """
        BUILD C — Load winning + dead hook patterns from performance_history.json.
        Pure deterministic. If file doesn't exist (first run on brand), both lists stay empty.
        Sets:
          self.winning_hooks: list of {value, median_score, post_count} for top hook patterns
          self.dead_hooks:    list of {value, median_score, reason} for flopped hook patterns
        """
        ph_path = os.path.join(self.brands_dir, "performance_history.json")
        if not os.path.exists(ph_path):
            self.log("Performance history: not found (first run on brand) — no hook bias applied")
            return
        try:
            with open(ph_path) as f:
                history = json.load(f)
            wp = history.get("winning_patterns", {}) or {}
            self.winning_hooks = wp.get("hook_patterns_top_3", []) or []
            dead = history.get("dead_patterns", []) or []
            self.dead_hooks = [d for d in dead if d.get("category") == "hook_pattern"]
            self.log(f"Performance history loaded: {len(self.winning_hooks)} winning hook patterns, {len(self.dead_hooks)} dead patterns")
        except Exception as e:
            self.log(f"WARNING: Could not load performance_history.json — {e}")

    def load_file(self, filename: str, label: str) -> dict:
        path = os.path.join(self.brands_dir, filename)
        if not os.path.exists(path):
            raise FileNotFoundError(
                f"{label} not found at {path}. "
                f"Ensure upstream agents ran and were approved."
            )
        with open(path, "r") as f:
            data = json.load(f)
        self.log(f"Loaded {label}")
        return data

    def run_autoresearch_loop_for_post(
        self,
        post: dict,
        trends: dict,
        week_theme: str,
        source_index: dict | None = None,
    ) -> dict:
        """
        Rule 9 — AutoResearch Loop per content piece.
        Three variants:
          Variant A — Hook angle (pain-first)
          Variant B — Result angle (outcome-first)
          Variant C — Curiosity angle (pattern interrupt)
        Metric: better = highest predicted save rate + DM inquiry rate for this post
        """
        brand_ctx = {
            "brand_name": self.brand_profile.get("brand_name"),
            "product": self.brand_profile.get("product"),
            "product_description": self.brand_profile.get("product_description"),
            "target_audience": self.brand_profile.get("target_audience"),
            "tone": self.brand_profile.get("tone"),
            "platforms": self.brand_profile.get("platforms")
        }

        # Pull relevant trend signals for this post
        trend_signals = ""
        instagram_trends = trends.get("instagram_trends", {})
        if isinstance(instagram_trends, dict):
            top_hooks = instagram_trends.get("top_hooks", [])
            if top_hooks:
                trend_signals = f"Top performing hooks this week: {json.dumps(top_hooks[:3])}"

        # Build voice DNA injection block if profile exists
        voice_dna_block = ""
        if self.voice_profile:
            voice_dna_block = f"""
BRAND VOICE DNA (read and match exactly):
{json.dumps(self.voice_profile, indent=2)}

Match sentence_length, energy, and hinglish_pattern exactly.
Never use any word in vocabulary.never_use.
"""

        # BUILD C — Performance feedback block (winning + dead hook patterns)
        perf_feedback_block = ""
        if self.winning_hooks or self.dead_hooks:
            winning_lines = []
            for w in self.winning_hooks:
                winning_lines.append(f"  - '{w.get('value','')}' (median performance score: {w.get('median_score', 0)} across {w.get('post_count', 0)} past posts)")
            dead_lines = []
            for d in self.dead_hooks:
                dead_lines.append(f"  - '{d.get('value','')}' — {d.get('reason', 'historically underperformed')}")

            perf_feedback_block = f"""
PERFORMANCE FEEDBACK FROM YOUR REAL PUBLISHED CONTENT (computed by Performance Tracker — pure math, no AI judgment):

WINNING HOOK PATTERNS (proven to work for THIS brand's audience — STRONGLY PREFER these):
{chr(10).join(winning_lines) if winning_lines else "  (no proven winners yet — first weeks of data)"}

DEAD HOOK PATTERNS (historically flopped for THIS brand — DO NOT use unless you have a specific reason):
{chr(10).join(dead_lines) if dead_lines else "  (none flagged dead yet)"}

Apply +15% confidence boost to any hook that matches a WINNING pattern.
Apply -20% confidence penalty to any hook that matches a DEAD pattern.
"""


        prompt = f"""You are the Script Writer for OffGrid Marketing OS.
Write a complete script for one content piece using the BEAT structure.
Check brand voice. Flag if human face or voice is required.

BRAND CONTEXT:
{json.dumps(brand_ctx, indent=2)}
{voice_dna_block}
{perf_feedback_block}
CONTENT PIECE TO SCRIPT:
{json.dumps(post, indent=2)}

WEEK THEME: {week_theme}

TREND SIGNALS:
{trend_signals if trend_signals else "No specific trend signals for this piece."}

---

Run the AutoResearch Loop. Write 3 hook/script variants:

VARIANT A — PAIN-FIRST HOOK
Open with the specific pain the audience feels right now.
Make them feel seen. Then present the solution.

VARIANT B — RESULT-FIRST HOOK
Open with the outcome/transformation. Lead with the win.
Then explain how to get there.

VARIANT C — CURIOSITY/PATTERN INTERRUPT
Open with something unexpected, contrarian, or counterintuitive.
Disrupts the scroll. Creates a gap the reader needs to close.

SELECTION METRIC:
better = highest predicted save rate + DM inquiry rate for this specific post

Select the winner. One-line reason.

HOOK GENERATOR — generate 5 hooks. Pick the 5 BEST-FIT patterns from this expanded list of 12
(adapted from Seedance 2.0 viral hook framework — proven for short-form retention curves):

VISUAL/COGNITIVE INTERRUPTS (work for text + video):
1. Pattern Interrupt — violates an expected pattern in the niche ("Stop using ChatGPT for [X]")
2. Curiosity Gap — opens a question the brain MUST close ("The one AI mistake that's killing your launch")
3. Contrast Principle — sets up A then immediately reveals NOT-A ("Everyone says AI replaces humans. The truth is opposite.")
4. Impossible Claim — states something that sounds like it can't be true ("I built this whole funnel in 11 minutes")

EMOTIONAL TRIGGERS:
5. Pain Point — calls out the exact frustration they feel right now ("Tired of AI tools that promise magic and deliver chaos?")
6. Aspirational — paints the dream outcome ("Imagine your content engine running while you sleep")
7. Fear/Loss — names what they're already losing by NOT acting ("If you're not using AI for [X] yet, you're already 6 months behind")
8. Identity — speaks to who they want to be ("This is what serious founders do at 4am")

AUTHORITY/PROOF:
9. Exclusivity — makes them feel like insiders ("This is what I tell my private clients first")
10. Time/Money Claim — quantifies a specific result ("How I cut my agency hiring cost by 70% in 30 days")
11. Specificity — drops one weirdly specific number/detail that signals real experience ("After running 47 AI experiments, only 3 patterns kept working")
12. Contrarian Truth — argues against the popular take ("AI strategy is not the bottleneck. Decision speed is.")

For each hook: score it out of 10 using this formula:
- Pattern match with top_hooks from trend data (40%)
- Competitor format alignment (35%)
- Brand tone fit (25%)
- Bonus +1 for hooks that work in the FIRST 2 SECONDS of a Reel (scroll-stop power)

IMPORTANT RULES:
- Scripts MUST use the BEAT structure (beat_1 → beat_2 → beat_3 → cta)
- Each beat: 2-3 sentences. Purpose: setup | core idea/proof | payoff/twist
- The hook lives ONLY in hook_block.recommended_hook. Do NOT put a hook inside the script object.
- beat_1 sets up the tension or context
- beat_2 delivers the core idea or proof point
- beat_3 is the payoff, twist, or emotional close
- cta must always be a comment trigger (e.g. "Comment 'AD' and I'll send you the breakdown")
- script object must have ONLY keys: beat_1, beat_2, beat_3, cta, platform, format, topic, caption, hashtags, production_notes
- If this piece requires a human face on camera, flag it clearly
- Caption must end with a specific CTA (not generic "follow for more")

---

⚠️ RULE 10 — SOURCE CITATION ENFORCEMENT (HARD REQUIREMENT) ⚠️

Every hook, every script beat, every audience claim, every "they think" / "they want" /
"they pay X" must trace back to a real source data point in:
  - content_calendar.json (the post slot you're scripting)
  - trends_live.json (signals + competitor intel + content angles)
  - brand_profile.json (voice, audience, tone)

Add an entry to "data_provenance" for EVERY hook in hook_block AND for the script's
beat_2 (core idea/proof — must cite the source data point that justifies the proof claim).

Each provenance entry needs:
  - "claim": the hook text OR the script beat text it grounds
  - "source_file": one of content_calendar.json | trends_live.json | brand_profile.json
  - "source_path": dot.notation path
  - "source_value": verbatim ≥30-char snippet from the source

If you cannot cite a source for a hook or proof beat, you must REMOVE it. Do not invent
audience pain points or behaviors not in the brand_profile or trends data.
Validation will reject claims with <30% token-overlap with the cited source.

Aim for 6+ provenance entries (5 hooks + at least 1 for beat_2).

---

OUTPUT: Return valid JSON only. No markdown. No commentary outside the JSON.

{{
  "loop_header": {{
    "agent": "Script Writer",
    "output_type": "{post.get('format', 'Content')} Script",
    "goal": "Write the highest-converting script for this specific content piece",
    "metric": "better = higher predicted save rate + DM inquiry rate vs alternatives",
    "variants_tested": 3,
    "winner": "Variant [A/B/C] — [one line reason]"
  }},
  "data_provenance": [
    {{
      "claim": "example: hook 3 text — quotes a real audience pain from brand_profile",
      "source_file": "brand_profile.json",
      "source_path": "target_audience",
      "source_value": "verbatim ≥30 char text from that source"
    }}
  ],
  "winning_variant": "A",
  "requires_human_face": false,
  "requires_human_voice": false,
  "human_face_note": "",
  "hook_block": {{
    "recommended_hook": 3,
    "hooks": [
      {{"id": 1, "pattern": "Aspirational", "text": "", "pattern_description": "paints the dream outcome", "competitor_match": "", "confidence": 0.0}},
      {{"id": 2, "pattern": "Pain Point", "text": "", "pattern_description": "calls out the exact frustration", "competitor_match": "", "confidence": 0.0}},
      {{"id": 3, "pattern": "Exclusivity", "text": "", "pattern_description": "insider secret info angle", "competitor_match": "", "confidence": 0.0}},
      {{"id": 4, "pattern": "Time/Money Claim", "text": "", "pattern_description": "quantified time or money result", "competitor_match": "", "confidence": 0.0}},
      {{"id": 5, "pattern": "Curiosity Gap", "text": "", "pattern_description": "information gap they must close", "competitor_match": "", "confidence": 0.0}}
    ]
  }},
  "script": {{
    "platform": "{post.get('platform', '')}",
    "format": "{post.get('format', '')}",
    "topic": "{post.get('topic', '')}",
    "beat_1": {{"content": "", "purpose": "setup"}},
    "beat_2": {{"content": "", "purpose": "core idea/proof"}},
    "beat_3": {{"content": "", "purpose": "payoff/twist"}},
    "cta": "",
    "caption": "",
    "hashtags": [],
    "production_notes": ""
  }}
}}"""

        # ── Rule 10: Claude call + validation-retry loop ────────────────────
        messages = [{"role": "user", "content": prompt}]
        result = None
        validation_report = None
        attempt = 0
        max_attempts = MAX_RERUN_ATTEMPTS + 1 if source_index else 1

        while attempt < max_attempts:
            attempt += 1
            response = self.client.messages.create(
                model=MODEL,
                max_tokens=12000,  # bumped for provenance entries
                messages=messages,
            )
            self._total_input_tokens += response.usage.input_tokens
            self._total_output_tokens += response.usage.output_tokens

            raw = response.content[0].text.strip()
            if "```" in raw:
                for part in raw.split("```"):
                    part = part.strip()
                    if part.startswith("json"):
                        part = part[4:].strip()
                    if part.startswith("{"):
                        raw = part
                        break

            result = _safe_json_loads(raw)

            # Skip validation if no source_index provided (back-compat for direct calls)
            if not source_index:
                return result

            is_valid, missing, validation_report = validate_citations(result, source_index)
            self.log(
                f"Rule 10 validation (attempt {attempt}): {validation_report['claims_validated']}/"
                f"{validation_report['claims_total']} claims passed. is_valid={is_valid}"
            )

            if is_valid:
                break

            if attempt >= max_attempts:
                self.log(f"FINAL ATTEMPT FAILED — saving with provenance_validation_failed")
                break

            violation_msg = build_violation_message(missing)
            self.log(f"Re-prompting Claude with {len(missing)} citation violations...")
            messages.append({"role": "assistant", "content": json.dumps(result)})
            messages.append({"role": "user", "content": (
                f"Your previous output failed Rule 10 source-citation validation.\n\n"
                f"{violation_msg}\n\n"
                f"Re-emit the COMPLETE corrected JSON with EITHER fixed citations OR "
                f"the offending hooks/claims removed. Do not add new claims you can't cite. "
                f"Return strict JSON only."
            )})

        if result is not None:
            result["provenance_validation"] = validation_report

        return result

    def run(self, weeks_to_script: int = 1):
        """
        Script the content calendar.
        Default: scripts Week 1 only (approve before scripting Week 2).
        Set weeks_to_script=4 to script all 4 weeks in one run.
        """
        self.log("=" * 60)
        self.log(f"SCRIPT WRITER — SCRIPTING WEEK(S) 1-{weeks_to_script}")
        self.log("=" * 60)

        # Step 1 — Load approved data (Rule 1 gate)
        self.log("STEP 1 — Loading calendar and trend data...")
        try:
            calendar = self.load_file("content_calendar.json", "Content Calendar")
            trends = self.load_file("trends_live.json", "Trend Data")
        except FileNotFoundError as e:
            self.log(f"HALT — {e}")
            return None

        # ── Rule 10: Build source index ONCE for the whole run ─────────────
        project_root = Path(__file__).resolve().parent.parent
        source_files = [
            project_root / "brands" / self.brand_slug / "content_calendar.json",
            project_root / "brands" / self.brand_slug / "trends_live.json",
            project_root / "brands" / self.brand_slug / "brand_profile.json",
        ]
        source_index = build_source_index(source_files)
        self.log(f"Rule 10: Source index built — {len(source_index)} citable keys across {len(source_files)} files")

        all_scripts = []
        human_face_flags = []
        total_posts = 0
        scripted_posts = 0

        # Step 2 — Script each post in requested weeks
        for week_num in range(1, weeks_to_script + 1):
            week_key = f"week_{week_num}"
            week_data = calendar.get(week_key, {})
            if not week_data:
                self.log(f"Week {week_num} not found in calendar. Stopping.")
                break

            week_theme = week_data.get("theme", f"Week {week_num}")
            posts = week_data.get("posts", [])
            self.log(f"STEP 2.{week_num} — Scripting Week {week_num}: '{week_theme}' ({len(posts)} posts)...")

            week_scripts = []
            for i, post in enumerate(posts):
                total_posts += 1
                self.log(f"  [{i+1}/{len(posts)}] {post.get('platform')} {post.get('format')} — {post.get('topic', '')[:50]}")

                try:
                    result = self.run_autoresearch_loop_for_post(post, trends, week_theme, source_index=source_index)
                    result["original_post"] = post
                    result["week"] = week_num
                    result["week_theme"] = week_theme
                    week_scripts.append(result)
                    scripted_posts += 1

                    if result.get("requires_human_face") or result.get("requires_human_voice"):
                        flag = {
                            "week": week_num,
                            "day": post.get("day"),
                            "platform": post.get("platform"),
                            "format": post.get("format"),
                            "topic": post.get("topic"),
                            "note": result.get("human_face_note", "Human face/voice required")
                        }
                        human_face_flags.append(flag)
                        self.log(f"  ⚑ HUMAN REQUIRED: {flag['note']}")

                except Exception as e:
                    self.log(f"  ERROR scripting post {i+1}: {e}")
                    week_scripts.append({"error": str(e), "original_post": post})

            all_scripts.extend(week_scripts)

        self.log(f"Scripted {scripted_posts}/{total_posts} posts successfully")

        # Step 3 — Build full output bundle
        output_bundle = {
            "created_at": datetime.now(timezone.utc).isoformat(),
            "brand": self.brand_slug,
            "weeks_scripted": weeks_to_script,
            "total_posts_scripted": scripted_posts,
            "human_face_required_count": len(human_face_flags),
            "human_face_flags": human_face_flags,
            "scripts": all_scripts
        }

        # Build summary for Loop Header
        winner_summary = f"{scripted_posts} scripts produced via AutoResearch Loop (3 variants per piece)"
        if human_face_flags:
            winner_summary += f" | {len(human_face_flags)} pieces flagged requiring human face/voice"

        # Step 4 — Push to pending_approval + Notion via CEO Brain
        self.log("STEP 4 — Pushing to pending_approval/ and Notion...")
        save_result = self.ceo.save_agent_output(
            agent_name="Script Writer",
            output_type=f"Content Scripts — Week(s) 1-{weeks_to_script}",
            loop_header={
                "goal": f"Write highest-converting scripts for {scripted_posts} content pieces",
                "metric": "better = higher predicted save rate + DM inquiry rate per piece",
                "variants_tested": scripted_posts * 3,
                "winner": winner_summary
            },
            content=json.dumps(output_bundle, indent=2),
            filename=f"scripts_week1to{weeks_to_script}.json"
        )

        if save_result["notion_result"]["success"]:
            self.log(f"Notion card: {save_result['notion_result']['notion_url']}")

        # Step 5 — Mark complete
        self.log("STEP 5 — Marking script-writer complete...")
        self.ceo.mark_agent_complete("script-writer")

        # Step 6 — Surface human face flags clearly
        if human_face_flags:
            self.log("=" * 60)
            self.log(f"⚑ HUMAN FACE/VOICE REQUIRED FOR {len(human_face_flags)} PIECES:")
            for flag in human_face_flags:
                self.log(f"  Week {flag['week']} Day {flag['day']} | {flag['platform']} {flag['format']}: {flag['note']}")
            self.log("=" * 60)

        self.log("=" * 60)
        self.log("SCRIPT WRITER — COMPLETE")
        self.log(f"Scripts produced: {scripted_posts}")
        self.log(f"Human flags: {len(human_face_flags)}")
        self.log("Pending approval in Notion. Approve to unlock: creative-director")
        self.log("=" * 60)
        cost_reporter.record(MODEL, self._total_input_tokens, self._total_output_tokens)
        return save_result


if __name__ == "__main__":
    agent = ScriptWriter()
    agent.run(weeks_to_script=1)
