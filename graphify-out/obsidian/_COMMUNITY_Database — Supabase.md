---
type: community
cohesion: 0.24
members: 11
---

# Database — Supabase

**Cohesion:** 0.24 - loosely connected
**Members:** 11 nodes

## Members
- [[Extract Loop Header keys from plain-text block before '---'.]] - rationale - supabase/etl.py
- [[Path_9]] - code - supabase/etl.py
- [[Read an agent output file.     Returns (raw_payload, loop_header).     Handles b]] - rationale - supabase/etl.py
- [[Return the most recently modified file from a list.]] - rationale - supabase/etl.py
- [[_folder_to_slug()]] - code - supabase/etl.py
- [[_most_recent()]] - code - supabase/etl.py
- [[_parse_loop_header()]] - code - supabase/etl.py
- [[_read_output_file()]] - code - supabase/etl.py
- [[etl.py]] - code - supabase/etl.py
- [[str_30]] - code - supabase/etl.py
- [[supabaseetl.py — GRID CONTROL One-Time Migration Migrates all existing JSON dat]] - rationale - supabase/etl.py

## Live Query (requires Dataview plugin)

```dataview
TABLE source_file, type FROM #community/Database__Supabase
SORT file.name ASC
```
