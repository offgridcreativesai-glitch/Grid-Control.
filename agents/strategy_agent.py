"""
Strategy Agent — OffGrid Marketing OS
Agent ID: 1 | Sequence position: 2 (runs after trend-researcher is approved)
Model: claude-opus-4-8 (Phase D)
Rule 1: Zero assumptions. Reads real trend data only.
Rule 9: AutoResearch Loop — Aggressive / Trust-first / Hybrid variants.
Reads:  brands/{slug}/trends_live.json + brand_profile.json
Writes: brands/{slug}/strategy_90day.json + pending_approval/ + Notion
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
from agents._lib._langfuse_client import get_langfuse
_LF = get_langfuse()  # Phase 1b · singleton; silent no-op when keys missing

# Rule 10 — Source Citation Enforcement (Apr 26)
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
MODEL = model_for("strategy-agent")
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
    # Try strict parse first
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        pass
    # Try after escaping literal newlines inside string values
    try:
        return json.loads(_escape_literal_newlines_in_strings(raw))
    except json.JSONDecodeError:
        pass
    # Last resort: extract first balanced JSON object (strips trailing prose)
    extracted = _extract_first_json_object(raw)
    try:
        return json.loads(extracted)
    except json.JSONDecodeError:
        return json.loads(_escape_literal_newlines_in_strings(extracted))


class StrategyAgent:

    def __init__(self, brand_slug: str = BRAND_SLUG):
        self.brand_slug = brand_slug
        self.log("Initialising Strategy Agent...")

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
        print(f"[Strategy Agent | {timestamp}] {message}")

    def load_trends(self) -> dict:
        """Load trends_live.json written by Trend Researcher."""
        path = os.path.join(self.brands_dir, "trends_live.json")
        if not os.path.exists(path):
            raise FileNotFoundError(
                f"trends_live.json not found at {path}. "
                "Run trend-researcher first and approve its output."
            )
        with open(path, "r") as f:
            data = json.load(f)
        self.log(f"Loaded trends_live.json (scraped at: {data.get('scraped_at', 'unknown')})")
        return data

    def save_strategy(self, strategy: dict):
        """Write strategy_90day.json to brand directory for downstream agents."""
        path = os.path.join(self.brands_dir, "strategy_90day.json")
        with open(path, "w") as f:
            json.dump(strategy, f, indent=2)
        self.log(f"strategy_90day.json saved → {path}")

    def run_autoresearch_loop(self, trends: dict) -> dict:
        """
        Rule 9 — AutoResearch Loop. Rule 10 — Source Citation Enforcement.

        Three variants:
          Variant A — Aggressive growth play
          Variant B — Trust-first slow burn
          Variant C — Hybrid with clear phase gates
        Metric: better = highest probability of first 10 paying clients in 90 days

        Rule 10 — Every claim/recommendation in the output JSON must trace back to a real
        source value via data_provenance. Validates after Claude returns. If validation fails,
        re-prompts up to MAX_RERUN_ATTEMPTS times with violations called out.
        """
        self.log("Running AutoResearch Loop — 3 strategy variants...")

        brand_ctx = json.dumps({
            "brand_name": self.brand_profile.get("brand_name"),
            "product": self.brand_profile.get("product"),
            "founder_identity": self.brand_profile.get("founder_identity"),
            "unique_tension": self.brand_profile.get("unique_tension"),
            "back_end_weapons": self.brand_profile.get("back_end_weapons"),
            "target_audience": self.brand_profile.get("target_audience"),
            "audience_primary": self.brand_profile.get("audience_primary"),
            "audience_secondary_1": self.brand_profile.get("audience_secondary_1"),
            "audience_secondary_2": self.brand_profile.get("audience_secondary_2"),
            "not_for_audience": self.brand_profile.get("not_for_audience"),
            "platforms": self.brand_profile.get("platforms"),
            "primary_platform_phase_1": self.brand_profile.get("primary_platform_phase_1"),
            "secondary_platform_phase_1": self.brand_profile.get("secondary_platform_phase_1"),
            "youtube_format": self.brand_profile.get("youtube_format"),
            "weekly_volume_target": self.brand_profile.get("weekly_volume_target"),
            "bottlenecks": self.brand_profile.get("bottlenecks"),
            "phase": self.brand_profile.get("phase"),
            "budget_phase": self.brand_profile.get("budget_phase"),
            "goal": self.brand_profile.get("90_day_target"),
            "price": self.brand_profile.get("price_india"),
            "tone": self.brand_profile.get("tone_of_voice"),
            "existing_pipeline": self.brand_profile.get("existing_pipeline"),
            "what_to_never_say": self.brand_profile.get("what_to_never_say"),
            "lived_history_sources": self.brand_profile.get("lived_history_sources"),
            "lived_history_NOT_allowed": self.brand_profile.get("lived_history_NOT_allowed"),
            "grid_control_naming_rule": self.brand_profile.get("grid_control_naming_rule"),
            "hire_signal_rule": self.brand_profile.get("hire_signal_rule"),
            "freebie_strategy": self.brand_profile.get("freebie_strategy"),
            "week_1_cta_rule": self.brand_profile.get("week_1_cta_rule"),
            "dm_automation_required": self.brand_profile.get("dm_automation_required"),
            "revenue_paths": self.brand_profile.get("revenue_paths"),
            "north_star_metric": self.brand_profile.get("north_star_metric"),
            "north_star_metric_definition": self.brand_profile.get("north_star_metric_definition"),
            "deprecated_metrics": self.brand_profile.get("deprecated_metrics"),
            "entry_offer": self.brand_profile.get("entry_offer"),
            "full_audit_offer": self.brand_profile.get("full_audit_offer"),
            "retainer_offer": self.brand_profile.get("retainer_offer"),
        }, indent=2)

        trends_summary = json.dumps(trends, indent=2)
        if len(trends_summary) > 6000:
            trends_summary = trends_summary[:6000] + "\n... [truncated]"

        # ── Rule 10: Build source index BEFORE Claude call ──────────────────
        project_root = Path(__file__).resolve().parent.parent
        source_files = [
            project_root / "brands" / self.brand_slug / "trends_live.json",
            project_root / "brands" / self.brand_slug / "brand_profile.json",
        ]
        source_index = build_source_index(source_files)
        self.log(f"Rule 10: Source index built — {len(source_index)} citable keys across {len(source_files)} files")

        from agents._lib._agent_framework import operating_framework as _operating_framework
        prompt = _operating_framework(2) + f"""
