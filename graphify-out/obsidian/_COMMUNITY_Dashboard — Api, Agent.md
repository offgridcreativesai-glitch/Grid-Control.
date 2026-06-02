---
type: community
cohesion: 0.08
members: 36
---

# Dashboard — Api, Agent

**Cohesion:** 0.08 - loosely connected
**Members:** 36 nodes

## Members
- [[After completed_slug is approved mark it done, set next_agent in session_state.]] - rationale - dashboard_api.py
- [[Background thread run agent script, update session state + Supabase on finish.]] - rationale - dashboard_api.py
- [[Extract approved output as a learned skill (fire-and-forget).]] - rationale - dashboard_api.py
- [[Patch agent skill with rejection lesson (fire-and-forget).]] - rationale - dashboard_api.py
- [[Path]] - code - dashboard_api.py
- [[Phase 3 Step 2 — Check Notion for approved pages, sync status back to Supabase.]] - rationale - dashboard_api.py
- [[Push an event to all SSE subscribers. Non-blocking.]] - rationale - dashboard_api.py
- [[Remove markdown syntax for clean plain-English display in the UI.     Strips]] - rationale - dashboard_api.py
- [[Resolve brand_slug → Supabase brand_id. Returns None if db unavailable or brand]] - rationale - dashboard_api.py
- [[Resolve user-supplied path relative to base and verify it stays inside base.]] - rationale - dashboard_api.py
- [[Return CEO Brain's recommended next agent and reason.     Phase 1 Step 2.]] - rationale - dashboard_api.py
- [[Return monthly cost breakdown for a brand.     Query params year (int, default]] - rationale - dashboard_api.py
- [[Return version history for an agent's outputs. Phase 1 Step 3.]] - rationale - dashboard_api.py
- [[Write per-agent status into session_state.json for the brand, and append to agen]] - rationale - dashboard_api.py
- [[_agent_name_to_slug()]] - code - dashboard_api.py
- [[_get_brand_id()]] - code - dashboard_api.py
- [[_run_agent_subprocess()]] - code - dashboard_api.py
- [[_run_managed_async()]] - code - dashboard_api.py
- [[_safe_path()]] - code - dashboard_api.py
- [[_skill_on_approve()]] - code - dashboard_api.py
- [[_skill_on_reject()]] - code - dashboard_api.py
- [[_strip_markdown()]] - code - dashboard_api.py
- [[_unlock_next_agent()]] - code - dashboard_api.py
- [[_update_session_agent_status()]] - code - dashboard_api.py
- [[approve_output()]] - code - dashboard_api.py
- [[brand_costs()]] - code - dashboard_api.py
- [[broadcast_event()]] - code - dashboard_api.py
- [[ceo_next_agent()]] - code - dashboard_api.py
- [[get_agent_output_history()]] - code - dashboard_api.py
- [[get_pending_outputs()]] - code - dashboard_api.py
- [[n8n → GRID CONTROL trigger endpoint.     n8n sends { brand_slug, agent_name, tr]] - rationale - dashboard_api.py
- [[n8n_webhook()]] - code - dashboard_api.py
- [[reject_output()]] - code - dashboard_api.py
- [[requestChanges()]] - code - dashboard/.port-backup/spaces.bak/ReviewSpace.tsx
- [[run_agent()]] - code - dashboard_api.py
- [[sync_notion_approvals()]] - code - dashboard_api.py

## Live Query (requires Dataview plugin)

```dataview
TABLE source_file, type FROM #community/Dashboard__Api_Agent
SORT file.name ASC
```

## Connections to other communities
- 26 edges to [[_COMMUNITY_Mixed — Api, Brand]]
- 18 edges to [[_COMMUNITY_Dashboard — Api, Brand]]
- 4 edges to [[_COMMUNITY_Utils — Api, Agent]]
- 3 edges to [[_COMMUNITY_Agent System — Skill, Brand]]
- 1 edge to [[_COMMUNITY_Mixed — Api, Brain]]
- 1 edge to [[_COMMUNITY_Mixed — Api]]
- 1 edge to [[_COMMUNITY_Mixed — Api, Agent]]
- 1 edge to [[_COMMUNITY_Database — Supabase, Brand]]
- 1 edge to [[_COMMUNITY_Notion_Integration — Brain, Api]]
- 1 edge to [[_COMMUNITY_Dashboard — Brand, Agent]]
- 1 edge to [[_COMMUNITY_Dashboard — Review, Content]]

## Top bridge nodes
- [[Path]] - degree 11, connects to 6 communities
- [[_get_brand_id()]] - degree 20, connects to 5 communities
- [[_run_agent_subprocess()]] - degree 8, connects to 3 communities
- [[_skill_on_approve()]] - degree 6, connects to 3 communities
- [[_skill_on_reject()]] - degree 5, connects to 3 communities