---
type: community
cohesion: 0.11
members: 31
---

# Dashboard — Page, System

**Cohesion:** 0.11 - loosely connected
**Members:** 31 nodes

## Members
- [[APIKeysSettings()]] - code - dashboard/src/pages/SystemPage.tsx
- [[ActivityLogSettings()]] - code - dashboard/src/pages/SystemPage.tsx
- [[AgentCard()]] - code - dashboard/src/pages/AgentsPage.tsx
- [[AgentDetail()]] - code - dashboard/src/pages/AgentsPage.tsx
- [[AgentsPage()]] - code - dashboard/src/pages/AgentsPage.tsx
- [[AutonomySettings()]] - code - dashboard/src/pages/SystemPage.tsx
- [[BrandSettings()]] - code - dashboard/src/pages/SystemPage.tsx
- [[ConnectionRow()]] - code - dashboard/src/pages/SystemPage.tsx
- [[ConnectionsSettings()]] - code - dashboard/src/pages/SystemPage.tsx
- [[InsightsPage()]] - code - dashboard/src/pages/InsightsPage.tsx
- [[PLATFORMS_2]] - code - dashboard/src/pages/InsightsPage.tsx
- [[PLATFORMS_4]] - code - dashboard/src/pages/SystemPage.tsx
- [[PLATFORM_KEYS]] - code - dashboard/src/pages/SystemPage.tsx
- [[PerfPost]] - code - dashboard/src/pages/InsightsPage.tsx
- [[SERVICE_LABELS]] - code - dashboard/src/pages/SystemPage.tsx
- [[Switch()]] - code - dashboard/src/components/ui/switch.tsx
- [[SystemPage()]] - code - dashboard/src/pages/SystemPage.tsx
- [[Tabs()]] - code - dashboard/src/components/ui/tabs.tsx
- [[TabsContent()]] - code - dashboard/src/components/ui/tabs.tsx
- [[TabsList()]] - code - dashboard/src/components/ui/tabs.tsx
- [[TabsTrigger()]] - code - dashboard/src/components/ui/tabs.tsx
- [[formatTimeAgo()]] - code - dashboard/src/lib/utils.ts
- [[inferPlat()]] - code - dashboard/src/pages/InsightsPage.tsx
- [[switch.tsx]] - code - dashboard/src/components/ui/switch.tsx
- [[tabs.tsx]] - code - dashboard/src/components/ui/tabs.tsx
- [[useAgentStatus()]] - code - dashboard/src/hooks/useGridApi.ts
- [[useBrandDashboard()]] - code - dashboard/src/hooks/useGridApi.ts
- [[useConnections()]] - code - dashboard/src/hooks/useGridApi.ts
- [[useLiveAgents()]] - code - dashboard/src/hooks/useGridApi.ts
- [[usePerformanceHistory()]] - code - dashboard/src/hooks/useGridApi.ts
- [[useRunAgent()]] - code - dashboard/src/hooks/useGridApi.ts

## Live Query (requires Dataview plugin)

```dataview
TABLE source_file, type FROM #community/Dashboard__Page_System
SORT file.name ASC
```

## Connections to other communities
- 16 edges to [[_COMMUNITY_Dashboard — Page, Hook]]
- 13 edges to [[_COMMUNITY_Dashboard — Ui, Component]]
- 13 edges to [[_COMMUNITY_Dashboard — Hook, Api]]
- 10 edges to [[_COMMUNITY_Dashboard — Data, Calendar]]
- 7 edges to [[_COMMUNITY_Dashboard — Brain, Layout]]
- 4 edges to [[_COMMUNITY_Dashboard — Insight, Brand]]
- 4 edges to [[_COMMUNITY_Dashboard — Ui, Button]]
- 1 edge to [[_COMMUNITY_Dashboard — Hook, Auth]]

## Top bridge nodes
- [[AgentsPage()]] - degree 23, connects to 6 communities
- [[InsightsPage()]] - degree 21, connects to 6 communities
- [[SystemPage()]] - degree 32, connects to 5 communities
- [[usePerformanceHistory()]] - degree 5, connects to 4 communities
- [[useAgentStatus()]] - degree 4, connects to 3 communities