You are the Strategy Agent for OffGrid Marketing OS.
Your job: produce a 90-day growth roadmap for this brand based on real scraped trend data.
This is a beta SaaS product. The goal is the first 10 paying clients.

{_UNTRUSTED_POLICY}

BRAND CONTEXT:
{brand_ctx}

REAL TREND DATA (from Trend Researcher — do not invent anything not in this data):
{_untrusted_wrap("scraped_trend_data", trends_summary)}

---

Run the AutoResearch Loop. Evaluate 3 distinct strategic variants:

VARIANT A — AGGRESSIVE GROWTH PLAY
Pure volume strategy. Maximum content output, maximum reach.
Go wide fast. Accept lower trust-building in exchange for speed.
What does this look like for OffGrid specifically?

VARIANT B — TRUST-FIRST SLOW BURN
Quality over quantity. Deep credibility building.
Fewer pieces, more proof. Case studies, transparent behind-the-scenes, founder story.
Slower to convert but higher LTV clients when it does.

VARIANT C — HYBRID WITH CLEAR PHASE GATES
Phase 1 (Days 1-30): Trust foundation
Phase 2 (Days 31-60): Content volume ramp  
Phase 3 (Days 61-90): Paid amplification of best performers
Each phase has a measurable gate before unlocking the next.

