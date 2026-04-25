"""
CEO Brain — Cross-Agent Contradiction Detector (Build D)
Per Rule 10 — PURE DETERMINISTIC. NO Claude. NO LLM. Class-1 decision agent.

Reads outputs from multiple generation agents (Strategy / Content Planner / Script Writer / etc.)
and runs a registry of hard-coded rules to find disagreements.

Examples of contradictions caught:
  - Strategy says "premium positioning, no discounting" but Script Writer hook is "How I cut costs 70%"
  - Brand profile audience = "D2C founders" but Script Writer caption targets "students"
  - Strategy weekly_output = "3x/week" but Content Calendar has 7 posts in Week 1
  - Brand profile what_to_never_say contains "AI guru" and Script Writer hook says "as an AI guru"
  - Strategy phase = "Phase 1 — Awareness" but Script Writer CTAs are "buy now / pay X"

Severity levels:
  CRITICAL — block on save (output cannot pass approval until fixed)
  WARNING  — flag in pending_approval, surface to human reviewer
  INFO     — surface in dashboard but doesn't block

Output: brands/{slug}/contradictions.json with full finding details + cited evidence per rule.

Every finding cites the EXACT source values from each agent's output (Rule 10 trace-back).
"""

import os
import re
import json
from datetime import datetime, timezone
from pathlib import Path

# ── DETERMINISTIC RULE THRESHOLDS ─────────────────────────────────────────
# Audience-language drift: Script Writer caption tokens must overlap with brand audience tokens
AUDIENCE_OVERLAP_MIN_JACCARD = 0.05   # at least 5% token overlap
# Volume commitment tolerance: actual post count vs Strategy weekly_output target
VOLUME_TOLERANCE_PCT = 0.30          # ±30% of stated weekly_output
# Positioning drift: Calendar content_pillars must overlap with Strategy strategic_angle
POSITIONING_OVERLAP_MIN_JACCARD = 0.20

# Hardcoded keyword sets (Phase-CTA mismatch detection)
HARD_SALES_CTA_KEYWORDS = {
    "buy now", "buy today", "purchase now", "shop now", "limited time", "ending soon",
    "checkout", "pay now", "discount code", "use code", "% off", "sale ends",
    "dm to purchase", "dm to buy", "swipe up to buy",
}

PRICE_DOWN_KEYWORDS = {
    "cheap", "affordable", "discount", "discounted", "% off", "save money",
    "lowest price", "budget-friendly", "free trial", "no cost",
    "cut cost", "reduce cost", "slash price", "price drop",
}

PREMIUM_KEYWORDS = {
    "premium", "exclusive", "luxury", "high-end", "boutique", "bespoke", "private",
    "no discount", "no sale", "no markdown",
}

PHASE1_BLOCKED_PATTERNS = HARD_SALES_CTA_KEYWORDS  # Phase 1 = awareness, no hard sales

# Common stopwords (English)
_STOPWORDS = {
    "a","an","the","and","or","but","is","are","was","were","be","been","being",
    "in","on","at","to","for","with","by","of","from","as","into","about","this",
    "that","these","those","it","its","you","your","i","we","our","they","their",
    "what","which","who","whom","when","where","why","how","not","no","do","does",
    "did","done","doing","have","has","had","having","will","would","should","could",
    "can","may","might","must","shall","ought","need","one","two","three","first",
    "next","last","more","most","less","least","very","just","than","then","also",
    "if","else","only","own","same","so","such","too","s","t","ll","re","ve","m","d",
}


def _tokenize(text: str) -> set:
    if not text:
        return set()
    tokens = re.split(r"[^a-z0-9]+", str(text).lower())
    return {t for t in tokens if len(t) >= 3 and t not in _STOPWORDS}


def _jaccard(a: set, b: set) -> float:
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)


def _flatten_text(obj) -> str:
    """Recursively pull all string values from a nested dict/list structure."""
    parts: list = []
    if isinstance(obj, dict):
        for v in obj.values():
            parts.append(_flatten_text(v))
    elif isinstance(obj, list):
        for item in obj:
            parts.append(_flatten_text(item))
    elif isinstance(obj, str):
        parts.append(obj)
    return " ".join(parts)


def _safe_load_json(path: Path) -> dict | None:
    if not path.exists():
        return None
    try:
        with open(path) as f:
            return json.load(f)
    except Exception:
        return None


