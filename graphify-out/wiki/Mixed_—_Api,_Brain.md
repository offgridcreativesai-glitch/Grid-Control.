# Mixed — Api, Brain

> 12 nodes · cohesion 0.17

## Key Concepts

- **_brain_safe_path()** (6 connections) — `dashboard_api.py`
- **brain_chat()** (5 connections) — `dashboard_api.py`
- **_brain_execute_read_tool()** (5 connections) — `dashboard_api.py`
- **_build_brain_agent_summary()** (5 connections) — `dashboard_api.py`
- **_build_brain_brand_summary()** (5 connections) — `dashboard_api.py`
- **brain_execute_proposal()** (3 connections) — `dashboard_api.py`
- **Resolve a relative path safely under BASE_DIR. Returns None if outside or hidden** (1 connections) — `dashboard_api.py`
- **Execute auto-approved read-only tools. Returns dict with 'output' or 'error'.** (1 connections) — `dashboard_api.py`
- **Execute a proposed action AFTER user approval in the UI.     Body: { kind: 'edit** (1 connections) — `dashboard_api.py`
- **Agent-scoped context: role, recent outputs, last run.      Used when The Brain i** (1 connections) — `dashboard_api.py`
- **Slim brand context for The Brain — uses agents._state compact summary.      Brai** (1 connections) — `dashboard_api.py`
- **Embedded Claude chat for The Brain right-rail panel.      Body: { messages: [{ro** (1 connections) — `dashboard_api.py`

## Relationships

- [[Mixed — Api, Brand]] (6 shared connections)
- [[Dashboard — Api, Brand]] (4 shared connections)
- [[Agent System — Skill, Brand]] (2 shared connections)
- [[Dashboard — Api, Agent]] (1 shared connections)

## Source Files

- `dashboard_api.py`

## Audit Trail

- EXTRACTED: 33 (94%)
- INFERRED: 2 (6%)
- AMBIGUOUS: 0 (0%)

---

*Part of the graphify knowledge wiki. See [[index]] to navigate.*