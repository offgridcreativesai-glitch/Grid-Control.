---
type: community
cohesion: 0.17
members: 20
---

# Agent System — Data, Api

**Cohesion:** 0.17 - loosely connected
**Members:** 20 nodes

## Members
- [[.__init__()_7]] - code - agents/data_analyst.py
- [[.collect_api_connection_status()]] - code - agents/data_analyst.py
- [[.collect_output_inventory()]] - code - agents/data_analyst.py
- [[.collect_script_sample()]] - code - agents/data_analyst.py
- [[.collect_session_data()]] - code - agents/data_analyst.py
- [[.log()_5]] - code - agents/data_analyst.py
- [[.run()_4]] - code - agents/data_analyst.py
- [[.run_autoresearch_loop()_2]] - code - agents/data_analyst.py
- [[3 variants         A — Raw metrics summary (what happened)         B — Trend +]] - rationale - agents/data_analyst.py
- [[Check which external APIs are configured.]] - rationale - agents/data_analyst.py
- [[Data Analyst — OffGrid Marketing OS Agent ID 6  Runs every week automatically.]] - rationale - agents/data_analyst.py
- [[Escape literal nrt inside JSON string values (Claude API quirk).]] - rationale - agents/data_analyst.py
- [[Pull a sample of script writer outputs for hook analysis.]] - rationale - agents/data_analyst.py
- [[Read session_state for agent run history and Notion card counts.]] - rationale - agents/data_analyst.py
- [[Scan all output files across pending + approved for scoring.]] - rationale - agents/data_analyst.py
- [[_escape_literal_newlines_in_strings()_1]] - code - agents/data_analyst.py
- [[_safe_json_loads()_1]] - code - agents/data_analyst.py
- [[data_analyst.py]] - code - agents/data_analyst.py
- [[json.loads with literal-newline repair fallback.]] - rationale - agents/data_analyst.py
- [[str_13]] - code - agents/data_analyst.py

## Live Query (requires Dataview plugin)

```dataview
TABLE source_file, type FROM #community/Agent_System__Data_Api
SORT file.name ASC
```

## Connections to other communities
- 2 edges to [[_COMMUNITY_Ceo_Brain — Agent]]
- 1 edge to [[_COMMUNITY_Agent System — Script, Review]]

## Top bridge nodes
- [[data_analyst.py]] - degree 12, connects to 1 community
- [[.__init__()_7]] - degree 4, connects to 1 community
- [[json.loads with literal-newline repair fallback.]] - degree 2, connects to 1 community