---
type: community
cohesion: 0.06
members: 49
---

# Dashboard — Api, Brand

**Cohesion:** 0.06 - loosely connected
**Members:** 49 nodes

## Members
- [[Agent adds a suggestion for Gaurav to review. NEVER writes to brand_memory direc]] - rationale - dashboard_api.py
- [[Apply approved updates to a brand_memory file.     Logs the change to decisions_]] - rationale - dashboard_api.py
- [[Build the real-data context block injected into every agent chat prompt.     Eac]] - rationale - dashboard_api.py
- [[Create a new brand and assign the current user as admin.]] - rationale - dashboard_api.py
- [[Create brand_memory and market_intelligence folders with empty initial files.]] - rationale - dashboard_api.py
- [[Gaurav approves a change to brand_memory.     Body { memory_key str, updates]] - rationale - dashboard_api.py
- [[Gaurav sets or updates an active goal (e.g. '500 followers in 30 days').     Imm]] - rationale - dashboard_api.py
- [[Generate a carousel (slides JSON + PNG render + pending_approval push).      Bod]] - rationale - dashboard_api.py
- [[Load conversation history — Supabase primary, JSON fallback.]] - rationale - dashboard_api.py
- [[Manual-paste path for logging real published-post metrics.     Works while META_]] - rationale - dashboard_api.py
- [[On server startup scan every brand folder.     If trends_live.json is stale (2]] - rationale - dashboard_api.py
- [[Only allow lowercase alphanumerics and hyphens, max 80 chars.     Prevents path]] - rationale - dashboard_api.py
- [[Persist conversation history — Supabase primary, JSON dual-write.]] - rationale - dashboard_api.py
- [[Read a brand_memory file by key. Returns {} if missing or unreadable.]] - rationale - dashboard_api.py
- [[Read a market_intelligence file by key. Returns {} if missing or unreadable.]] - rationale - dashboard_api.py
- [[Read a single JSON file from a brand's directory (whitelisted set only).     Use]] - rationale - dashboard_api.py
- [[Return True if the intelligence file is missing or older than its TTL.]] - rationale - dashboard_api.py
- [[Return current performance_inbox.json (queued, not-yet-ingested entries).]] - rationale - dashboard_api.py
- [[Return market_intelligence files + staleness info.]] - rationale - dashboard_api.py
- [[Return the most recent contradictions.json report for a brand (or empty if never]] - rationale - dashboard_api.py
- [[Update a market_intelligence file. Safe to call from agent threads.]] - rationale - dashboard_api.py
- [[Write JSON atomically — temp file + os.replace() prevents corruption.]] - rationale - dashboard_api.py
- [[_add_suggestion()]] - code - dashboard_api.py
- [[_approve_memory_update()]] - code - dashboard_api.py
- [[_atomic_write_json()]] - code - dashboard_api.py
- [[_auto_refresh_intelligence()]] - code - dashboard_api.py
- [[_bootstrap_brand_memory()]] - code - dashboard_api.py
- [[_build_agent_context()]] - code - dashboard_api.py
- [[_intelligence_is_stale()]] - code - dashboard_api.py
- [[_load_conversation()]] - code - dashboard_api.py
- [[_read_intelligence()]] - code - dashboard_api.py
- [[_read_memory()]] - code - dashboard_api.py
- [[_save_conversation()]] - code - dashboard_api.py
- [[_validate_brand_slug()]] - code - dashboard_api.py
- [[_write_intelligence()]] - code - dashboard_api.py
- [[agent_chat()]] - code - dashboard_api.py
- [[auth_create_brand()]] - code - dashboard_api.py
- [[bool]] - code - dashboard_api.py
- [[brand_file()]] - code - dashboard_api.py
- [[carousel_generate()]] - code - dashboard_api.py
- [[contradictions_latest()]] - code - dashboard_api.py
- [[createBrand()]] - code - dashboard/.port-backup/spaces.bak/BrandSpace.tsx
- [[delete_brand()]] - code - dashboard_api.py
- [[get_brand_intelligence()]] - code - dashboard_api.py
- [[is_managed_ready()]] - code - dashboard_api.py
- [[performance_inbox()]] - code - dashboard_api.py
- [[performance_log_post()]] - code - dashboard_api.py
- [[set_brand_goal()]] - code - dashboard_api.py
- [[str]] - code - dashboard_api.py

## Live Query (requires Dataview plugin)

```dataview
TABLE source_file, type FROM #community/Dashboard__Api_Brand
SORT file.name ASC
```

## Connections to other communities
- 30 edges to [[_COMMUNITY_Mixed — Api, Brand]]
- 18 edges to [[_COMMUNITY_Dashboard — Api, Agent]]
- 4 edges to [[_COMMUNITY_Mixed — Api, Brain]]
- 3 edges to [[_COMMUNITY_Database — Supabase, Brand]]
- 2 edges to [[_COMMUNITY_Agent System — Skill, Brand]]
- 2 edges to [[_COMMUNITY_Mixed — Api, Agent]]
- 2 edges to [[_COMMUNITY_Dashboard — Brand, Agent]]
- 1 edge to [[_COMMUNITY_Utils — Api, Agent]]
- 1 edge to [[_COMMUNITY_Dashboard — Api, Billing]]
- 1 edge to [[_COMMUNITY_Mixed — Api]]
- 1 edge to [[_COMMUNITY_Notion_Integration — Brain, Api]]
- 1 edge to [[_COMMUNITY_Mixed — Api]]
- 1 edge to [[_COMMUNITY_Ceo_Brain — Api, Brand]]

## Top bridge nodes
- [[str]] - degree 39, connects to 10 communities
- [[_validate_brand_slug()]] - degree 21, connects to 5 communities
- [[_load_conversation()]] - degree 6, connects to 3 communities
- [[_atomic_write_json()]] - degree 10, connects to 2 communities
- [[_build_agent_context()]] - degree 7, connects to 2 communities