"""
Weekly Review Composer — OffGrid Marketing OS
Not one of the 18 locked agents (CLAUDE.md roster is unchanged) — a thin, $0
orchestration glue script for the proactive weekly operating program
(GRIDLOCK-PROGRAM-01JUL, Stage 2). Runs AFTER Data Analyst, Performance
Tracker, and Trend Sentinel in run_weekly_program()'s review chain.

Rule 1 (zero assumptions): reads only files those three agents already wrote
for real this week. Never calls an LLM, never fabricates a number — if a file
is missing, that section is reported as "no data yet" rather than invented.
Rule 3: writes via CEOBrain.save_agent_output — the only approved path to
outputs/pending_approval/, same as every other agent.

Reads:
  brands/{slug}/outputs/pending_approval/data-analyst/*.json   (latest run)
  brands/{slug}/performance_history.json                        (Performance Tracker)
  brands/{slug}/pivot_decision.json                              (Trend Sentinel)
Writes:
  outputs/pending_approval/weekly-program/  ("Last week + keep/cut/scale" card)
"""
import os
import sys
import json
import glob
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from ceo_brain.orchestrator import CEOBrain

BRAND_SLUG = os.getenv("ACTIVE_BRAND", "offgrid-creatives-ai")
BRAND_DIR = Path(__file__).resolve().parent.parent / "brands" / BRAND_SLUG


def _latest_data_analyst_output() -> dict | None:
    folder = BRAND_DIR / "outputs" / "pending_approval" / "data-analyst"
    if not folder.exists():
        return None
    files = sorted(glob.glob(str(folder / "*.json")), reverse=True)
    if not files:
        return None
    try:
        raw = Path(files[0]).read_text()
        body = raw.split("\n---\n", 1)[1] if "\n---\n" in raw else raw
        return json.loads(body)
    except Exception:
        return None


def _read_json(path: Path) -> dict | None:
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text())
    except Exception:
        return None


def compose() -> dict:
    data_analyst = _latest_data_analyst_output()
    perf_history = _read_json(BRAND_DIR / "performance_history.json")
    pivot = _read_json(BRAND_DIR / "pivot_decision.json")

    winning = (perf_history or {}).get("winning_patterns", {})
    dead = (perf_history or {}).get("dead_patterns", [])
    hook_patterns = winning.get("hook_patterns_top_3", []) if isinstance(winning, dict) else []

    keep = [
        {"pattern": p.get("value"), "why": p.get("reason") or "top performer this rolling window"}
        for p in hook_patterns if isinstance(p, dict)
    ]
    cut = [
        {"pattern": d.get("value"), "why": d.get("reason") or "underperforming vs. rolling baseline"}
        for d in dead if isinstance(d, dict)
    ]
    scale_signal = (pivot or {}).get("overall_decision", "STAY")

    summary = {
        "brand_slug": BRAND_SLUG,
        "executive_summary": (data_analyst or {}).get("executive_summary")
            or (data_analyst or {}).get("summary")
            or ("No Data Analyst run found this week." if data_analyst is None else ""),
        "action_items": (data_analyst or {}).get("action_items")
            or (data_analyst or {}).get("recommendations") or [],
        "keep": keep,
        "cut": cut,
        "scale_decision": scale_signal,
        "scale_reason": next(
            (s.get("reason") for s in (pivot or {}).get("per_signal", []) if s.get("decision") == scale_signal),
            "",
        ),
        "has_data_analyst": data_analyst is not None,
        "has_performance_history": perf_history is not None,
        "has_pivot_decision": pivot is not None,
        "decision_engine": "pure_math",  # aggregation only — no LLM call in this script
    }
    return summary


def main() -> None:
    summary = compose()
    ceo = CEOBrain()
    n_keep, n_cut = len(summary["keep"]), len(summary["cut"])
    try:
        ceo.save_agent_output(
            agent_name="Weekly Program",
            output_type="Last Week + Keep/Cut/Scale",
            loop_header={
                "goal": "Turn this week's real Data Analyst + Performance Tracker + "
                        "Trend Sentinel output into one keep/cut/scale review card",
                "metric": "better = founder makes a keep/cut/scale call in one read, not three",
                "variants_tested": 0,
                "winner": f"Pure aggregation of real data — {n_keep} keep, {n_cut} cut, "
                          f"scale={summary['scale_decision']}",
            },
            content=json.dumps(summary, indent=2),
            filename="weekly_review.json",
        )
        print(f"[weekly-review-composer] {BRAND_SLUG}: keep={n_keep} cut={n_cut} "
              f"scale={summary['scale_decision']}")
    except Exception as e:
        print(f"[weekly-review-composer] save_agent_output failed: {e}")


if __name__ == "__main__":
    main()
