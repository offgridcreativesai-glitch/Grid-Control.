# CONNECTIONS SETUP — single source of truth (READ before touching any connection, UPDATE after any change)

Governed by RULE ZERO in `.claude/CLAUDE.md`: if something here is UNKNOWN, **ASK Gaurav — do not guess or infer.**

Last updated: 2026-07-11

## ⭐ ONE-TIME vs PER-BRAND (answer to the recurring "do I do this every brand?" — the answer is mostly NO)
- **ONE-TIME platform setup, NEVER repeated per brand:** Railway env vars (Variables tab on service `web`); the Meta OAuth **redirect URI** in the Instagram app's business-login settings; the Meta app itself (`1710260696579392`); the durable Supabase token store. All shared across every brand.
- **PER-BRAND but ONLY while the Meta app is "In development":** add that brand's Instagram account as an **Instagram Tester** on app `1710260696579392`. This ONE step disappears once the app passes **Meta App Review → Live**.
- **PER-BRAND always (trivial, done by the client, zero console work by Gaurav):** brand owner clicks "Connect Instagram" and authorizes their own account.
- Do NOT ask Gaurav to redo one-time platform steps for a new brand. If unsure whether something is one-time or per-brand, it's in this list — check here first.

---

## Token storage architecture (built Jul 8 2026, commit e0df097)
- Platform tokens persist in Supabase table `public.brand_connections` (KV: brand_id, env_key, value; encrypted `enc:<fernet>`; RLS on, service_role only). Durable, shared between the deployed (Railway) backend and local app/agents.
- `brands/<slug>/.env` is now only a local fallback/cache. `core.brand_env()` reads Supabase-authoritative; `_write_brand_env_token()` mirrors to both.
- OAuth callbacks point at the **stable Railway URL** (never a tunnel): `https://web-production-175d5.up.railway.app`. Set `OAUTH_PUBLIC_BASE_URL` to this on BOTH local and Railway. This retires the ephemeral-tunnel bug — Meta/Google/etc. redirect URIs get whitelisted ONCE and never drift.
- Railway env vars that MUST equal local exactly or the flow breaks: `GRID_TOKEN_ENCRYPTION_KEY` (else tokens written on Railway won't decrypt locally), `DASHBOARD_SECRET` (state signing), the platform app id/secret pairs, `SUPABASE_URL`/`SUPABASE_SERVICE_ROLE_KEY`/`SUPABASE_ANON_KEY`.

---

## Bright Data — scrape provider (added Jul 11 2026, VERIFIED live)
- **Account:** `gridadmin1@gmail.com`. **Infra-level — ONE account for ALL brands** (NOT per-brand). Billing added Jul 11 (free 5K records/mo, then pay-as-you-go ~$1.50/1K; blocked/failed requests never billed, no monthly minimum).
- **Token:** `BRIGHTDATA_API_TOKEN` lives in the **global `/.env`** (infra credential — NOT per-brand, NOT in `brands/<slug>/.env`, NOT in Supabase brand_connections). 36-char account API token from BD dashboard → Settings → API Tokens. (An earlier token got pasted in chat and was rotated — current one is the rotated value.)
- **Purpose:** alternative scrape provider to Apify for the brand-book intel pipeline. Higher reliability than Apify community Actors (which silently break), richer output (returns `avg_engagement`, `category_name`, `related_accounts`, `external_url`, `email_address` etc. that the IG Login API + Apify don't).
- **Client:** `agents/_lib/_brightdata_client.py` — Web Scraper API v3 (`POST /datasets/v3/trigger` → poll `/progress/{id}` → download `/snapshot/{id}`). Selected via `SCRAPE_PROVIDER` env flag (`apify` | `brightdata`, default apify — set to `brightdata` in `/.env` to activate); **Apify stays the fallback.** To run live either way, `GRID_PAID_OPS=1` (same cost gate).
- **Pilot (Jul 11):** ran IG scrape on TGT's 3 competitors via BD — all routed `via: brightdata`, `SCRAPE_PROVIDER=brightdata` live in `/.env`. Win: BD returns follower counts the Apify cache had as `None` (enables engagement-RATE). Caveat: BD samples 12 recent posts (profile endpoint's embedded `posts[]`) vs Apify's 24 → absolute engagement differs; relative ranking preserved since all competitors use BD uniformly. Decision: keep the 12-post profile endpoint (recent + followers + correct account); do NOT reopen the Posts-scraper "own vs tagged" issue for +12 posts.
- **Wiring status (Jul 11):** competitor **Instagram** in `competitor_intel.py` = ✅ **DONE + verified end-to-end** (BD profile scraper → mapped to the exact Apify output shape, `via` field tags provider, Apify auto-fallback). `meta_ads()` + `youtube()` = **still Apify** (BD Meta Ad Library input schema not yet confirmed — do NOT switch until verified). `brand_self` (brand's OWN IG) intentionally **unchanged** — it uses the IG Login API (authoritative connected-account data), not a scraper.
- **Dataset IDs (gd_*, global per scraper):** `instagram_profiles = gd_l1vikfch901nx3by4` ✅ VERIFIED. `instagram_posts = gd_lk5ns7kz21pck8jpis` ✅ verified (returns profile's own posts). `instagram_hashtag = gd_lk5ns7kz21pck8jpis` (= posts dataset via `discover_by=hashtag`; no standalone hashtag scraper exists). `facebook_ads = None` — **Bright Data has NO Meta Ad Library scraper** (confirmed Jul 11 on Gaurav's screen; BD Facebook scrapers are Pages/Posts/Comments/Profiles/Marketplace/Reels/Reviews only). Meta Ad Library **stays on Apify** (`brilliant_gum/facebook-ads-library-scraper`) — hybrid by design, do NOT build a custom BD Ad Library scraper.
- **SERP zone (social listening, gap #4):** Bright Data **SERP API** zone **`grid_control`** created Jul 11 (Web Access → SERP API, Full JSON). `BRIGHTDATA_SERP_ZONE=grid_control` in the global `/.env` (same account token — no new key). Called via the Direct API `POST https://api.brightdata.com/request` with `{"zone","url","format":"json","data_format":"parsed"}`; results are wrapped in a `body` JSON-string envelope (unwrap it). `serp_search()` in `_brightdata_client.py` → `agents/intel/social_listening.py` → `/api/listening` (+ `/run`). ✅ VERIFIED live on TGT (12 real mentions). Cost-gated by `GRID_PAID_OPS` (free tier 5K/mo).
- **Gotcha:** `400 Customer is not active` = account billing not activated → add a payment method at brightdata.com/cp (free tier still needs a card on file). Resolved Jul 11.

---

## Instagram — 🔒 LOCKED (Jul 8 2026, confirmed on Gaurav's live screen)

**THE Grid Control Instagram app = "Grid Control – TGT test", App ID `1710260696579392`** (account `gridadmin1@gmail.com`, In development / Unpublished). Its Use cases page HAS **"Manage messaging & content on Instagram"** (Instagram API — publish/stories/comments/DMs) + "Manage everything on your Page". This is the app all brand Instagram OAuth uses. (Name still says "TGT test" — rename to something like "Grid Control – Instagram" when convenient; the App ID is what matters.)

- The OTHER app, **"Grid Control Admin Panel" `1808033523500012`**, CANNOT host Instagram (only "Facebook Login" use case is addable there). Do NOT try to add Instagram to `1808033523500012` — that's the dead-end loop. Instagram lives in `1710260696579392`. Two distinct apps, one purpose each.
- Code: `publishing/instagram_login.py` → `https://www.instagram.com/oauth/authorize`, `client_id = INSTAGRAM_APP_ID`.
- **Env is ALREADY CORRECT — do not change the app id.** Confirmed on live screen Jul 8: app `1710260696579392` → "API setup with Instagram login" shows Instagram app name "Grid Control - TGT test-IG", **Instagram app ID `2158492338217879`**, which matches env `INSTAGRAM_APP_ID`. `INSTAGRAM_APP_SECRET` also correct (this OAuth flow succeeded before with these creds). (Earlier note that `2158492338217879` was "stale/wrong-app" was Claude's mistake — it is the right app's IG app ID.)
- Messaging permissions already added (green): instagram_business_basic, manage_comments, manage_messages.
- **Redirect URI to whitelist ONCE** — goes in this app's **Instagram Business login settings → "Valid OAuth Redirect URIs"** (NOT the webhook "Callback URL" field, which is a different thing):
  `https://web-production-175d5.up.railway.app/api/connections/instagram/callback`
- **Why it worked before and failed this session:** login DID succeed previously — a Cloudflare tunnel URL was whitelisted at that moment. It failed now because that tunnel URL is ephemeral and changed, so it no longer matched the whitelist. The permanent Railway URL (already set in env Jul 8) fixes this for good: whitelist it once, it never drifts.

### 🔑 The permanent multi-brand fix (so onboarding is NOT per-brand work)
Per-brand friction (adding each brand's IG as a Tester) exists ONLY because the app is **"In development"**. In dev mode Meta only lets accounts with an app *role* connect.
- **One-time fix = Meta App Review on app `1710260696579392` → set it Live.** After that, ANY brand connects by just clicking "Connect Instagram" and authorizing their own IG — zero Meta-console work per brand, one redirect URI whitelisted once, no per-brand app or tester. This is ONE app for ALL brands, never one-app-per-brand.
- App Review needs: business verification, privacy-policy URL, a working OAuth-flow demo/screencast, and per-scope justification. Days–weeks, once for the whole platform.
- **Today's stopgap for Third Gen Tribe UAT:** keep app in dev mode + `thirdgentribe` as Instagram Tester → connect. Do App Review in parallel as the real fix. Gaurav approved this direction Jul 8.

### ✅ Setup state on app 1710260696579392 (confirmed on live screen Jul 8 — do NOT re-ask)
- `thirdgentribe` is already an **Instagram Tester**, invite **ACCEPTED** (Roles tab shows it). DONE — never ask Gaurav to re-add/re-accept this.
- Also an Administrator on the app: "Aastha Khanna".
- **OAuth redirect URI** in Business login settings updated from the old dead tunnel (`reproductive-coleman-blvd-renewable.trycloudflare.com/...`) to the permanent Railway URL `https://web-production-175d5.up.railway.app/api/connections/instagram/callback` on Jul 8 (Gaurav clicked Save; final proof = a successful connect with no redirect_uri error).
- Messaging permissions added (instagram_business_basic, manage_comments, manage_messages).
- STILL OPEN before connect can succeed: Railway env parity (callback now lands on Railway, not local) — see Railway section below. NOTE: it "worked before" via a tunnel to LOCAL flask, so Railway env was never needed until we moved the callback to Railway today.

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
