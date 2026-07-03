# Grid Control — Dependency & Architecture Alternatives (Jul 3 2026)

Rule for this doc: every "switch" comes with numbers and migration cost, every
"keep" with the reason the alternative loses. No "consider X."

---

## 1. Stack: Flask + React + Supabase — **KEEP (split, don't switch)**

Evaluated: FastAPI rewrite, Next.js full-stack, Django.
- FastAPI's async wins matter for high-concurrency APIs; GC's traffic is one
  dashboard user + a scheduler. Agents are long subprocesses, not async I/O.
  Migration: ~2 weeks re-testing 80+ endpoints for zero user-visible gain.
- Next.js full-stack would merge FE/BE deploys but strands the Python agent
  layer (the actual product) behind an RPC boundary.
- Supabase (auth+RLS+pgvector+storage) is doing 4 jobs for $0–25/mo; replacing
  it is negative value.

**Do instead:** split core.py (3,062 lines) into app/auth/brand_files modules;
move `brands/` canonical state to Supabase Storage or a Railway volume
(gap report #2). Cost: ~1 day. This captures most of what a rewrite would buy.

## 2. Hosting: Vercel + Railway — **KEEP, attach a volume**

Railway's ephemeral FS is the flaw, not Railway. A 5GB volume is ~$1.25/mo.
Alternatives (Fly.io, Render) have identical volume economics and would cost a
redeploy pipeline rebuild. Move only if Railway's ~$5–20/mo worker pricing
becomes material — it won't before 10 brands.

## 3. MCP tool layer for the 18 agents — **NOT NOW, revisit at multi-model**

Brief asks explicitly. Direct SDK calls today are: in-process, typed, cheap to
debug, and covered by paid_ops guards at the call site. An MCP layer buys:
tool reuse across heterogeneous agents, per-tool authz, swappable backends.
GC's agents are all Python in one repo sharing `_lib/` — they ALREADY have the
reuse MCP would add, without a serialization boundary. The trigger to revisit:
(a) agents running on non-Claude models via LiteLLM that need uniform tools, or
(b) letting the client's own Claude/tools call INTO GC (then GC exposes an MCP
server — that one is worth building when a client asks).

## 4. Model routing — **CHANGE ONE LINE, keep the design**

`model_gateway.py` single-source routing + effort→thinking-budget is the right
architecture. The error is one row: `"script-writer": ("opus", "high")`.
- Opus 4.8: $15 in / $75 out per MTok. Sonnet 4.6: $3 / $15. **5×.**
- Script Writer is the highest-call-volume generation agent (3 variants × 5
  hooks × 30 slots/mo × up to 3 provenance retries).
- The system's own routing law (hard-earned, May 2026): Opus decides, Sonnet
  generates, and Brand Guardian (Opus) already QCs the output downstream.
Change to `("sonnet", "high")`, A/B one week of output through Brand Guardian
pass-rate. Expected saving ≈ 80% of the largest LLM line item per brand.
Keep Opus: ceo-brain (xhigh), strategy-agent, brand-guardian, ad-strategist.

Also unify: content agents instantiate `anthropic.Anthropic` directly; route
them through `model_gateway.complete()` so LiteLLM multi-provider + per-call
paid-ops guard apply uniformly. Mechanical change, ~1 hr/agent, do during Wave 2.

## 5. Apify — **KEEP for competitor scraping, stop using it where APIs are free**

- Apify instagram-scraper: ~$0.5–2.3/1K results + actor compute; the pipeline's
  90s-sleep pattern works and survives IG DOM changes (actor maintainer's job).
- The free replacements only cover OWN accounts: Meta Graph API insights for
  the brand itself (already integrated) — never route own-account metrics
  through Apify (some current task_scrapes did).
- Self-hosted scraping (`_scrapling_client.py` exists) trades Apify's fee for
  proxy costs (~$8/GB residential) + ban-fighting time; loses money below ~50
  brands. Keep scrapling for plain web pages only.
- Legal note stands: scraping IG violates platform ToS regardless of tool —
  business risk decision documented in the legal register, not a tooling fix.

## 6. FAL.ai — **REPLACE per existing plan (Higgsfield), agreed with one caveat**

The Creative Engine Rebuild decision (docs/CREATIVE_ENGINE_REBUILD.md) already
replaces FAL with Higgsfield. Endorsed: FAL is a raw model marketplace; the
creative-director agent needs opinionated art direction, which is exactly the
gap the rebuild targets. Caveat: keep the FAL client behind an interface until
Higgsfield's per-asset cost is measured against FAL's ~$0.03–0.05/image at
equal acceptance rate — the metric is cost per APPROVED asset, not per
generated asset.

## 7. ElevenLabs — **KEEP**

Usage is a few narrations/week; $5/mo tier covers it. OpenAI TTS is ~1/3 the
price at meaningfully lower voice quality for brand voiceover; switching saves
under $5/mo. Not worth an integration. Revisit only if voice becomes a per-post
default across brands.

## 8. Embeddings: Voyage voyage-3-lite — **KEEP**

512-dim, $0.02/MTok — already the cheap option (OpenAI text-embedding-3-small
$0.02/MTok, 1536-dim = 3× pgvector storage/scan for no recall gain at this
corpus size). The schema's stray 1536-dim `brand_memory.embedding` column
should be consolidated to the 512 tables `_mem0_client` actually uses.

## 9. Scheduler: APScheduler worker — **KEEP, one guard**

The separate Railway worker with shared-secret trigger is correct (learned from
the Jun 15-16 double-scheduler credit drain). Add: an in-flight lock per
(brand, pipeline) in Supabase so a hung run can't stack with the next trigger —
that's the remaining piece of the cost-control incident design.

## 10. Auth: Supabase Auth + JWT — **KEEP, scope the escape hatch**

The design flaw isn't Supabase Auth, it's the `X-Dashboard-Secret` bypass
(gap #3.2). Scope it to scheduler/system routes, JWT-only for humans. Auth0/
Clerk would cost $25–240/mo to solve a problem GC doesn't have.

---

### Summary table

| Piece | Verdict | One-line reason |
|---|---|---|
| Flask+React+Supabase | keep, split core.py | rewrite = 2 wks, zero user value |
| Vercel+Railway | keep + volume ($1.25/mo) | ephemeral FS is the bug, not the host |
| MCP tool layer | not now | in-repo `_lib` already gives the reuse |
| script-writer on Opus | switch to Sonnet | 5× cost vs own routing law; QC net exists |
| Apify | keep (competitors only) | self-host loses money < 50 brands |
| FAL | replace w/ Higgsfield (planned) | measure cost per approved asset |
| ElevenLabs | keep | saving < $5/mo |
| Voyage embeddings | keep | already cheapest; drop stray 1536 column |
| APScheduler worker | keep + in-flight lock | finishes the cost-incident fix |
| Supabase Auth | keep, scope god header | Clerk solves a non-problem |
