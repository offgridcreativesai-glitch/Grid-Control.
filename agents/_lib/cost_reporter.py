"""
cost_reporter.py — GRID CONTROL
Lightweight utility imported by every agent to record run costs to Supabase.
Reads GRID_RUN_ID and GRID_BRAND_SLUG from env (set by dashboard_api.py).
If env vars are missing (direct script run), costs are only printed, not stored.
"""

import os
import sys
import importlib.util
from datetime import datetime

# Force-load the local supabase/db.py directly, bypassing the pip-installed
# 'supabase' package which has no 'db' submodule and would shadow the local one.
_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, _PROJECT_ROOT)

def _load_local_db():
    """Load supabase/db.py from disk, avoiding conflict with the pip 'supabase' package."""
    db_path = os.path.join(_PROJECT_ROOT, "supabase", "db.py")
    spec = importlib.util.spec_from_file_location("_grid_db", db_path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def record(
    model: str,
    total_input_tokens: int,
    total_output_tokens: int,
    fal_generations: int = 0,
    apify_runs: int = 0,
) -> None:
    """
    Call once at the end of every agent run.
    Reads GRID_RUN_ID and GRID_BRAND_SLUG from environment.
    Records cost to Supabase if run_id is present; always prints summary.
    """
    run_id     = os.getenv("GRID_RUN_ID", "").strip()
    brand_slug = os.getenv("GRID_BRAND_SLUG", "").strip()
    ts         = datetime.now().strftime("%H:%M:%S")

    try:
        _db = _load_local_db()
        api_cost   = _db.calc_api_cost(model, total_input_tokens, total_output_tokens)
        fal_cost   = fal_generations * _db.FAL_COST_PER_IMAGE
        apify_cost = apify_runs      * _db.APIFY_COST_PER_RUN
        total_cost = api_cost + fal_cost + apify_cost

        # Convert to INR for logging (1 USD ≈ 85 INR)
        inr = total_cost * 85

        print(
            f"[{ts}] [COST] model={model} | "
            f"tokens in={total_input_tokens:,} out={total_output_tokens:,} | "
            f"API=${api_cost:.4f} | FAL=${fal_cost:.4f} ({fal_generations} imgs) | "
            f"Apify=${apify_cost:.4f} ({apify_runs} runs) | "
            f"TOTAL=${total_cost:.4f} (₹{inr:.2f})"
        )

        if run_id:
            _db.update_agent_run_costs(
                run_id, model,
                total_input_tokens, total_output_tokens,
                fal_generations, apify_runs,
            )
            print(f"[{ts}] [COST] ✅ Recorded to Supabase run_id={run_id[:8]}...")
        else:
            print(f"[{ts}] [COST] ℹ️  GRID_RUN_ID not set — cost logged but not stored in Supabase")

    except Exception as e:
        print(f"[{ts}] [COST] ⚠️  cost_reporter failed: {e}")
