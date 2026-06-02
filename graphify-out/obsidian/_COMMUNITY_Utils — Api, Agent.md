---
type: community
cohesion: 0.11
members: 27
---

# Utils — Api, Agent

**Cohesion:** 0.11 - loosely connected
**Members:** 27 nodes

## Members
- [[Any_1]] - code - utils/output_formatter.py
- [[Convert Content Planner output to flattened list.     Keys day, topic, platform]] - rationale - utils/output_formatter.py
- [[Convert Data Analyst output to (executive_summary string, action_items list).]] - rationale - utils/output_formatter.py
- [[Convert Funnel Specialist output to list of stage dicts.     Each stage has sta]] - rationale - utils/output_formatter.py
- [[Convert Script Writer output to a list of clean dicts.     Keys platform, forma]] - rationale - utils/output_formatter.py
- [[Convert Strategy Agent output to list of phase dicts.     Keys phase_name, days]] - rationale - utils/output_formatter.py
- [[Convert Website Agent output to list of pages.     Each page has name, purpose,]] - rationale - utils/output_formatter.py
- [[Convert any agent output to a clean human-readable markdown string.     No JSON]] - rationale - utils/output_formatter.py
- [[Escape literal newlinetabCR characters that appear inside JSON string     valu]] - rationale - dashboard_api.py
- [[Parse an agent output file that may contain Loop Header + '---' + JSON.]] - rationale - dashboard_api.py
- [[Recursively convert a dictlist to readable markdown lines.]] - rationale - utils/output_formatter.py
- [[_flatten_to_markdown()]] - code - utils/output_formatter.py
- [[_parse_agent_output_file()]] - code - dashboard_api.py
- [[escape_literal_newlines_in_strings()]] - code - dashboard_api.py
- [[format_calendar()]] - code - utils/output_formatter.py
- [[format_data_analyst()]] - code - utils/output_formatter.py
- [[format_for_notion()]] - code - utils/output_formatter.py
- [[format_funnel()]] - code - utils/output_formatter.py
- [[format_scripts()]] - code - utils/output_formatter.py
- [[format_strategy()]] - code - utils/output_formatter.py
- [[format_website()]] - code - utils/output_formatter.py
- [[get_agent_output()]] - code - dashboard_api.py
- [[get_dashboard_output()]] - code - dashboard_api.py
- [[int_11]] - code - utils/output_formatter.py
- [[output_formatter.py]] - code - utils/output_formatter.py
- [[output_formatter.py — OffGrid Marketing OS Converts agent JSON outputs to clean]] - rationale - utils/output_formatter.py
- [[str_24]] - code - utils/output_formatter.py

## Live Query (requires Dataview plugin)

```dataview
TABLE source_file, type FROM #community/Utils__Api_Agent
SORT file.name ASC
```

## Connections to other communities
- 9 edges to [[_COMMUNITY_Mixed — Api, Brand]]
- 4 edges to [[_COMMUNITY_Dashboard — Api, Agent]]
- 2 edges to [[_COMMUNITY_Notion_Integration — Brain, Api]]
- 1 edge to [[_COMMUNITY_Dashboard — Api, Brand]]

## Top bridge nodes
- [[format_for_notion()]] - degree 16, connects to 3 communities
- [[get_agent_output()]] - degree 9, connects to 2 communities
- [[_parse_agent_output_file()]] - degree 5, connects to 2 communities
- [[escape_literal_newlines_in_strings()]] - degree 4, connects to 2 communities
- [[format_calendar()]] - degree 6, connects to 1 community