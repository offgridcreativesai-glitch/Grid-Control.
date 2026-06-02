---
type: community
cohesion: 0.29
members: 8
---

# Agent System

**Cohesion:** 0.29 - loosely connected
**Members:** 8 nodes

## Members
- [[Call once at the end of every agent run.     Reads GRID_RUN_ID and GRID_BRAND_SL]] - rationale - agents/cost_reporter.py
- [[Load supabasedb.py from disk, avoiding conflict with the pip 'supabase' package]] - rationale - agents/cost_reporter.py
- [[_load_local_db()]] - code - agents/cost_reporter.py
- [[cost_reporter.py]] - code - agents/cost_reporter.py
- [[cost_reporter.py — GRID CONTROL Lightweight utility imported by every agent to r]] - rationale - agents/cost_reporter.py
- [[int_8]] - code - agents/cost_reporter.py
- [[record()]] - code - agents/cost_reporter.py
- [[str_19]] - code - agents/cost_reporter.py

## Live Query (requires Dataview plugin)

```dataview
TABLE source_file, type FROM #community/Agent_System
SORT file.name ASC
```