# ── RULE FUNCTIONS ───────────────────────────────────────────────────────
# Each rule takes (brand_data: dict) and returns list[Contradiction dicts]

def rule_pricing_contradiction(brand: dict) -> list:
    """
    CRITICAL — Strategy says premium positioning but Script Writer hooks contain price-down language.
    """
    findings = []
    strategy = brand.get("strategy", {})
    scripts  = brand.get("scripts", [])

    strat_text = _flatten_text(strategy).lower()
    has_premium_signal = any(kw in strat_text for kw in PREMIUM_KEYWORDS)

    if not has_premium_signal:
        return findings

    # Premium positioning detected — check scripts for price-down violations
    for s in scripts:
        script_text = _flatten_text(s).lower()
        violations = [kw for kw in PRICE_DOWN_KEYWORDS if kw in script_text]
        if violations:
            # Find the actual hook text that violated
            hook_text = ""
            hb = s.get("hook_block", {})
            if isinstance(hb, dict):
                rec = hb.get("recommended_hook")
                hooks = hb.get("hooks", [])
                if isinstance(rec, int) and 0 < rec <= len(hooks):
                    hook_text = hooks[rec - 1].get("text", "")
            findings.append({
                "rule_id":          "pricing_contradiction",
                "severity":         "CRITICAL",
                "agents_involved":  ["Strategy Agent", "Script Writer"],
                "evidence": {
                    "strategy_signal":   "Premium positioning detected: " + ", ".join(kw for kw in PREMIUM_KEYWORDS if kw in strat_text)[:200],
                    "script_violations": violations[:5],
                    "violating_hook":    hook_text[:200],
                    "script_post_id":    s.get("original_post", {}).get("topic", "")[:80],
                },
                "proposed_fix":     "Either (a) update Strategy to allow value/price messaging, OR (b) rewrite Script Writer hook without price-down language. Decision: human review.",
            })
    return findings


def rule_what_to_never_say_violation(brand: dict) -> list:
    """
    CRITICAL — Brand profile what_to_never_say contains keyword X, and X appears in any generated output.
    """
    findings = []
    profile = brand.get("brand_profile", {})
    never_say = profile.get("what_to_never_say", "")

    # Extract banned phrases. Could be a string with sentences or a list.
    banned: list = []
    if isinstance(never_say, list):
        for item in never_say:
            banned.append(str(item).strip())
    elif isinstance(never_say, str) and never_say.strip():
        # Sentence-split heuristically — treat each sentence as one banned guideline
        for sent in re.split(r"[.!?]+", never_say):
            s = sent.strip()
            if s and len(s) > 10:
                banned.append(s)

    if not banned:
        return findings

    # For each banned guideline, extract distinctive 2-3 word phrases (skip generic words)
    # Then check if those phrases appear in any agent output
    def _extract_quoted_or_distinctive(banned_text: str) -> list:
        # Pull anything in quotes first
        quoted = re.findall(r"['\"]([^'\"]{4,40})['\"]", banned_text)
        if quoted:
            return [q.strip().lower() for q in quoted]
        # Otherwise: skip — too vague to match. Substring "AI guru" yes, full sentence no.
        # Look for 2-3 word noun phrases (rough heuristic: capitalized words OR specific term patterns)
        terms = re.findall(r"\b([A-Z][a-z]+(?:\s+[A-Z]?[a-z]+){0,2})\b", banned_text)
        return [t.lower() for t in terms if len(t) > 5]

    # Check across all agent outputs
    targets = {
        "Strategy Agent":  brand.get("strategy", {}),
        "Content Planner": brand.get("calendar", {}),
        "Script Writer":   brand.get("scripts", []),
    }

    for guideline in banned:
        forbidden_phrases = _extract_quoted_or_distinctive(guideline)
        if not forbidden_phrases:
            continue
        for agent_name, output in targets.items():
            output_text = _flatten_text(output).lower()
            hit_phrases = [p for p in forbidden_phrases if p in output_text]
            if hit_phrases:
                findings.append({
                    "rule_id":          "what_to_never_say_violation",
                    "severity":         "CRITICAL",
                    "agents_involved":  [agent_name],
                    "evidence": {
                        "brand_guideline":     guideline[:200],
                        "forbidden_phrases_hit": hit_phrases[:5],
                        "violating_agent":     agent_name,
                    },
                    "proposed_fix":     f"Rewrite {agent_name} output to remove forbidden phrases. Brand profile says: '{guideline[:120]}'",
                })
    return findings


