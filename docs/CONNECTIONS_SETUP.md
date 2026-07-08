# CONNECTIONS SETUP — single source of truth (READ before touching any connection, UPDATE after any change)

Governed by RULE ZERO in `.claude/CLAUDE.md`: if something here is UNKNOWN, **ASK Gaurav — do not guess or infer.**

Last updated: 2026-07-08

---

## Token storage architecture (built Jul 8 2026, commit e0df097)
- Platform tokens persist in Supabase table `public.brand_connections` (KV: brand_id, env_key, value; encrypted `enc:<fernet>`; RLS on, service_role only). Durable, shared between the deployed (Railway) backend and local app/agents.
- `brands/<slug>/.env` is now only a local fallback/cache. `core.brand_env()` reads Supabase-authoritative; `_write_brand_env_token()` mirrors to both.
- OAuth callbacks point at the **stable Railway URL** (never a tunnel): `https://web-production-175d5.up.railway.app`. Set `OAUTH_PUBLIC_BASE_URL` to this on BOTH local and Railway. This retires the ephemeral-tunnel bug — Meta/Google/etc. redirect URIs get whitelisted ONCE and never drift.
- Railway env vars that MUST equal local exactly or the flow breaks: `GRID_TOKEN_ENCRYPTION_KEY` (else tokens written on Railway won't decrypt locally), `DASHBOARD_SECRET` (state signing), the platform app id/secret pairs, `SUPABASE_URL`/`SUPABASE_SERVICE_ROLE_KEY`/`SUPABASE_ANON_KEY`.

---

## Instagram — 🔒 LOCKED DECISION: needs its OWN dedicated Meta app

**Gaurav has stated this repeatedly, with screenshots.** The existing Meta app **"Grid Control Admin Panel"** (App ID `1808033523500012`, business_id `1652546332524982`, under the `gridadmin1@gmail.com` Facebook/Meta developer account) **CANNOT add the "Instagram API with Instagram login" use case** — its Use cases page only offers/permits "Authenticate and request data with Facebook Login". So Instagram OAuth cannot live in that app.

- **Decision:** create a SEPARATE, dedicated Meta app for Instagram OAuth (Instagram API with Instagram login). Status: **NOT yet created** (as of Jul 8).
- **Why a separate app (not just a use case):** the current app physically won't let the Instagram use case be added. (If Gaurav has an additional reason — app review / business verification — capture it here when he states it.)
- Code that drives it: `publishing/instagram_login.py` → `https://www.instagram.com/oauth/authorize`, `client_id = INSTAGRAM_APP_ID` (falls back to `META_APP_ID`).
- **Stale env warning:** current `INSTAGRAM_APP_ID=2158492338217879` / `INSTAGRAM_APP_SECRET` do NOT correspond to a working Instagram-login app (that value came from the old app that can't host the use case). Once the new dedicated app exists, its Instagram app ID + secret REPLACE these in local `.env` AND Railway.
- **Redirect URI to whitelist once, in the NEW app's Business login settings:**
  `https://web-production-175d5.up.railway.app/api/connections/instagram/callback`
- Dev-mode gotcha to expect after the app exists: the IG account being connected (e.g. `thirdgentribe`) must be added as an **Instagram Tester** and accept the invite, or consent fails.
- History: this flow has NEVER completed end-to-end. askgauravai's old IG connection used a hand-pasted Graph token, not this OAuth flow. This UAT is its first real run.

**NEXT ACTION (needs Gaurav): create the dedicated Instagram Meta app. Claude has no Meta console access and will NOT guess the click-path — guide/verify against Gaurav's live screen.**

## Facebook / Meta (Graph) — app "Grid Control Admin Panel"
- App ID `1808033523500012` = `META_APP_ID`; account `gridadmin1@gmail.com`; business_id `1652546332524982`; app is Unpublished (Development). Has the "Facebook Login" use case only.

## Google / YouTube — UNKNOWN here, confirm before use
- Google Cloud + OAuth app owned by `gridadmin1@gmail.com` (per platform-identity memory). Redirect URI for YouTube callback would be `.../api/connections/youtube/callback`. **State of the Google OAuth app's authorized redirect URIs = UNKNOWN — ASK before relying on it.**

## LinkedIn — UNKNOWN, ASK
- Prior askgauravai connection used hand-edited tokens. Dedicated LinkedIn app / redirect-URI state = UNKNOWN.

## X / Twitter — UNKNOWN, ASK
- Prior askgauravai used hand-edited OAuth 1.0a keys. App/redirect state = UNKNOWN.

---

## Change log
- 2026-07-08: Created. Recorded durable Supabase token store, stable Railway callback, and the LOCKED "Instagram needs its own app" decision (existing app can't add the IG use case).
