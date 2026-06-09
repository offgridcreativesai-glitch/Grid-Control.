"""
Brand Guardian — OffGrid Marketing OS
Agent ID: 10 | Sequence: runs after Script Writer / Content Planner approve outputs
Model: claude-opus-4-8 (Phase D)
Rule 1: Zero assumptions. Reads real brand profile + agent outputs only.
Rule 9: AutoResearch Loop — Voice / Audience / Positioning lens before output.
Rule 10: Source citation enforcement — every consistency-finding must cite the source agent output.

Purpose:
  Independent quality check across all generated content for brand consistency.
  Distinct from Contradiction Detector (which is pure-math cross-AGENT diffs);
  Brand Guardian is the SOUL check — does this content sound like the brand?
  Catches subtle voice drift, positioning weakening, audience-tone mismatches that
  rule-based diffs miss.

Reads:
  brands/{slug}/brand_profile.json
  brands/{slug}/voice_profile.json (if present)
  brands/{slug}/strategy_90day.json
  brands/{slug}/content_calendar.json
  brands/{slug}/outputs/pending_approval/script-writer/*.json

Writes:
  brands/{slug}/brand_consistency_report.json
  outputs/pending_approval/brand-guardian/{timestamp}_consistency_report.json
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
# Rule 10 — Source citation enforcement
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _provenance import (
    build_source_index,
    validate_citations,
    build_violation_message,
    MAX_RERUN_ATTEMPTS,
)

load_dotenv(override=True)

ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "").strip()
# Phase D — model sourced from the single-source-of-truth gateway
try:
    from model_gateway import model_for
except ImportError:
    from agents.model_gateway import model_for
MODEL = model_for("brand-guardian")
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


def _safe_json_loads(raw: str):
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return json.loads(_escape_literal_newlines_in_strings(raw))


class BrandGuardian:

    def __init__(self, brand_slug: str = BRAND_SLUG):
        self.brand_slug = brand_slug
        self.run_at     = datetime.now(timezone.utc).isoformat()

        self.ceo = CEOBrain()
        self.brand_profile = self.ceo.brand_profile

        if not ANTHROPIC_API_KEY:
            raise ValueError("ANTHROPIC_API_KEY not found in .env")

        self.client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
        self._total_input_tokens = 0
        self._total_output_tokens = 0

        project_root = Path(__file__).resolve().parent.parent
        self.brand_dir = project_root / "brands" / self.brand_slug
        self.report_path = self.brand_dir / "brand_consistency_report.json"

        # Optional voice profile
        self.voice_profile = None
        vp_path = self.brand_dir / "voice_profile.json"
        if vp_path.exists():
            try:
                with open(vp_path) as f:
                    self.voice_profile = json.load(f)
            except Exception:
                pass

        self.log(f"Initialised. Brand: {self.brand_profile.get('brand_name', self.brand_slug)}")

    def log(self, msg: str):
        print(f"[Brand Guardian | {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] {msg}")

    # -------------------------------------------------------------------------
    # INPUT — load all agent outputs
    # -------------------------------------------------------------------------

    def _load_outputs(self) -> dict:
        """Load strategy + calendar + scripts. Returns dict for prompt injection."""
        outputs = {}
        for fname, key in (("strategy_90day.json", "strategy"), ("content_calendar.json", "calendar")):
            p = self.brand_dir / fname
            if p.exists():
                try:
                    with open(p) as f:
                        outputs[key] = json.load(f)
                except Exception:
                    outputs[key] = {}
            else:
                outputs[key] = {}

        # Scripts: load from pending_approval — wrapper or single
        scripts = []
        sw_dir = self.brand_dir / "outputs" / "pending_approval" / "script-writer"
        if sw_dir.exists():
            for f in sorted(sw_dir.glob("*.json")):
                raw = f.read_text()
                if "---" in raw:
                    raw = raw.split("---", 1)[1].strip()
                try:
                    parsed = json.loads(raw)
                except Exception:
                    continue
                if isinstance(parsed, dict) and isinstance(parsed.get("scripts"), list):
                    scripts.extend(parsed["scripts"])
                elif isinstance(parsed, dict):
                    scripts.append(parsed)
        outputs["scripts"] = scripts
        return outputs

    # -------------------------------------------------------------------------
    # CORE — Claude-judged consistency check (Rule 10 enforced)
    # -------------------------------------------------------------------------

    def run_consistency_check(self) -> dict:
        outputs = self._load_outputs()
        if not outputs.get("strategy") and not outputs.get("calendar") and not outputs.get("scripts"):
            self.log("HALT — no agent outputs to audit. Run Strategy/Content Planner/Script Writer first.")
            return {"status": "HALTED", "reason": "no_outputs"}

        # Rule 10 — source index
        project_root = Path(__file__).resolve().parent.parent
        source_files = [
            project_root / "brands" / self.brand_slug / "brand_profile.json",
            project_root / "brands" / self.brand_slug / "strategy_90day.json",
            project_root / "brands" / self.brand_slug / "content_calendar.json",
            project_root / "brands" / self.brand_slug / "voice_profile.json",
        ]
        source_index = build_source_index(source_files)
        self.log(f"Rule 10: Source index built — {len(source_index)} citable keys across {len(source_files)} files")

        # Truncate scripts for prompt size
        scripts_summary = json.dumps(outputs.get("scripts", [])[:8], indent=2)
        if len(scripts_summary) > 12000:
            scripts_summary = scripts_summary[:12000] + "\n... [truncated]"

        # Token optimization: use compact _state.json instead of dumping full
        # brand_profile (17KB) + voice_profile (12KB). Saves ~7000 tokens/run.
        # Specific deep fields can be referenced by key but the SOUL audit only
        # needs the core voice + audience + positioning summary.
        try:
            from _state import load_brand_state  # type: ignore
            _state = load_brand_state(self.brand_slug)
            state_block = json.dumps(_state, indent=2)
        except Exception:
            state_block = json.dumps({
                "brand_name": self.brand_profile.get("brand_name"),
                "audience": self.brand_profile.get("audience"),
                "tone_of_voice": self.brand_profile.get("tone_of_voice"),
                "what_to_never_say": self.brand_profile.get("what_to_never_say"),
            }, indent=2)

        # Voice profile core fields only (full file referenced by name if needed)
        voice_block = ""
        if self.voice_profile:
            vp_core = {
                "voice_dna_summary": self.voice_profile.get("voice_dna_summary_for_script_writer"),
                "scripts_must": self.voice_profile.get("scripts_must"),
                "scripts_must_not": self.voice_profile.get("scripts_must_not"),
                "vocabulary_signature": (self.voice_profile.get("vocabulary") or {}).get("signature_phrases"),
                "cta_style": self.voice_profile.get("cta_style"),
            }
            voice_block = f"\nBRAND VOICE DNA (core):\n{json.dumps(vp_core, indent=2)}\n"

        prompt = f"""You are the Brand Guardian for {self.brand_profile.get('brand_name', self.brand_slug)}.
