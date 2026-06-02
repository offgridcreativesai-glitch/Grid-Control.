# Mixed — Api, Agent

> 4 nodes · cohesion 0.50

## Key Concepts

- **agent_group_chat()** (5 connections) — `dashboard_api.py`
- **get_conversation()** (4 connections) — `dashboard_api.py`
- **Return persisted conversation history for a brand+agent pair.** (1 connections) — `dashboard_api.py`
- **Group Meeting Room — dynamic @mention routing.     Body: { brand_slug: str, mess** (1 connections) — `dashboard_api.py`

## Relationships

- [[Mixed — Api, Brand]] (2 shared connections)
- [[Dashboard — Api, Brand]] (2 shared connections)
- [[Dashboard — Api, Agent]] (1 shared connections)

## Source Files

- `dashboard_api.py`

## Audit Trail

- EXTRACTED: 11 (100%)
- INFERRED: 0 (0%)
- AMBIGUOUS: 0 (0%)

---

*Part of the graphify knowledge wiki. See [[index]] to navigate.*