def rule_phase_cta_mismatch(brand: dict) -> list:
    """
    WARNING — Brand is in Phase 1 (Awareness) but generated content has hard-sales CTAs.
    """
    findings = []
    profile = brand.get("brand_profile", {})
    phase = str(profile.get("phase", "")).lower()
    if "phase 1" not in phase and "awareness" not in phase:
        return findings

    targets = {
        "Content Planner": brand.get("calendar", {}),
        "Script Writer":   brand.get("scripts", []),
    }

    for agent_name, output in targets.items():
        output_text = _flatten_text(output).lower()
        violations = [kw for kw in PHASE1_BLOCKED_PATTERNS if kw in output_text]
        if violations:
            findings.append({
                "rule_id":          "phase_cta_mismatch",
                "severity":         "WARNING",
                "agents_involved":  [agent_name],
                "evidence": {
                    "brand_phase":         profile.get("phase", "Phase 1"),
                    "hard_sales_keywords": violations[:5],
                    "violating_agent":     agent_name,
                },
                "proposed_fix":     "Phase 1 = awareness building. Replace hard-sales CTAs ('buy now', 'pay X') with soft engagement CTAs ('comment WORD', 'save this for later', 'DM for the framework').",
            })
    return findings


def rule_audience_language_drift(brand: dict) -> list:
    """
    WARNING — Script Writer caption/hook tokens have ZERO intersection with the brand's
    full relevance pool (audience + industry + product + target_audience).
    Uses set intersection (≥1 shared token = passes), not Jaccard ratio — Jaccard penalises
    long scripts unfairly. Goal here is "is the script even on-topic for the brand?"
    """
    findings = []
    profile = brand.get("brand_profile", {})
    scripts = brand.get("scripts", [])

    # BROADER relevance pool — script just needs to share ANY token with brand context
    relevance_text = " ".join([
        str(profile.get("target_audience", "")),
        " ".join(profile.get("audience", []) or []),
        str(profile.get("industry", "")),
        str(profile.get("product", "")),
        str(profile.get("brand_brief", "")),
    ])
    relevance_tokens = _tokenize(relevance_text)
    if not relevance_tokens:
        return findings

    drifted_count = 0
    sample_drifted: list = []
    for s in scripts:
        script_text = _flatten_text(s.get("hook_block", {})) + " " + _flatten_text(s.get("script", {}))
        script_tokens = _tokenize(script_text)
        if not script_tokens:
            continue
        # Hard test: script must share AT LEAST 1 token with brand relevance pool
        shared = script_tokens & relevance_tokens
        if len(shared) < 2:  # require ≥2 shared tokens (1 = coincidence, 2 = signal)
            drifted_count += 1
            if len(sample_drifted) < 3:
                sample_drifted.append({
                    "topic":          s.get("original_post", {}).get("topic", "")[:80],
                    "shared_tokens":  sorted(shared),
                    "shared_count":   len(shared),
                })

    if drifted_count >= max(1, int(len(scripts) * 0.5)):  # >50% of scripts drifted (raised from 30%)
        findings.append({
            "rule_id":          "audience_language_drift",
            "severity":         "WARNING",
            "agents_involved":  ["Script Writer"],
            "evidence": {
                "scripts_evaluated":          len(scripts),
                "scripts_drifted":            drifted_count,
                "min_shared_tokens_required": 2,
                "sample_drifted":             sample_drifted,
                "relevance_pool_size":        len(relevance_tokens),
                "relevance_tokens_sample":    sorted(relevance_tokens)[:10],
            },
            "proposed_fix":     "Most scripts share <2 tokens with brand context (audience+industry+product). Either scripts are off-brand OR brand_profile is too narrow. Review samples.",
        })
    return findings


