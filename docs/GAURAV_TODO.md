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

## Jul 16 — Q5: fresh Chrome login bounced to landing (localhost)
**Reported:** Fresh Google login in Gaurav's Chrome on localhost:5280 → dumped
back on the landing page, signed out. (Closed tab by accident — harmless.)
**Root cause found:** the landing page lives outside the auth system; when a
sign-in returns to the site root (Supabase Site-URL fallback), the login code
in the URL was silently dropped. Fixed (commit d418836) + 5 tests + verified
live: a login code on "/" now forwards into the app.
**Also caught:** the live site's address was MISSING from Supabase Redirect
URLs → Gaurav asked to add `https://v0-grid-control-dashboard.vercel.app/command`
and Save. **Answered:** (pending)
**Retry for Gaurav:** open http://localhost:5280 in Chrome → sign in with
Google (tgtstoress) → should land on the Third Gen Tribe dashboard, not landing.
**Answered (Jul 16):** "Was able to sign in into my account." FIXED, Gaurav-verified.
**Still open from Q5:** confirm the Vercel line was added to Supabase Redirect
URLs (needed before fresh logins on the LIVE site — ask again before 2.3).

## READY WHEN YOU ARE — the production dress rehearsal (runbook 2.3)
Whenever you have ~10 minutes, on https://v0-grid-control-dashboard.vercel.app:
1. Log in (tgtstoress account) → Third Gen Tribe dashboard loads.
2. In Atlas chat, type: "What should we track this week? Run the trend check."
   → Atlas should DISPATCH a real specialist (you'll see it working, not
   instant fake text). The trend check costs $0 (pure math, no AI credits).
3. When its card appears in Review → open it → the text reads like a human
   wrote it (no raw data dumps) → click Approve → the card moves to Ready.
4. Tell me what happened at each step — anything odd, I fix with a test.
Before this: confirm the Supabase Redirect URLs line from Q5 was added
(`https://v0-grid-control-dashboard.vercel.app/command`) — fresh logins on the
live site need it.

## FOR LATER — publishing prerequisites (runbook 3.5, your accounts only)
The publish buttons exist and are honest: without live tokens they produce a
"prepared" package instead of posting. To make them post for real, per brand:
- **Instagram/Meta**: the Meta app (1710260696579392) needs App Review → Live
  (one-time, all brands benefit). Until then: connect via Connections page works
  for testers only.
- **LinkedIn**: connect the brand's LinkedIn on the Connections page (token +
  URN saved per brand).
- **YouTube**: Google OAuth app is in "Testing" — tokens die every 7 days.
  One-time fix: Google Cloud Console → OAuth consent screen → "Publish app".
- **X**: manual by standing rule — GC prepares the text; you post it.
No rush — tell me which platform first and I'll walk that one with you.
