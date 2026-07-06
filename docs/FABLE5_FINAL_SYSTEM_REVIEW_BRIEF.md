# Grid Control (GC) — Final System Review & Rebuild Brief for Claude Fable 5

**How to use this document:** Paste this whole file as your opening prompt to a Fable 5
session, with read/write access to this repository. This is the *only* context you need
to start — it tells you what GC is, why it exists, what real-world process it automates,
what's already been tried and found wanting, what must never break, and what's completely
open for you to challenge and rebuild. Read `graphify-out/GRAPH_REPORT.md` and
`graphify-out/graph.json` first — they're a pre-built map of every file, agent, and
relationship in this codebase (11,319 nodes, refreshed today), so you don't have to
re-derive the structure from scratch. Use `graphify-out/obsidian/` as a starting point if
you explore the "second brain" ask in section 7 — it's already a linked-notes export of
this system, not something you need to build from zero.

---

## 0. Your role

You are being brought in as the most senior technical + product reviewer this system has
ever had — the kind of person who has built or scaled products like CRED, Myntra, or
Canva, or who has built a direct competitor to this one. You have full authority to
disagree with every decision in this codebase, including the frontend design (which was
previously locked — that lock is lifted for this review). Nothing is sacred except the
handful of invariants in section 6. Score everything. Say plainly where this system is
weak, generic, or over-engineered, and where it's genuinely good. The founder's money and
name are attached to what ships next — be honest, not agreeable.

---

## 1. What Grid Control is (the mission)

**What**: A multi-tenant, AI-agent-operated marketing agency. A brand owner signs up,
onboards once, and from then on a coordinated team of AI agents does the work a real
marketing agency's staff would do — research, strategy, content, creative, publishing,
performance tracking, reporting — with a human approval click before anything real goes
out or gets spent.

**How**: 18 specialized AI agents (Claude-powered), each mapped to one real agency job
function (see section 2), orchestrated by a "CEO Brain" that sequences them, all gated by
a human-approval queue, all cost-metered per brand.

**Why**: Running a real marketing agency is expensive and slow — a small/growing brand
can't afford a full in-house team, and agencies are inconsistent and expensive per
deliverable. GC's bet is that an orchestrated agent team can do the same *kind* of work,
faster and cheaper, without losing the judgment that makes marketing actually work —
which is the open question this review needs to stress-test.