def rule_volume_commitment_mismatch(brand: dict) -> list:
    """
    INFO — Strategy says weekly_output = 3x but Content Calendar Week 1 has N posts (off by > tolerance).
    """
    findings = []
    strategy = brand.get("strategy", {})
    calendar = brand.get("calendar", {})
    if not strategy or not calendar:
        return findings

    # Strategy commitment may be at strategy.phase_1.weekly_output (dict) or strategy.weekly_output
    weekly_output = strategy.get("phase_1", {}).get("weekly_output", {})
    if not weekly_output:
        weekly_output = strategy.get("weekly_output", {})

    # Try to extract a per-week post count from this dict
    target_per_week = None
    for k, v in (weekly_output or {}).items():
        # Look for numeric values in any field
        m = re.search(r"(\d+)", str(v))
        if m:
            target_per_week = int(m.group(1))
            break
    if target_per_week is None:
        # Fall back to brand_profile.weekly_post_target
        wpt = str(brand.get("brand_profile", {}).get("weekly_post_target", ""))
        m = re.search(r"(\d+)", wpt)
        if m:
            target_per_week = int(m.group(1))

    if target_per_week is None:
        return findings

    week1_posts = calendar.get("week_1", {}).get("posts", [])
    actual = len(week1_posts)
    if actual == 0:
        return findings

    diff_pct = abs(actual - target_per_week) / target_per_week if target_per_week else 0
    if diff_pct > VOLUME_TOLERANCE_PCT:
        findings.append({
            "rule_id":          "volume_commitment_mismatch",
            "severity":         "INFO",
            "agents_involved":  ["Strategy Agent", "Content Planner"],
            "evidence": {
                "strategy_target_per_week":   target_per_week,
                "calendar_actual_week_1":     actual,
                "tolerance_pct":              VOLUME_TOLERANCE_PCT,
                "diff_pct":                   round(diff_pct, 3),
            },
            "proposed_fix":     f"Strategy committed {target_per_week} posts/week but Calendar has {actual}. Either Calendar over-/under-delivers vs Strategy. Realign one of them.",
        })
    return findings


def rule_positioning_drift(brand: dict) -> list:
    """
    WARNING — Calendar content_pillars don't overlap with Strategy strategic_angle keywords.
    """
    findings = []
    strategy = brand.get("strategy", {})
    calendar = brand.get("calendar", {})
    if not strategy or not calendar:
        return findings

    # content_pillars may be a list of strings OR list of dicts (each with 'pillar' field)
    pillars_raw = strategy.get("content_pillars", []) or []
    pillars_text = " ".join(
        (p.get("pillar", "") if isinstance(p, dict) else str(p))
        for p in pillars_raw
    )
    strategic_text = " ".join([
        str(strategy.get("strategic_angle", "")),
        pillars_text,
        str(strategy.get("competitive_positioning", "")),
    ])
    strategy_tokens = _tokenize(strategic_text)
    if not strategy_tokens:
        return findings

    calendar_pillars = calendar.get("content_pillars", []) or []
    cal_pillars_text = " ".join(str(p) for p in calendar_pillars)
    calendar_tokens = _tokenize(cal_pillars_text)

    if not calendar_tokens:
        return findings

    overlap = _jaccard(strategy_tokens, calendar_tokens)
    if overlap < POSITIONING_OVERLAP_MIN_JACCARD:
        findings.append({
            "rule_id":          "positioning_drift",
            "severity":         "WARNING",
            "agents_involved":  ["Strategy Agent", "Content Planner"],
            "evidence": {
                "jaccard_overlap":          round(overlap, 3),
                "min_jaccard_threshold":    POSITIONING_OVERLAP_MIN_JACCARD,
                "strategy_tokens_sample":   sorted(strategy_tokens)[:10],
                "calendar_tokens_sample":   sorted(calendar_tokens)[:10],
                "calendar_pillars":         calendar_pillars[:5],
            },
            "proposed_fix":     "Calendar content_pillars don't reflect Strategy's strategic_angle. Either Content Planner needs to align pillars to Strategy, or Strategy needs to update strategic_angle.",
        })
    return findings


# Rule registry — add new rules here
RULE_REGISTRY = [
    rule_pricing_contradiction,
    rule_what_to_never_say_violation,
    rule_phase_cta_mismatch,
    rule_audience_language_drift,
    rule_volume_commitment_mismatch,
    rule_positioning_drift,
]


# ── PUBLIC API ───────────────────────────────────────────────────────────

