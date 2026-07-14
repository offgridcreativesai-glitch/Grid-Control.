# Grid Control — Honest Handoff (Jul 14 2026)

Written for a fresh model / developer / Fable 5 to pick this up. No sugar-coating. The founder
(Gaurav) is **non-technical** — he gives intent, the AI executes. Treat that as a hard constraint.

---

## 1. What Grid Control is

An 18-agent autonomous marketing OS on the Claude Agent SDK.
- **Backend:** Python Flask (`dashboard_api.py`, port 5001), agents are standalone scripts in `agents/*.py` dispatched as subprocesses, registered in `core.AGENT_SCRIPTS`.
- **Frontend:** React 19 + Vite (port 5280) + Tailwind v4 + TanStack Query v5 + Zustand, in `dashboard/`.
- **Data:** Supabase (Postgres + auth + RLS). Deploy: Vercel (FE) + Railway (API). Auto-deploys from `main`.
- **Persona layer ("THE SECRET"):** the client never sees 18 agents — every backend slug maps to one of 9 friendly characters (`dashboard/src/lib/agentPersona.ts`). Atlas = chief of staff / orchestrator.
- **Onboarding → report → approve → agents** is the intended flow. All agent output is gated by human approval (`brands/<slug>/outputs/pending_approval/` → `approved/`).

## 2. The single most important architectural fact (source of most bugs)

**Brand data lives in local files (`brands/<slug>/…`), which are GITIGNORED and therefore NOT on Railway.** Supabase holds auth + some metadata + agent_outputs rows, but the actual generated artifacts and many per-brand files are local-only.

Consequence: **the deployed app and the local app are two different worlds.** The reference brand "Third Gen Tribe" (TGT) only exists fully on the founder's laptop. This split is the root of repeated confusion. **This must be resolved (pick one source of truth) before the product is trustworthy.**

## 3. What was built this session (all committed to `main`)

- Competitor-gap features: Creative Library, analytics panel, Social Listening, Reputation engine, White-label branding + reseller-economics panel (all reuse Bright Data SERP + existing billing).
- Bright Data adopted as scrape provider (`SCRAPE_PROVIDER=brightdata`); Apify kept as fallback/Meta-Ads.
- **Voicebox:** local founder-voice clone (Chatterbox in a `~/.venvs/voicebox` Python 3.12 venv, shelled out from the 3.14 app). Verified working end-to-end on the founder's Mac. LOCAL-ONLY (needs the Mac's GPU; can't run on Railway).
- Three previously-unimplemented agents built: **ad-strategist** (budget-gated), **seo-aeo-agent** (real technical audit via scrapling, verified 92/100 on the live site), and **email-marketing-agent** extended to nurture/testimonial/reengagement.
- New **Beacon** persona (9th cast character) for the SEO agent + its art.
- **Atlas dispatch fix:** the Brain (Atlas) previously had NO way to run agents (client chat ran with `tools=[]`), so it fabricated answers "from training." Added a `run_agent` tool + gated approval card so Atlas dispatches real specialists. **Model-level verified only — never confirmed by a real human click-through.**
- Bug fixes today: onboarding no longer restarts when the API is down; demo mode can no longer hijack a real login.

## 4. What is genuinely broken or unverified (HONEST list)

1. **No tests. No CI. Nothing pins a fix.** This is why the SAME bugs regressed 5–6 times. Every fix shipped on "looks right," not "proven and locked." **This is the #1 problem.** Until there's a test suite + a CI gate that blocks broken deploys, regressions will keep reaching the founder live.
2. **Environment is nondeterministic.** Flask doesn't auto-start after a reboot; local vs deployed data differ; "it works" means different things on different runs.
3. **Brand-isolation landmine:** ~25 endpoints default `brand_slug` to the hardcoded `"offgrid-creatives-ai"` when the parameter is missing. A missing/empty slug silently serves or writes the WRONG brand. **NOT fixed. High priority** — should require an explicit brand_slug and error otherwise.
4. **Atlas end-to-end dispatch is unverified by a human.** It compiles and the tool exists; nobody confirmed a real "tell Atlas → agent runs → output appears" click-through.
5. **Approve/reject "stuck" items** were likely caused by clicks made while the API was down (no-op). Logic looks correct but this was never verified clean.
6. **TGT is not content-ready:** it has an approved brand-book but NO `strategy_90day.json`, `trends_live.json`, or `content_calendar.json`, and `voice_profile.json` is empty. The content pipeline (Trend Researcher → Strategy → Content Planner) has not run.
7. **Cost exposure:** agent runs cost real money (Claude + Apify/Bright Data + FAL). There have been prior credit-drain incidents. Cost caps exist but the whole thing needs care.

## 5. The honest root cause of the frustration

Features were added faster than the system was stabilized, on an environment that isn't deterministic, with no automated safety net. That combination guarantees "fix one thing, break another." It is a **process** failure, not a model-capability failure — and it will repeat under any AI model until the process changes.

## 6. What a competent next step looks like (do this BEFORE any new feature)

1. **Decide one source of truth for brand data** (local OR Supabase). Remove the split.
2. **Fix the brand_slug isolation defaults** (item 4.3) — require it everywhere.
3. **One-command startup + `/api/health`**, so "is it running" is never ambiguous.
4. **A smoke test** of the critical path (login → brand loads → dispatch agent → output → approve) that must pass before shipping.
5. **A regression test for every past bug** + a CI gate that blocks deploys on failure. This is what ends the recurrence loop.
6. Only then: run TGT's content pipeline and continue features.

## 7. Honest tooling / model recommendation for a non-technical founder

- **No single AI model, driven alone by a non-coder, will reliably finish AND maintain a system this size.** The loop you hit is structural. Switching models (to Fable 5 or anything else) without fixing the process (Section 6) will reproduce the same loop.
- If continuing AI-driven: use **Cursor** with **Claude Opus 4.8 or Fable 5**, because you SEE and approve every diff — but adopt the non-negotiable rule: *every fix ships with a test, and CI blocks broken deploys.*
- **The sustainable path:** hire a contract/part-time developer for ONE stabilization pass (Section 6), then use AI for feature work on top of a stable, tested floor. This is the realistic way to get a non-technical founder to a shippable product without the endless regression loop.
