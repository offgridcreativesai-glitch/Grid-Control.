# Agent System — Ui, Supabase

> 14 nodes · cohesion 0.29

## Key Concepts

- **cost_tracker.py** (9 connections) — `agents/cost_tracker.py`
- **.log()** (7 connections) — `agents/cost_tracker.py`
- **.run()** (6 connections) — `agents/cost_tracker.py`
- **._push_to_supabase()** (5 connections) — `agents/cost_tracker.py`
- **._save_report()** (5 connections) — `agents/cost_tracker.py`
- **str** (5 connections) — `agents/cost_tracker.py`
- **._build_cost_analysis()** (4 connections) — `agents/cost_tracker.py`
- **.__init__()** (4 connections) — `agents/cost_tracker.py`
- **._pull_monthly_costs()** (4 connections) — `agents/cost_tracker.py`
- **Cost Tracker — GRID CONTROL Agent ID: 9 | Runs on-demand (no Apify, no scraping)** (1 connections) — `agents/cost_tracker.py`
- **Write cost report to brands/{slug}/cost_report.json.** (1 connections) — `agents/cost_tracker.py`
- **Save output to agent_outputs via CEO Brain.** (1 connections) — `agents/cost_tracker.py`
- **Pull aggregated cost data from Supabase for this month.** (1 connections) — `agents/cost_tracker.py`
- **Ask Claude Haiku to interpret the cost data into a plain-English report.** (1 connections) — `agents/cost_tracker.py`

## Relationships

- [[Ceo_Brain — Agent]] (2 shared connections)

## Source Files

- `agents/cost_tracker.py`

## Audit Trail

- EXTRACTED: 54 (100%)
- INFERRED: 0 (0%)
- AMBIGUOUS: 0 (0%)

---

*Part of the graphify knowledge wiki. See [[index]] to navigate.*