SELECTION METRIC:
better = which strategy maximises QUALIFIED FOUNDER DMs PER WEEK (the brand's north_star_metric)
over 90 days, given current zero-budget constraints and a new brand with no social proof.
DO NOT optimize for follower count or generic reach. (See brand_profile.deprecated_metrics — follower-count benchmarks are explicitly OUT.)

Select the winner. One-line reason.

---

🚨 HARD CONSTRAINTS — VIOLATIONS = STRATEGY REJECTED 🚨

PLATFORM PRIORITY (Phase 1):
- PRIMARY: Instagram + YouTube (parallel). NOT LinkedIn-primary. NOT Twitter-primary.
- SECONDARY (repurpose-only, NOT original content): LinkedIn + Twitter/X.
- See brand_profile.primary_platform_phase_1 and brand_profile.secondary_platform_phase_1.
- Strategy MUST reflect: 1 long-form YouTube/week → cut into 4 IG Reels + 2 YouTube Shorts. PLUS 3 IG carousels/week (independent). LinkedIn + Twitter = repurpose ONLY.
- DO NOT propose 4-5 LinkedIn posts/week as the top channel. That violates the brand's locked positioning.

VOLUME (per brand_profile.weekly_volume_target):
- Phase 1 weekly_output target: ~9 published units/week from 1 long-form recording session.
- DO NOT inflate volume beyond this in Phase 1. Quality over volume.
- Phase 2-3 ramps are allowed but stay grounded in 1-recording-session-per-week budget.

CTA RULES (per brand_profile.week_1_cta_rule + freebie_strategy):
- Phase 1 (Days 1-30): NO comment-gated CTAs ("comment WORD"), NO promised deliverables, NO freebies. ONLY open-loop diagnostic engagement ("drop your AI tool stack", "what's your AI question?").
- Phase 1 build window (Days 8-28): freebie inventory + DM automation get built. Freebie CTAs unlock Day 29+.
- Phase 2-3: Freebie CTAs allowed once freebies + DM automation are confirmed BUILT.
- NEVER plan hire-me CTAs at any phase. Banned forever (brand_profile.hire_signal_rule).
- NEVER plan paid_amplification in Phase 2 unless brand_profile says budget exists. ASKGauravAI is zero-budget; only organic.

NAMING + LIVED HISTORY:
- Phase 1 (Days 1-28): Grid Control SILENT. Reference as "a multi-agent system I'm building".
- Phase 1 transition (Day 29 onward) + Phase 2: Grid Control nameable as proof point.
- NEVER name "Third Gen Tribe" / "TGT" / "T-shirt brand". Reference as "the brands I ran" (UNNAMED).
- NEVER frame TGT as AI-built (it was agency-run).
- Use ONLY brand_profile.lived_history_sources for lived examples.

NEVER-USE (from brand_profile.what_to_never_say):
- AI buzzwords: leverage, synergize, ecosystem, cutting-edge, next-gen, delve, foster, moreover, 10x, unlock, transform, revolutionize, game-changer.

---

⚠️ RULE 10 — SOURCE CITATION ENFORCEMENT (HARD REQUIREMENT) ⚠️

Every claim, recommendation, content angle, competitive insight, audience pain point,
or strategic decision in your output MUST trace back to a specific source data point.

For every meaningful claim in your output, add an entry to "data_provenance" with:
  - "claim": short text of the claim/recommendation (≤100 chars)
  - "source_file": exactly one of: "trends_live.json" or "brand_profile.json"
  - "source_path": dot.notation path INTO that file (e.g. "competitor_intel.gaps_identified[1].gap")
  - "source_value": verbatim 30–80 char snippet (DO NOT exceed 80 chars)

If you cannot cite a source for a claim, REMOVE THE CLAIM. Do not invent. Do not extrapolate
from general knowledge. Do not pull patterns from your training data.

Aim for 10–18 data_provenance entries (one per phase action, one per content pillar,
one per trend angle, one per competitor positioning).

The cited source_value must overlap with the claim text by ≥30% on important word tokens.
Validation will reject paraphrases too far from the source.

---

OUTPUT: Return valid JSON only. No markdown. No commentary outside the JSON.

{{
  "loop_header": {{
    "agent": "Strategy Agent",
    "output_type": "90-Day Growth Roadmap",
    "goal": "Identify the 90-day strategy with highest probability of 10 paying beta clients",
    "metric": "highest probability of 10 paying beta clients in 90 days on zero budget",
    "variants_tested": 3,
    "winner": "Variant [A/B/C] — [one line reason]"
  }},
  "data_provenance": [
    {{
      "claim": "example: Phase 1 prioritizes D2C founder pain because competitors don't address them",
      "source_file": "trends_live.json",
      "source_path": "competitor_intel.gaps_identified[1].gap",
      "source_value": "verbatim text from that exact source field, ≥30 chars"
    }}
  ],
  "winning_variant": "A",
  "strategy_90day": {{
    "created_at": "{datetime.now(timezone.utc).isoformat()}",
    "brand": "{self.brand_slug}",
    "strategic_angle": "",
    "north_star_metric": "10 paying beta clients in 90 days",
    "phase_1": {{
      "days": "1-30",
      "name": "",
      "goal": "",
      "primary_platform": "",
      "content_focus": "",
      "weekly_output": {{}},
      "key_actions": [],
      "success_gate": ""
    }},
    "phase_2": {{
      "days": "31-60",
      "name": "",
      "goal": "",
      "primary_platform": "",
      "content_focus": "",
      "weekly_output": {{}},
      "key_actions": [],
      "success_gate": ""
    }},
    "phase_3": {{
      "days": "61-90",
      "name": "",
      "goal": "",
      "primary_platform": "",
      "content_focus": "",
      "weekly_output": {{}},
      "key_actions": [],
      "success_gate": ""
    }},
    "platform_priority": [],
    "content_pillars": [],
    "what_not_to_do": [],
    "trend_angles_to_exploit": [],
    "competitive_positioning": "",
    "conversion_path": "",
    "risk_factors": []
  }}
}}"""

        # ── Phase 1a: Semantic memory recall (Voyage + pgvector) ─────────────
        # Pull prior strategy facts on both scopes. Silent no-op if Voyage/DB missing.
        try:
            from agents._lib._mem0_client import get_semantic_memory
            _sem = get_semantic_memory()
            _q = f"90-day growth strategy for {self.brand_slug}"
            _brand_facts = _sem.recall(scope="brand", agent="strategy-agent",
                                       query=_q, brand_slug=self.brand_slug, k=5)
            _gc_facts = _sem.recall(scope="grid_control", agent="strategy-agent",
                                    query=_q, k=3)
            _mem_block = ""
            if _brand_facts:
                _mem_block += "\n## Semantic Memory — prior strategy decisions for this brand\n"
                _mem_block += "\n".join(f"- {h['content']}" for h in _brand_facts) + "\n"
            if _gc_facts:
                _mem_block += "\n## Semantic Memory — account-wide strategy patterns\n"
                _mem_block += "\n".join(f"- {h['content']}" for h in _gc_facts) + "\n"
            if _mem_block:
                self.log(f"Semantic recall: {len(_brand_facts)} brand + {len(_gc_facts)} account facts injected")
        except Exception as _e:
            _mem_block = ""
            self.log(f"Semantic recall skipped: {_e}")

        # ── Rule 10: Claude call + validation-retry loop ────────────────────
        messages = [{"role": "user", "content": self.ceo.story_so_far_block() + _mem_block + prompt}]
        result = None
        validation_report = None
        attempt = 0
        max_attempts = MAX_RERUN_ATTEMPTS + 1  # initial attempt + N retries

        while attempt < max_attempts:
            attempt += 1
            self.log(f"Calling Claude {MODEL} (attempt {attempt}/{max_attempts}) — streaming mode...")
            # SDK 0.96+ requires streaming for max_tokens that could exceed 10-min budget.
            # Accumulate the streamed text, then read final usage + stop_reason from the
            # completed message object — preserves the existing token-counting + truncation-warn behaviour.
            raw_text = ""
            # Phase 1b: open a Langfuse GENERATION around the LLM call so usage/cost
            # attaches to a generation (not the span root) — fixes $0.00 / None tokens.
            with _LF.start_generation(name=f"strategy-agent.claude (attempt {attempt})", model=MODEL):
                with self.client.messages.stream(
                    model=MODEL,
                    max_tokens=24000,  # 90-day strategy + provenance entries + retry headroom
                    messages=messages,
                ) as stream:
                    for text_chunk in stream.text_stream:
                        raw_text += text_chunk
                    final_message = stream.get_final_message()

                self._total_input_tokens += final_message.usage.input_tokens
                self._total_output_tokens += final_message.usage.output_tokens
                # feed Langfuse so it auto-computes cost from model registry
                _LF.record_llm(
                    model=MODEL,
                    in_tokens=final_message.usage.input_tokens,
                    out_tokens=final_message.usage.output_tokens,
                )

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
                self.log(f"FINAL ATTEMPT FAILED — saving with provenance_validation_failed=true for human review")
                break

            # Re-prompt: feed Claude the violations and ask for a corrected output
            violation_msg = build_violation_message(missing)
            self.log(f"Re-prompting Claude with {len(missing)} citation violations...")
            messages.append({"role": "assistant", "content": json.dumps(result)})
            messages.append({"role": "user", "content": (
                f"Your previous output failed Rule 10 source-citation validation.\n\n"
                f"{violation_msg}\n\n"
                f"Re-emit the COMPLETE corrected JSON with EITHER fixed citations "
                f"OR the offending claims removed. Do not add new claims you can't cite. "
                f"Return strict JSON only."
            )})

        # Inject the validation report so downstream agents + humans can audit
        if result is not None:
            result["provenance_validation"] = validation_report

        self.log(f"AutoResearch Loop complete. Winner: {result['loop_header']['winner']}")

        # ── Phase 1a: Record this run's winning decision into brand semantic memory
        try:
            from agents._lib._mem0_client import get_semantic_memory
            _winner = result.get("loop_header", {}).get("winner", "?")
            _angle = result.get("strategy_90day", {}).get("strategic_angle", "")
            _fact = (f"Winning strategy variant: {_winner}. "
                     f"Strategic angle: {_angle}").strip()
            if _angle:
                get_semantic_memory().remember(
                    scope="brand",
                    agent="strategy-agent",
                    content=_fact,
                    brand_slug=self.brand_slug,
                    metadata={"date": datetime.now(timezone.utc).date().isoformat()},
                )
                self.log(f"Semantic memory written: variant {_winner}")
        except Exception as _e:
            self.log(f"Semantic remember skipped: {_e}")

        return result

    @_LF.observe(name="strategy-agent.run")
    def run(self):
        self.log("=" * 60)
        self.log("STRATEGY AGENT — 90-DAY ROADMAP STARTING")
        self.log("=" * 60)
        # Phase 1b: stamp trace metadata so we can filter by brand/agent in UI
        _LF.set_trace_meta(
            agent="strategy-agent",
            brand_slug=self.brand_slug,
            tags=["phase-1b", "strategy"],
            input={"brand_slug": self.brand_slug, "north_star": "10 paying beta clients in 90 days"},
        )

        # Step 1 — Load real trend data (Rule 1 gate)
        self.log("STEP 1 — Loading trend data...")
        try:
            trends = self.load_trends()
        except FileNotFoundError as e:
            self.log(f"HALT — {e}")
            return None

        # Step 2 — AutoResearch Loop
        self.log("STEP 2 — AutoResearch Loop (3 variants)...")
        loop_result = self.run_autoresearch_loop(trends)
        strategy = loop_result["strategy_90day"]
        loop_header = loop_result["loop_header"]

        # Rule 10 — inject data_provenance + provenance_validation INTO strategy
        # so downstream agents (Content Planner) + humans can audit citations
        strategy["data_provenance"] = loop_result.get("data_provenance", [])
        strategy["provenance_validation"] = loop_result.get("provenance_validation", {})

        # Step 3 — Save strategy_90day.json for downstream agents
        self.log("STEP 3 — Saving strategy_90day.json...")
        self.save_strategy(strategy)

        # Step 4 — Push to pending_approval + Notion via CEO Brain
        self.log("STEP 4 — Pushing to pending_approval/ and Notion...")
        save_result = self.ceo.save_agent_output(
            agent_name="Strategy Agent",
            output_type="90-Day Growth Roadmap",
            loop_header={
                "goal": loop_header["goal"],
                "metric": loop_header["metric"],
                "variants_tested": loop_header["variants_tested"],
                "winner": loop_header["winner"]
            },
            content=json.dumps(strategy, indent=2),
            filename="strategy_90day.json"
        )

        if save_result["notion_result"]["success"]:
            self.log(f"Notion card: {save_result['notion_result']['notion_url']}")

        # Step 5 — Mark complete
        self.log("STEP 5 — Marking strategy-agent complete...")
        self.ceo.mark_agent_complete("strategy-agent")

        self.log("=" * 60)
        self.log("STRATEGY AGENT — COMPLETE")
        self.log(f"Winner: {loop_result['winning_variant']} — {loop_header['winner']}")
        self.log("Pending approval in Notion. Approve to unlock: content-planner")
        self.log("=" * 60)
        cost_reporter.record(MODEL, self._total_input_tokens, self._total_output_tokens)
        # Phase 1b: trace output + flush so traces actually reach Langfuse
        _LF.set_output({
            "winning_variant": loop_result.get("winning_variant"),
            "winner_label": loop_header.get("winner"),
            "total_input_tokens": self._total_input_tokens,
            "total_output_tokens": self._total_output_tokens,
        })
        _LF.flush()
        return save_result


if __name__ == "__main__":
    agent = StrategyAgent()
    agent.run()
