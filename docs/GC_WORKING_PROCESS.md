# Grid Control — Working Process

> Living document. Source of truth for how Grid Control (GC) works and what does what.
> Last updated: 2026-06-25 · Status: WIRE phase (Stage 5 of 10).

---

## 1. What Grid Control Is

Grid Control is a client-ready, multi-tenant AI marketing operating system. A brand owner (the client) signs up, onboards their brand once, and an orchestrated team of AI agents researches, plans, creates, and (on approval) publishes their marketing — with a human approval gate on every output and a per-brand cost meter behind it.

- **Client app** = chat-console-primary. Atlas (the lead agent) guides the user; work appears inline in chat as approve-cards, with a Live Work Feed.
- **Real-data mandate / zero assumptions:** every data point traces to a real scrape, API call, or user input. Never fabricated. If a fact can't be verified, the system stops and asks.

---

## 2. Identities — who is who

| Identity | Role | Notes |
|----------|------|-------|
| `grid.admin1@gmail.com` | **GC platform owner / developer** | Owns the Google Cloud project, the OAuth app, and all GC Google infra. The landlord. **Never** a tenant/brand. |
| Super-admin app user | GC operator | Currently `offgridcreativesai@gmail.com` (`profiles.is_super_admin=true`). Sees all brands; runs operator mode. |
| Client / tenant | A brand owner | Self-signs-up (email or Google). Sees only their own brand(s). Each brand fully isolated under `brands/<slug>/`. |

Test brands (run through the real client flow): **Third Gen Tribe** (first), then AskGauravAI, OffgridCreatives.

---

## 3. The Client Lifecycle (the core flow)

```
Sign in  →  Onboarding form (Atlas)  →  Connect accounts  →  Pre-flight validation
        →  Research report (paid)  →  Review / approve / 1 change
        →  Foundation + Memory seed  →  First task handoff  →  Ongoing agent ops
```

### 3.1 Sign in
Email + password, magic link, or **Google** (enabled). New user with no brand → routed to onboarding wizard. Returning user with a brand → straight to Command Center. (Gated on live `/api/brands`, not localStorage.)

### 3.2 Onboarding form — Atlas-guided
7 screens: (0) new vs existing → (1) basics → (2) audience & goal → (3) voice & safety → (4) platforms, competitors, identity → (5) review → **(6) connect accounts** *(to build)*. Submits to `POST /api/auth/create-brand` → Supabase `brands` + `brand_members(admin)` + filesystem `brand_profile.json`.

### 3.3 Connect accounts (new 7th screen)
Per-platform connect buttons (Instagram/LinkedIn/YouTube/X), Noimos-style. Each connection reflects on the Connections page (same per-brand connection system). **Skippable.** Connected → report uses first-party insights (`onboarding_connected`); skipped → public research only (`cold_sellable`).
*Constraint:* IG/LinkedIn insight + posting scopes need platform App Review (Phase B). Build the UI now, light up platforms as approved.

### 3.4 Pre-flight validation gate (cheap — no Opus)
Before any paid run, resolve every handle in real time (own IG + each competitor) via a light public-profile lookup. Any handle that doesn't resolve → Atlas stops in chat, asks the user to confirm/correct → re-check → only then start the report. **The system never assumes a handle is real.**

### 3.5 Research report (the onboarding deliverable — PAID)
`brand-book/generate` → `agents/brand_book_v7` (Opus + real research/scraping + IG insights). Runs async. Atlas: "generating…" → "ready". This is the brand audit / Foundation, not raw agent dumps.

### 3.6 Review, approve, or change (ONE paid change cycle)
In-chat approve-card: short summary + **Open full PDF · Approve · Request changes**.
- **Approve** → Foundation locked.
- **Request changes** → captured as `change_request` → **scoped re-research only** (re-run just the changed section, reuse cached research), shown once. **Hard cap: 1 paid revision** (`revision_count` enforced in code).
- **Further changes** → done later in the Memory section (free, no model calls).
- **Brand colors:** if left empty / "you decide" → system proposes palette options → user approves one → locked.

### 3.7 Approve → Foundation + Memory seed
`brand-book/approve` writes Foundation → `brand_profile.json` + `voice_profile.json` + `brand_narrative`, and **seeds editable Memory entries** (positioning, audience, voice, competitors, do-not-say). This is the final source-of-truth agents read.

### 3.8 First-task handoff
Atlas proposes the first task from the brand's bottleneck (e.g. Third Gen Tribe inactive 15 months → "revival week" → Content Planner).

---

