# GC Completion Runbook — Phases 1–4 (Jul 16 2026)

> The durable anchor for the autonomous completion loop. Each loop iteration:
> read this file → pick the next unchecked slice → build → test → verify →
> commit → push → CI green → check the slice off HERE (edit this file) → next.
> Memory context: `project_completion_plan_16jul` + `project_enforcement_net_16jul`.

## Identity rule (never violate)
GC is a **multi-tenant agency replacement** for any brand owner. **Third Gen Tribe
is a disposable SAMPLE.** No TGT-specific logic/prompts/data in product code —
everything generic, keyed by `brand_slug`.

## Protocol per slice (non-negotiable)
1. Build the slice (smallest shippable piece).
2. Test: fail-on-old / pass-on-fix, wired to the real code path.
3. Full suites: `python3 -m pytest tests/ utils/ .claude/hooks/test_test_guard.py test_reject_resolution.py -q` and `cd dashboard && npx tsc -b && npm test`.
4. `gc-verify` skill for anything runtime-observable (restart Flask for .py!).
5. Commit by EXPLICIT paths (never -A), push, confirm CI green (`gh run list`).
6. Check the slice off in this file (same commit or the next).
7. Anything needing Gaurav → append to `docs/GAURAV_TODO.md`, keep moving.

## Hard rules
No user-facing GC actions from CLI · no fabrication · RULE ZERO (infra/OAuth
unknowns → GAURAV_TODO.md, never guessed) · pre-flight before paid runs ·
one repo/main only · no raw JSON to humans.

---

