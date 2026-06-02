# Mixed — Api

> 4 nodes · cohesion 0.50

## Key Concepts

- **_write_env_token()** (4 connections) — `dashboard_api.py`
- **save_connection_token()** (3 connections) — `dashboard_api.py`
- **Update or append a key=value line in the .env file, then reload into os.environ.** (1 connections) — `dashboard_api.py`
- **Persist a platform API token to .env and reload it immediately.     Body: { "pla** (1 connections) — `dashboard_api.py`

## Relationships

- [[Mixed — Api, Brand]] (2 shared connections)
- [[Dashboard — Api, Brand]] (1 shared connections)

## Source Files

- `dashboard_api.py`

## Audit Trail

- EXTRACTED: 9 (100%)
- INFERRED: 0 (0%)
- AMBIGUOUS: 0 (0%)

---

*Part of the graphify knowledge wiki. See [[index]] to navigate.*