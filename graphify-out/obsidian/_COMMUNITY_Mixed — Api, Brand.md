---
type: community
cohesion: 0.04
members: 68
---

# Mixed — Api, Brand

**Cohesion:** 0.04 - loosely connected
**Members:** 68 nodes

## Members
- [[Approved + scheduled + published posts across all platforms.      Reads       -]] - rationale - dashboard_api.py
- [[Called by agent scripts at end of each run to record token counts.     Body { r]] - rationale - dashboard_api.py
- [[Chain Trend Researcher → Data Analyst → Script Writer in a background thread.]] - rationale - dashboard_api.py
- [[Check if the current user is a super admin.]] - rationale - dashboard_api.py
- [[Decorator — accepts Supabase JWT (Authorization Bearer) or legacy X-Dashboard-S]] - rationale - dashboard_api.py
- [[Decorator — only allows super_admin users. Must be used after require_auth.]] - rationale - dashboard_api.py
- [[Decorator — verifies the authenticated user has access to the requested brand.]] - rationale - dashboard_api.py
- [[Extract voice DNA from raw script samples.     Calls Claude to analyze writing p]] - rationale - dashboard_api.py
- [[For each brand in Supabase, ensure session_state has all required keys.]] - rationale - dashboard_api.py
- [[GRID CONTROL — Flask Dashboard API Port 5001 Serves real data from brands fold]] - rationale - dashboard_api.py
- [[Generate a brief team standup summary from session state + recent agent activity]] - rationale - dashboard_api.py
- [[Global SSE stream — client subscribes to get live agent activity updates.]] - rationale - dashboard_api.py
- [[Jarvis spoken query endpoint.     Takes a natural language question, answers in]] - rationale - dashboard_api.py
- [[Phase 4 Step 1 — Live connection validator. Each check has a 5s timeout.     Run]] - rationale - dashboard_api.py
- [[Pull human-readable meta + media paths from an agent JSON output.      Returns d]] - rationale - dashboard_api.py
- [[Razorpay webhook handler. Updates subscriptionpayment status.]] - rationale - dashboard_api.py
- [[Return brands for authenticated user.]] - rationale - dashboard_api.py
- [[Return current performance_history.json or empty skeleton if not yet computed.]] - rationale - dashboard_api.py
- [[Return standard error envelope for any unhandled exception.]] - rationale - dashboard_api.py
- [[Return the full text content of an output file for in-dashboard reading.]] - rationale - dashboard_api.py
- [[Return voice_profile.json for a brand, or {exists false} if not created yet.]] - rationale - dashboard_api.py
- [[Returns a flat summary card for the Brand Dashboard screen     brand_profile fi]] - rationale - dashboard_api.py
- [[Returns which API keys are configured (never exposes the keys themselves).]] - rationale - dashboard_api.py
- [[SSE endpoint. Polls Supabase agent_run row every 2s.     Closes stream when stat]] - rationale - dashboard_api.py
- [[Save feedback for an agent, reset its status to idle so it can be re-run.]] - rationale - dashboard_api.py
- [[Verify subscription payment after Razorpay checkout.]] - rationale - dashboard_api.py
- [[_enrich_agents_with_flags()]] - code - dashboard_api.py
- [[_extract_output_meta()]] - code - dashboard_api.py
- [[_verify_session_states()]] - code - dashboard_api.py
- [[admin_check()]] - code - dashboard_api.py
- [[agent_request_changes()]] - code - dashboard_api.py
- [[agent_run_status()]] - code - dashboard_api.py
- [[agent_train()]] - code - dashboard_api.py
- [[billing_verify()]] - code - dashboard_api.py
- [[billing_webhook()]] - code - dashboard_api.py
- [[check_connections()]] - code - dashboard_api.py
- [[daily_pipeline_run()]] - code - dashboard_api.py
- [[dashboard_api.py]] - code - dashboard_api.py
- [[get_agent_log()]] - code - dashboard_api.py
- [[get_agents_list()]] - code - dashboard_api.py
- [[get_agents_status()]] - code - dashboard_api.py
- [[get_all_outputs()]] - code - dashboard_api.py
- [[get_brand_dashboard()]] - code - dashboard_api.py
- [[get_brand_dir()]] - code - dashboard_api.py
- [[get_brand_profile()]] - code - dashboard_api.py
- [[get_brand_summary()]] - code - dashboard_api.py
- [[get_brands()]] - code - dashboard_api.py
- [[get_key_status()]] - code - dashboard_api.py
- [[get_my_brands()]] - code - dashboard_api.py
- [[get_notion_cards()]] - code - dashboard_api.py
- [[get_output_content()]] - code - dashboard_api.py
- [[get_published()]] - code - dashboard_api.py
- [[handle_404()]] - code - dashboard_api.py
- [[handle_405()]] - code - dashboard_api.py
- [[handle_exception()]] - code - dashboard_api.py
- [[health()]] - code - dashboard_api.py
- [[jarvis_query()]] - code - dashboard_api.py
- [[list_brands()]] - code - dashboard_api.py
- [[performance_history()]] - code - dashboard_api.py
- [[record_agent_cost()]] - code - dashboard_api.py
- [[require_auth()]] - code - dashboard_api.py
- [[require_brand_access()]] - code - dashboard_api.py
- [[require_super_admin()]] - code - dashboard_api.py
- [[save_brand_profile()]] - code - dashboard_api.py
- [[sse_events()]] - code - dashboard_api.py
- [[team_standup()]] - code - dashboard_api.py
- [[voice_extract_profile()]] - code - dashboard_api.py
- [[voice_get_profile()]] - code - dashboard_api.py

## Live Query (requires Dataview plugin)

```dataview
TABLE source_file, type FROM #community/Mixed__Api_Brand
SORT file.name ASC
```

## Connections to other communities
- 30 edges to [[_COMMUNITY_Dashboard — Api, Brand]]
- 26 edges to [[_COMMUNITY_Dashboard — Api, Agent]]
- 17 edges to [[_COMMUNITY_Dashboard — Api, Billing]]
- 9 edges to [[_COMMUNITY_Utils — Api, Agent]]
- 6 edges to [[_COMMUNITY_Mixed — Api, Brain]]
- 5 edges to [[_COMMUNITY_Notion_Integration — Brain, Api]]
- 4 edges to [[_COMMUNITY_Dashboard — Hook, Page]]
- 3 edges to [[_COMMUNITY_Mixed — Api]]
- 2 edges to [[_COMMUNITY_Agent System — Skill, Brand]]
- 2 edges to [[_COMMUNITY_Agent Prompts — Ui, Store]]
- 2 edges to [[_COMMUNITY_Mixed — Api, Agent]]
- 2 edges to [[_COMMUNITY_Mixed — Api]]
- 2 edges to [[_COMMUNITY_Mixed — Api]]
- 1 edge to [[_COMMUNITY_Dashboard — Billing, Hook]]
- 1 edge to [[_COMMUNITY_Agent Prompts — Store, Brand]]
- 1 edge to [[_COMMUNITY_Ceo_Brain — Api, Brand]]
- 1 edge to [[_COMMUNITY_Database — Supabase, Brand]]

## Top bridge nodes
- [[dashboard_api.py]] - degree 145, connects to 17 communities
- [[get_brand_dir()]] - degree 17, connects to 3 communities
- [[_extract_output_meta()]] - degree 5, connects to 2 communities
- [[voice_extract_profile()]] - degree 4, connects to 1 community
- [[get_agents_status()]] - degree 3, connects to 1 community