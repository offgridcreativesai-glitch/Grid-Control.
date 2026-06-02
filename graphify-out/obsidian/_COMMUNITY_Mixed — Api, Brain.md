---
type: community
cohesion: 0.17
members: 12
---

# Mixed — Api, Brain

**Cohesion:** 0.17 - loosely connected
**Members:** 12 nodes

## Members
- [[Agent-scoped context role, recent outputs, last run.      Used when The Brain i]] - rationale - dashboard_api.py
- [[Embedded Claude chat for The Brain right-rail panel.      Body { messages {ro]] - rationale - dashboard_api.py
- [[Execute a proposed action AFTER user approval in the UI.     Body { kind 'edit]] - rationale - dashboard_api.py
- [[Execute auto-approved read-only tools. Returns dict with 'output' or 'error'.]] - rationale - dashboard_api.py
- [[Resolve a relative path safely under BASE_DIR. Returns None if outside or hidden]] - rationale - dashboard_api.py
- [[Slim brand context for The Brain — uses agents._state compact summary.      Brai]] - rationale - dashboard_api.py
- [[_brain_execute_read_tool()]] - code - dashboard_api.py
- [[_brain_safe_path()]] - code - dashboard_api.py
- [[_build_brain_agent_summary()]] - code - dashboard_api.py
- [[_build_brain_brand_summary()]] - code - dashboard_api.py
- [[brain_chat()]] - code - dashboard_api.py
- [[brain_execute_proposal()]] - code - dashboard_api.py

## Live Query (requires Dataview plugin)

```dataview
TABLE source_file, type FROM #community/Mixed__Api_Brain
SORT file.name ASC
```

## Connections to other communities
- 6 edges to [[_COMMUNITY_Mixed — Api, Brand]]
- 4 edges to [[_COMMUNITY_Dashboard — Api, Brand]]
- 2 edges to [[_COMMUNITY_Agent System — Skill, Brand]]
- 1 edge to [[_COMMUNITY_Dashboard — Api, Agent]]

## Top bridge nodes
- [[_brain_safe_path()]] - degree 6, connects to 3 communities
- [[_build_brain_agent_summary()]] - degree 5, connects to 3 communities
- [[_build_brain_brand_summary()]] - degree 5, connects to 3 communities
- [[_brain_execute_read_tool()]] - degree 5, connects to 2 communities
- [[brain_chat()]] - degree 5, connects to 1 community