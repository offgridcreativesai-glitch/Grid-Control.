---
type: community
cohesion: 0.06
members: 71
---

# Agent System — Skill, Brand

**Cohesion:** 0.06 - loosely connected
**Members:** 71 nodes

## Members
- [[.__init__()_6]] - code - agents/base_agent.py
- [[._agent_slug()]] - code - agents/base_agent.py
- [[._get_brand_id()]] - code - agents/base_agent.py
- [[._skills_dir()]] - code - agents/base_agent.py
- [[.extract_skill_on_approval()]] - code - agents/base_agent.py
- [[.load_brand_profile()]] - code - agents/base_agent.py
- [[.load_competitors()_1]] - code - agents/base_agent.py
- [[.load_program()]] - code - agents/base_agent.py
- [[.load_session_state()]] - code - agents/base_agent.py
- [[.load_skills()]] - code - agents/base_agent.py
- [[.load_trends()]] - code - agents/base_agent.py
- [[.log()_4]] - code - agents/base_agent.py
- [[.patch_skill()]] - code - agents/base_agent.py
- [[.patch_skill_on_rejection()]] - code - agents/base_agent.py
- [[.recall()]] - code - agents/base_agent.py
- [[.recall_as_text()]] - code - agents/base_agent.py
- [[.remember()]] - code - agents/base_agent.py
- [[.report_costs()]] - code - agents/base_agent.py
- [[.save_output()]] - code - agents/base_agent.py
- [[.save_skill()]] - code - agents/base_agent.py
- [[.session_end()]] - code - agents/base_agent.py
- [[.session_save()]] - code - agents/base_agent.py
- [[.session_start()]] - code - agents/base_agent.py
- [[.update_session_state()]] - code - agents/base_agent.py
- [[Agent learnings — file-based persistent memory across runs.  Stand-in for Anthro]] - rationale - agents/_learnings.py
- [[Any]] - code - agents/_state.py
- [[Append a learning entry. Safe — creates file if missing.]] - rationale - agents/_learnings.py
- [[Append a lesson learned to an existing skill file.         Returns True if skill]] - rationale - agents/base_agent.py
- [[Brand state compaction.  Builds `brands{slug}_state.json` — a ~3KB summary tha]] - rationale - agents/_state.py
- [[Build and persist `_state.json`. Returns path.]] - rationale - agents/_state.py
- [[Call this at the end of every agent run to record cost data.         run_id come]] - rationale - agents/base_agent.py
- [[Called when an output is approved — extract the working pattern as a skill.]] - rationale - agents/base_agent.py
- [[Called when an output is rejected — patch the skill with the lesson.]] - rationale - agents/base_agent.py
- [[Construct compact state from full brand files. Returns dict.]] - rationale - agents/_state.py
- [[Format recent learnings as a short text block for system prompts.]] - rationale - agents/_learnings.py
- [[Get compact brand state. Auto-rebuilds if missing or stale.      Use this in age]] - rationale - agents/_state.py
- [[In-memory rate limiter per IP. Returns 429 on excess.     Note resets on deploy]] - rationale - dashboard_api.py
- [[Load compact brand context + recent learnings. Call at agent boot.          Retu]] - rationale - agents/base_agent.py
- [[Load skill metadata for this agent+brand. Returns formatted text         for inj]] - rationale - agents/base_agent.py
- [[Load this agent's program.md — defines experimentation boundaries.         Retur]] - rationale - agents/base_agent.py
- [[Path_3]] - code - agents/base_agent.py
- [[Path_4]] - code - agents/_state.py
- [[Persist session learnings + refresh _state.json. Call at agent completion.]] - rationale - agents/base_agent.py
- [[Return all memory entries for this agent + brand.         Returns list of { memo]] - rationale - agents/base_agent.py
- [[Return last N learnings (newest first), optionally filtered by agent.]] - rationale - agents/_learnings.py
- [[Return memory as a formatted string ready to inject into a system prompt.]] - rationale - agents/base_agent.py
- [[Save a memory entry for this agent + brand.         key short label (e.g. best]] - rationale - agents/base_agent.py
- [[Save current brand state to disk. Call before context compression         or any]] - rationale - agents/base_agent.py
- [[Save or update a skill file.]] - rationale - agents/base_agent.py
- [[_learnings.py]] - code - agents/_learnings.py
- [[_path()]] - code - agents/_learnings.py
- [[_safe_load()]] - code - agents/_state.py
- [[_state.py]] - code - agents/_state.py
- [[_truncate()]] - code - agents/_state.py
- [[append()]] - code - agents/_learnings.py
- [[base_agent.py]] - code - agents/base_agent.py
- [[bool_3]] - code - agents/base_agent.py
- [[bool_4]] - code - agents/_state.py
- [[build_brand_state()]] - code - agents/_state.py
- [[int_4]] - code - agents/base_agent.py
- [[int_3]] - code - agents/_learnings.py
- [[int_5]] - code - agents/_state.py
- [[int]] - code - dashboard_api.py
- [[load_brand_state()]] - code - agents/_state.py
- [[rate_limit()]] - code - dashboard_api.py
- [[recent()]] - code - agents/_learnings.py
- [[render_recent_for_prompt()]] - code - agents/_learnings.py
- [[str_9]] - code - agents/base_agent.py
- [[str_4]] - code - agents/_learnings.py
- [[str_10]] - code - agents/_state.py
- [[write_brand_state()]] - code - agents/_state.py

## Live Query (requires Dataview plugin)

```dataview
TABLE source_file, type FROM #community/Agent_System__Skill_Brand
SORT file.name ASC
```

## Connections to other communities
- 3 edges to [[_COMMUNITY_Dashboard — Api, Agent]]
- 2 edges to [[_COMMUNITY_Mixed — Api, Brand]]
- 2 edges to [[_COMMUNITY_Dashboard — Api, Brand]]
- 2 edges to [[_COMMUNITY_Mixed — Api, Brain]]
- 1 edge to [[_COMMUNITY_Ceo_Brain — Agent]]
- 1 edge to [[_COMMUNITY_Agent System — Brand]]

## Top bridge nodes
- [[base_agent.py]] - degree 35, connects to 3 communities
- [[load_brand_state()]] - degree 9, connects to 2 communities
- [[render_recent_for_prompt()]] - degree 9, connects to 1 community
- [[_path()]] - degree 5, connects to 1 community
- [[rate_limit()]] - degree 3, connects to 1 community