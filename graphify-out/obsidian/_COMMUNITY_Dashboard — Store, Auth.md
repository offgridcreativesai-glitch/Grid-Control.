---
type: community
cohesion: 0.36
members: 8
---

# Dashboard — Store, Auth

**Cohesion:** 0.36 - loosely connected
**Members:** 8 nodes

## Members
- [[AuthState]] - code - dashboard/src/store/authStore.ts
- [[ViewMode]] - code - dashboard/src/store/authStore.ts
- [[api.ts]] - code - dashboard/src/lib/api.ts
- [[authStore.ts]] - code - dashboard/src/store/authStore.ts
- [[checkSuperAdmin()]] - code - dashboard/src/store/authStore.ts
- [[initSupabase()]] - code - dashboard/src/lib/supabase.ts
- [[supabase]] - code - dashboard/src/lib/supabase.ts
- [[supabase.ts]] - code - dashboard/src/lib/supabase.ts

## Live Query (requires Dataview plugin)

```dataview
TABLE source_file, type FROM #community/Dashboard__Store_Auth
SORT file.name ASC
```

## Connections to other communities
- 5 edges to [[_COMMUNITY_Dashboard — Brand, Agent]]
- 3 edges to [[_COMMUNITY_Dashboard — Insight, Brand]]
- 2 edges to [[_COMMUNITY_Dashboard — Hook, Auth]]
- 2 edges to [[_COMMUNITY_Dashboard — Brain, Layout]]
- 2 edges to [[_COMMUNITY_Dashboard — Hook, Page]]
- 2 edges to [[_COMMUNITY_Dashboard — Ui, Button]]
- 1 edge to [[_COMMUNITY_Dashboard — System]]
- 1 edge to [[_COMMUNITY_Dashboard — Review, Content]]
- 1 edge to [[_COMMUNITY_Dashboard — Agent, Button]]
- 1 edge to [[_COMMUNITY_Dashboard — Ui, Layout]]
- 1 edge to [[_COMMUNITY_Dashboard — Hook, Page]]
- 1 edge to [[_COMMUNITY_Dashboard — Hook, Api]]
- 1 edge to [[_COMMUNITY_Dashboard — Billing, Hook]]

## Top bridge nodes
- [[api.ts]] - degree 19, connects to 11 communities
- [[authStore.ts]] - degree 12, connects to 5 communities
- [[checkSuperAdmin()]] - degree 2, connects to 1 community