# Agent System — Pipeline, Supabase

> 36 nodes · cohesion 0.08

## Key Concepts

- **AgentTrace** (11 connections) — `agents/tracing.py`
- **orchestrator.py** (6 connections) — `agents/orchestrator.py`
- **tracing.py** (6 connections) — `agents/tracing.py`
- **trace_agent()** (6 connections) — `agents/tracing.py`
- **run_parallel_group()** (5 connections) — `agents/orchestrator.py`
- **run_single_agent()** (5 connections) — `agents/orchestrator.py`
- **.add_generation()** (5 connections) — `agents/tracing.py`
- **str** (4 connections) — `agents/orchestrator.py`
- **run_agents_async()** (4 connections) — `agents/orchestrator.py`
- **run_pipeline()** (4 connections) — `agents/orchestrator.py`
- **.add_tokens()** (4 connections) — `agents/tracing.py`
- **._log_to_supabase()** (4 connections) — `agents/tracing.py`
- **.cost_usd()** (3 connections) — `agents/tracing.py`
- **_get_db()** (3 connections) — `agents/tracing.py`
- **str** (3 connections) — `agents/tracing.py`
- **int** (2 connections) — `agents/orchestrator.py`
- **.duration_s()** (2 connections) — `agents/tracing.py`
- **.__exit__()** (2 connections) — `agents/tracing.py`
- **.__init__()** (2 connections) — `agents/tracing.py`
- **float** (2 connections) — `agents/tracing.py`
- **int** (2 connections) — `agents/tracing.py`
- **CEO Brain — Subagent Orchestration Engine. Handles parallel + sequential agent r** (1 connections) — `agents/orchestrator.py`
- **Run a group of agents in parallel using ThreadPoolExecutor.** (1 connections) — `agents/orchestrator.py`
- **Run the full agent pipeline sequentially by group,     with agents within each g** (1 connections) — `agents/orchestrator.py`
- **Fire-and-forget: run agents in background thread.** (1 connections) — `agents/orchestrator.py`
- *... and 11 more nodes in this community*

## Relationships

- [[Database — Supabase, Brand]] (2 shared connections)

## Source Files

- `agents/orchestrator.py`
- `agents/tracing.py`

## Audit Trail

- EXTRACTED: 100 (100%)
- INFERRED: 0 (0%)
- AMBIGUOUS: 0 (0%)

---

*Part of the graphify knowledge wiki. See [[index]] to navigate.*