Your only job: audit all generated content for brand SOUL — voice consistency, audience-tone match,
positioning fidelity, and forbidden-phrase compliance.

You are NOT a rule-checker (the Contradiction Detector handles hard rules).
You are the SOUL check — does this content sound like the brand a real founder would publish?

BRAND STATE (compact — full files in brand dir if needed):
{state_block}
{voice_block}
APPROVED 90-DAY STRATEGY:
{json.dumps(outputs.get('strategy', {}), indent=2)[:3000]}

CONTENT CALENDAR:
{json.dumps(outputs.get('calendar', {}), indent=2)[:3000]}

GENERATED SCRIPTS (sample of first 8):
{scripts_summary}

---

Run an AutoResearch Loop with 3 lenses, then produce ONE consolidated audit:

LENS A — VOICE
Does the script copy sound like the brand_profile.tone_of_voice + tone_specifics?
Does it match voice_profile (if present)?
Find drift: scripts that sound generic, AI-flavored, or off-tone for this brand.

LENS B — AUDIENCE
Does the script speak to brand_profile.target_audience and audience[]?
Or is it speaking past them (e.g. enterprise tone for solopreneur audience)?

LENS C — POSITIONING + FORBIDDEN
Does the script reinforce strategy.strategic_angle + competitive_positioning?
Does it violate brand_profile.what_to_never_say?

---

⚠️ RULE 10 — SOURCE CITATION ENFORCEMENT (HARD REQUIREMENT) ⚠️

Every finding in your output MUST cite the source data point that justifies it via data_provenance.
For each finding, add an entry with: claim, source_file, source_path, source_value (verbatim ≥30 chars).
If you cannot cite a source for a finding, REMOVE the finding. Do not invent.

Aim for 5–10 data_provenance entries (one per major finding).

---

OUTPUT: Return STRICT JSON only.

