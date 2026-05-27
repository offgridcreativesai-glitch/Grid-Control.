"""
CEO Brain — Subagent Orchestration Engine.
Handles parallel + sequential agent runs with dependency resolution.
"""
import os
import time
import threading
import subprocess
from typing import Optional
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed

from agents.tracing import trace_agent

PROJECT_ROOT = Path(__file__).resolve().parent.parent

# ── Agent Dependency Graph ────────────────────────────────────────────────────
# Agents that can run in parallel (no dependencies on each other)
PARALLEL_GROUPS = {
    "research": ["trend-researcher", "data-analyst"],  # Independent — run together
    "planning": ["content-planner"],                    # Depends on trend-researcher
    "creation": ["script-writer"],                      # Depends on content-planner
    "creative": ["creative-director", "carousel-designer"],  # Independent of each other
    "distribution": ["community-manager", "dm-customer-hunter", "email-marketing-agent"],
    "quality": ["brand-guardian"],                       # Runs last — checks everything
}

# Sequential pipeline: group order
PIPELINE_ORDER = ["research", "planning", "creation", "creative", "distribution", "quality"]

# Agents that are pure-math (no LLM cost)
PURE_MATH_AGENTS = {"trend-sentinel", "performance-tracker"}


def run_single_agent(
    agent_slug: str,
    brand_slug: str,
    model: str = "sonnet-4-6",
    timeout_s: int = 300,
    extra_env: Optional[dict] = None,
) -> dict:
    """Run a single agent as subprocess. Returns result dict."""
    env = {**os.environ, "ACTIVE_BRAND": brand_slug}
    if extra_env:
        env.update(extra_env)

    script = PROJECT_ROOT / "agents" / f"{agent_slug.replace('-', '_')}.py"
    if not script.exists():
        # Try kebab-case filename
        script = PROJECT_ROOT / "agents" / f"{agent_slug}.py"
    if not script.exists():
        return {
            "agent": agent_slug,
            "status": "error",
            "error": f"Agent script not found: {script}",
            "duration_s": 0,
            "cost_usd": 0,
        }

    with trace_agent(agent_slug, brand_slug, model) as t:
        try:
            result = subprocess.run(
                ["python3", str(script)],
                cwd=str(PROJECT_ROOT),
                env=env,
                capture_output=True,
                text=True,
                timeout=timeout_s,
            )
            if result.returncode != 0:
                t.status = "error"
                t.error = result.stderr[:500] if result.stderr else "Non-zero exit"
                return {
                    "agent": agent_slug,
                    "status": "error",
                    "error": t.error,
                    "duration_s": t.duration_s,
                    "cost_usd": t.cost_usd,
                }
            return {
                "agent": agent_slug,
                "status": "success",
                "output": result.stdout[:2000] if result.stdout else "",
                "duration_s": t.duration_s,
                "cost_usd": t.cost_usd,
            }
        except subprocess.TimeoutExpired:
            t.status = "error"
            t.error = f"Timeout after {timeout_s}s"
            return {
                "agent": agent_slug,
                "status": "timeout",
                "error": t.error,
                "duration_s": timeout_s,
                "cost_usd": t.cost_usd,
            }


def run_parallel_group(
    agents: list[str],
    brand_slug: str,
    model: str = "sonnet-4-6",
    max_workers: int = 3,
) -> list[dict]:
    """Run a group of agents in parallel using ThreadPoolExecutor."""
    if not agents:
        return []

    results = []
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {
            executor.submit(run_single_agent, slug, brand_slug, model): slug
            for slug in agents
        }
        for future in as_completed(futures):
            slug = futures[future]
            try:
                result = future.result()
                results.append(result)
            except Exception as e:
                results.append({
                    "agent": slug,
                    "status": "error",
                    "error": str(e),
                    "duration_s": 0,
                    "cost_usd": 0,
                })
    return results


def run_pipeline(
    brand_slug: str,
    groups: Optional[list[str]] = None,
    model: str = "sonnet-4-6",
) -> dict:
    """
    Run the full agent pipeline sequentially by group,
    with agents within each group running in parallel.

    Args:
        brand_slug: Target brand
        groups: Optional list of group names to run (defaults to full pipeline)
        model: Default model for tracing

    Returns:
        {"status": "complete", "groups": {...}, "total_duration_s": ..., "total_cost_usd": ...}
    """
    groups_to_run = groups or PIPELINE_ORDER
    all_results = {}
    total_start = time.time()
    total_cost = 0.0

    for group_name in groups_to_run:
        agents = PARALLEL_GROUPS.get(group_name, [])
        if not agents:
            continue

        group_results = run_parallel_group(agents, brand_slug, model)
        all_results[group_name] = group_results
        total_cost += sum(r.get("cost_usd", 0) for r in group_results)

        # Check for critical failures — stop pipeline if research fails
        if group_name == "research":
            errors = [r for r in group_results if r["status"] == "error"]
            if len(errors) == len(agents):
                return {
                    "status": "aborted",
                    "reason": "All research agents failed",
                    "groups": all_results,
                    "total_duration_s": round(time.time() - total_start, 2),
                    "total_cost_usd": total_cost,
                }

    return {
        "status": "complete",
        "groups": all_results,
        "total_duration_s": round(time.time() - total_start, 2),
        "total_cost_usd": total_cost,
    }


def run_agents_async(
    agents: list[str],
    brand_slug: str,
    callback=None,
) -> threading.Thread:
    """Fire-and-forget: run agents in background thread."""
    def _worker():
        results = run_parallel_group(agents, brand_slug)
        if callback:
            callback(results)

    t = threading.Thread(target=_worker, daemon=True)
    t.start()
    return t
