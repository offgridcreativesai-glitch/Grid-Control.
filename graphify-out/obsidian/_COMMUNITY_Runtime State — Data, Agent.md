---
type: community
cohesion: 0.12
members: 17
---

# Runtime State — Data, Agent

**Cohesion:** 0.12 - loosely connected
**Members:** 17 nodes

## Members
- [[accounts_connected]] - code - data/session_state.json
- [[agents_approved]] - code - data/session_state.json
- [[agents_pending]] - code - data/session_state.json
- [[agents_run]] - code - data/session_state.json
- [[brand_1]] - code - data/session_state.json
- [[competitor_data_available]] - code - data/session_state.json
- [[current_phase]] - code - data/session_state.json
- [[ga4]] - code - data/session_state.json
- [[instagram]] - code - data/session_state.json
- [[last_run]] - code - data/session_state.json
- [[linkedin]] - code - data/session_state.json
- [[meta_ads]] - code - data/session_state.json
- [[notes]] - code - data/session_state.json
- [[search_console]] - code - data/session_state.json
- [[session_id]] - code - data/session_state.json
- [[session_state.json]] - code - data/session_state.json
- [[trend_data_available]] - code - data/session_state.json

## Live Query (requires Dataview plugin)

```dataview
TABLE source_file, type FROM #community/Runtime_State__Data_Agent
SORT file.name ASC
```
