---
type: community
cohesion: 0.35
members: 11
---

# Dashboard — Hook, Page

**Cohesion:** 0.35 - loosely connected
**Members:** 11 nodes

## Members
- [[MemberRow()]] - code - dashboard/src/pages/TeamPage.tsx
- [[RoleBadge()]] - code - dashboard/src/pages/TeamPage.tsx
- [[TeamMember]] - code - dashboard/src/hooks/useTeam.ts
- [[TeamPage()]] - code - dashboard/src/pages/TeamPage.tsx
- [[TeamPage.tsx]] - code - dashboard/src/pages/TeamPage.tsx
- [[roleConfig]] - code - dashboard/src/pages/TeamPage.tsx
- [[useInviteMember()]] - code - dashboard/src/hooks/useTeam.ts
- [[useRemoveMember()]] - code - dashboard/src/hooks/useTeam.ts
- [[useTeam.ts]] - code - dashboard/src/hooks/useTeam.ts
- [[useTeamMembers()]] - code - dashboard/src/hooks/useTeam.ts
- [[useUpdateRole()]] - code - dashboard/src/hooks/useTeam.ts

## Live Query (requires Dataview plugin)

```dataview
TABLE source_file, type FROM #community/Dashboard__Hook_Page
SORT file.name ASC
```

## Connections to other communities
- 6 edges to [[_COMMUNITY_Dashboard — Insight, Brand]]
- 2 edges to [[_COMMUNITY_Dashboard — Store, Auth]]
- 2 edges to [[_COMMUNITY_Dashboard — Ui, Component]]
- 2 edges to [[_COMMUNITY_Dashboard — Hook, Auth]]
- 1 edge to [[_COMMUNITY_Dashboard — Brand, Agent]]
- 1 edge to [[_COMMUNITY_Dashboard — Page, Hook]]

## Top bridge nodes
- [[TeamPage.tsx]] - degree 14, connects to 4 communities
- [[useTeam.ts]] - degree 10, connects to 3 communities
- [[useInviteMember()]] - degree 4, connects to 1 community
- [[useRemoveMember()]] - degree 4, connects to 1 community
- [[useTeamMembers()]] - degree 4, connects to 1 community