"""
Content Planner — OffGrid Marketing OS
Agent ID: 2 | Sequence position: 3 (runs after strategy-agent is approved)
Model: claude-sonnet-4-6 (Phase D: floor)
Rule 1: Zero assumptions. Reads real strategy + trend data only.
Rule 9: AutoResearch Loop — Education / Social Proof / Curiosity variants.
Reads:  brands/{slug}/strategy_90day.json + trends_live.json + brand_profile.json
Writes: brands/{slug}/content_calendar.json + pending_approval/ + Notion
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

# Rule 10 — Source Citation Enforcement
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from agents._lib._provenance import (
    build_source_index,
    validate_citations,
    build_violation_message,
    MAX_RERUN_ATTEMPTS,
)

load_dotenv(override=True)

ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "").strip()
# Phase D — model sourced from the single-source-of-truth gateway
try:
    from agents._lib.model_gateway import model_for
    from agents._lib._untrusted import wrap as _untrusted_wrap, UNTRUSTED_POLICY as _UNTRUSTED_POLICY
except ImportError:
    from agents._lib.model_gateway import model_for
    from agents._lib._untrusted import wrap as _untrusted_wrap, UNTRUSTED_POLICY as _UNTRUSTED_POLICY
MODEL = model_for("content-planner")
BRAND_SLUG = os.getenv("ACTIVE_BRAND", "offgrid-creatives-ai")


def _escape_literal_newlines_in_strings(json_str: str) -> str:
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


def _extract_first_json_object(raw: str) -> str:
    """Find the first balanced { ... } block. Strips any trailing prose Claude appended."""
    start = raw.find("{")
    if start < 0:
        return raw
    depth = 0
    in_string = False
    escape = False
    for i in range(start, len(raw)):
        c = raw[i]
        if escape:
            escape = False
            continue
        if c == "\\" and in_string:
            escape = True
            continue
        if c == '"':
            in_string = not in_string
            continue
        if in_string:
            continue
        if c == "{":
            depth += 1
        elif c == "}":
            depth -= 1
            if depth == 0:
                return raw[start:i + 1]
    return raw[start:]


def _safe_json_loads(raw: str):
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        pass
    try:
        return json.loads(_escape_literal_newlines_in_strings(raw))
    except json.JSONDecodeError:
        pass
    extracted = _extract_first_json_object(raw)
    try:
        return json.loads(extracted)
    except json.JSONDecodeError:
        return json.loads(_escape_literal_newlines_in_strings(extracted))


class ContentPlanner:

    def __init__(self, brand_slug: str = BRAND_SLUG):
        self.brand_slug = brand_slug
        self.log("Initialising Content Planner...")

        self.ceo = CEOBrain()
        self.brand_profile = self.ceo.brand_profile

        if not ANTHROPIC_API_KEY:
            raise ValueError("ANTHROPIC_API_KEY not found in .env")
        self.client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

        self.brands_dir = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "brands", self.brand_slug
        )
        self.log(f"Ready. Brand: {self.brand_profile.get('brand_name', 'Unknown')}")
        self._total_input_tokens = 0
        self._total_output_tokens = 0

    def log(self, message: str):
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        print(f"[Content Planner | {timestamp}] {message}")

    def load_file(self, filename: str, label: str) -> dict:
        """Load a JSON file from brand directory. Raises FileNotFoundError if missing."""
        path = os.path.join(self.brands_dir, filename)
        if not os.path.exists(path):
            agent_name = filename.replace(".json", "")
            raise FileNotFoundError(
                f"{filename} not found at {path}. Ensure {agent_name} agent ran and was approved."
            )
        with open(path, "r") as f:
            data = json.load(f)
        self.log(f"Loaded {label}")
        return data

    def save_calendar(self, calendar: dict):
        """Write content_calendar.json to brand directory for downstream agents."""
        path = os.path.join(self.brands_dir, "content_calendar.json")
        with open(path, "w") as f:
            json.dump(calendar, f, indent=2)
        self.log(f"content_calendar.json saved → {path}")

    def run_autoresearch_loop(self, strategy: dict, trends: dict) -> dict:
        """
        Rule 9 — AutoResearch Loop.
        Three variants:
          Variant A — Education-heavy calendar
          Variant B — Social proof-heavy calendar
          Variant C — Curiosity/hook-heavy calendar
        Metric: better = which calendar maximises saves + DM inquiries in 30 days
        """
        self.log("Running AutoResearch Loop — 3 calendar variants...")

        brand_ctx = json.dumps({
            "brand_name": self.brand_profile.get("brand_name"),
            "product": self.brand_profile.get("product"),
            "founder_identity": self.brand_profile.get("founder_identity"),
            "unique_tension": self.brand_profile.get("unique_tension"),
            "back_end_weapons": self.brand_profile.get("back_end_weapons"),
            "target_audience": self.brand_profile.get("target_audience"),
            "audience_primary": self.brand_profile.get("audience_primary"),
            "not_for_audience": self.brand_profile.get("not_for_audience"),
            "platforms": self.brand_profile.get("platforms"),
            "primary_platform_phase_1": self.brand_profile.get("primary_platform_phase_1"),
            "youtube_format": self.brand_profile.get("youtube_format"),
            "weekly_volume_target": self.brand_profile.get("weekly_volume_target"),
            "tone": self.brand_profile.get("tone_of_voice") or self.brand_profile.get("tone"),
            "bottlenecks": self.brand_profile.get("bottlenecks"),
            "phase": self.brand_profile.get("phase"),
            "what_to_never_say": self.brand_profile.get("what_to_never_say"),
            "lived_history_sources": self.brand_profile.get("lived_history_sources"),
            "lived_history_NOT_allowed": self.brand_profile.get("lived_history_NOT_allowed"),
            "grid_control_naming_rule": self.brand_profile.get("grid_control_naming_rule"),
            "hire_signal_rule": self.brand_profile.get("hire_signal_rule"),
            "freebie_strategy": self.brand_profile.get("freebie_strategy"),
            "week_1_cta_rule": self.brand_profile.get("week_1_cta_rule"),
            "north_star_metric": self.brand_profile.get("north_star_metric"),
            "north_star_metric_definition": self.brand_profile.get("north_star_metric_definition"),
            "deprecated_metrics": self.brand_profile.get("deprecated_metrics"),
        }, indent=2)

        strategy_summary = json.dumps(strategy, indent=2)
        if len(strategy_summary) > 4000:
            strategy_summary = strategy_summary[:4000] + "\n... [truncated]"

        trends_summary = json.dumps(trends, indent=2)
        if len(trends_summary) > 4000:
            trends_summary = trends_summary[:4000] + "\n... [truncated]"
        # LAW: trends_live.json carries raw scraped captions/comments → wrap DATA-not-instruction
        trends_summary = _untrusted_wrap("scraped_trend_data", trends_summary)

        import datetime as _dt
        now_iso = _dt.datetime.now(_dt.timezone.utc).isoformat()

        # ── Rule 10: Build source index ─────────────────────────────────────
        project_root = Path(__file__).resolve().parent.parent
        source_files = [
            project_root / "brands" / self.brand_slug / "trends_live.json",
            project_root / "brands" / self.brand_slug / "strategy_90day.json",
            project_root / "brands" / self.brand_slug / "brand_profile.json",
        ]
        source_index = build_source_index(source_files)
        self.log(f"Rule 10: Source index built — {len(source_index)} citable keys across {len(source_files)} files")

        from agents._lib._agent_framework import operating_framework as _operating_framework
        prompt = _operating_framework(2) + f"""
