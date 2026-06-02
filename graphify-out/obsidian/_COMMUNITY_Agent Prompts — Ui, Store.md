---
type: community
cohesion: 0.10
members: 34
---

# Agent Prompts — Ui, Store

**Cohesion:** 0.10 - loosely connected
**Members:** 34 nodes

## Members
- [[Any_2]] - code - managed_agents/context_builder.py
- [[Build a structured text context string from a brand's data files.     Returns a]] - rationale - managed_agents/context_builder.py
- [[Build session resources list from memory store IDs.]] - rationale - managed_agents/session_runner.py
- [[Create and stream a Managed Agent session.      - Prepends brand context to task]] - rationale - managed_agents/session_runner.py
- [[Generator that yields SSE lines for a run_id. Called by Flask status endpoint.]] - rationale - managed_agents/session_runner.py
- [[Load JSON file; return empty dictlist on missing or corrupt file.]] - rationale - managed_agents/context_builder.py
- [[Path_8]] - code - managed_agents/context_builder.py
- [[Path_6]] - code - managed_agents/session_runner.py
- [[Push output to Notion approval database (mirrors existing behaviour).]] - rationale - managed_agents/session_runner.py
- [[Returns True only if     1. The registry has an agent_id for this agent     2.]] - rationale - managed_agents/session_runner.py
- [[Save agent output JSON (or raw text) to pending_approval directory.]] - rationale - managed_agents/session_runner.py
- [[Wrapper that runs run_agent_session in a thread.     Mirrors the existing subpro]] - rationale - managed_agents/session_runner.py
- [[_emit()]] - code - managed_agents/session_runner.py
- [[_fmt_dict()]] - code - managed_agents/context_builder.py
- [[_fmt_list()]] - code - managed_agents/context_builder.py
- [[_load_json()]] - code - managed_agents/context_builder.py
- [[_slugify()]] - code - managed_agents/session_runner.py
- [[bool_7]] - code - managed_agents/session_runner.py
- [[build_context()]] - code - managed_agents/context_builder.py
- [[build_resources()]] - code - managed_agents/session_runner.py
- [[context_builder.py]] - code - managed_agents/context_builder.py
- [[get_sse_events()]] - code - managed_agents/session_runner.py
- [[int_13]] - code - managed_agents/context_builder.py
- [[is_managed_ready()_1]] - code - managed_agents/session_runner.py
- [[load_memory_stores()]] - code - managed_agents/session_runner.py
- [[load_registry()]] - code - managed_agents/session_runner.py
- [[managed_agentscontext_builder.py  Serialises per-brand data files into a human-]] - rationale - managed_agents/context_builder.py
- [[managed_agentssession_runner.py  Replaces the old _run_agent_subprocess pattern]] - rationale - managed_agents/session_runner.py
- [[push_to_notion()]] - code - managed_agents/session_runner.py
- [[run_agent_session()]] - code - managed_agents/session_runner.py
- [[save_agent_output()]] - code - managed_agents/session_runner.py
- [[session_runner.py]] - code - managed_agents/session_runner.py
- [[str_28]] - code - managed_agents/context_builder.py
- [[str_26]] - code - managed_agents/session_runner.py

## Live Query (requires Dataview plugin)

```dataview
TABLE source_file, type FROM #community/Agent_Prompts__Ui_Store
SORT file.name ASC
```

## Connections to other communities
- 2 edges to [[_COMMUNITY_Mixed — Api, Brand]]

## Top bridge nodes
- [[run_agent_session()]] - degree 13, connects to 1 community
- [[is_managed_ready()_1]] - degree 6, connects to 1 community