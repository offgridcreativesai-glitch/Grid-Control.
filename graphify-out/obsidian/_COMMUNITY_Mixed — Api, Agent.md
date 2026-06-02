---
type: community
cohesion: 0.50
members: 4
---

# Mixed — Api, Agent

**Cohesion:** 0.50 - moderately connected
**Members:** 4 nodes

## Members
- [[Group Meeting Room — dynamic @mention routing.     Body { brand_slug str, mess]] - rationale - dashboard_api.py
- [[Return persisted conversation history for a brand+agent pair.]] - rationale - dashboard_api.py
- [[agent_group_chat()]] - code - dashboard_api.py
- [[get_conversation()]] - code - dashboard_api.py

## Live Query (requires Dataview plugin)

```dataview
TABLE source_file, type FROM #community/Mixed__Api_Agent
SORT file.name ASC
```

## Connections to other communities
- 2 edges to [[_COMMUNITY_Mixed — Api, Brand]]
- 2 edges to [[_COMMUNITY_Dashboard — Api, Brand]]
- 1 edge to [[_COMMUNITY_Dashboard — Api, Agent]]

## Top bridge nodes
- [[agent_group_chat()]] - degree 5, connects to 3 communities
- [[get_conversation()]] - degree 4, connects to 2 communities