# Gaurav ↔ Loop — running log of asked & answered

## Jul 16 — Q1: Railway environment variables (Phase 1.6 → 2.1)
**Asked:** The cloud brand-data system is built and proven locally (your sample
brand's data round-trips through Supabase perfectly). To turn it on for the
DEPLOYED server I need to know what Railway already has — I cannot see your
Railway settings (RULE ZERO).

**How to check (2 minutes):** railway.app → log in → project **web-production-175d5**
→ click the service → **Variables** tab. Look for these names in the list:
`SUPABASE_URL` and `SUPABASE_SERVICE_ROLE_KEY`.

**Then:** whatever the answer, we'll also add one new variable there together:
`GRID_BRAND_STORE` = `on` — the switch that activates cloud brand data on the server.

**Answered (Jul 16):** Both `SUPABASE_URL` and `SUPABASE_SERVICE_ROLE_KEY` exist on Railway. → Next: add `GRID_BRAND_STORE=on` (Q2).

## Jul 16 — Q2: flip the switch on Railway
**Asked:** In the same Variables tab: **New Variable** → name `GRID_BRAND_STORE`, value `on` → save. Railway redeploys itself (~2 min).
**Answered (Jul 16):** Added and deployed. Fable verified: deployed /api/health 200, auth gate intact.

## Jul 16 — Q3: the 2-minute live proof (Phase 2.2/2.3 first pass)
**Asked:** Open https://v0-grid-control-dashboard.vercel.app → log in with the
sample-brand account (Google, tgtstoress@gmail.com) → open Third Gen Tribe.
Look for: brand loads with its real profile data (not "brand not found", not
onboarding restart), and the Review vault shows the approved brand book.
**Answered (Jul 16):** BLANK screen after login. Fable diagnosed live: a stale
stored session made the auth boot throw (Invalid Refresh Token) → app hung on
loading forever. Fixed (commit 48b01d3) + test + verified with a planted
corrupt token → now lands on sign-in instead of hanging. Redo the check after
Vercel redeploys (~2 min): hard-refresh the page (Cmd+Shift+R), log in again.

## Jul 16 — Q4: retry after auth fix
**Answered:** Logged in (Google screen skipped = normal remembered session) →
**"Dashboard with Third Gen Tribe data."** PHASE 1 PROVEN: the deployed server
served brand data hydrated from Supabase — nothing came from the laptop.
