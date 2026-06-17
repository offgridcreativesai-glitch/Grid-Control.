# GRID CONTROL — Front-End Integration Guide

Companion to `docs/API_REFERENCE.md` + `docs/SCREEN_ENDPOINT_MAP.md`. Everything the FE needs to talk to the backend.

## Base URLs
- **Prod API:** `https://web-production-175d5.up.railway.app`
- **Local API:** `http://localhost:5001` (run: `source .env && python3 dashboard_api.py` from repo root)
- Recommend a single `VITE_API_BASE` env var; default to prod.

## Environment variables (FE)
```
VITE_API_BASE=https://web-production-175d5.up.railway.app
VITE_SUPABASE_URL=<from repo .env>
VITE_SUPABASE_ANON_KEY=<from repo .env>
# Dev/admin shortcut only (bypasses Supabase login): VITE_DASHBOARD_SECRET=<from repo .env>
```

## Auth flow (Supabase JWT)
1. FE uses `@supabase/supabase-js` with `VITE_SUPABASE_URL` + `VITE_SUPABASE_ANON_KEY` to sign in (email/password).
2. Supabase returns a session with `access_token` (JWT).
3. Send it on **every** `/api/*` request: `Authorization: Bearer <access_token>`.
4. Backend `@require_auth` validates the JWT (or accepts legacy `X-Dashboard-Secret` for admin/dev).
5. `401` → token missing/expired → refresh session or re-login. `🔓` endpoints (e.g. `/api/auth/me`) work anonymously.

## Conventions (must-follow)
- **Envelope:** `{ success, data }` on most endpoints; **bare** shapes on `/api/auth/*` and `/api/brands` (see API_REFERENCE "Envelope exceptions"). Write a thin `unwrap()` that handles both.
- **Brand scope:** pass `?brand_slug=<slug>` on brand data calls. Drive it from the brand switcher.
- **TanStack Query:** key every brand query by `['<resource>', activeBrand.slug]` so switching brands refetches.
- **Rule 8 — never render raw JSON.** Agent output bodies are pre-formatted **markdown**; render with a markdown component. Files carry a LOOP-header prefix — split on the first `\n---\n` before parsing if you read raw.
- **Live updates (SSE):** `GET /api/events` is a server-sent-events stream (run status, approvals). Subscribe with `EventSource`; refetch the affected query on relevant events.

## Error contract
| Code | Meaning | FE handling |
|------|---------|-------------|
| 400 | bad/missing params | show validation msg from `error` |
| 401 | no/expired JWT | refresh session or redirect to login |
| 403 | gate (e.g. Brand-Foundation not approved before strategy/content-planner) | show the gate reason from `error` |
| 409 | conflict (agent already running) | disable trigger, poll status |
| 5xx | server | toast + retry |

## Known gotchas (from the contract pass)
1. **No live social metrics endpoint.** "Brand Health / LIVE" numbers come from `/api/performance/history` (last data-analyst run). Label with the run timestamp — don't imply real-time.
2. **Concierge:** one endpoint — `POST /api/concierge` (tiered, no-LLM trivial tier). The older `/api/brands/<slug>/concierge` was removed Jun 17.
3. **Calendar** has no own route — read `GET /api/dashboard-output` → `data.calendar_formatted`.
4. **Cost gating:** triggering `/api/agents/run` is safe; real spend is server-gated by `GRID_PAID_OPS`. The FE can always trigger; the backend decides whether it spends.

## Local dev (full stack)
```bash
# Terminal 1 — backend
cd <repo> && source .env && python3 dashboard_api.py     # :5001

# Terminal 2 — front-end (Vite); proxy /api → :5001 in vite.config
npm run dev                                               # :5173
```
