---
type: community
cohesion: 0.50
members: 4
---

# Mixed — Api

**Cohesion:** 0.50 - moderately connected
**Members:** 4 nodes

## Members
- [[Persist a platform API token to .env and reload it immediately.     Body { pla]] - rationale - dashboard_api.py
- [[Update or append a key=value line in the .env file, then reload into os.environ.]] - rationale - dashboard_api.py
- [[_write_env_token()]] - code - dashboard_api.py
- [[save_connection_token()]] - code - dashboard_api.py

## Live Query (requires Dataview plugin)

```dataview
TABLE source_file, type FROM #community/Mixed__Api
SORT file.name ASC
```

## Connections to other communities
- 2 edges to [[_COMMUNITY_Mixed — Api, Brand]]
- 1 edge to [[_COMMUNITY_Dashboard — Api, Brand]]

## Top bridge nodes
- [[_write_env_token()]] - degree 4, connects to 2 communities
- [[save_connection_token()]] - degree 3, connects to 1 community