**For whom**: Brand owners who can't yet afford (or don't want) a full agency retainer —
D2C/product brands, service businesses, and personal/influencer brands are all real
target segments (this matters — see section 5, they are NOT the same customer and
shouldn't get the same treatment).

---

## 2. The real-world process GC automates — do not lose this shape

A real digital/social marketing agency, working for a client, does these things, roughly
in this order, on a repeating cycle. This is the actual product GC is copying. If a
rebuild loses this shape and becomes "a nice AI dashboard" instead, it has failed, no
matter how good the code is.

| # | What a real agency does | The human role it replicates | GC's current agent(s) |
|---|---|---|---|
| 1 | Onboarding — learn the business, audience, goals, budget | Account manager | Atlas-guided onboarding chat |
| 2 | Research the market, competitors, trends | Researcher / social listening | Trend Researcher |
| 3 | Build a 90-day growth strategy | Strategist / account planner | Strategy Agent |
| 4 | Turn strategy into a content calendar | Editorial/content planner | Content Planner |
| 5 | Write the actual scripts/captions | Copywriter | Script Writer |
| 6 | Produce the actual visuals/video | Creative/design director | Creative Director, Carousel Designer |
| 7 | Check everything matches brand voice before the client sees it | Brand/QA lead | Brand Guardian |
| 8 | Show the client, get approval or changes | Account manager | The approval-queue UI — **human, always** |
| 9 | Publish what's approved | Social media manager | The publish pipeline (IG/LinkedIn/YouTube/X) |
| 10 | Track real performance weekly | Analyst | Data Analyst, Performance Tracker |
| 11 | Report back: what worked, what's next | Account manager | The Weekly Review card |
| 12 | Reply to comments/DMs as the brand | Community manager | Community Manager |
| 13 | Reach out to warm leads | Business development | DM Customer Hunter |
| 14 | Step back monthly on content mix / budget split | Strategist | The Monthly Mix card |
| 15 | Redo the big strategy quarterly, based on real results | Strategist | The Quarterly QBR (re-runs Strategy Agent) |
| 16 | Run paid ads, but only once budget is confirmed | Media buyer | Ad Strategist (not yet built) |

**The one-time onboarding journey** (point A to point B, before the cycle above starts):
sign up → answer questions about the brand in a guided chat (not a form) → connect social
accounts (skippable) → system verifies every handle is real before spending anything →
one real paid research report gets generated → the client approves it or requests one
round of changes → the approved version becomes the brand's permanent memory that every
downstream agent reads from → the system proposes the first task based on the brand's
actual bottleneck → the repeating cycle above begins.

---

## 3. The core, proven-real finding this review must fix — not just note

This was found and confirmed during today's work, not hypothesized: **GC's content
agents apply one fixed psychological framework to every brand, and only substitute
surface variables (brand name, palette, posting volume) — they do not reason differently
based on what kind of brand they're writing for.** That is the difference between a
template with find-and-replace and an actual strategist, and it's the single biggest gap
between what GC is and what it needs to be.

Concretely: a product brand (e.g. apparel), a service brand, and a personal/influencer
brand require *different* psychological drivers, not different volumes of the same
driver:

- **Product brand (e.g. T-shirts)** — impulse-driven, visual-first. STEPPS "Public" and
  "Practical Value" matter most. Hooks lean Aspirational/Exclusivity. CTA is short-distance
  — straight to a shop link, same session.
- **Service brand** — trust-driven, long consideration cycle. STEPPS "Social Currency"
  and "Stories" matter most. Hooks lean Authority/Specificity. CTA is long-distance —
  book a call, DM to qualify, never a hard sell early.
- **Personal/influencer brand** — parasocial. STEPPS "Emotion" and "Identity" matter
  most. Hooks lean Pain Point/Identity. The CTA is about relationship and reply, not
  immediate conversion.

Today's incremental fixes (a `production_format` field for founder-vs-product shoot
style, phase-driven volume, conditional rule-blocks) only adapted *formatting and
data*, not this deeper reasoning layer. **Your mandate: agents should classify a brand's
business-model/archetype as an explicit reasoning step before generating anything, and
that classification should change which hook patterns, STEPPS levers, and CTA distance
get used — not just which numbers get filled in.** This should show up architecturally,
not as one more `if` branch bolted onto the existing prompts.

---

## 4. Scope of review — go everywhere, hold nothing back

- **All backend code** — `agents/` (18 agents + shared `_lib`), `core.py`, `routes/*.py`
  (Flask blueprints), `publishing/` (4 platform publishers), `scheduler/` (APScheduler
  worker), `ceo_brain/` (orchestrator), `notion_integration/`, `supabase/` (schema +
  client).
- **All frontend code** — `dashboard/` (React 19 + Vite + Tailwind v4 + shadcn +
  TanStack Query v5 + Zustand). **Full redesign license — the previous "locked, no
  redesign" rule is lifted for this review.** If the current cinematic/persona-based
  design (8 client-facing "team" personas hiding 18 real agents) is the wrong call,
  say so and propose better.
- **Every external connector/integration** — Anthropic API, Apify (scraping),
  FAL.ai (image/video gen), ElevenLabs (voice), Meta Graph API, LinkedIn API, YouTube
  Data API + OAuth, Twitter/X OAuth1, Supabase, Notion API. Evaluate whether each is
  the right tool, the right integration pattern (direct SDK calls today — evaluate
  whether an MCP-based tool-connection layer would be a better architecture for how
  the 18 agents reach external services), and whether any should be replaced.
- **Dependencies and architecture as a whole** — Flask+React+Supabase is the current
  stack. If there's a materially better stack for this specific product (a multi-tenant,
  agent-orchestrated SaaS with a human approval gate), propose it and justify the switch,
  including migration cost.
- **Cost structure** — review real spend patterns (`agents/_lib/model_gateway.py`'s
  Opus/Sonnet/Haiku routing, `agents/_lib/paid_ops.py`'s circuit breaker,
  `agents/_lib/cost_reporter.py`). Is the current model routing actually optimal, or
  is it a rough first guess? Are there free/cheaper alternatives to any paid dependency
  (Apify, FAL, ElevenLabs) that don't sacrifice quality? Be concrete with numbers, not
  vague "consider cheaper options."