## 4. Cost Model (per brand — feeds GC pricing)

```
Pre-flight checks   →  cheap   (light lookups, no model)
First full report   →  PAID    (Opus + research)   ← the main onboarding cost
≤ 1 scoped revision →  cheap   (only changed section, cached research reused)
Memory edits        →  free    (no model calls)
Ongoing agent runs  →  metered (every run logged per brand)
```

Tracking already built: `agents/_lib/cost_reporter.py` logs full run spend (Anthropic + Apify + FAL) → Supabase `usage_logs` + `agent_runs`. `/api/billing/usage` + `/api/brands/<slug>/costs` aggregate per-brand monthly cost + by-agent. To surface on the System page.

---

## 5. The Agent Roster — what does what

| # | Agent | Role |
|---|-------|------|
| 0 | CEO Brain | Orchestrator, session state, Notion push |
| 1 | Strategy Agent | 90-day roadmap + competitor research (real scrapes) |
| 2 | Content Planner | 30-day calendar |
| 3 | Script Writer | Scripts/hooks/captions + voice check |
| 4 | Creative Director | AI video/image (runs after founder records) |
| 5 | Ad Strategist | Paid funnels (only when budget confirmed) |
| 6 | Data Analyst | Real-account metrics, weekly score |
| 7 | Funnel Specialist | Conversion journey |
| 8 | Trend Researcher | Apify + Whisper + clustering |
| 9 | Website Agent | Site + GA4 + Search Console |
| 10 | Brand Guardian | SOUL/brand-safety check on all content |
| 11 | SEO/AEO Agent | Search + answer-engine optimisation |
| 12 | Email Marketing | Email sequences |
| 13 | Community Manager | Replies, mentions |
| 14 | DM Customer Hunter | Inbound + warm DMs |
| 15 | Carousel Designer | 7-slide carousel → editorial HTML/CSS |
| 16 | Trend Sentinel | Daily PIVOT/TRACK/STAY (pure math) |
| 17 | Performance Tracker | Winning/dead patterns (pure math) |

Class-1 (decision) agents = pure math, no model. Class-2 (generation) = Claude, every output cites `data_provenance` (source file + path + value).

---

## 6. Approval Gate & Publishing

Every agent output → `brands/<slug>/outputs/pending_approval/`. Human approves → `outputs/approved/`. Nothing auto-publishes. Publishing per platform (IG/LinkedIn/YouTube Shorts → automation; X → manual upload) only after explicit "approved".

---

## 7. Memory System

Per-brand memory (Supabase `brand_memory` + the Memory page). Seeded from the approved report; user/agents can add/edit entries over time. Becomes the evolving source of truth alongside `brand_profile.json` + `voice_profile.json`.

---

## 8. Tech & Infra

- **Frontend:** React 19 + Vite + Tailwind v4 + shadcn + TanStack Query v5 + Zustand + react-router v7. Dev on fixed port **localhost:5280** (strictPort; not 5173).
- **Backend:** Flask `/api/*` on 5001, `/api` proxy via Vite. Blueprints in `routes/*.py` (brands, agents, content, brain, billing, connections, system, leads).
- **Auth:** Supabase (project `mnivbrelhrwgndxcgega`). JWT (`Authorization: Bearer`) or legacy `X-Dashboard-Secret` operator bypass. Google OAuth enabled (basic scopes).
- **Data:** Supabase (brands, brand_members, usage_logs, agent_runs, brand_memory, …). Per-brand secrets in `brands/<slug>/.env` (gitignored).
- **Deploy:** Vercel (dashboard) + Railway (Flask API + scheduler worker). Custom domain pending.

---

## 9. Current Build Status (WIRE — Stage 5 of 10)

Done: portal reset to empty · Google sign-in enabled · unique port 5280 · onboarding form → brand creation verified (Third Gen Tribe).
Next (agreed order): (1) fix data + form NA/comma bug → (2) live handle-validation gate → (3) report generate + Atlas status loop → (4) review/approve/one-change card → (5) approve → Foundation + Memory seed → (6) first-task handoff. Connect screen = 7th step in parallel.

---

## 10. Open Items / Risk Flags

- **Platform App Review** (Meta/LinkedIn insight + posting scopes) before reliable connect/publish.
- **Legal before paying clients:** ToS + Privacy Policy + DPA; encrypt stored tokens at rest; restrict CORS; confirm operator mode never client-reachable.
- **Cost control:** in-flight lock, one scheduler, budget caps (post the Jun credit-drain incident).
- Surface per-brand cost on the System page.
