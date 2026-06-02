# Dashboard — Hook, Page

> 20 nodes · cohesion 0.12

## Key Concepts

- **useAdmin.ts** (12 connections) — `dashboard/src/hooks/useAdmin.ts`
- **AdminRevenue** (9 connections) — `dashboard/src/hooks/useAdmin.ts`
- **AdminClient** (8 connections) — `dashboard/src/hooks/useAdmin.ts`
- **AdminOverviewPage.tsx** (6 connections) — `dashboard/src/pages/AdminOverviewPage.tsx`
- **AdminSystemPage()** (6 connections) — `dashboard/src/pages/AdminSystemPage.tsx`
- **AdminOverview** (3 connections) — `dashboard/src/hooks/useAdmin.ts`
- **AdminSystem** (3 connections) — `dashboard/src/hooks/useAdmin.ts`
- **useAdminClients()** (2 connections) — `dashboard/src/hooks/useAdmin.ts`
- **useAdminOverview()** (2 connections) — `dashboard/src/hooks/useAdmin.ts`
- **useAdminRevenue()** (2 connections) — `dashboard/src/hooks/useAdmin.ts`
- **useAdminSystem()** (2 connections) — `dashboard/src/hooks/useAdmin.ts`
- **StatusBadge()** (2 connections) — `dashboard/src/pages/AdminClientsPage.tsx`
- **KpiCard()** (2 connections) — `dashboard/src/pages/AdminOverviewPage.tsx`
- **PaymentStatus()** (2 connections) — `dashboard/src/pages/AdminRevenuePage.tsx`
- **StatCard()** (2 connections) — `dashboard/src/pages/AdminSystemPage.tsx`
- **Business overview — MRR, client count, costs, agent stats.** (1 connections) — `dashboard_api.py`
- **All brands with owner info, plan, status, costs.** (1 connections) — `dashboard_api.py`
- **Payment history + MRR timeline.** (1 connections) — `dashboard_api.py`
- **System health — agent runs, error rates, cost breakdown.** (1 connections) — `dashboard_api.py`
- **formatINR()** (1 connections) — `dashboard/src/pages/AdminRevenuePage.tsx`

## Relationships

- [[Dashboard — Ui, Component]] (8 shared connections)
- [[Dashboard — Hook, Auth]] (4 shared connections)
- [[Dashboard — Page, Hook]] (4 shared connections)
- [[Mixed — Api, Brand]] (4 shared connections)
- [[Dashboard — Store, Auth]] (1 shared connections)
- [[Dashboard — Brand, Agent]] (1 shared connections)

## Source Files

- `dashboard/src/hooks/useAdmin.ts`
- `dashboard/src/pages/AdminClientsPage.tsx`
- `dashboard/src/pages/AdminOverviewPage.tsx`
- `dashboard/src/pages/AdminRevenuePage.tsx`
- `dashboard/src/pages/AdminSystemPage.tsx`
- `dashboard_api.py`

## Audit Trail

- EXTRACTED: 68 (100%)
- INFERRED: 0 (0%)
- AMBIGUOUS: 0 (0%)

---

*Part of the graphify knowledge wiki. See [[index]] to navigate.*