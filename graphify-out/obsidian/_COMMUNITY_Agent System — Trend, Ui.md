---
type: community
cohesion: 0.18
members: 12
---

# Agent System — Trend, Ui

**Cohesion:** 0.18 - loosely connected
**Members:** 12 nodes

## Members
- [[.__init__()_10]] - code - agents/trend_researcher.py
- [[._load_competitor_handles()]] - code - agents/trend_researcher.py
- [[Build Google Trends seed keywords from brand profile.     Returns 5 relevant key]] - rationale - agents/trend_researcher.py
- [[Collect competitor handles from two sources (deduplicated)           1. brand_p]] - rationale - agents/trend_researcher.py
- [[Escape literal newlinetabCR characters that appear inside JSON string     valu_1]] - rationale - agents/trend_researcher.py
- [[Generate relevant Instagram hashtags from brand profile fields.     Falls back t]] - rationale - agents/trend_researcher.py
- [[Try json.loads; if it fails, attempt multiple repair strategies     1. Escape l]] - rationale - agents/trend_researcher.py
- [[_build_niche_hashtags()]] - code - agents/trend_researcher.py
- [[_build_trend_keywords()]] - code - agents/trend_researcher.py
- [[_escape_literal_newlines_in_strings()_3]] - code - agents/trend_researcher.py
- [[_safe_json_loads()_3]] - code - agents/trend_researcher.py
- [[str_16]] - code - agents/trend_researcher.py

## Live Query (requires Dataview plugin)

```dataview
TABLE source_file, type FROM #community/Agent_System__Trend_Ui
SORT file.name ASC
```

## Connections to other communities
- 13 edges to [[_COMMUNITY_Agent System — Trend, Api]]
- 1 edge to [[_COMMUNITY_Agent System — Ui, Trend]]
- 1 edge to [[_COMMUNITY_Ceo_Brain — Agent]]

## Top bridge nodes
- [[_safe_json_loads()_3]] - degree 6, connects to 2 communities
- [[.__init__()_10]] - degree 6, connects to 2 communities
- [[str_16]] - degree 7, connects to 1 community
- [[._load_competitor_handles()]] - degree 5, connects to 1 community
- [[_escape_literal_newlines_in_strings()_3]] - degree 4, connects to 1 community