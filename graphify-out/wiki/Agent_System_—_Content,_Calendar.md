# Agent System — Content, Calendar

> 16 nodes · cohesion 0.26

## Key Concepts

- **Content Planner Prompt** (15 connections) — `managed_agents/prompts/content_planner.md`
- **.run_autoresearch_loop()** (8 connections) — `agents/content_planner.py`
- **.log()** (7 connections) — `agents/content_planner.py`
- **str** (6 connections) — `agents/content_planner.py`
- **.load_file()** (5 connections) — `agents/content_planner.py`
- **.run()** (5 connections) — `agents/content_planner.py`
- **_safe_json_loads()** (5 connections) — `agents/content_planner.py`
- **.__init__()** (4 connections) — `agents/content_planner.py`
- **.save_calendar()** (4 connections) — `agents/content_planner.py`
- **_extract_first_json_object()** (4 connections) — `agents/content_planner.py`
- **_escape_literal_newlines_in_strings()** (3 connections) — `agents/content_planner.py`
- **Find the first balanced { ... } block. Strips trailing prose Claude appended.** (2 connections) — `agents/script_writer.py`
- **Content Planner — OffGrid Marketing OS Agent ID: 2 | Sequence position: 3 (runs** (1 connections) — `agents/content_planner.py`
- **Load a JSON file from brand directory. Raises FileNotFoundError if missing.** (1 connections) — `agents/content_planner.py`
- **Write content_calendar.json to brand directory for downstream agents.** (1 connections) — `agents/content_planner.py`
- **Rule 9 — AutoResearch Loop.         Three variants:           Variant A — Educat** (1 connections) — `agents/content_planner.py`

## Relationships

- [[Managed Agent Prompts — Pipeline]] (4 shared connections)
- [[Agent System — Ui, Trend]] (3 shared connections)
- [[Ceo_Brain — Agent]] (2 shared connections)
- [[Agent System — Script, Review]] (1 shared connections)

## Source Files

- `agents/content_planner.py`
- `agents/script_writer.py`
- `managed_agents/prompts/content_planner.md`

## Audit Trail

- EXTRACTED: 69 (96%)
- INFERRED: 3 (4%)
- AMBIGUOUS: 0 (0%)

---

*Part of the graphify knowledge wiki. See [[index]] to navigate.*