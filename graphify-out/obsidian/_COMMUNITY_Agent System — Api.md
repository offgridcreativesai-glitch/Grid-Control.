---
type: community
cohesion: 0.10
members: 32
---

# Agent System — Api

**Cohesion:** 0.10 - loosely connected
**Members:** 32 nodes

## Members
- [[.__init__()_11]] - code - agents/performance_tracker.py
- [[._clear_inbox()]] - code - agents/performance_tracker.py
- [[._compute_dead_patterns()]] - code - agents/performance_tracker.py
- [[._compute_rolling_baselines()]] - code - agents/performance_tracker.py
- [[._compute_winning_patterns()]] - code - agents/performance_tracker.py
- [[._fetch_meta_api()]] - code - agents/performance_tracker.py
- [[._flag_outperformers()]] - code - agents/performance_tracker.py
- [[._ingest_new_entries()]] - code - agents/performance_tracker.py
- [[._load_existing_history()]] - code - agents/performance_tracker.py
- [[._load_inbox()]] - code - agents/performance_tracker.py
- [[._merge_into_history()]] - code - agents/performance_tracker.py
- [[.log()_9]] - code - agents/performance_tracker.py
- [[.run()_8]] - code - agents/performance_tracker.py
- [[Add 'outperformed_baseline' bool to every post based on top_quartile_threshold_s]] - rationale - agents/performance_tracker.py
- [[After ingesting inbox entries, clear it so they don't get re-ingested.]] - rationale - agents/performance_tracker.py
- [[Combine entries from inbox (manual) + Meta API (auto). Returns merged list of ne]] - rationale - agents/performance_tracker.py
- [[Compute save_rate_pct and engagement_rate_pct from raw counts if not provided.]] - rationale - agents/performance_tracker.py
- [[Merge new entries into history.posts, deduping by post_id (last-write-wins for s]] - rationale - agents/performance_tracker.py
- [[Performance Tracker — OffGrid Marketing OS Agent ID 17 (NEW Apr 26)  Sequence]] - rationale - agents/performance_tracker.py
- [[Pull recent post metrics from Meta Graph API.         BLOCKED — META_GRAPH_API_T]] - rationale - agents/performance_tracker.py
- [[Pure math. Group posts by hook_pattern_used  topic  format.         For each g]] - rationale - agents/performance_tracker.py
- [[Pure math. Median of save_rate  ER  performance_score across last ROLLING_WIND]] - rationale - agents/performance_tracker.py
- [[Pure math. Patterns whose median performance_score is below the DEAD_PATTERN_PER]] - rationale - agents/performance_tracker.py
- [[Pure-deterministic performance feedback agent. NO Claude. NO LLM.     Every outp]] - rationale - agents/performance_tracker.py
- [[Pure-math compound score (0-100). Every weight + cap is in SCORE_WEIGHTS.     In]] - rationale - agents/performance_tracker.py
- [[Read manual-paste inbox queue. Each entry should match the post schema.]] - rationale - agents/performance_tracker.py
- [[Returns existing performance_history.json or empty skeleton.]] - rationale - agents/performance_tracker.py
- [[_compute_performance_score()]] - code - agents/performance_tracker.py
- [[_derive_save_rate_and_er()]] - code - agents/performance_tracker.py
- [[float_4]] - code - agents/performance_tracker.py
- [[performance_tracker.py]] - code - agents/performance_tracker.py
- [[str_17]] - code - agents/performance_tracker.py

## Live Query (requires Dataview plugin)

```dataview
TABLE source_file, type FROM #community/Agent_System__Api
SORT file.name ASC
```

## Connections to other communities
- 2 edges to [[_COMMUNITY_Ceo_Brain — Agent]]

## Top bridge nodes
- [[performance_tracker.py]] - degree 18, connects to 1 community
- [[.__init__()_11]] - degree 4, connects to 1 community