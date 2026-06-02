---
type: community
cohesion: 0.13
members: 32
---

# Agent Prompts — Store, Brand

**Cohesion:** 0.13 - loosely connected
**Members:** 32 nodes

## Members
- [[Anthropic]] - code - managed_agents/memory_manager.py
- [[Called after Trend Researcher or Strategy Agent completes —     adds a fresh doc]] - rationale - managed_agents/memory_manager.py
- [[Called at the end of any agent session to persist a key insight.     Agents call]] - rationale - managed_agents/memory_manager.py
- [[Create 3 memory stores for a brand if they don't exist.     Returns dict {brand]] - rationale - managed_agents/memory_manager.py
- [[Create a memory store and return its ID.]] - rationale - managed_agents/memory_manager.py
- [[Full setup for a brand create stores + seed them.     Called from dashboard_api]] - rationale - managed_agents/memory_manager.py
- [[Path_7]] - code - managed_agents/memory_manager.py
- [[Persist one learning. Best-effort. Never raises.]] - rationale - agents/_record_learning.py
- [[Seed agent_learnings with a placeholder — grows across sessions.]] - rationale - managed_agents/memory_manager.py
- [[Seed brand_context store with brand_profile.json content.]] - rationale - managed_agents/memory_manager.py
- [[Seed market_data store with trends_live.json + competitors_db.json.]] - rationale - managed_agents/memory_manager.py
- [[Single helper to persist an agent learning at run completion.  Writes to TWO pla]] - rationale - agents/_record_learning.py
- [[_record_learning.py]] - code - agents/_record_learning.py
- [[bool_8]] - code - managed_agents/memory_manager.py
- [[create_store()]] - code - managed_agents/memory_manager.py
- [[ensure_stores()]] - code - managed_agents/memory_manager.py
- [[get_client()]] - code - managed_agents/memory_manager.py
- [[load_json()]] - code - managed_agents/memory_manager.py
- [[load_stores()]] - code - managed_agents/memory_manager.py
- [[main()_2]] - code - managed_agents/memory_manager.py
- [[managed_agentsmemory_manager.py  Creates and seeds 3 memory stores per brand]] - rationale - managed_agents/memory_manager.py
- [[memory_manager.py]] - code - managed_agents/memory_manager.py
- [[record()_1]] - code - agents/_record_learning.py
- [[record_agent_learning()]] - code - managed_agents/memory_manager.py
- [[save_stores()]] - code - managed_agents/memory_manager.py
- [[seed_agent_learnings()]] - code - managed_agents/memory_manager.py
- [[seed_brand_context()]] - code - managed_agents/memory_manager.py
- [[seed_market_data()]] - code - managed_agents/memory_manager.py
- [[setup_brand_memory()]] - code - managed_agents/memory_manager.py
- [[str_21]] - code - agents/_record_learning.py
- [[str_27]] - code - managed_agents/memory_manager.py
- [[update_market_data()]] - code - managed_agents/memory_manager.py

## Live Query (requires Dataview plugin)

```dataview
TABLE source_file, type FROM #community/Agent_Prompts__Store_Brand
SORT file.name ASC
```

## Connections to other communities
- 1 edge to [[_COMMUNITY_Mixed — Api, Brand]]

## Top bridge nodes
- [[setup_brand_memory()]] - degree 11, connects to 1 community