# Agent System — Data, Api

> 20 nodes · cohesion 0.17

## Key Concepts

- **data_analyst.py** (12 connections) — `agents/data_analyst.py`
- **.run()** (7 connections) — `agents/data_analyst.py`
- **_safe_json_loads()** (6 connections) — `agents/data_analyst.py`
- **.log()** (5 connections) — `agents/data_analyst.py`
- **.run_autoresearch_loop()** (5 connections) — `agents/data_analyst.py`
- **.collect_script_sample()** (4 connections) — `agents/data_analyst.py`
- **.__init__()** (4 connections) — `agents/data_analyst.py`
- **_escape_literal_newlines_in_strings()** (4 connections) — `agents/data_analyst.py`
- **str** (4 connections) — `agents/data_analyst.py`
- **.collect_api_connection_status()** (3 connections) — `agents/data_analyst.py`
- **.collect_output_inventory()** (3 connections) — `agents/data_analyst.py`
- **.collect_session_data()** (3 connections) — `agents/data_analyst.py`
- **json.loads with literal-newline repair fallback.** (2 connections) — `agents/data_analyst.py`
- **Data Analyst — OffGrid Marketing OS Agent ID: 6 | Runs every week automatically.** (1 connections) — `agents/data_analyst.py`
- **Read session_state for agent run history and Notion card counts.** (1 connections) — `agents/data_analyst.py`
- **Check which external APIs are configured.** (1 connections) — `agents/data_analyst.py`
- **Pull a sample of script writer outputs for hook analysis.** (1 connections) — `agents/data_analyst.py`
- **3 variants:         A — Raw metrics summary (what happened)         B — Trend +** (1 connections) — `agents/data_analyst.py`
- **Escape literal \\n/\\r/\\t inside JSON string values (Claude API quirk).** (1 connections) — `agents/data_analyst.py`
- **Scan all output files across pending + approved for scoring.** (1 connections) — `agents/data_analyst.py`

## Relationships

- [[Ceo_Brain — Agent]] (2 shared connections)
- [[Agent System — Script, Review]] (1 shared connections)

## Source Files

- `agents/data_analyst.py`

## Audit Trail

- EXTRACTED: 69 (100%)
- INFERRED: 0 (0%)
- AMBIGUOUS: 0 (0%)

---

*Part of the graphify knowledge wiki. See [[index]] to navigate.*