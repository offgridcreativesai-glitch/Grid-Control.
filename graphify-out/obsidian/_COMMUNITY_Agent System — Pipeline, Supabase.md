---
type: community
cohesion: 0.08
members: 36
---

# Agent System — Pipeline, Supabase

**Cohesion:** 0.08 - loosely connected
**Members:** 36 nodes

## Members
- [[.__enter__()]] - code - agents/tracing.py
- [[.__exit__()]] - code - agents/tracing.py
- [[.__init__()_1]] - code - agents/tracing.py
- [[._log_to_supabase()]] - code - agents/tracing.py
- [[.add_generation()]] - code - agents/tracing.py
- [[.add_tokens()]] - code - agents/tracing.py
- [[.cost_usd()]] - code - agents/tracing.py
- [[.duration_s()]] - code - agents/tracing.py
- [[Accumulate token usage during the run.]] - rationale - agents/tracing.py
- [[Agent run tracing & cost tracking. Logs every agent run to Supabase usage_logs.]] - rationale - agents/tracing.py
- [[AgentTrace]] - code - agents/tracing.py
- [[CEO Brain — Subagent Orchestration Engine. Handles parallel + sequential agent r]] - rationale - agents/orchestrator.py
- [[Context manager for tracing a single agent run.]] - rationale - agents/tracing.py
- [[Create an agent trace context manager.]] - rationale - agents/tracing.py
- [[Fire-and-forget run agents in background thread.]] - rationale - agents/orchestrator.py
- [[Lazy import to avoid circular deps.]] - rationale - agents/tracing.py
- [[Log a single LLM generation within this run.]] - rationale - agents/tracing.py
- [[Run a group of agents in parallel using ThreadPoolExecutor.]] - rationale - agents/orchestrator.py
- [[Run a single agent as subprocess. Returns result dict.]] - rationale - agents/orchestrator.py
- [[Run the full agent pipeline sequentially by group,     with agents within each g]] - rationale - agents/orchestrator.py
- [[Thread]] - code - agents/orchestrator.py
- [[Write usage record to usage_logs table.]] - rationale - agents/tracing.py
- [[_get_db()]] - code - agents/tracing.py
- [[_init_langfuse()]] - code - agents/tracing.py
- [[float]] - code - agents/tracing.py
- [[int_6]] - code - agents/orchestrator.py
- [[int_2]] - code - agents/tracing.py
- [[orchestrator.py]] - code - agents/orchestrator.py
- [[run_agents_async()]] - code - agents/orchestrator.py
- [[run_parallel_group()]] - code - agents/orchestrator.py
- [[run_pipeline()]] - code - agents/orchestrator.py
- [[run_single_agent()]] - code - agents/orchestrator.py
- [[str_11]] - code - agents/orchestrator.py
- [[str_3]] - code - agents/tracing.py
- [[trace_agent()]] - code - agents/tracing.py
- [[tracing.py]] - code - agents/tracing.py

## Live Query (requires Dataview plugin)

```dataview
TABLE source_file, type FROM #community/Agent_System__Pipeline_Supabase
SORT file.name ASC
```

## Connections to other communities
- 2 edges to [[_COMMUNITY_Database — Supabase, Brand]]

## Top bridge nodes
- [[tracing.py]] - degree 6, connects to 1 community
- [[.cost_usd()]] - degree 3, connects to 1 community