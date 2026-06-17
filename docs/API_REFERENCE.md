# GRID CONTROL — API Reference (FE-facing contract)

> Source of truth for the front-end. Base URL (prod): `https://web-production-175d5.up.railway.app`
> Shapes below are read from the live route handlers, not guessed. Status: **foundation groups done
> (Auth, Brands, Agents); remaining groups stubbed at the bottom — being documented in the next pass.**

## Conventions

- **Auth:** Supabase JWT. Send `Authorization: Bearer <access_token>` on every `/api/*` call.
  Endpoints marked 🔓 work without a token (return null/empty instead of 401).
- **Brand scope:** brand data endpoints take `?brand_slug=<slug>` (query) or `<brand_slug>` (path).
  Defaults to `offgrid-creatives-ai` if omitted on some endpoints — **always pass it explicitly.**
- **Standard envelope:** most endpoints return
  `{ "success": true, "data": <payload> }` or `{ "success": false, "error": "<msg>" }` (+ HTTP 4xx/5xx).
- **⚠️ Envelope exceptions (do NOT assume `success`/`data`):** the `/api/auth/*` and `/api/brands`
  (list) endpoints return **bare** objects/arrays — see each below. This is a known inconsistency;
  handle per-endpoint.
- **No raw JSON in UI:** agent *output* bodies are pre-formatted markdown (Rule 8). Render as markdown.

---

## Group A — Auth & Session

### GET /api/auth/me 🔓
Current user + their brands. No token required (returns nulls if anonymous). **Bare envelope.**
```jsonc
// 200
{
  "user": { /* profile row or null */ } | null,
  "brands": [ { "id": "uuid", "slug": "askgauravai", "name": "AskGaurav AI", "role": "admin" } ]
}
```

### GET /api/auth/brands
Brands for the authenticated user. **Bare array.**
```jsonc
// 200
[ { "id": "uuid", "slug": "askgauravai", "name": "AskGaurav AI", "role": "admin", "profile": { /* … */ } } ]
```

### POST /api/auth/create-brand
Body: `{ "slug": "newbrand", "name": "New Brand", "profile": { /* optional */ } }`
Returns standard envelope. 400 if slug/name missing or slug invalid; 503 if DB down.

---

## Group B — Brands & Brand Switcher

### GET /api/brands
Brands the user can access (super-admin → all; else their memberships). **Bare envelope.**
```jsonc
// 200
{ "brands": [ { "slug": "askgauravai", "name": "AskGaurav AI" } ] }
```

### GET /api/brand/summary?brand_slug=…
**The Command-Center aggregate.** Standard envelope. `data` =
```jsonc
{
  "brand_name": "AskGaurav AI", "product": "...", "phase": "Beta",
  "platforms": ["instagram","linkedin"], "bottlenecks": [], "audience": [],
  "price_india": "", "price_international": "", "railway_url": "",
  "instagram_handle": "", "competitor_handles": [], "brand_face": "",
  "tone_specifics": "", "content_goal_90d": "", "what_to_never_say": "", "weekly_post_target": "3x",
  "posts_scripted": 0, "agents_run": 0, "agents_approved": 0,
  "notion_pending": 0, "notion_approved": 0, "notion_rejected": 0,
  "completed_agents": ["trend-researcher", "..."],
  "activity_feed": [ { "agent": "Trend Researcher", "status": "done", "icon": "✅",
                      "summary": "…(≤200 chars)", "timestamp": "ISO" } ],   // last 20, newest first
  "keys": { "anthropic": true, "elevenlabs": false, "notion": true, "fal": true }
}
```

### GET /api/brand/dashboard?brand_slug=…
Raw brand files. Standard envelope. `data` = `{ "brand_profile": {…}, "trends_live": {…}, "session_state": {…} }`
(only the files that exist are included).

### GET /api/brand/profile?brand_slug=… · POST /api/brand/profile
GET returns the brand_profile.json; POST updates it. (Settings screen.)

### DELETE /api/brands/<brand_slug>
Removes a brand. Admin-only.

---

## Group C — Agents & The Team

### GET /api/agents/list
All 18 agents, enriched (static roster + metadata). Standard envelope; `data` = `AGENTS_ENRICHED[]`:
```jsonc
[ { "id": 0, "name": "CEO Brain", "slug": "ceo-brain", "role": "...", "model": "opus-4-8", /* +meta */ } ]
```

