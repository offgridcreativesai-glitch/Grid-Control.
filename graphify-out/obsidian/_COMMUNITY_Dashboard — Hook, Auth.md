---
type: community
cohesion: 0.16
members: 18
---

# Dashboard — Hook, Auth

**Cohesion:** 0.16 - loosely connected
**Members:** 18 nodes

## Members
- [[.componentDidCatch()]] - code - dashboard/src/App.tsx
- [[.constructor()]] - code - dashboard/src/App.tsx
- [[.getDerivedStateFromError()]] - code - dashboard/src/App.tsx
- [[.render()]] - code - dashboard/src/App.tsx
- [[AdminGuard()]] - code - dashboard/src/App.tsx
- [[App()]] - code - dashboard/src/App.tsx
- [[App.tsx]] - code - dashboard/src/App.tsx
- [[AuthGate()]] - code - dashboard/src/App.tsx
- [[AuthPage()]] - code - dashboard/src/pages/AuthPage.tsx
- [[ErrorBoundary]] - code - dashboard/src/App.tsx
- [[OnboardingGuard()]] - code - dashboard/src/App.tsx
- [[SSEEvent]] - code - dashboard/src/hooks/useSSE.ts
- [[SSEProvider()]] - code - dashboard/src/App.tsx
- [[queryClient]] - code - dashboard/src/App.tsx
- [[useAuthStore]] - code - dashboard/src/store/authStore.ts
- [[useBrands()]] - code - dashboard/src/hooks/useGridApi.ts
- [[useSSE()]] - code - dashboard/src/hooks/useSSE.ts
- [[useSSE.ts]] - code - dashboard/src/hooks/useSSE.ts

## Live Query (requires Dataview plugin)

```dataview
TABLE source_file, type FROM #community/Dashboard__Hook_Auth
SORT file.name ASC
```

## Connections to other communities
- 5 edges to [[_COMMUNITY_Dashboard — Brain, Layout]]
- 4 edges to [[_COMMUNITY_Dashboard — Hook, Page]]
- 4 edges to [[_COMMUNITY_Dashboard — Ui, Button]]
- 3 edges to [[_COMMUNITY_Dashboard — Hook, Api]]
- 3 edges to [[_COMMUNITY_Dashboard — Data, Calendar]]
- 3 edges to [[_COMMUNITY_Dashboard — Insight, Brand]]
- 2 edges to [[_COMMUNITY_Dashboard — Ui, Layout]]
- 2 edges to [[_COMMUNITY_Dashboard — Store, Auth]]
- 2 edges to [[_COMMUNITY_Dashboard — Hook, Page]]
- 1 edge to [[_COMMUNITY_Dashboard — Page, System]]
- 1 edge to [[_COMMUNITY_Database — Supabase, Brand]]

## Top bridge nodes
- [[App.tsx]] - degree 32, connects to 10 communities
- [[useAuthStore]] - degree 10, connects to 4 communities
- [[useSSE.ts]] - degree 5, connects to 2 communities
- [[OnboardingGuard()]] - degree 4, connects to 1 community
- [[useBrands()]] - degree 3, connects to 1 community