## PHASE 1 — Supabase data home (brand state off the laptop)
Reference: `~/GC-ref-repos/SaaS-Boilerplate` (tenancy patterns only — no replatforming).
- [x] 1.1 Inventory DONE (Jul 16): docs/DATA_HOME_DESIGN.md — reader/writer map grep-verified; design = Supabase authoritative, disk = rehydratable cache via ONE brand_store module (30+ file readers stay untouched). Supabase already has brands/agent_outputs/brand_connections tables + RLS.
- [x] 1.2 Schema DONE (Jul 16): `brand_state` table (brand_id+file_key PK, jsonb content, RLS member-read/service-write) + private `brand-assets` storage bucket. Applied live via MCP; SQL copy: supabase/migrations/20260716_brand_state.sql. Advisor pre-existing warns (SECURITY DEFINER anon-exec, brands_insert always-true, leaked-pw protection off) → folded into 4.3.
- [x] 1.3 DONE (Jul 16): `supabase/brand_store.py` — hydrate(slug) fills cache from DB (freshness-guarded, never clobbers newer local), push(slug,key)/push_all upsert to brand_state (refuses corrupt/unknown). Flag GRID_BRAND_STORE=on (default off). 6 tests: tests/test_brand_store.py.
- [x] 1.4 DONE (Jul 16): hydrate wired into get_brand_dir (cold cache miss → DB fill before 404, 60s TTL memo); write-backs at create_brand, save_brand_profile, approve_brand_book (profile+voice+narrative), set_trust_dial, and _run_agent_subprocess success (push_all — agents write in subprocesses). All flag-gated GRID_BRAND_STORE (default off). Tests: tests/test_brand_store_wiring.py. Flask restarted healthy, flag-off behavior unchanged.
- [x] 1.5 DONE (Jul 16): `hydrate_vault()` cache-fills pending files from agent_outputs rows (names match FE's `{slug}_{id8}.json` so filename approve/reject resolve on a fresh server; never overwrites). Wired into the same TTL-gated hydrate path. Rows already carry full raw_output — DB was already written on every save; now it's readable-back. Tests extended (11 store tests).
- [x] 1.6 DONE (Jul 16): local round-trip proven (dir wiped → 8 files rehydrated JSON-identical) AND deployed proof: Gaurav confirmed Railway env keys, added GRID_BRAND_STORE=on, logged into the deployed dashboard → "Dashboard with Third Gen Tribe data". Along the way: fixed + test-pinned the blank-screen-after-login bug (auth boot threw on stale session → loading hung; commit 48b01d3). **PHASE 1 COMPLETE.**

## PHASE 2 — Sample brand through the DEPLOYED spine
- [x] 2.1 DONE (Jul 16): Gaurav confirmed SUPABASE_URL + SUPABASE_SERVICE_ROLE_KEY on Railway; added GRID_BRAND_STORE=on; redeployed.
- [x] 2.2 DONE (Jul 16): deployed /api/health 200, auth gate 401s unauthenticated, and Gaurav's real login rendered TGT data (hydrated from Supabase).
- [ ] 2.3 **GAURAV**: full click-through on production — login → brand loads → Atlas dispatch → output card → approve → (no publish yet). Write him a plain-words checklist in GAURAV_TODO.md.
- [ ] 2.4 Fix whatever his click-through surfaces (each fix ships with a test).

## PHASE 3 — Publishers (LinkedIn / YouTube / X) + publish pipeline
Mine: `~/GC-ref-repos/Socioboard-5.0` (working LI/YT/TW publish flows) — patterns only.
- [x] 3.1 ALREADY BUILT (verified Jul 16, prior session): publishing/linkedin_publisher.py complete — text/images/video via UGC API, token_status probe, prepared-mode fallback. Impl wired in core._publish_linkedin_impl. (Built pre-test-net; add mocked tests on first regression.)
- [x] 3.2 ALREADY BUILT (verified Jul 16): youtube_publisher.py — real upload via refresh token, zero-fabrication needs_video contract, prepared fallback.
- [x] 3.3 ALREADY BUILT (verified Jul 16): X manual-always enforced in core._publish_twitter_impl (prepared text package by default; auto only via explicit TWITTER_AUTO_PUBLISH opt-in). Policy pinned by tests/test_publish_policy.py.
- [x] 3.4 ALREADY BUILT (verified Jul 16): /api/publish routes all four platforms to real impls; ReviewPage has Drafts→Ready→Published lanes with per-item Publish button (usePublish). NOTE: stale comment in useGridApi.ts says LI/YT/TW 'unbuilt' — fix with next tested FE commit.
- [ ] 3.5 **GAURAV**: platform prerequisites → GAURAV_TODO.md (Meta/LinkedIn App Review, Google OAuth app "Publish app", real tokens per brand). Live publish test is HIS click, one platform at a time.

## PHASE 4 — Ops-auditor + first-client checklist
- [ ] 4.1 `agents/ops_auditor.py` — platform-level scheduled worker ($0 pattern like weekly_review_composer): checks API health (local+Railway), CI status (gh), paid ledger vs caps, Supabase advisors (security/performance), token expiries, disk/DB drift → weekly plain-English "Production Health" card. Registered `tier: none`. Tests.
- [ ] 4.2 Scheduler job (DISABLED by default; Gaurav enables).
- [ ] 4.3 First-client checklist doc: token encryption at rest, CORS restriction, ToS/Privacy/DPA status (legal/ has drafts), domain, backups. PLUS Supabase advisor fixes (Jul 16 scan): revoke anon/authenticated EXECUTE on SECURITY DEFINER fns (handle_new_user, is_brand_member/admin, mem_search_*, rls_auto_enable), fix `brands_insert`/`brain_usage` always-true policies, set function search_path, move vector ext out of public, enable leaked-password protection (Gaurav toggle). Verify what's code-checkable; ask Gaurav the rest.
- [ ] 4.4 Jun-24 security read + legal risk register review (GRIDLOCK-WIRE-24JUN memory) — fold unresolved items into the checklist.

## Done means
Runbook fully checked, CI green, GAURAV_TODO.md is the only remaining list,
and a real brand can run signup→onboard→book→approve→program→publish on the
deployed app the moment Gaurav's own items are complete.