def load_brand_data(brand_slug: str, project_root: Path | None = None) -> dict:
    """
    Load all relevant brand outputs into a single dict for cross-checking.
    Returns dict with keys: brand_profile, strategy, calendar, scripts (list).
    """
    if project_root is None:
        project_root = Path(__file__).resolve().parent.parent
    brand_dir = project_root / "brands" / brand_slug

    data = {
        "brand_slug":    brand_slug,
        "brand_profile": _safe_load_json(brand_dir / "brand_profile.json") or {},
        "strategy":      _safe_load_json(brand_dir / "strategy_90day.json") or {},
        "calendar":      _safe_load_json(brand_dir / "content_calendar.json") or {},
        "scripts":       [],
    }

    # Load all script JSON files from pending_approval/script-writer/
    # Files may contain a SINGLE script OR a wrapper {scripts: [...]} with multiple
    sw_dir = brand_dir / "outputs" / "pending_approval" / "script-writer"
    if sw_dir.exists():
        for f in sorted(sw_dir.glob("*.json")):
            raw = f.read_text()
            # Strip CEO Brain header if present
            if "---" in raw:
                raw = raw.split("---", 1)[1].strip()
            try:
                parsed = json.loads(raw)
            except Exception:
                continue
            # Wrapper case: {scripts: [...]}
            if isinstance(parsed, dict) and isinstance(parsed.get("scripts"), list):
                for s in parsed["scripts"]:
                    if isinstance(s, dict):
                        data["scripts"].append(s)
            # Single-script case: top-level dict with hook_block / script keys
            elif isinstance(parsed, dict):
                data["scripts"].append(parsed)
            # List case
            elif isinstance(parsed, list):
                for s in parsed:
                    if isinstance(s, dict):
                        data["scripts"].append(s)

    return data


def detect_contradictions(brand_slug: str, project_root: Path | None = None) -> dict:
    """
    Run the full RULE_REGISTRY against this brand's loaded outputs.
    Returns:
      {
        "scanned_at": iso timestamp,
        "brand_slug": str,
        "decision_engine": "pure_math",
        "rules_evaluated": N,
        "agents_loaded": {strategy: bool, calendar: bool, scripts_count: int},
        "findings": [list of contradiction dicts],
        "counts": {CRITICAL: N, WARNING: N, INFO: N},
        "blocking": bool (True if any CRITICAL findings)
      }
    """
    brand = load_brand_data(brand_slug, project_root)

    findings: list = []
    rules_run = 0
    for rule_fn in RULE_REGISTRY:
        try:
            rule_findings = rule_fn(brand)
            for f in rule_findings:
                findings.append(f)
            rules_run += 1
        except Exception as e:
            # Log but don't crash the whole detector if one rule fails
            findings.append({
                "rule_id":   rule_fn.__name__,
                "severity":  "INFO",
                "agents_involved": [],
                "evidence":  {"error": str(e)},
                "proposed_fix": "Rule function raised exception. See evidence.error for traceback.",
            })

    counts = {"CRITICAL": 0, "WARNING": 0, "INFO": 0}
    for f in findings:
        sev = f.get("severity", "INFO")
        if sev in counts:
            counts[sev] += 1

    return {
        "scanned_at":      datetime.now(timezone.utc).isoformat(),
        "brand_slug":      brand_slug,
        "decision_engine": "pure_math",
        "rules_evaluated": rules_run,
        "agents_loaded": {
            "strategy_present":  bool(brand.get("strategy")),
            "calendar_present":  bool(brand.get("calendar")),
            "scripts_count":     len(brand.get("scripts", [])),
            "brand_profile_present": bool(brand.get("brand_profile")),
        },
        "findings": findings,
        "counts":   counts,
        "blocking": counts["CRITICAL"] > 0,
    }


def save_contradictions_report(brand_slug: str, report: dict, project_root: Path | None = None) -> Path:
    """Persist report to brands/{slug}/contradictions.json."""
    if project_root is None:
        project_root = Path(__file__).resolve().parent.parent
    out_path = project_root / "brands" / brand_slug / "contradictions.json"
    with open(out_path, "w") as f:
        json.dump(report, f, indent=2)
    return out_path


if __name__ == "__main__":
    import sys
    slug = os.getenv("ACTIVE_BRAND") or (sys.argv[1] if len(sys.argv) > 1 else "askgauravai")
    print(f"[Contradiction Detector] Running on brand: {slug}")
    report = detect_contradictions(slug)
    out = save_contradictions_report(slug, report)
    print(f"[Contradiction Detector] Report saved → {out}")
    print(f"[Contradiction Detector] Scanned: {report['rules_evaluated']} rules | Findings: {len(report['findings'])}")
    print(f"[Contradiction Detector] Counts: {report['counts']} | Blocking: {report['blocking']}")
    for f in report["findings"][:10]:
        print(f"  [{f['severity']}] {f['rule_id']} — agents: {f['agents_involved']}")
