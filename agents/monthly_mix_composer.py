"""
Monthly Mix Composer — OffGrid Marketing OS
Not one of the 18 locked agents — a thin, $0 orchestration glue script for the
proactive weekly operating program (GRIDLOCK-PROGRAM-01JUL, Stage 4). Runs on
the monthly cadence (scheduler/worker.py, gated to one week-of-month per
scheduler/schedule_config.json) to roll the last ~30 days of real,
already-computed Performance Tracker output into one "content mix" card —
what's working, what to cut, at monthly (not weekly) resolution.

Rule 1 (zero assumptions): reads only performance_history.json, which
Performance Tracker already computed pure-math from real published-post data.
Never calls an LLM, never fabricates a number.

Scope note: the original plan called this a "budget/channel-mix" review, but
GC has no per-brand-attributed ad-spend data source today (paid_ledger.json is
a GLOBAL cross-brand ledger, not brand-scoped; ad-strategist — the only agent
that would produce real paid-channel spend — is still coming_soon in
AGENT_SCRIPTS). Fabricating a budget split with no real spend data would break
Rule 1, so this composer sticks to CONTENT mix (formats/hooks/topics that are
actually winning or dead) until real per-brand ad-spend data exists. The
budget_split field below is left explicitly null with a reason, not guessed.

Reads:
  brands/{slug}/performance_history.json   (Performance Tracker — pure math)
Writes:
  outputs/pending_approval/monthly-program/  ("Monthly Content Mix" card)
"""
import os
import sys
import json
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from ceo_brain.orchestrator import CEOBrain

BRAND_SLUG = os.getenv("ACTIVE_BRAND", "offgrid-creatives-ai")
BRAND_DIR = Path(__file__).resolve().parent.parent / "brands" / BRAND_SLUG


def _read_json(path: Path) -> dict | None:
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text())
    except Exception:
        return None


def compose() -> dict:
    perf_history = _read_json(BRAND_DIR / "performance_history.json")
    winning = (perf_history or {}).get("winning_patterns", {}) if perf_history else {}
    dead = (perf_history or {}).get("dead_patterns", []) if perf_history else []
    posts = (perf_history or {}).get("posts", []) if perf_history else []

    scale = [
        {"format": f.get("value"), "why": f.get("reason") or "top performer this rolling window"}
        for f in (winning.get("formats_top_3") or []) if isinstance(f, dict)
    ]
    keep = [
        {"pattern": p.get("value"), "why": p.get("reason") or "consistent performer"}
        for p in (winning.get("hook_patterns_top_3") or []) if isinstance(p, dict)
    ]
    cut = [
        {"pattern": d.get("value"), "why": d.get("reason") or "underperforming vs. rolling baseline"}
        for d in dead if isinstance(d, dict)
    ]

    summary = {
        "brand_slug": BRAND_SLUG,
        "window": "trailing performance_history.json rolling window (Performance Tracker's own thresholds)",
        "posts_in_window": len(posts),
        "scale_next_month": scale,
        "keep": keep,
        "cut": cut,
        "budget_split": None,
        "budget_split_reason": (
            "No real per-brand paid-channel spend data exists yet — ad-strategist "
            "is not built and paid_ledger.json is a global cross-brand ledger, not "
            "brand-attributed. This section activates once real ad spend exists for "
            "this brand. Not fabricated."
        ),
        "has_performance_history": perf_history is not None,
        "decision_engine": "pure_math",  # aggregation only — no LLM call in this script
    }
    return summary


def main() -> None:
    summary = compose()
    ceo = CEOBrain()
    n_scale, n_keep, n_cut = len(summary["scale_next_month"]), len(summary["keep"]), len(summary["cut"])
    try:
        ceo.save_agent_output(
            agent_name="Monthly Program",
            output_type="Monthly Content Mix Review",
            loop_header={
                "goal": "Roll up the last month's real performance data into one "
                        "scale/keep/cut mix decision for next month",
                "metric": "better = founder makes a monthly mix call in one read, grounded in real data",
                "variants_tested": 0,
                "winner": f"Pure aggregation of real data — {n_scale} scale, {n_keep} keep, {n_cut} cut",
            },
            content=json.dumps(summary, indent=2),
            filename="monthly_mix.json",
        )
        print(f"[monthly-mix-composer] {BRAND_SLUG}: scale={n_scale} keep={n_keep} cut={n_cut}")
    except Exception as e:
        print(f"[monthly-mix-composer] save_agent_output failed: {e}")


if __name__ == "__main__":
    main()
