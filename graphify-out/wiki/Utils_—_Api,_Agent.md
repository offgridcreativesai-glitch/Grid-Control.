# Utils — Api, Agent

> 27 nodes · cohesion 0.11

## Key Concepts

- **format_for_notion()** (16 connections) — `utils/output_formatter.py`
- **get_agent_output()** (9 connections) — `dashboard_api.py`
- **output_formatter.py** (9 connections) — `utils/output_formatter.py`
- **format_calendar()** (6 connections) — `utils/output_formatter.py`
- **format_scripts()** (6 connections) — `utils/output_formatter.py`
- **format_strategy()** (6 connections) — `utils/output_formatter.py`
- **_parse_agent_output_file()** (5 connections) — `dashboard_api.py`
- **_flatten_to_markdown()** (5 connections) — `utils/output_formatter.py`
- **escape_literal_newlines_in_strings()** (4 connections) — `dashboard_api.py`
- **get_dashboard_output()** (4 connections) — `dashboard_api.py`
- **format_data_analyst()** (4 connections) — `utils/output_formatter.py`
- **format_funnel()** (3 connections) — `utils/output_formatter.py`
- **format_website()** (3 connections) — `utils/output_formatter.py`
- **Any** (2 connections) — `utils/output_formatter.py`
- **str** (2 connections) — `utils/output_formatter.py`
- **Escape literal newline/tab/CR characters that appear inside JSON string     valu** (1 connections) — `dashboard_api.py`
- **Parse an agent output file that may contain Loop Header + '---' + JSON.** (1 connections) — `dashboard_api.py`
- **int** (1 connections) — `utils/output_formatter.py`
- **output_formatter.py — OffGrid Marketing OS Converts agent JSON outputs to clean** (1 connections) — `utils/output_formatter.py`
- **Convert Script Writer output to a list of clean dicts.     Keys: platform, forma** (1 connections) — `utils/output_formatter.py`
- **Convert Data Analyst output to (executive_summary string, action_items list).** (1 connections) — `utils/output_formatter.py`
- **Convert Funnel Specialist output to list of stage dicts.     Each stage has: sta** (1 connections) — `utils/output_formatter.py`
- **Convert Website Agent output to list of pages.     Each page has: name, purpose,** (1 connections) — `utils/output_formatter.py`
- **Convert any agent output to a clean human-readable markdown string.     No JSON** (1 connections) — `utils/output_formatter.py`
- **Recursively convert a dict/list to readable markdown lines.** (1 connections) — `utils/output_formatter.py`
- *... and 2 more nodes in this community*

## Relationships

- [[Mixed — Api, Brand]] (9 shared connections)
- [[Dashboard — Api, Agent]] (4 shared connections)
- [[Notion_Integration — Brain, Api]] (2 shared connections)
- [[Dashboard — Api, Brand]] (1 shared connections)

## Source Files

- `dashboard_api.py`
- `utils/output_formatter.py`

## Audit Trail

- EXTRACTED: 96 (100%)
- INFERRED: 0 (0%)
- AMBIGUOUS: 0 (0%)

---

*Part of the graphify knowledge wiki. See [[index]] to navigate.*