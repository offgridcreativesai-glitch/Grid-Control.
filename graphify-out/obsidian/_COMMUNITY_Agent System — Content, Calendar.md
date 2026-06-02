---
type: community
cohesion: 0.26
members: 16
---

# Agent System — Content, Calendar

**Cohesion:** 0.26 - loosely connected
**Members:** 16 nodes

## Members
- [[.__init__()_9]] - code - agents/content_planner.py
- [[.load_file()]] - code - agents/content_planner.py
- [[.log()_7]] - code - agents/content_planner.py
- [[.run()_6]] - code - agents/content_planner.py
- [[.run_autoresearch_loop()_4]] - code - agents/content_planner.py
- [[.save_calendar()]] - code - agents/content_planner.py
- [[Content Planner Prompt]] - document - managed_agents/prompts/content_planner.md
- [[Content Planner — OffGrid Marketing OS Agent ID 2  Sequence position 3 (runs]] - rationale - agents/content_planner.py
- [[Find the first balanced { ... } block. Strips trailing prose Claude appended.]] - rationale - agents/script_writer.py
- [[Load a JSON file from brand directory. Raises FileNotFoundError if missing.]] - rationale - agents/content_planner.py
- [[Rule 9 — AutoResearch Loop.         Three variants           Variant A — Educat]] - rationale - agents/content_planner.py
- [[Write content_calendar.json to brand directory for downstream agents.]] - rationale - agents/content_planner.py
- [[_escape_literal_newlines_in_strings()_2]] - code - agents/content_planner.py
- [[_extract_first_json_object()]] - code - agents/content_planner.py
- [[_safe_json_loads()_2]] - code - agents/content_planner.py
- [[str_15]] - code - agents/content_planner.py

## Live Query (requires Dataview plugin)

```dataview
TABLE source_file, type FROM #community/Agent_System__Content_Calendar
SORT file.name ASC
```

## Connections to other communities
- 4 edges to [[_COMMUNITY_Managed Agent Prompts — Pipeline]]
- 3 edges to [[_COMMUNITY_Agent System — Ui, Trend]]
- 2 edges to [[_COMMUNITY_Ceo_Brain — Agent]]
- 1 edge to [[_COMMUNITY_Agent System — Script, Review]]

## Top bridge nodes
- [[Content Planner Prompt]] - degree 15, connects to 2 communities
- [[.run_autoresearch_loop()_4]] - degree 8, connects to 1 community
- [[.__init__()_9]] - degree 4, connects to 1 community
- [[Find the first balanced { ... } block. Strips trailing prose Claude appended.]] - degree 2, connects to 1 community