# Agent Prompts — Ui, Store

> 34 nodes · cohesion 0.10

## Key Concepts

- **run_agent_session()** (13 connections) — `managed_agents/session_runner.py`
- **session_runner.py** (12 connections) — `managed_agents/session_runner.py`
- **str** (8 connections) — `managed_agents/session_runner.py`
- **build_context()** (6 connections) — `managed_agents/context_builder.py`
- **is_managed_ready()** (6 connections) — `managed_agents/session_runner.py`
- **save_agent_output()** (6 connections) — `managed_agents/session_runner.py`
- **_load_json()** (5 connections) — `managed_agents/context_builder.py`
- **context_builder.py** (5 connections) — `managed_agents/context_builder.py`
- **push_to_notion()** (5 connections) — `managed_agents/session_runner.py`
- **_fmt_dict()** (4 connections) — `managed_agents/context_builder.py`
- **_fmt_list()** (4 connections) — `managed_agents/context_builder.py`
- **_slugify()** (4 connections) — `managed_agents/session_runner.py`
- **str** (3 connections) — `managed_agents/context_builder.py`
- **build_resources()** (3 connections) — `managed_agents/session_runner.py`
- **_emit()** (3 connections) — `managed_agents/session_runner.py`
- **get_sse_events()** (3 connections) — `managed_agents/session_runner.py`
- **load_memory_stores()** (3 connections) — `managed_agents/session_runner.py`
- **load_registry()** (3 connections) — `managed_agents/session_runner.py`
- **int** (2 connections) — `managed_agents/context_builder.py`
- **Path** (2 connections) — `managed_agents/session_runner.py`
- **Any** (1 connections) — `managed_agents/context_builder.py`
- **Path** (1 connections) — `managed_agents/context_builder.py`
- **managed_agents/context_builder.py  Serialises per-brand data files into a human-** (1 connections) — `managed_agents/context_builder.py`
- **Load JSON file; return empty dict/list on missing or corrupt file.** (1 connections) — `managed_agents/context_builder.py`
- **Build a structured text context string from a brand's data files.     Returns a** (1 connections) — `managed_agents/context_builder.py`
- *... and 9 more nodes in this community*

## Relationships

- [[Mixed — Api, Brand]] (2 shared connections)

## Source Files

- `managed_agents/context_builder.py`
- `managed_agents/session_runner.py`

## Audit Trail

- EXTRACTED: 114 (100%)
- INFERRED: 0 (0%)
- AMBIGUOUS: 0 (0%)

---

*Part of the graphify knowledge wiki. See [[index]] to navigate.*