# Agent System — Trend, Calendar

> 31 nodes · cohesion 0.11

## Key Concepts

- **trend_sentinel.py** (19 connections) — `agents/trend_sentinel.py`
- **.run()** (12 connections) — `agents/trend_sentinel.py`
- **.log()** (8 connections) — `agents/trend_sentinel.py`
- **._decide()** (6 connections) — `agents/trend_sentinel.py`
- **_tokenize()** (5 connections) — `agents/trend_sentinel.py`
- **.__init__()** (5 connections) — `agents/trend_sentinel.py`
- **_jaccard()** (4 connections) — `agents/trend_sentinel.py`
- **._load_calendar()** (4 connections) — `agents/trend_sentinel.py`
- **._load_watchlist()** (4 connections) — `agents/trend_sentinel.py`
- **._trigger_content_planner()** (4 connections) — `agents/trend_sentinel.py`
- **str** (3 connections) — `agents/trend_sentinel.py`
- **._compute_pivot_impact()** (3 connections) — `agents/trend_sentinel.py`
- **._extract_calendar_topics()** (3 connections) — `agents/trend_sentinel.py`
- **._extract_today_signals()** (3 connections) — `agents/trend_sentinel.py`
- **._load_trends()** (3 connections) — `agents/trend_sentinel.py`
- **._update_watchlist()** (3 connections) — `agents/trend_sentinel.py`
- **._save_watchlist()** (2 connections) — `agents/trend_sentinel.py`
- **bool** (1 connections) — `agents/trend_sentinel.py`
- **float** (1 connections) — `agents/trend_sentinel.py`
- **Trend Sentinel — OffGrid Marketing OS Agent ID: 16 (NEW) | Sequence position: ru** (1 connections) — `agents/trend_sentinel.py`
- **Returns calendar dict OR empty dict if no calendar exists yet.** (1 connections) — `agents/trend_sentinel.py`
- **Returns watchlist dict. Auto-create if missing.** (1 connections) — `agents/trend_sentinel.py`
- **Pull today's strongest comparable signals from trends_live.json.         Each si** (1 connections) — `agents/trend_sentinel.py`
- **# NOTE: scored_posts isn't currently saved into trends_live.json — it's only in** (1 connections) — `agents/trend_sentinel.py`
- **Pull topics from calendar slots in the next CALENDAR_LOOKAHEAD_DAYS days.** (1 connections) — `agents/trend_sentinel.py`
- *... and 6 more nodes in this community*

## Relationships

- [[Ceo_Brain — Agent]] (2 shared connections)
- [[Agent System — Ui, Trend]] (1 shared connections)

## Source Files

- `agents/trend_sentinel.py`

## Audit Trail

- EXTRACTED: 105 (100%)
- INFERRED: 0 (0%)
- AMBIGUOUS: 0 (0%)

---

*Part of the graphify knowledge wiki. See [[index]] to navigate.*