---
type: community
cohesion: 0.29
members: 14
---

# Agent System — Ui, Supabase

**Cohesion:** 0.29 - loosely connected
**Members:** 14 nodes

## Members
- [[.__init__()_3]] - code - agents/cost_tracker.py
- [[._build_cost_analysis()]] - code - agents/cost_tracker.py
- [[._pull_monthly_costs()]] - code - agents/cost_tracker.py
- [[._push_to_supabase()]] - code - agents/cost_tracker.py
- [[._save_report()]] - code - agents/cost_tracker.py
- [[.log()_1]] - code - agents/cost_tracker.py
- [[.run()_1]] - code - agents/cost_tracker.py
- [[Ask Claude Haiku to interpret the cost data into a plain-English report.]] - rationale - agents/cost_tracker.py
- [[Cost Tracker — GRID CONTROL Agent ID 9  Runs on-demand (no Apify, no scraping)]] - rationale - agents/cost_tracker.py
- [[Pull aggregated cost data from Supabase for this month.]] - rationale - agents/cost_tracker.py
- [[Save output to agent_outputs via CEO Brain.]] - rationale - agents/cost_tracker.py
- [[Write cost report to brands{slug}cost_report.json.]] - rationale - agents/cost_tracker.py
- [[cost_tracker.py]] - code - agents/cost_tracker.py
- [[str_6]] - code - agents/cost_tracker.py

## Live Query (requires Dataview plugin)

```dataview
TABLE source_file, type FROM #community/Agent_System__Ui_Supabase
SORT file.name ASC
```

## Connections to other communities
- 2 edges to [[_COMMUNITY_Ceo_Brain — Agent]]

## Top bridge nodes
- [[cost_tracker.py]] - degree 9, connects to 1 community
- [[.__init__()_3]] - degree 4, connects to 1 community