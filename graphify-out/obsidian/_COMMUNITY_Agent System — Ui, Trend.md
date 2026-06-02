---
type: community
cohesion: 0.15
members: 19
---

# Agent System — Ui, Trend

**Cohesion:** 0.15 - loosely connected
**Members:** 19 nodes

## Members
- [[.run_autoresearch_loop()_5]] - code - agents/trend_researcher.py
- [[Build a human-readable violation message to feed back into the next Claude call.]] - rationale - agents/_provenance.py
- [[Jaccard similarity = intersection  union.]] - rationale - agents/_provenance.py
- [[Lowercase, split on non-word, drop stopwords + tokens  3 chars. Pure determinis_1]] - rationale - agents/_provenance.py
- [[Read every JSON file in source_files and build a flat lookup       { trends_li]] - rationale - agents/_provenance.py
- [[Recursively flatten a JSON object into outkey_path = value (string).     Lists]] - rationale - agents/_provenance.py
- [[Rule 10 — Source Citation Enforcement Shared utility for generation agents (Stra]] - rationale - agents/_provenance.py
- [[Rule 9 — AutoResearch Loop.          Runs 3 internal variants through Claude]] - rationale - agents/trend_researcher.py
- [[Validate every entry in outputdata_provenance against source_index.      Eac]] - rationale - agents/_provenance.py
- [[_flatten()]] - code - agents/_provenance.py
- [[_jaccard()_1]] - code - agents/_provenance.py
- [[_provenance.py]] - code - agents/_provenance.py
- [[_tokenize()_1]] - code - agents/_provenance.py
- [[bool_5]] - code - agents/_provenance.py
- [[build_source_index()]] - code - agents/_provenance.py
- [[build_violation_message()]] - code - agents/_provenance.py
- [[float_3]] - code - agents/_provenance.py
- [[str_12]] - code - agents/_provenance.py
- [[validate_citations()]] - code - agents/_provenance.py

## Live Query (requires Dataview plugin)

```dataview
TABLE source_file, type FROM #community/Agent_System__Ui_Trend
SORT file.name ASC
```

## Connections to other communities
- 3 edges to [[_COMMUNITY_Agent System — Creative, Brand]]
- 3 edges to [[_COMMUNITY_Agent System — Brand]]
- 3 edges to [[_COMMUNITY_Agent System — Content, Calendar]]
- 3 edges to [[_COMMUNITY_Agent System — Script, Review]]
- 3 edges to [[_COMMUNITY_Agent System — Strategy, Trend]]
- 3 edges to [[_COMMUNITY_Agent System — Trend, Api]]
- 1 edge to [[_COMMUNITY_Agent System — Trend, Calendar]]
- 1 edge to [[_COMMUNITY_Agent System — Trend, Ui]]

## Top bridge nodes
- [[validate_citations()]] - degree 11, connects to 5 communities
- [[build_source_index()]] - degree 9, connects to 5 communities
- [[build_violation_message()]] - degree 9, connects to 5 communities
- [[.run_autoresearch_loop()_5]] - degree 8, connects to 2 communities
- [[Jaccard similarity = intersection  union.]] - degree 2, connects to 1 community