- **Repos** — this repo (`Grid-Control.`) is the only one with real, current work.
  `grid-control-v0-export` and `brand-companion-ai` are dead-end early prototypes
  (frontend-only, no backend, superseded) — glance at them for any genuinely good UI
  ideas worth reconsidering, but do not try to merge or reconcile them; there's nothing
  there worth preserving beyond ideas. `offgrid-pdf-api` is a deliberately separate
  product (the actual "Reporting SaaS" GC markets) — do not merge it into GC, it's
  correctly a different repo.

---

## 5. Non-negotiable invariants — must survive any rebuild

These are not implementation details up for debate. They can be *rebuilt differently*,
but the guarantee they provide must not be weakened:

1. **Zero fabrication.** Every fact/number/claim an agent produces must trace to a real
   scrape, API call, or user input. If data is missing, the agent must say so, never
   invent it. (Currently enforced via `data_provenance` citation requirements — the
   mechanism can change, the guarantee cannot.)
2. **Nothing real happens without a human approval click**, unless a human has
   explicitly opted a specific agent into more autonomy (see the trust dial,
   `agents/_lib/trust_dial.py`) — and even then, nothing auto-*publishes* to a real
   platform yet; that boundary is intentionally still closed until a human decides
   otherwise.
3. **Per-brand data isolation.** One brand's data, memory, or context must never leak
   into another brand's agent runs.
4. **Cost must stay visible and boundable**, per brand and in aggregate. The specific
   mechanism (today: a JSON ledger + daily USD cap) is open to replacement; "spend can
   silently run away" is not acceptable under any new design.

---

## 6. Open for you to challenge — nothing sacred here

- The exact 18-agent roster and boundaries — if a different agent architecture covers
  the same 16 real-world functions in section 2 better, propose it.
- The current tech stack, hosting (Vercel + Railway), and auth (Supabase) — propose
  alternatives with real justification.
- The frontend design, including the "8 client-facing personas hide 18 real agents"
  concept (internally called "THE SECRET") — is this the right UX, or should the
  client see the real agent structure? Argue it either way.
- The specific cost-routing model (which agents get Opus vs Sonnet vs Haiku vs a new
  model like yourself) — is the current split defensible, or wrong?
- The whole approval-gate UX (currently: everything lands in a queue, human clicks
  approve/reject/request-changes) — is there a better interaction model that still
  satisfies invariant #2 above?

---

## 7. The "second brain" ask

The founder has seen people build an Obsidian-style "second brain" for their AI agents
and wants to know if/how GC's 18 agents should have one — a persistent, linked knowledge
system the agents draw on and contribute to over time (beyond the current per-brand
`brand_memory/` JSON files and Supabase `brand_memory`/`grid_control_memory_vec` tables).
**Note before you start:** this repo already has `graphify-out/obsidian/` — a real,
generated Obsidian vault of this codebase's own structure. It's a starting point, not
nothing. Evaluate whether the *agents themselves* (not just the codebase) should have a
similar persistent, cross-session, linked-notes memory system, propose a concrete design
if so, and build it as part of this pass if it's worth doing.

---

## 8. What you must actually deliver

1. A single ranked gap/risk report across security, architecture, cost, and product
   depth (the section 3 finding is the headline item — treat it as such).
2. A scored assessment (your honest number, not a diplomatic one) of where this system
   stands today versus a CRED/Myntra/Canva-caliber product, and what specifically closes
   that gap.
3. Concrete alternatives for any dependency/architecture piece you think is wrong,
   with real justification, not just "consider X."
4. A working answer to the second-brain question (section 7).
5. **One consolidated, fully working, wired application** — frontend and backend
   actually talking to each other, ready for a real first brand to onboard and use —
   not a set of recommendations left for someone else to implement.

---

## 9. How this gets run (operational note for whoever executes this prompt)

Run this in an isolated git worktree/branch, not directly on `main` or
`gridcontrol-rebuild`. This repo's local `.env` and the deployed Railway backend point
at the *same* Supabase project — nothing here should touch that live database directly.
Only after a human has reviewed the result does it get merged into a real branch and
deployed.
