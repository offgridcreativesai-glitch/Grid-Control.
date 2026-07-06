# GRID CONTROL — Build Plan + As-Built Status

> Safe word: **GRIDLOCK-RESUME-18JUNE**.
> Master sequence (Gaurav, unchanged): **Backend → Frontend → Stitch → Test brand → Launch.**
> **Plan written Jun 18 2026 · As-built status updated Jun 20 2026.**
>
> **STATUS: Backend (Master-Sequence Step 1) = ✅ COMPLETE.** Phases 1–5 shipped + validated.
> Total Phase-5 validation spend ≈ **$1.83** (budget was $15). Now moving to **Step 2 — Front-end.**
> Legend: ✅ shipped · ⚠️ shipped with deviation · ⛔ not done (reason) · ⏳ pending.

## 0 · Why this exists

After the Jun 18 deep-fetch of ~71 repos (`REPO_RESEARCH_INDEX.md` §C), two system-level pieces —
**semantic memory** and **observability/cost** — touch every agent, so they went FIRST, before per-agent
expertise packs. **caveman** is separate: a Claude-Code session-ergonomics skill (cuts build-chat tokens),
NOT a production-cost lever. Picsart Agents (reviewed Jun 18) added one backlog item only: WhatsApp/Telegram
as future Chief-of-Staff channels (post-launch).

## 1 · Phase 1 — Foundation upgrades ✅ COMPLETE

| # | Item | As-built status |
|---|---|---|
| 1a | Semantic memory backbone | ⚠️ **Shipped as Voyage `voyage-3-lite` (512-dim) → Supabase pgvector**, NOT the `mem0ai` lib (chose direct embed→pgvector for control + simplicity). Migrations 007/008. `agents/_lib/_mem0_client.py`. **2 scopes** (`grid_control` + `brand:<slug>`), not 3 — Gaurav's call, keeps agent context clean. strategy-agent wired as first consumer (recall before, write winner after). |
| 1b | Langfuse observability | ⚠️ **Langfuse Cloud** (free tier), not self-hosted. `cost_reporter` **KEPT** (not retired) — `utils/pricing.py` is the cost source of truth; Langfuse is additive. Per-generation cost attribution **fixed** (`start_generation` context mgr + `base_agent.lf_generation`); strategy-agent wired + verified on cloud. Other agents adopt the one-line wrap when next touched. |
| 1c | rate_limit decorator-order bug | ✅ Already fixed earlier (commit 32aa062, Jun 16) — `@bp.route` outer / `@rate_limit` inner on all 10 endpoints. Audit-confirmed. |
| 1d | AgentShield baseline | ✅ Baseline saved (`docs/AGENTSHIELD_BASELINE_18JUNE_FIXED.txt`). Grade C (62/100); 2 CRITICALs eliminated (sudo allow-rules removed + `Bash(sudo *)` denylisted). Re-run before first client. |
| 1e | caveman skill | ✅ Installed **opt-in only** (`/caveman …`), not always-on (CLAUDE.md already caps length). Dev-ergonomics, doesn't touch the 18 agents. |

## 2 · Phase 2 — Data & research hardening ✅ COMPLETE

