# Agent System — Api

> 32 nodes · cohesion 0.10

## Key Concepts

- **performance_tracker.py** (18 connections) — `agents/performance_tracker.py`
- **.run()** (11 connections) — `agents/performance_tracker.py`
- **._ingest_new_entries()** (8 connections) — `agents/performance_tracker.py`
- **.log()** (8 connections) — `agents/performance_tracker.py`
- **._load_inbox()** (5 connections) — `agents/performance_tracker.py`
- **_compute_performance_score()** (4 connections) — `agents/performance_tracker.py`
- **._fetch_meta_api()** (4 connections) — `agents/performance_tracker.py`
- **.__init__()** (4 connections) — `agents/performance_tracker.py`
- **._load_existing_history()** (4 connections) — `agents/performance_tracker.py`
- **_derive_save_rate_and_er()** (3 connections) — `agents/performance_tracker.py`
- **._clear_inbox()** (3 connections) — `agents/performance_tracker.py`
- **._compute_dead_patterns()** (3 connections) — `agents/performance_tracker.py`
- **._compute_rolling_baselines()** (3 connections) — `agents/performance_tracker.py`
- **._compute_winning_patterns()** (3 connections) — `agents/performance_tracker.py`
- **._flag_outperformers()** (3 connections) — `agents/performance_tracker.py`
- **._merge_into_history()** (3 connections) — `agents/performance_tracker.py`
- **str** (2 connections) — `agents/performance_tracker.py`
- **float** (1 connections) — `agents/performance_tracker.py`
- **Performance Tracker — OffGrid Marketing OS Agent ID: 17 (NEW Apr 26) | Sequence:** (1 connections) — `agents/performance_tracker.py`
- **Pure-deterministic performance feedback agent. NO Claude. NO LLM.     Every outp** (1 connections) — `agents/performance_tracker.py`
- **Returns existing performance_history.json or empty skeleton.** (1 connections) — `agents/performance_tracker.py`
- **Read manual-paste inbox queue. Each entry should match the post schema.** (1 connections) — `agents/performance_tracker.py`
- **After ingesting inbox entries, clear it so they don't get re-ingested.** (1 connections) — `agents/performance_tracker.py`
- **Pull recent post metrics from Meta Graph API.         BLOCKED — META_GRAPH_API_T** (1 connections) — `agents/performance_tracker.py`
- **Combine entries from inbox (manual) + Meta API (auto). Returns merged list of ne** (1 connections) — `agents/performance_tracker.py`
- *... and 7 more nodes in this community*

## Relationships

- [[Ceo_Brain — Agent]] (2 shared connections)

## Source Files

- `agents/performance_tracker.py`

## Audit Trail

- EXTRACTED: 104 (100%)
- INFERRED: 0 (0%)
- AMBIGUOUS: 0 (0%)

---

*Part of the graphify knowledge wiki. See [[index]] to navigate.*