You are the Content Planner for OffGrid Marketing OS.
Your job: produce a 30-day content calendar based on the approved 90-day strategy and real trend data.
Every piece must be specific — platform, format, topic, hook angle, CTA.

{_UNTRUSTED_POLICY}

BRAND CONTEXT:
{brand_ctx}

APPROVED 90-DAY STRATEGY (Phase 1 focus — Days 1-30):
{strategy_summary}

REAL TREND DATA:
{trends_summary}

---

Run the AutoResearch Loop. Evaluate 3 calendar variants:

VARIANT A — EDUCATION-HEAVY CALENDAR
Majority of posts teach the audience something valuable.
"How to read competitor ads", "Why most D2C brands waste ad spend", etc.
Builds authority. Slower to convert but positions OffGrid as the expert.

VARIANT B — SOCIAL PROOF-HEAVY CALENDAR
Majority of posts show results, behind-the-scenes, process transparency.
Client stories, live demos, report screenshots (anonymised).
Faster trust for warm leads but requires existing proof to show.

VARIANT C — CURIOSITY/HOOK-HEAVY CALENDAR
Majority of posts use pattern interrupts, contrarian takes, bold claims.
"Your competitors know what you're spending. You don't know what they're spending."
High reach potential. Drives saves and shares. Works even with zero social proof.

