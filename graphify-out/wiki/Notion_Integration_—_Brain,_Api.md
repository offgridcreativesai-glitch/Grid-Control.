# Notion_Integration — Brain, Api

> 20 nodes · cohesion 0.14

## Key Concepts

- **push_to_notion()** (7 connections) — `notion_integration/notion_pusher.py`
- **notion_pusher.py** (7 connections) — `notion_integration/notion_pusher.py`
- **update_notion_status()** (7 connections) — `notion_integration/notion_pusher.py`
- **_get_or_create_database()** (6 connections) — `notion_integration/notion_pusher.py`
- **test_notion_connection()** (5 connections) — `notion_integration/notion_pusher.py`
- **_update_notion_card_status()** (5 connections) — `dashboard_api.py`
- **approveNotionCard()** (5 connections) — `dashboard/.port-backup/spaces.bak/ReviewSpace.tsx`
- **rejectNotionCard()** (5 connections) — `dashboard/.port-backup/spaces.bak/ReviewSpace.tsx`
- **orchestrator.py** (4 connections) — `ceo_brain/orchestrator.py`
- **NotionAuthError** (4 connections) — `notion_integration/notion_pusher.py`
- **Exception** (3 connections)
- **str** (3 connections) — `notion_integration/notion_pusher.py`
- **bool** (2 connections) — `notion_integration/notion_pusher.py`
- **CEO Brain — OffGrid Marketing OS Orchestrator. Dynamic router. Session state man** (1 connections) — `ceo_brain/orchestrator.py`
- **NotionPusher — OffGrid Marketing OS Pushes all agent outputs to Notion for human** (1 connections) — `notion_integration/notion_pusher.py`
- **Update the Status field and approval checkboxes on an existing Notion page.** (1 connections) — `notion_integration/notion_pusher.py`
- **Raised when Notion API returns 401 unauthorized — token invalid/expired.** (1 connections) — `notion_integration/notion_pusher.py`
- **Quick connection test. Call this from main.py on startup.     Returns True if No** (1 connections) — `notion_integration/notion_pusher.py`
- **Check if OffGrid Approvals database exists under the page.     If not, create it** (1 connections) — `notion_integration/notion_pusher.py`
- **Flip the status field on a notion_card entry in session_state.json.** (1 connections) — `dashboard_api.py`

## Relationships

- [[Mixed — Api, Brand]] (5 shared connections)
- [[Ceo_Brain — Agent]] (2 shared connections)
- [[Utils — Api, Agent]] (2 shared connections)
- [[Dashboard — Brand, Agent]] (2 shared connections)
- [[Dashboard — Review, Content]] (2 shared connections)
- [[Agent System — Carousel, Calendar]] (1 shared connections)
- [[Dashboard — Api, Agent]] (1 shared connections)
- [[Dashboard — Api, Brand]] (1 shared connections)

## Source Files

- `ceo_brain/orchestrator.py`
- `dashboard/.port-backup/spaces.bak/ReviewSpace.tsx`
- `dashboard_api.py`
- `notion_integration/notion_pusher.py`

## Audit Trail

- EXTRACTED: 69 (99%)
- INFERRED: 1 (1%)
- AMBIGUOUS: 0 (0%)

---

*Part of the graphify knowledge wiki. See [[index]] to navigate.*