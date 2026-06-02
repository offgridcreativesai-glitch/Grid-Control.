---
type: community
cohesion: 0.11
members: 31
---

# Agent System — Trend, Calendar

**Cohesion:** 0.11 - loosely connected
**Members:** 31 nodes

## Members
- [[NOTE scored_posts isn't currently saved into trends_live.json — it's only in]] - rationale - agents/trend_sentinel.py
- [[.__init__()_2]] - code - agents/trend_sentinel.py
- [[._compute_pivot_impact()]] - code - agents/trend_sentinel.py
- [[._decide()]] - code - agents/trend_sentinel.py
- [[._extract_calendar_topics()]] - code - agents/trend_sentinel.py
- [[._extract_today_signals()]] - code - agents/trend_sentinel.py
- [[._load_calendar()]] - code - agents/trend_sentinel.py
- [[._load_trends()]] - code - agents/trend_sentinel.py
- [[._load_watchlist()]] - code - agents/trend_sentinel.py
- [[._save_watchlist()]] - code - agents/trend_sentinel.py
- [[._trigger_content_planner()]] - code - agents/trend_sentinel.py
- [[._update_watchlist()]] - code - agents/trend_sentinel.py
- [[.log()]] - code - agents/trend_sentinel.py
- [[.run()]] - code - agents/trend_sentinel.py
- [[If SENTINEL_AUTO_PIVOT enabled, fire Content Planner as background subprocess.]] - rationale - agents/trend_sentinel.py
- [[Lowercase, split on non-word, drop stopwords + tokens  3 chars. Pure determinis]] - rationale - agents/trend_sentinel.py
- [[On PIVOT decision, list which already-planned content slots would be invalidated]] - rationale - agents/trend_sentinel.py
- [[Pull today's strongest comparable signals from trends_live.json.         Each si]] - rationale - agents/trend_sentinel.py
- [[Pull topics from calendar slots in the next CALENDAR_LOOKAHEAD_DAYS days.]] - rationale - agents/trend_sentinel.py
- [[Pure-deterministic decision agent. NO Claude. NO LLM. NO synthesis.     Every ST]] - rationale - agents/trend_sentinel.py
- [[Pure-math decision per signal. Each decision cites the exact numbers it used.]] - rationale - agents/trend_sentinel.py
- [[Returns calendar dict OR empty dict if no calendar exists yet.]] - rationale - agents/trend_sentinel.py
- [[Returns watchlist dict. Auto-create if missing.]] - rationale - agents/trend_sentinel.py
- [[Trend Sentinel — OffGrid Marketing OS Agent ID 16 (NEW)  Sequence position ru]] - rationale - agents/trend_sentinel.py
- [[Update watchlist based on per_signal decisions.         - TRACK signals increme]] - rationale - agents/trend_sentinel.py
- [[_jaccard()]] - code - agents/trend_sentinel.py
- [[_tokenize()]] - code - agents/trend_sentinel.py
- [[bool_1]] - code - agents/trend_sentinel.py
- [[float_1]] - code - agents/trend_sentinel.py
- [[str_5]] - code - agents/trend_sentinel.py
- [[trend_sentinel.py]] - code - agents/trend_sentinel.py

## Live Query (requires Dataview plugin)

```dataview
TABLE source_file, type FROM #community/Agent_System__Trend_Calendar
SORT file.name ASC
```

## Connections to other communities
- 2 edges to [[_COMMUNITY_Ceo_Brain — Agent]]
- 1 edge to [[_COMMUNITY_Agent System — Ui, Trend]]

## Top bridge nodes
- [[trend_sentinel.py]] - degree 19, connects to 1 community
- [[.__init__()_2]] - degree 5, connects to 1 community
- [[_jaccard()]] - degree 4, connects to 1 community