| # | Item | As-built status |
|---|---|---|
| 2a | Scrapling | ✅ `agents/_lib/_scrapling_client.py` (Fetcher + stealthy_headers). New `trend_researcher.scrape_competitor_websites()` reads `brand_profile.competitor_websites`. **Additive — NOT an Apify replacement** (Apify stays canonical for IG/YT, fixed-cost Starter plan). |
| 2b | Supadata video→transcript | ✅ `agents/_lib/_supadata_client.py`. `trend_researcher._extract_whisper_transcripts` now Supadata-first / Whisper-fallback. Real fix: yt_dlp was silently missing → transcripts broken for months. |
| 2c | Google/Meta/GA4 metrics MCP | ⛔ **Not installed.** Native Meta Ads/IG MCP already connected (~80 tools cover Meta). Ryze unified MCP redundant + blocked (signup needs a website that doesn't exist yet). GA4 + Google Ads metrics deferred until those upstream accounts actually exist — not blocking. |

## 3 · Phase 3 — Expertise packs ✅ COMPLETE (lighter than original spec)

⚠️ **Shipped as prompt-only expertise-pack tables** in each `managed_agents/prompts/*.md` (sub-task → skill
mapping before the AutoResearch loop). **13 agents wired, 1 N/A** (carousel-designer = deterministic renderer).
No per-agent `program.md` files (the original exit criterion) — the prompt-table approach was lighter and
sufficient. Packs used: `arnabbagxd/Brand-building-skills`, `phuryn/pm-skills`,
`carlosarthurr1/business-playbook`, `AgriciDaniel/claude-ads` + existing higgsfield/geo/searchfit/design/
data/marketing/sales packs.

> **Roster correction:** the Jun-18 draft listed a "Lead Generator" (3o) and "AI-setter" (3p) as agents.
> Those are **NOT in the locked 18-agent roster.** No new agents were created — `dm-customer-hunter`
> absorbed local-biz prospecting instead (see 4b). The 18-agent roster is unchanged.

## 4 · Phase 4 — Routing policy + new capabilities ✅ COMPLETE

| # | Item | As-built status |
|---|---|---|
| 4a | Cheaper tier for high-volume grunt | ⚠️ **Haiku GRUNT tier, SPLIT not swap.** `model_gateway.grunt_model()` = `claude-haiku-4-5`. `community-manager` + `dm-customer-hunter` split 2-stage: **Haiku triages ALL items** (categorize / ICP-score, incl. spam/off-ICP) → **Sonnet writes brand-voice only for winners.** Honors the Jun-9 Sonnet-floor lock (brand-facing text never on Haiku). Separate cost lines. (No "Lead Generator"/"AI-setter" — those agents don't exist.) |
| 4b | Local-biz prospecting | ⚠️ **Apify Compass `crawler-google-places`**, NOT `omkarcloud/google-maps-scraper` (botasaurus/Chromium = heavy on Railway). Reuses existing `_apify_run_sync`. `discover_via_google_maps()` gated on `brand_profile.gmaps_queries` (off by default, brand-agnostic). Flows through the same Haiku triage. Zero new deps. |
| 4c | Google Ads API client | ✅/⏳ `agents/_lib/_google_ads_client.py` wired. **OAuth chain verified LIVE** (returns MCC `customers/7023267019`). Dev token in **TEST** access; **Basic Access application submitted Jun 19 → Google review 5–14 business days.** Live campaign data unlocks on approval. |

## 5 · Phase 5 — Validation gate ✅ COMPLETE (≈ $1.83 of $15 budget)

| # | Item | As-built status |
|---|---|---|
| 5a | F4 magnet copy via funnel_specialist | ✅ Ran for askgauravai → winner Variant C, in `pending_approval/funnel-specialist/`. **$0.115.** Fixed a real bug: `run_autoresearch_loop` max_tokens 6000→16000 (3-variant JSON was truncating). |
| 5b | Paid-ops validation | ⚠️ **Tested DRY ($0, NO real ads).** Gaurav vetoed ad spend — never discussed + not in the master sequence yet (paid = Step 5, post brand-onboard). Circuit-breaker verified on all 4 gate states (switch-off→block, on+under-cap→allow, on+est>cap→block, on+ledger-over-cap→block). Real-spend ledger confirmed live. |
| 5c | End-to-end smoke test | ⚠️ **Lean keystone run** (not all 13 agents — most unchanged except prompt packs). Ran strategy-agent (Opus, $1.554 — 3 passes, Rule-10 forced 2 citation re-prompts → 13/13) + community-manager + dm-customer-hunter (Haiku split, ~$0.04) on synthetic inputs (since deleted). **Proven live:** semantic recall+write · Rule-10 provenance loop · Haiku triage→Sonnet split · cost capture · Langfuse traces in cloud. |

**Findings (non-blocking):** (1) Langfuse trace-level cost was $0 — fixed via `start_generation` wrap
(strategy done; others adopt when touched). (2) Notion push broken everywhere — `NOTION_PAGE_ID` is a URL
not a UUID + Notion bill unpaid; outputs save locally to `pending_approval/`.

**Exit criteria of Phase 5 = exit of Master-Sequence Step 1 (Backend). ✅ MET.**

## 6 · Cost-control actions (Jun 19–20)

Gaurav recharged Anthropic credits = **TEST USE ONLY; no automation runs without an explicit green signal.**
- ✅ Railway **scheduler-worker service REMOVED** (was firing askgauravai 06:30 + offgrid 07:00 IST daily — Apify+Claude spend). `scheduler/schedule_config.json` jobs also set `enabled=false`.
- ✅ Local crontab already disabled (Jun 16). Paid-ops **kill-switch OFF (safe)**; `GRID_PAID_OPS` never persisted.
- ℹ️ A separate `Trading-Bot` paper loop (`run_v2_paper.py`, until Jun 30) uses **no** Anthropic credits — left running.

## 7 · Housekeeping (Jun 20)

- ✅ **Dead code removed:** `jarvis_config/`, `jarvis-skills/`, `scripts/install_jarvis.sh` (April voice
  experiment, never imported) + 4 stale AgentShield-flagged allow-rules. Live `/api/jarvis/query` route kept.
- ⚠️ Orphan candidate flagged: `main.py` (stale launcher, superseded by `dashboard_api.py`) — awaiting decision.
- ✅ **Backend committed + pushed** to `gridcontrol-rebuild` (7 commits): scheduler pause, 4a/4b+funnel-fix,
  Mem0+Langfuse+cost-fix, Scrapling+Supadata, Phase-3 packs, Google Ads client, docs/config, jarvis cleanup.

## 8 · NEXT — Master-Sequence Step 2: Front-end

Build the **GRID CONTROL** owner-facing command deck. Direction locked Jun 20 (`docs/FE_MASTER_PROMPT.md`):

- **Mental model:** Owner → **Chief of Staff** (the one persona they talk to) → **the Team on the factory
  floor** (avatar'd specialist *characters* who visibly work and bring finished pieces up for approval).
  Like an owner directing a manager and watching the team build it.
- **THE SECRET (hard rule):** the client UI **never** exposes backend machinery — no model names, costs,
  tokens, JSON, provenance, agent slugs, or infra. The team are *people*; the technology is invisible.
  Cost/token transparency is **internal ops only**, removed from the client UI.
- **Character/avatar system** is a design pillar (warm mascot energy, one per role).
- Design vibe to be chosen from Gaurav's **reference links** (slot in FE prompt §7 + §13).
- Build path: design against mock data → wire to the live API (`web-production-175d5…`) → translate every
  technical field into character/outcome language at the boundary.

## 9 · Deferred (not in this plan)

Higgsfield PRO + per-agent creative work (Step 5) · ManyChat F3 / live AI-setter (needs live offer + 2 links)
· Open Design mining · WhatsApp/Telegram CoS channels (post-launch) · Postiz on Hetzner (post-launch)
· GA4/Google-Ads live metrics (when those accounts exist) · roll Langfuse cost-wrap out to remaining agents.

---

*Related: [FE_MASTER_PROMPT](FE_MASTER_PROMPT.md) · [REPO_RESEARCH_INDEX](REPO_RESEARCH_INDEX.md) · [ONBOARDING_CLONE_SPEC](ONBOARDING_CLONE_SPEC.md) · [CREATIVE_ENGINE_REBUILD](CREATIVE_ENGINE_REBUILD.md) · [AGENT_MODEL_FIT_RESEARCH](AGENT_MODEL_FIT_RESEARCH.md).*