### GET /api/agents/status?brand_slug=…
Per-agent live status for a brand (from session_state). `data` = list of agents enriched with run state:
```jsonc
[ { /* …agent fields… */ "status": "idle|running|done|error", "lastRun": "ISO|null", "lastOutput": "str|null" } ]
```

### POST /api/agents/run
Body: `{ "brand_slug": "askgauravai", "agent_slug"|"agent_name": "trend-researcher" }`.
Starts a run (background). 400 missing keys; 403 Brand-Foundation gate (strategy/content-planner need an
approved brand-book); 409 already running. Success `data` = `{ "run_id": "...", "agent": "...", ... }`.
**Cost note:** real runs spend money and are gated by `GRID_PAID_OPS`. The FE triggers runs; spend is server-gated.

### GET /api/agents/run/status?run_id=…
Poll a run. 400 if run_id missing. Returns run state/progress.

### GET /api/agents/conversation?agent_slug=…&brand_slug=…
Chat/log history for one agent. `data` = message history array.

---

## Group D — Command Center queue, Insights, Memory (verified)

### GET /api/brands/<brand_slug>/needs-you
The approval queue. Standard envelope; `data` =
```jsonc
{ "count": 2,
  "items": [ { "agent": "trend-researcher", "filename": "20260615_..._trend_report.json",
               "path": "outputs/pending_approval/trend-researcher/…", "created_at": "ISO" } ],
  "email_configured": true, "notification_email": "g***@gmail.com" }   // email masked, never raw
```

### GET /api/brands/<brand_slug>/costs?year=&month=
Monthly cost breakdown (defaults to current y/m). Standard envelope; `data` = `get_brand_monthly_costs()`
(per-source + per-agent cost rows). 503 if DB down. **Feeds the Insights "Cost & Tokens" panel.**

### GET /api/brands/<brand_slug>/narrative?n=&agent=
Story-so-far (Phase A). `n` ≤ 100, optional `agent` filter. `data` = `{ "entries": [...], "count": N }`.
Each entry = `{ agent, type, summary, refs, created_at }`. **Feeds Memory & Brain timeline.**

### GET /api/performance/history?brand_slug=…
Performance history (data-analyst). `data` = `{ "exists": true, ...performance_history.json }`.
⚠️ **There is no real-time social-metrics endpoint** — "Brand Health / LIVE" numbers come from here
(last data-analyst run), not live IG. The FE should label them with the run timestamp, not "live".

### Content calendar
No dedicated route — comes from **`GET /api/dashboard-output?brand_slug=…`** → `data.calendar_formatted`
(pre-formatted markdown) + `data.calendar` (raw). Same endpoint also returns `scripts_formatted`, `strategy_formatted`.

### GET /api/brands/<brand_slug>/connections
Per-platform live status (Instagram/LinkedIn/YouTube/X). **Never returns tokens.** Standard envelope;
`data` ≈ `{ "instagram": {"connected": true, "account": "@askgauravai"}, "linkedin": {...}, ... }`.

---

## Still un-documented (out of cockpit scope unless a screen needs it)
- **Approvals/Content actions:** `POST /api/outputs/approve|reject|request-changes|revise`, `GET /api/outputs/pending|all`, `/api/outputs/media/<path>`, `/api/published`, `POST /api/publish`, `POST /api/carousel/generate`.
- **Growth:** `POST /api/leads/capture`, `GET /lead-magnet/<slug>`; community/dm/email drafts read via `/api/outputs/pending?agent=<slug>`.
- **Concierge:** `POST /api/concierge` — the single Chief-of-Staff router (tiered, no-LLM trivial tier). The older `/api/brands/<slug>/concierge` was removed (Jun 17) to honor "chat drives intent, buttons guard actions."
- **Brand-Book / Uploads / Connections save-token / billing** — documented when a screen wires them.

## Known issues for the FE (senior-dev notes)
1. **Envelope inconsistency** — `/api/auth/*` + `/api/brands` use bare shapes; everything else uses `{success,data}`.
2. ~~Duplicate concierge endpoints~~ — **resolved (Jun 17):** only `POST /api/concierge` remains.
3. ~~`get_brands` duplicated `@require_auth`~~ — **resolved (Jun 17).**
