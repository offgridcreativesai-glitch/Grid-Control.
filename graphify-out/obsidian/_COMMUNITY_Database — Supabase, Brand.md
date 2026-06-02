---
type: community
cohesion: 0.06
members: 67
---

# Database — Supabase, Brand

**Cohesion:** 0.06 - loosely connected
**Members:** 67 nodes

## Members
- [[Add a user to a brand by email. Returns the membership row.]] - rationale - supabase/db.py
- [[Check if user has super_admin flag.]] - rationale - supabase/db.py
- [[Client]] - code - supabase/db.py
- [[Create a brand and add the creator as admin. Returns the brand row.]] - rationale - supabase/db.py
- [[Estimate USD cost for a single API call.]] - rationale - utils/pricing.py
- [[Return admin client (service_role, bypasses RLS). Falls back to public.]] - rationale - supabase/db.py
- [[Return all brand memberships with profile + brand info.]] - rationale - supabase/db.py
- [[Return all brand_memory files for a brand.]] - rationale - dashboard_api.py
- [[Return all brands (super admin only).]] - rationale - supabase/db.py
- [[Return all brands the user is a member of.]] - rationale - supabase/db.py
- [[Return all stored memory entries from Supabase for a brand (all agents or filter]] - rationale - dashboard_api.py
- [[Return all subscriptions with plan info.]] - rationale - supabase/db.py
- [[Return recent agent runs across all brands.]] - rationale - supabase/db.py
- [[Return recent payments across all brands.]] - rationale - supabase/db.py
- [[Return usage logs across all brands from month_start.]] - rationale - supabase/db.py
- [[Return user's role for a brand, or None if no access.]] - rationale - supabase/db.py
- [[Single source of truth for model pricing (USD per 1M tokens, May 2026). Both age]] - rationale - utils/pricing.py
- [[Verify a Supabase JWT and return the user object. None if invalid.]] - rationale - supabase/db.py
- [[_now()]] - code - supabase/db.py
- [[_svc()]] - code - supabase/db.py
- [[add_brand_member()]] - code - supabase/db.py
- [[approve_output()_1]] - code - supabase/db.py
- [[bool_9]] - code - supabase/db.py
- [[check_brand_access()]] - code - supabase/db.py
- [[create_brand_with_owner()]] - code - supabase/db.py
- [[db.py]] - code - supabase/db.py
- [[estimate_cost()]] - code - utils/pricing.py
- [[float_6]] - code - supabase/db.py
- [[float_5]] - code - utils/pricing.py
- [[get_agent_run()]] - code - supabase/db.py
- [[get_all_agent_runs()]] - code - supabase/db.py
- [[get_all_brand_members()]] - code - supabase/db.py
- [[get_all_brand_memory()]] - code - supabase/db.py
- [[get_all_brands()]] - code - supabase/db.py
- [[get_all_payments()]] - code - supabase/db.py
- [[get_all_subscriptions()]] - code - supabase/db.py
- [[get_brand()]] - code - supabase/db.py
- [[get_brand_memory()]] - code - supabase/db.py
- [[get_brand_monthly_costs()]] - code - supabase/db.py
- [[get_conversation()_1]] - code - supabase/db.py
- [[get_global_usage_stats()]] - code - supabase/db.py
- [[get_output_history()]] - code - supabase/db.py
- [[get_outputs_by_agent()]] - code - supabase/db.py
- [[get_pending_outputs()_1]] - code - supabase/db.py
- [[get_profile()]] - code - supabase/db.py
- [[get_session_state()]] - code - supabase/db.py
- [[get_user_brands()]] - code - supabase/db.py
- [[int_14]] - code - supabase/db.py
- [[int_12]] - code - utils/pricing.py
- [[is_super_admin()]] - code - supabase/db.py
- [[log_audit()]] - code - supabase/db.py
- [[main.tsx]] - code - dashboard/src/main.tsx
- [[pricing.py]] - code - utils/pricing.py
- [[reject_output()_1]] - code - supabase/db.py
- [[save_agent_output()_1]] - code - supabase/db.py
- [[save_agent_run()]] - code - supabase/db.py
- [[save_brand_memory()]] - code - supabase/db.py
- [[save_conversation()]] - code - supabase/db.py
- [[str_31]] - code - supabase/db.py
- [[str_25]] - code - utils/pricing.py
- [[supabasedb.py — GRID CONTROL Supabase Integration Layer  Two clients   _admin]] - rationale - supabase/db.py
- [[update_agent_run_costs()]] - code - supabase/db.py
- [[update_agent_run_status()]] - code - supabase/db.py
- [[update_output_notion_id()]] - code - supabase/db.py
- [[upsert_brand()]] - code - supabase/db.py
- [[upsert_session_state()]] - code - supabase/db.py
- [[verify_jwt()]] - code - supabase/db.py

## Live Query (requires Dataview plugin)

```dataview
TABLE source_file, type FROM #community/Database__Supabase_Brand
SORT file.name ASC
```

## Connections to other communities
- 3 edges to [[_COMMUNITY_Dashboard — Api, Brand]]
- 2 edges to [[_COMMUNITY_Agent System — Pipeline, Supabase]]
- 1 edge to [[_COMMUNITY_Mixed — Api, Brand]]
- 1 edge to [[_COMMUNITY_Dashboard — Api, Agent]]
- 1 edge to [[_COMMUNITY_Dashboard — Hook, Auth]]

## Top bridge nodes
- [[get_brand_memory()]] - degree 10, connects to 3 communities
- [[estimate_cost()]] - degree 9, connects to 1 community
- [[main.tsx]] - degree 2, connects to 1 community