---
type: community
cohesion: 0.06
members: 34
---

# Dashboard — Api, Billing

**Cohesion:** 0.06 - loosely connected
**Members:** 34 nodes

## Members
- [[Cancel a subscription (at end of billing cycle).]] - rationale - dashboard_api.py
- [[Capture a learningpattern from an agent run.     Body { brand_slug, agent_slug]] - rationale - dashboard_api.py
- [[Create a Razorpay subscription for a brand.]] - rationale - dashboard_api.py
- [[Get count of pending approvals per brand for email digest.]] - rationale - dashboard_api.py
- [[Get learning stats for a brand — 'your agents learned X things this month'.]] - rationale - dashboard_api.py
- [[Get payment history for a brand.]] - rationale - dashboard_api.py
- [[Get revision history for a brand.]] - rationale - dashboard_api.py
- [[Get the active subscription for a brand.]] - rationale - dashboard_api.py
- [[Get usage stats for a brand (current month).]] - rationale - dashboard_api.py
- [[Invite a user to a brand team.     Body { brand_slug, email, role }  role = adm]] - rationale - dashboard_api.py
- [[LearningStats]] - code - dashboard/src/hooks/useLearning.ts
- [[List captured learnings for a brand, optionally filtered by agent.]] - rationale - dashboard_api.py
- [[List team members for a brand.]] - rationale - dashboard_api.py
- [[Remove a team member from a brand.     Body { brand_slug, user_id }]] - rationale - dashboard_api.py
- [[Request a revision on a rejectedapproved output.     Body { brand_slug, output]] - rationale - dashboard_api.py
- [[Resolve a brand_slug to its UUID brand_id. Pass-through if already a UUID.]] - rationale - dashboard_api.py
- [[Send an email digest of pending approvals.     Body { brand_slug, recipient_ema]] - rationale - dashboard_api.py
- [[Update a team member's role.     Body { brand_slug, user_id, role }]] - rationale - dashboard_api.py
- [[_resolve_brand_id()]] - code - dashboard_api.py
- [[billing_cancel()]] - code - dashboard_api.py
- [[billing_get_subscription()]] - code - dashboard_api.py
- [[billing_payments()]] - code - dashboard_api.py
- [[billing_subscribe()]] - code - dashboard_api.py
- [[billing_usage()]] - code - dashboard_api.py
- [[learning_capture()]] - code - dashboard_api.py
- [[learning_list()]] - code - dashboard_api.py
- [[notifications_pending_summary()]] - code - dashboard_api.py
- [[notifications_send_digest()]] - code - dashboard_api.py
- [[output_revise()]] - code - dashboard_api.py
- [[output_revisions()]] - code - dashboard_api.py
- [[team_invite()]] - code - dashboard_api.py
- [[team_members()]] - code - dashboard_api.py
- [[team_remove()]] - code - dashboard_api.py
- [[team_update_role()]] - code - dashboard_api.py

## Live Query (requires Dataview plugin)

```dataview
TABLE source_file, type FROM #community/Dashboard__Api_Billing
SORT file.name ASC
```

## Connections to other communities
- 17 edges to [[_COMMUNITY_Mixed — Api, Brand]]
- 1 edge to [[_COMMUNITY_Dashboard — Api, Brand]]
- 1 edge to [[_COMMUNITY_Dashboard — Insight, Brand]]

## Top bridge nodes
- [[_resolve_brand_id()]] - degree 19, connects to 2 communities
- [[LearningStats]] - degree 4, connects to 2 communities
- [[billing_cancel()]] - degree 3, connects to 1 community
- [[billing_get_subscription()]] - degree 3, connects to 1 community
- [[billing_payments()]] - degree 3, connects to 1 community