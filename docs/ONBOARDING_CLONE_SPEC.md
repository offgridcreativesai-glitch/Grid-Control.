# GRID CONTROL — Self-Serve Clone Spec (studied from NoimosAI, built on our system)

> Decided Jun 17 2026 after a live teardown of NoimosAI's onboarding + template library + a real
> first-task deliverable. We clone the **structure**, not the product. Everything maps to agents,
> scheduler, approval gate, and provenance we already own. Locked-18 roster is preserved.

## 0. The shift this enables
From **agency** (we hand-wire each brand → sells our time, doesn't scale) → **self-serve product**
(a stranger signs up, onboards via chat, connects their own accounts, the team starts working → sells
a product, scales). The agents underneath are the same; the difference is the **front door**.

## 1. Interface model (locked) — Chief-of-Staff chat is THE primary surface
**One assistant — the Chief of Staff (the Brain) — talks to the user; the specialists work behind it.**
The **self-serve chat IS the main page** that does the heavy lifting (not a cockpit with chat bolted on).
- The user **only ever talks to the Chief of Staff.** Never to individual agents.
- The Chief of Staff has authority to **call and brief any agent in-chat** on the user's behalf.
- The user requests changes *through* the CoS; the CoS dispatches. Chat = intent, buttons = action.
This is consolidation of what we already have (CEO Brain + `/api/concierge` + the 18), not a rebuild.

### 1a. Per-brand agent roster = curated by the CoS, dynamic, roadmap-driven (the key difference from NoimosAI)
NoimosAI makes the (non-technical) user assemble their own agents — backwards. **We don't.** The Chief of
Staff **staffs the team for them**:
- After onboarding, the CoS **assigns only the agents this brand actually needs** — a *curated subset* of
  the 18, not all, not user-assembled. (e.g. askgauravai today → no Ads agent, no Website agent.)
- The roster is **dynamic**: agents are added later when **(a) the roadmap calls for it** (e.g. "Ads agent
  activates ~day 45") or **(b) the owner asks** — and in both cases **the CoS adds them**, the user wires nothing.
- Mechanism we already own: roadmap = **strategy-agent**; activation = **scheduler**; dispatch/brief = **concierge** (now CoS-only).
- **Net-new data model:** per-brand *agent assignment + activation rules* (active subset · activation date/trigger from roadmap). Everything else exists.

## 2. The onboarding entry flow (chat-guided, ~6 steps) → maps to our system
Mirrors NoimosAI's "In 6 steps I'll build your Brand Profile, run your first task, set up an Agent."

| Step | NoimosAI | GRID CONTROL (our system) |
|---|---|---|
| 1. Use case | Personal vs Company Brand | Sets `brand_profile.json` type. Brain asks. |
| 2. Goals (multi-select) | 6 goal buttons | Maps to which of our 18 agents to prioritize for this brand. |
| 3. About | website URL + "what you do" | Seeds the profile draft. |
| 4. Connect accounts | 25 OAuth buttons, skippable | **Curated set only** (§5) via existing Connections OAuth; skippable. |
| 5. Build Brand Profile | 3 real research tasks → editable profile (overview, audience, influencers, keywords) | **trend-researcher + strategy-agent + brand-guardian** run real Apify research → write `brand_profile.json`. Editable, Regenerate, human-confirms. |
| 6. First task + agent | template gallery → deliverable → "use as agent" | Template launcher → runs one of our agents → output to **approval queue** → "promote to scheduled agent" (§4). |

**Observed quality bar (the first-task report):** grounded, sourced (9 real citations), founder-ready —
reference posts + 3 content ideas (concept/hook/angle) + strategic patterns + a clear recommendation.
This equals our **trend-researcher + script-writer** output today. Matchable, no new capability needed.

## 3. Templates = SECONDARY quick-actions (NOT the entry point)
The entry point is the **Chief-of-Staff chat** (§1). Templates are *optional* preset prompts the CoS can
offer or the user can pick for a fast one-shot — they are not how the user assembles a team and not the
primary surface. A "template" = a **named, parametrized one-shot prompt that triggers one of our existing
agents** on a brand and produces a known deliverable shape. The roster pool stays the locked 18; the CoS
decides which are active per brand (§1a).

**Template catalog (launch set) → agent map:**
| Template | Our agent(s) | Category |
|---|---|---|
| Viral Content / Hook Finder | trend-researcher + script-writer | social/content |
| Competitor Teardown (SWOT / positioning / pain points) | strategy-agent | competitor |
| 30-Day Content Calendar | content-planner | social/content |
| SEO Keyword Gap | seo-aeo-agent → seo-technical | seo |
| AI-Search / GEO Citation Audit | seo-aeo-agent → aeo-content | geo |
| Carousel / Reel | carousel-designer / creative-director | social/content |
| Funnel / CVR Audit | funnel-specialist | cvr |
| Performance + Pattern Report | data-analyst + performance-tracker | growth |
| Email Nurture Sequence | email-marketing-agent | growth |

**Skip for now (no matching agent; revisit post-launch):** Events / Speaking, Media & PR Outreach,
Hiring Strategy Analyst (irrelevant to our ICP). Their category keys for reference:
`competitor · seo · cvr · geo · growth · social · social_listening`.

## 4. "Use it as an Agent" = promote a one-shot to a scheduled recurring run
The bridge from first-task → standing team member. We already have the parts:
- One-shot: `POST /api/agents/run` (agent + brand).
- Recurring: a **scheduler job** in `scheduler/worker.py` + `scheduler/schedule_config.json` (per brand+agent+cadence).
- Review: the **approval gate** (every recurring output still lands in pending_approval).
- "Promote to agent" UI = create/enable a schedule_config entry for that agent+brand. No new engine.

## 5. Connections (curated, NOT the 25)
Only: **X, Facebook, Instagram, LinkedIn, YouTube,** and **Google as one "full package"** connect that
grants **Gmail + Calendar + Search Console + Analytics** together. **Google Calendar doubles as the
post-scheduling engine** — scheduled posts become calendar events that drive phone reminders.
- Phase A (now): self-serve for platforms we already OAuth (IG/LinkedIn/YouTube/X); "we'll set this up
  for you" fallback for the rest.
- Phase B (later, the expensive moat): per-platform OAuth **app approval** (Google verification for
  Gmail/Calendar/GSC/Analytics scopes, Meta review). Funded track, UI can lead, backend follows.

## 6. What's genuinely NEW to build (everything else exists)
1. **Onboarding orchestration** — the Brain runs the 6-step chat → ordered agent calls → draft `brand_profile.json` (profile auto-synthesis).
2. **Template launcher UI** — category tabs + cards, each card = preset prompt → agent run.
3. **"Promote to agent"** — one-click write of a `schedule_config.json` entry (+ a small endpoint).
4. **Self-serve workspace provisioning** — sign-up → isolated brand workspace (we have brand isolation + Supabase auth; need the self-serve create path).

## 6b. NoimosAI sections teardown (Jun 17 walkthrough) — take vs dump
| Their section | What it is | Verdict for GRID |
|---|---|---|
| New task (chat) | "Ask me" chat-first home + quick-action category chips | TAKE — validates CoS-chat-as-home; steal the category quick-start chips |
| Agents | Library of **scheduled** agents (template + cadence + **est. credits/mo**); List/Schedule tabs | TAKE — Agent = template + schedule = our scheduler. Take per-agent monthly cost (real ₹). DUMP user-self-adds → CoS assigns |
| Customize → Skills | "Skills teach your agent reusable procedures" (SOPs) | PARTIAL — we have agent-learnings/program.md |
| Customize → Integrations | Connected accounts | HAVE — = our Connections |
| Pages | Notion-style doc store; outputs saved as editable pages | TAKE-LITE — living doc hub for deliverables |
| Library | Archive of every generated file/"Canvas" | TAKE-LITE — "all assets" view over approved outputs |
| Settings → Memory | **3-scope structured editable memory** (Brand/Personal/Account) + Patterns/Pitfalls/Rules, auto-maintained | TAKE — BIG (see §6c) |
| Settings → Knowledge Base | RAG doc upload (brand docs agents reference) | TAKE-LITE — brand-doc grounding |
| Settings → Members/Basic info | team + workspace basics | HAVE — standard |

## 6c. Memory model to adopt (the standout idea; Gaurav flagged it)
Restructure our scattered memory (`brand_profile.json` · `voice_profile.json` · `performance_history.json` ·
`agent_learnings.jsonl`) into ONE structured, editable, **3-scope** surface — auto-written by the system,
user-correctable (their banner: "Memory may be automatically adjusted… to maintain optimal performance"):
1. **Brand (Workspace) Memory** — Brand Overview · Services/Products (name+desc) · Goals · Key Metrics.
2. **Personal Memory** (the founder) — Overview · Voice Keywords · Voice Examples · Content Pillars · Content Audience · **Effective Patterns · Pitfalls · Rules**.
3. **Account Memory** (per connected platform) — *same fields, per-account* (X-voice ≠ LinkedIn-voice).
Key insight: **Effective Patterns / Pitfalls / Rules** = our performance-tracker (winning/dead patterns) +
brand-guardian (rules) output, surfaced as **editable memory**. This becomes the "Memory & Brain" section.

## 7. What we keep that they don't have (our wedges)
Cost/token transparency as a feature · provenance on every output · locked expert roster · approval
gate as law · premium alive/3D design direction (`docs/FE_DESIGN_DIRECTION.md`). See [competitor_noimosai].

## 8. Backend backlog (derived; build later, on go)
- Onboarding orchestration endpoint(s): `POST /api/onboarding/build-profile` (Brain → agents → draft), confirm/edit save via `POST /api/brand/profile`.
- Template registry (static config: id, title, category, agent_slug, prompt, recommended_for, sample) + `GET /api/templates`.
- `POST /api/agents/run` already exists for one-shot.
- `POST /api/schedules` (promote-to-agent) → writes schedule_config; scheduler/worker already consumes it.
- Self-serve workspace create: `POST /api/auth/create-brand` exists; add sign-up → first-workspace wiring.