SELECTION METRIC:
better = which calendar maximises QUALIFIED FOUNDER DMs PER WEEK (the brand's north_star_metric)
in the first 30 days, for a brand with no existing audience and no social proof.
DO NOT optimize for follower-count benchmarks (deprecated metric per brand_profile.deprecated_metrics).

Select the winner. One-line reason.

---

🚨 HARD CONTENT CALENDAR CONSTRAINTS (read brand_profile, violations = REJECTED):

PLATFORM + VOLUME:
- PRIMARY platforms: Instagram + YouTube. NOT LinkedIn-primary. (See brand_profile.primary_platform_phase_1.)
- Volume per week: 1 long-form YouTube (10-15 min) → cut into 4 IG Reels + 2 YouTube Shorts. PLUS 3 IG carousels (independent). TOTAL ~9 published units/week. (See brand_profile.weekly_volume_target.)
- Do NOT plan more than ~9-12 units/week in Week 1. Less is better. Quality > volume.
- LinkedIn + Twitter = repurpose-only from primary content. Don't plan original LinkedIn-first content.

CTA RULES BY WEEK:
- Week 1: NO comment-gated CTAs ("comment WORD"), NO promised deliverables. Only OPEN-LOOP DIAGNOSTIC engagement: "drop your AI tool stack", "what's your AI question". (See brand_profile.week_1_cta_rule.)
- Week 2-4: Same as Week 1 by default. Freebie CTAs allowed ONLY IF brand_profile.freebie_strategy.first_freebie_built becomes true AND dm_automation_required.status becomes BUILT.
- Week 5+: Freebie CTAs allowed. Grid Control nameable as proof point.
- NEVER plan hire-me CTAs at any week. Banned forever per brand_profile.hire_signal_rule.

LIVED-HISTORY + NAMING RULES:
- NEVER name "Third Gen Tribe", "TGT", "T-shirt brand". Reference is "the brands I ran" (UNNAMED).
- NEVER frame TGT as AI-built — it was agency-run.
- Week 1-4: NEVER name "Grid Control". Reference as "a multi-agent system I'm building" / "the back-end I'm building".
- Week 5+: Grid Control nameable. Approved framing: "I'm building this brand using Grid Control — a multi-agent system I built with Claude as a non-coder."
- Use ONLY the lived-history sources in brand_profile.lived_history_sources.

NEVER-USE WORDS (from brand_profile.what_to_never_say):
- AI buzzwords: leverage, synergize, ecosystem, cutting-edge, next-gen, delve, foster, moreover, 10x, unlock, transform, revolutionize, game-changer, paradigm shift, master AI in 7 days

---

⚠️ RULE 10 — SOURCE CITATION ENFORCEMENT (HARD REQUIREMENT) ⚠️

Every post topic, hook angle, content pillar, and trend_angle_used in your output
MUST trace back to a specific source data point in trends_live.json,
strategy_90day.json, or brand_profile.json.

For every post in your calendar, add an entry to "data_provenance" with:
  - "claim": the post topic OR hook OR content_pillar text
  - "source_file": one of: "trends_live.json" | "strategy_90day.json" | "brand_profile.json"
  - "source_path": dot.notation path INTO that file
  - "source_value": verbatim 30–60 char snippet (HARD CAP 60 chars)

If you cannot cite a source for a post idea, REMOVE THE POST. Do not invent.
Validation requires ≥30% token-overlap between claim and source_value.

Aim for 10–14 provenance entries TOTAL (one per content_pillar + trend_angle + strategic angle).
You do NOT need a provenance entry per individual post.

OUTPUT VERBOSITY LIMITS (strict — calendar will not fit token budget otherwise):
- caption_direction: ≤120 chars
- hook: ≤80 chars
- topic: ≤80 chars
- production_notes: ≤100 chars
- WEEK 1 ONLY at full detail. Weeks 2-4: minimal stub posts (day, platform, format, topic only).

---

OUTPUT: Return valid JSON only. No markdown. No commentary outside the JSON.
Generate a full 30-day calendar with specific posts — not placeholders.
Each post must have: week, day, platform, format, topic, hook, caption_direction, cta, content_pillar.

{{
  "loop_header": {{
    "agent": "Content Planner",
    "output_type": "30-Day Content Calendar",
    "goal": "Maximise saves and DM inquiries in first 30 days with zero existing audience",
    "metric": "better = higher saves + DM inquiries than alternative calendar approaches",
    "variants_tested": 3,
    "winner": "Variant [A/B/C] — [one line reason]"
  }},
  "data_provenance": [
    {{
      "claim": "example: Day 3 hook — 'You don't have an AI tool problem. You have a strategy problem'",
      "source_file": "trends_live.json",
      "source_path": "content_angles_to_pursue[6].angle",
      "source_value": "verbatim text from that source field, ≥30 chars"
    }}
  ],
  "winning_variant": "A",
  "content_calendar": {{
    "created_at": "{now_iso}",
    "brand": "{self.brand_slug}",
    "calendar_angle": "",
    "posting_frequency": {{}},
    "content_pillars": [],
    "week_1": {{
      "theme": "",
      "posts": [
        {{
          "day": 1,
          "platform": "Instagram|LinkedIn",
          "format": "Reel|Carousel|Static|Text Post",
          "topic": "",
          "hook": "",
          "caption_direction": "",
          "cta": "",
          "content_pillar": "",
          "trend_angle_used": ""
        }}
      ]
    }},
    "week_2": {{
      "theme": "",
      "posts": []
    }},
    "week_3": {{
      "theme": "",
      "posts": []
    }},
    "week_4": {{
      "theme": "",
      "posts": []
    }},
    "posting_rules": [],
    "what_not_to_post": []
  }}
}}"""

        # ── Rule 10: Claude call + validation-retry loop ────────────────────
        messages = [{"role": "user", "content": self.ceo.story_so_far_block() + prompt}]
        result = None
        validation_report = None
        attempt = 0
        max_attempts = MAX_RERUN_ATTEMPTS + 1

        while attempt < max_attempts:
            attempt += 1
            self.log(f"Calling Claude {MODEL} (attempt {attempt}/{max_attempts}) — streaming mode...")
            # SDK 0.96+ requires streaming for large max_tokens. Bumped 21000 -> 24000 now that
            # streaming is enabled — gives provenance + retry headroom for full 30-day calendars.
            raw_text = ""
            with self.client.messages.stream(
                model=MODEL,
                max_tokens=24000,
                messages=messages,
            ) as stream:
                for text_chunk in stream.text_stream:
                    raw_text += text_chunk
                final_message = stream.get_final_message()

            self._total_input_tokens += final_message.usage.input_tokens
            self._total_output_tokens += final_message.usage.output_tokens

            if final_message.stop_reason == "max_tokens":
                self.log(f"WARNING: Claude hit max_tokens cap ({final_message.usage.output_tokens} out)")

            raw = raw_text.strip()
            if "```" in raw:
                for part in raw.split("```"):
                    part = part.strip()
                    if part.startswith("json"):
                        part = part[4:].strip()
                    if part.startswith("{"):
                        raw = part
                        break

            result = _safe_json_loads(raw)

            # Rule 10 validation
            is_valid, missing, validation_report = validate_citations(result, source_index)
            self.log(
                f"Rule 10 validation (attempt {attempt}): {validation_report['claims_validated']}/"
                f"{validation_report['claims_total']} claims passed. is_valid={is_valid}"
            )

            if is_valid:
                break

            if attempt >= max_attempts:
                self.log(f"FINAL ATTEMPT FAILED — saving with provenance_validation_failed=true")
                break

            violation_msg = build_violation_message(missing)
            self.log(f"Re-prompting Claude with {len(missing)} citation violations...")
            messages.append({"role": "assistant", "content": json.dumps(result)})
            messages.append({"role": "user", "content": (
                f"Your previous output failed Rule 10 source-citation validation.\n\n"
                f"{violation_msg}\n\n"
                f"Re-emit the COMPLETE corrected JSON with EITHER fixed citations OR "
                f"the offending claims/posts removed. Do not add new claims you can't cite. "
                f"Return strict JSON only."
            )})

        if result is not None:
            result["provenance_validation"] = validation_report

        self.log(f"AutoResearch Loop complete. Winner: {result['loop_header']['winner']}")
        return result

    def run(self):
        self.log("=" * 60)
        self.log("CONTENT PLANNER — 30-DAY CALENDAR STARTING")
        self.log("=" * 60)

        # Step 1 — Load approved data files (Rule 1 gate)
        self.log("STEP 1 — Loading strategy and trend data...")
        try:
            strategy = self.load_file("strategy_90day.json", "90-Day Strategy")
            trends = self.load_file("trends_live.json", "Trend Data")
        except FileNotFoundError as e:
            self.log(f"HALT — {e}")
            return None

        # Step 2 — AutoResearch Loop
        self.log("STEP 2 — AutoResearch Loop (3 variants)...")
        loop_result = self.run_autoresearch_loop(strategy, trends)
        calendar = loop_result["content_calendar"]
        loop_header = loop_result["loop_header"]

        # Rule 10 — inject data_provenance + provenance_validation INTO calendar
        # so Script Writer (downstream) + humans can audit citations
        calendar["data_provenance"] = loop_result.get("data_provenance", [])
        calendar["provenance_validation"] = loop_result.get("provenance_validation", {})

        # Step 3 — Save content_calendar.json for Script Writer
        self.log("STEP 3 — Saving content_calendar.json...")
        self.save_calendar(calendar)

        # Step 4 — Push to pending_approval + Notion via CEO Brain
        self.log("STEP 4 — Pushing to pending_approval/ and Notion...")
        save_result = self.ceo.save_agent_output(
            agent_name="Content Planner",
            output_type="30-Day Content Calendar",
            loop_header={
                "goal": loop_header["goal"],
                "metric": loop_header["metric"],
                "variants_tested": loop_header["variants_tested"],
                "winner": loop_header["winner"]
            },
            content=json.dumps(calendar, indent=2),
            filename="content_calendar.json"
        )

        if save_result["notion_result"]["success"]:
            self.log(f"Notion card: {save_result['notion_result']['notion_url']}")

        # Step 5 — Mark complete
        self.log("STEP 5 — Marking content-planner complete...")
        self.ceo.mark_agent_complete("content-planner")

        self.log("=" * 60)
        self.log("CONTENT PLANNER — COMPLETE")
        self.log(f"Winner: {loop_result['winning_variant']} — {loop_header['winner']}")
        self.log("Pending approval in Notion. Approve to unlock: script-writer")
        self.log("=" * 60)
        cost_reporter.record(MODEL, self._total_input_tokens, self._total_output_tokens)
        return save_result


if __name__ == "__main__":
    agent = ContentPlanner()
    agent.run()
