---
type: community
cohesion: 0.20
members: 18
---

# Dashboard — Billing, Hook

**Cohesion:** 0.20 - loosely connected
**Members:** 18 nodes

## Members
- [[BillingPage()]] - code - dashboard/src/pages/BillingPage.tsx
- [[BillingPage.tsx]] - code - dashboard/src/pages/BillingPage.tsx
- [[BillingPlan]] - code - dashboard/src/hooks/useBilling.ts
- [[List available billing plans from Supabase.]] - rationale - dashboard_api.py
- [[Payment]] - code - dashboard/src/hooks/useBilling.ts
- [[PlanCard()]] - code - dashboard/src/pages/BillingPage.tsx
- [[StatusBadge()]] - code - dashboard/src/pages/BillingPage.tsx
- [[Subscription]] - code - dashboard/src/hooks/useBilling.ts
- [[UsageData]] - code - dashboard/src/hooks/useBilling.ts
- [[formatINR()_1]] - code - dashboard/src/pages/BillingPage.tsx
- [[planIcons]] - code - dashboard/src/pages/BillingPage.tsx
- [[useBilling.ts]] - code - dashboard/src/hooks/useBilling.ts
- [[useBillingPlans()]] - code - dashboard/src/hooks/useBilling.ts
- [[useCancelSubscription()]] - code - dashboard/src/hooks/useBilling.ts
- [[usePayments()]] - code - dashboard/src/hooks/useBilling.ts
- [[useSubscribe()]] - code - dashboard/src/hooks/useBilling.ts
- [[useSubscription()]] - code - dashboard/src/hooks/useBilling.ts
- [[useUsage()]] - code - dashboard/src/hooks/useBilling.ts

## Live Query (requires Dataview plugin)

```dataview
TABLE source_file, type FROM #community/Dashboard__Billing_Hook
SORT file.name ASC
```

## Connections to other communities
- 7 edges to [[_COMMUNITY_Dashboard — Insight, Brand]]
- 3 edges to [[_COMMUNITY_Dashboard — Ui, Component]]
- 2 edges to [[_COMMUNITY_Billing — Script, Config]]
- 1 edge to [[_COMMUNITY_Mixed — Api, Brand]]
- 1 edge to [[_COMMUNITY_Dashboard — Store, Auth]]
- 1 edge to [[_COMMUNITY_Dashboard — Brand, Agent]]
- 1 edge to [[_COMMUNITY_Dashboard — Page, Hook]]

## Top bridge nodes
- [[useBilling.ts]] - degree 15, connects to 3 communities
- [[BillingPage.tsx]] - degree 15, connects to 2 communities
- [[useSubscription()]] - degree 6, connects to 2 communities
- [[BillingPlan]] - degree 4, connects to 1 community
- [[useCancelSubscription()]] - degree 4, connects to 1 community