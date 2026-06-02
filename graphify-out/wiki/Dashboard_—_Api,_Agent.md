# Dashboard — Api, Agent

> 36 nodes · cohesion 0.08

## Key Concepts

- **_get_brand_id()** (20 connections) — `dashboard_api.py`
- **Path** (11 connections) — `dashboard_api.py`
- **approve_output()** (10 connections) — `dashboard_api.py`
- **get_pending_outputs()** (10 connections) — `dashboard_api.py`
- **_agent_name_to_slug()** (9 connections) — `dashboard_api.py`
- **_update_session_agent_status()** (9 connections) — `dashboard_api.py`
- **_run_agent_subprocess()** (8 connections) — `dashboard_api.py`
- **run_agent()** (7 connections) — `dashboard_api.py`
- **_safe_path()** (7 connections) — `dashboard_api.py`
- **reject_output()** (6 connections) — `dashboard_api.py`
- **_skill_on_approve()** (6 connections) — `dashboard_api.py`
- **sync_notion_approvals()** (6 connections) — `dashboard_api.py`
- **_unlock_next_agent()** (6 connections) — `dashboard_api.py`
- **n8n_webhook()** (5 connections) — `dashboard_api.py`
- **_skill_on_reject()** (5 connections) — `dashboard_api.py`
- **brand_costs()** (4 connections) — `dashboard_api.py`
- **broadcast_event()** (4 connections) — `dashboard_api.py`
- **ceo_next_agent()** (4 connections) — `dashboard_api.py`
- **_strip_markdown()** (4 connections) — `dashboard_api.py`
- **requestChanges()** (4 connections) — `dashboard/.port-backup/spaces.bak/ReviewSpace.tsx`
- **get_agent_output_history()** (3 connections) — `dashboard_api.py`
- **_run_managed_async()** (2 connections) — `dashboard_api.py`
- **Push an event to all SSE subscribers. Non-blocking.** (1 connections) — `dashboard_api.py`
- **Return monthly cost breakdown for a brand.     Query params: year (int, default** (1 connections) — `dashboard_api.py`
- **n8n → GRID CONTROL trigger endpoint.     n8n sends: { brand_slug, agent_name, tr** (1 connections) — `dashboard_api.py`
- *... and 11 more nodes in this community*

## Relationships

- [[Mixed — Api, Brand]] (26 shared connections)
- [[Dashboard — Api, Brand]] (18 shared connections)
- [[Utils — Api, Agent]] (4 shared connections)
- [[Agent System — Skill, Brand]] (3 shared connections)
- [[Mixed — Api, Brain]] (1 shared connections)
- [[Mixed — Api]] (1 shared connections)
- [[Mixed — Api, Agent]] (1 shared connections)
- [[Database — Supabase, Brand]] (1 shared connections)
- [[Notion_Integration — Brain, Api]] (1 shared connections)
- [[Dashboard — Brand, Agent]] (1 shared connections)
- [[Dashboard — Review, Content]] (1 shared connections)

## Source Files

- `dashboard/.port-backup/spaces.bak/ReviewSpace.tsx`
- `dashboard_api.py`

## Audit Trail

- EXTRACTED: 163 (99%)
- INFERRED: 1 (1%)
- AMBIGUOUS: 0 (0%)

---

*Part of the graphify knowledge wiki. See [[index]] to navigate.*