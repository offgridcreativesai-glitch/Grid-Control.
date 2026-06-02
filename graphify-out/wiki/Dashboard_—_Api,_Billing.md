# Dashboard — Api, Billing

> 34 nodes · cohesion 0.06

## Key Concepts

- **_resolve_brand_id()** (19 connections) — `dashboard_api.py`
- **LearningStats** (4 connections) — `dashboard/src/hooks/useLearning.ts`
- **billing_cancel()** (3 connections) — `dashboard_api.py`
- **billing_get_subscription()** (3 connections) — `dashboard_api.py`
- **billing_payments()** (3 connections) — `dashboard_api.py`
- **billing_subscribe()** (3 connections) — `dashboard_api.py`
- **billing_usage()** (3 connections) — `dashboard_api.py`
- **learning_capture()** (3 connections) — `dashboard_api.py`
- **learning_list()** (3 connections) — `dashboard_api.py`
- **notifications_pending_summary()** (3 connections) — `dashboard_api.py`
- **notifications_send_digest()** (3 connections) — `dashboard_api.py`
- **output_revise()** (3 connections) — `dashboard_api.py`
- **output_revisions()** (3 connections) — `dashboard_api.py`
- **team_invite()** (3 connections) — `dashboard_api.py`
- **team_members()** (3 connections) — `dashboard_api.py`
- **team_remove()** (3 connections) — `dashboard_api.py`
- **team_update_role()** (3 connections) — `dashboard_api.py`
- **Resolve a brand_slug to its UUID brand_id. Pass-through if already a UUID.** (1 connections) — `dashboard_api.py`
- **Get the active subscription for a brand.** (1 connections) — `dashboard_api.py`
- **Create a Razorpay subscription for a brand.** (1 connections) — `dashboard_api.py`
- **Cancel a subscription (at end of billing cycle).** (1 connections) — `dashboard_api.py`
- **Get usage stats for a brand (current month).** (1 connections) — `dashboard_api.py`
- **Get payment history for a brand.** (1 connections) — `dashboard_api.py`
- **Request a revision on a rejected/approved output.     Body: { brand_slug, output** (1 connections) — `dashboard_api.py`
- **Get revision history for a brand.** (1 connections) — `dashboard_api.py`
- *... and 9 more nodes in this community*

## Relationships

- [[Mixed — Api, Brand]] (17 shared connections)
- [[Dashboard — Insight, Brand]] (1 shared connections)
- [[Dashboard — Api, Brand]] (1 shared connections)

## Source Files

- `dashboard/src/hooks/useLearning.ts`
- `dashboard_api.py`

## Audit Trail

- EXTRACTED: 85 (100%)
- INFERRED: 0 (0%)
- AMBIGUOUS: 0 (0%)

---

*Part of the graphify knowledge wiki. See [[index]] to navigate.*