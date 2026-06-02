# Agent System

> 8 nodes · cohesion 0.29

## Key Concepts

- **record()** (5 connections) — `agents/cost_reporter.py`
- **_load_local_db()** (3 connections) — `agents/cost_reporter.py`
- **cost_reporter.py** (3 connections) — `agents/cost_reporter.py`
- **int** (1 connections) — `agents/cost_reporter.py`
- **str** (1 connections) — `agents/cost_reporter.py`
- **cost_reporter.py — GRID CONTROL Lightweight utility imported by every agent to r** (1 connections) — `agents/cost_reporter.py`
- **Load supabase/db.py from disk, avoiding conflict with the pip 'supabase' package** (1 connections) — `agents/cost_reporter.py`
- **Call once at the end of every agent run.     Reads GRID_RUN_ID and GRID_BRAND_SL** (1 connections) — `agents/cost_reporter.py`

## Relationships

- No strong cross-community connections detected

## Source Files

- `agents/cost_reporter.py`

## Audit Trail

- EXTRACTED: 16 (100%)
- INFERRED: 0 (0%)
- AMBIGUOUS: 0 (0%)

---

*Part of the graphify knowledge wiki. See [[index]] to navigate.*