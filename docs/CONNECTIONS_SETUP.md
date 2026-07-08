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

## Instagram — 🔒 LOCKED (Jul 8 2026, confirmed on Gaurav's live screen)

**THE Grid Control Instagram app = "Grid Control – TGT test", App ID `1710260696579392`** (account `gridadmin1@gmail.com`, In development / Unpublished). Its Use cases page HAS **"Manage messaging & content on Instagram"** (Instagram API — publish/stories/comments/DMs) + "Manage everything on your Page". This is the app all brand Instagram OAuth uses. (Name still says "TGT test" — rename to something like "Grid Control – Instagram" when convenient; the App ID is what matters.)

- The OTHER app, **"Grid Control Admin Panel" `1808033523500012`**, CANNOT host Instagram (only "Facebook Login" use case is addable there). Do NOT try to add Instagram to `1808033523500012` — that's the dead-end loop. Instagram lives in `1710260696579392`. Two distinct apps, one purpose each.
- Code: `publishing/instagram_login.py` → `https://www.instagram.com/oauth/authorize`, `client_id = INSTAGRAM_APP_ID`.
- **Env to update to THIS app's Instagram credentials** (local `.env` + Railway): `INSTAGRAM_APP_ID` + `INSTAGRAM_APP_SECRET` = the Instagram app id/secret shown inside `1710260696579392`'s Instagram use case → Customize / API setup. (Old value `2158492338217879` was from the wrong app — replace it once we read the real one.) STATUS: not yet read/updated.
- **Redirect URI to whitelist ONCE**, in `1710260696579392`'s Instagram business-login settings:
  `https://web-production-175d5.up.railway.app/api/connections/instagram/callback`

### 🔑 The permanent multi-brand fix (so onboarding is NOT per-brand work)
Per-brand friction (adding each brand's IG as a Tester) exists ONLY because the app is **"In development"**. In dev mode Meta only lets accounts with an app *role* connect.
- **One-time fix = Meta App Review on app `1710260696579392` → set it Live.** After that, ANY brand connects by just clicking "Connect Instagram" and authorizing their own IG — zero Meta-console work per brand, one redirect URI whitelisted once, no per-brand app or tester. This is ONE app for ALL brands, never one-app-per-brand.
- App Review needs: business verification, privacy-policy URL, a working OAuth-flow demo/screencast, and per-scope justification. Days–weeks, once for the whole platform.
- **Today's stopgap for Third Gen Tribe UAT:** keep app in dev mode + add `thirdgentribe` as an Instagram Tester (accept invite from that IG account) → connect. Do App Review in parallel as the real fix. Gaurav approved this direction Jul 8.

- History: this OAuth flow has NEVER completed end-to-end (askgauravai used a hand-pasted Graph token). This UAT is its first real run.

**NEXT ACTION: open `1710260696579392` → Instagram use case → Customize/API setup → read the Instagram app ID + secret, add the redirect URI, add the tester. Guide/verify against Gaurav's live screen — never guess the click-path.**

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