{{
  "loop_header": {{
    "agent": "Brand Guardian",
    "output_type": "Brand Consistency Audit",
    "goal": "Catch voice/audience/positioning drift across all generated agent outputs",
    "metric": "better = catches real drift without flagging acceptable creative variance",
    "variants_tested": 3,
    "winner": "one-line summary"
  }},
  "data_provenance": [
    {{
      "claim": "example finding text",
      "source_file": "brand_profile.json",
      "source_path": "tone_of_voice",
      "source_value": "verbatim ≥30 char snippet"
    }}
  ],
  "brand_consistency_report": {{
    "scanned_at": "{self.run_at}",
    "agents_audited": ["Strategy Agent", "Content Planner", "Script Writer"],
    "scripts_evaluated": {len(outputs.get('scripts', []))},
    "overall_grade": "A | B | C | D | F",
    "voice_findings": [
      {{"severity": "CRITICAL|WARNING|INFO", "finding": "...", "evidence": "...", "fix": "..."}}
    ],
    "audience_findings": [
      {{"severity": "CRITICAL|WARNING|INFO", "finding": "...", "evidence": "...", "fix": "..."}}
    ],
    "positioning_findings": [
      {{"severity": "CRITICAL|WARNING|INFO", "finding": "...", "evidence": "...", "fix": "..."}}
    ],
    "forbidden_phrase_violations": [
      {{"severity": "CRITICAL", "phrase_violated": "...", "where": "agent_name + script_topic", "fix": "..."}}
    ]
  }}
}}
"""

        # Rule 10 retry loop
        messages = [{"role": "user", "content": prompt}]
        result = None
        validation_report = None
        attempt = 0
        max_attempts = MAX_RERUN_ATTEMPTS + 1

        while attempt < max_attempts:
            attempt += 1
            self.log(f"Calling Claude {MODEL} (attempt {attempt}/{max_attempts})...")
            response = self.client.messages.create(
                model=MODEL,
                max_tokens=16000,
                messages=messages,
            )
            self._total_input_tokens += response.usage.input_tokens
            self._total_output_tokens += response.usage.output_tokens

            if response.stop_reason == "max_tokens":
                self.log(f"WARNING: max_tokens cap hit ({response.usage.output_tokens})")

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
            is_valid, missing, validation_report = validate_citations(result, source_index)
            self.log(f"Rule 10 validation (attempt {attempt}): {validation_report['claims_validated']}/{validation_report['claims_total']} passed")

            if is_valid or attempt >= max_attempts:
                break

            messages.append({"role": "assistant", "content": json.dumps(result)})
            messages.append({"role": "user", "content": (
                f"Your previous output failed Rule 10 validation.\n\n"
                f"{build_violation_message(missing)}\n\n"
                f"Re-emit COMPLETE corrected JSON with fixed citations or removed claims. Strict JSON only."
            )})

        if result is not None:
            result["provenance_validation"] = validation_report

        return result

    # -------------------------------------------------------------------------
    # MAIN RUN
    # -------------------------------------------------------------------------

    def run(self) -> dict:
        self.log("=" * 60)
        self.log("BRAND GUARDIAN — CONSISTENCY AUDIT STARTING")
        self.log("=" * 60)

        result = self.run_consistency_check()
        if not result or result.get("status") == "HALTED":
            return result or {"status": "HALTED"}

        report = result.get("brand_consistency_report", {})
        loop_header = result.get("loop_header", {})

        # Inject provenance INTO the saved report
        report["data_provenance"] = result.get("data_provenance", [])
        report["provenance_validation"] = result.get("provenance_validation", {})

        # Save brand_consistency_report.json for downstream use
        with open(self.report_path, "w") as f:
            json.dump(report, f, indent=2)
        self.log(f"brand_consistency_report.json saved → {self.report_path}")

        # Push to pending_approval + Notion via CEO Brain
        try:
            save_result = self.ceo.save_agent_output(
                agent_name="Brand Guardian",
                output_type="Brand Consistency Audit",
                loop_header={
                    "goal":            loop_header.get("goal", ""),
                    "metric":          loop_header.get("metric", ""),
                    "variants_tested": loop_header.get("variants_tested", 3),
                    "winner":          loop_header.get("winner", ""),
                },
                content=json.dumps(report, indent=2),
                filename="brand_consistency_report.json",
            )
        except Exception as e:
            self.log(f"WARNING: CEO Brain save_agent_output skipped — {e}")

        # Cost report
        try:
            cost_reporter.report_cost(
                agent_name="Brand Guardian",
                model=MODEL,
                input_tokens=self._total_input_tokens,
                output_tokens=self._total_output_tokens,
            )
        except Exception:
            pass

        self.log("=" * 60)
        self.log(f"BRAND GUARDIAN — RUN COMPLETE")
        self.log(f"Overall grade: {report.get('overall_grade', 'N/A')}")
        self.log(f"Findings: voice={len(report.get('voice_findings', []))} | "
                 f"audience={len(report.get('audience_findings', []))} | "
                 f"positioning={len(report.get('positioning_findings', []))} | "
                 f"forbidden={len(report.get('forbidden_phrase_violations', []))}")
        self.log("=" * 60)

        return report


if __name__ == "__main__":
    guardian = BrandGuardian()
    guardian.run()
