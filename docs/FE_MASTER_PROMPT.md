# GRID CONTROL — Master Build Prompt (paste into Emergent / Manus / Lovable / Replit)

> **How to use this:** paste this whole file as your first message to the AI UI builder.
> It is self-contained — the tool can design and build from this alone. You have a **free
> hand on the design**; only the backend contract and the non-negotiable behaviors are fixed.
> For deeper API detail, attach `docs/API_REFERENCE.md`, `docs/SCREEN_ENDPOINT_MAP.md`,
> `docs/FE_INTEGRATION_GUIDE.md`, `docs/api-types.ts` when you reach the wiring stage.

---

## 0. Your brief in one line
Build a **premium, alive, founder-facing command deck** for an 18-agent AI marketing team —
where a non-technical founder watches their AI team work, reviews what it made, and approves it.
Design it however you think is best. Make it feel expensive, calm, and *alive*.

## 1. What the product is
GRID CONTROL is a founder's command deck for an autonomous AI marketing team (18 specialist
agents — strategist, content planner, script writer, creative director, etc.). The agents do the
work in the background; the founder's job is to **review and approve**. Think *"a calm, premium
mission control where you can feel a team of specialists working for you"* — not an analytics
dashboard, not an engineer's tool.

## 2. Who uses it
A solo founder / small brand owner. **Non-technical.** Wants to feel **in command and in the
loop** without operating machinery. Calm > busy. Clarity > density. One clear "here's what needs
you" moment per day.

## 3. The feeling to hit
- **Premium, warm, alive.** Expensive-feeling, not corporate-cold. The team should feel *present* —
  like loyal employees working in the background.
- **Calm but not static.** Motion + 3D signal life, not chaos. Stillness by default, energy on purpose.
- **Trustworthy & precise.** Numbers / costs / model names feel like instruments — exact, legible, honest.
- **Founder-to-founder voice** in all copy: plain, confident, zero fluff. No corporate filler.

## 4. Creative freedom + the few soft anchors
**You own the design — layout, components, motion, illustration, and the 3D language are yours to
invent.** The only soft anchors (evolve them if you have something better):
- **Warm dark** base (charcoal, not cool navy/black) + a **warm accent** (we've used coral) + a
  **luxe accent** (muted gold). Make it feel *ours*, not generic SaaS blue.
- **Monospace for all data** (numbers, costs, model names, timestamps) — the "precision instrument" feel.
- **Editorial serif** for big headlines is welcome; clean sans for UI.

## 5. 3D / motion / animation (wanted — go for it)
We *want* 3D assets, 3D objects, and animation where they earn their place:
- **The team as living entities.** The agents (or the 6 role-groups) can be 3D avatars / objects /
  orbs that visibly idle / think / work / wait. **Status as motion, not just a dot.** This is the
  signature moment of the app.
- **"The Brain" / concierge** — a 3D focal object you talk to; reacts when thinking vs. answering.
- **Data as dimensional.** Cost / tokens, growth, reach can be 3D or richly-animated viz — but stay readable.
- **Hero / empty / transition moments** — a 3D scene on the home deck, smooth screen transitions,
  cards that animate in, the "Needs You" item that animates out on approve.

**Guardrails:** motion must be *purposeful and smooth* (ease, ~150–400ms), never gimmicky or
seizure-y; respect `prefers-reduced-motion`; keep it **performant** (a founder on a laptop — 3D must
never jank the data). Premium = restraint with a few wow moments, not a constant light show.

## 6. The screens (their INTENT — design them however you like)

0. **Onboarding (THE ENTRY FLOW — first thing a new user sees).** A **chat-driven, guided
   setup** that feels like talking to a chief of staff, not filling a form. ~6 steps that
   progressively *build the brand profile, run the first task, and provision the first agent*,
   then drop the user into the Command Center. Use guided buttons + a few free-text fields
   (assistant asks, user clicks/answers). Suggested arc:
   1. **Use case** — Personal Brand vs Company Brand.
   2. **Goals** — pick what to help with (e.g. content & social, SEO/AI-search, competitors,
      sales/CVR, growth roadmap). Multi-select.
   3. **About you / the brand** — website URL + a "what you do" free-text.
   4. **Connect your accounts** — the curated set below (skippable). Each is an OAuth **Connect**.
   5. **Build Brand Profile** — assistant synthesizes a profile from the above + any connected
      data; user confirms/edits.
   6. **First task + agent** — assistant runs a first real task and shows it provisioning an
      agent, so the user *sees the team start working* before they ever hit the dashboard.
   Make this feel alive and premium (3D "Brain" present, the team coming online) — it's the
   first impression and the moment the product earns trust.
   **Connections shown here (ONLY these — do not list more):**
   **X, Facebook, Instagram, LinkedIn, YouTube,** and **Google (one connection = "full
   package")** which grants **Gmail + Google Calendar + Search Console + Analytics** together.
   Note: **Google Calendar is also our post-scheduling engine** — scheduled posts create calendar
   events that drive phone reminders, so frame Google as core, not optional.

1. **Command Center (home)** — *"Here's what your team did overnight, and the one thing that needs
   you."* The daily decision moment and hero of the app. The **"Needs You" approval queue** is the
   emotional center.
2. **Content** — the plan over time (calendar) + work moving through a pipeline. Feel of momentum.
3. **Growth** — community replies, leads, funnel — all *drafted, awaiting your yes*. Human-in-the-loop.
4. **The Team** — meet your specialists. 6 roles ↔ 18 agents. Where the 3D agent-presence shines.
5. **Insights** — proof it's working + a **signature cost/tokens transparency panel** (answers
   "how much does this spend?" — a feature, not fine print).
6. **Memory & Brain** — the brand's "story so far," append-only, document-like. The system's memory made visible.
7. **Connections / Settings** — platform status, brand profile, notifications. Light, utilitarian.

## 7. Non-negotiable product behaviors (design MUST respect these)
1. **Approval gate is sacred.** Nothing publishes / sends without an explicit human approve. Every
   piece of agent work surfaces as a reviewable card with **Approve / Change / Reject**. Make that
   action obvious and safe.
2. **Never render raw JSON.** Agent outputs are pre-formatted **markdown** — render as rich text,
   never code blobs.
3. **Brand switching is global** (top-level). All data is per-brand; the switcher reframes the whole app.
4. **Cost transparency is a feature** — show spend / tokens proudly, not hidden.
5. **"Live" honesty.** Some metrics come from the last agent run, not real-time — label with
   timestamps, never fake live.
6. **Chat drives intent, buttons guard actions.** A concierge ("Brain") takes natural language;
   destructive / publish actions still go through explicit buttons.

## 8. The backend (real, live — design so it's buildable)
A real REST API already exists and is deployed. **You design freely, then wire to these endpoints.**
If a screen wants data we don't expose yet, flag it — we'll add the endpoint.

- **Base URL (prod):** `https://web-production-175d5.up.railway.app`  — all routes under `/api/*`.
- **Auth:** Supabase Auth (email/password) → JWT. Send `Authorization: Bearer <jwt>` on every call.
  FE env vars: `VITE_API_BASE`, `VITE_SUPABASE_URL`, `VITE_SUPABASE_ANON_KEY`.
- **Brand scope:** every data call takes `?brand_slug=<slug>` (e.g. `askgauravai`). The brand
  switcher drives it.
- **Envelope:** most endpoints return `{ success, data }`; a few (`/api/auth/*`, `/api/brands`)
  return bare shapes — handle per-endpoint (see API_REFERENCE.md).
- **Live updates:** `GET /api/events` is a Server-Sent-Events stream (run status, approvals).

**Key endpoints per screen (full list in `docs/SCREEN_ENDPOINT_MAP.md`):**
| Screen | Primary endpoints |
|---|---|
| Onboarding (entry flow) | `POST /api/auth/create-brand` · `POST /api/brand/profile` · `GET/POST connect-token` per platform · `POST /api/agents/run` (first task) |
| Command Center | `GET /api/brand/summary` · `GET /api/brands/<slug>/needs-you` |
| Approve / Change / Reject | `POST /api/outputs/approve` · `/reject` · `/revise` |
| The Team | `GET /api/agents/list` · `GET /api/agents/status` · `POST /api/agents/run` |
| Content (calendar) | `GET /api/dashboard-output` → `data.calendar_formatted` |
| Insights (cost) | `GET /api/brands/<slug>/costs` |
| Memory & Brain | `GET /api/brands/<slug>/narrative` |
| Connections | `GET /api/brands/<slug>/connections` (never returns tokens). Curated set only: X, Facebook, Instagram, LinkedIn, YouTube, Google ("full package" = Gmail + Calendar + Search Console + Analytics in one connect) |
| Concierge (the "Brain") | `POST /api/concierge` — returns intent + points to the gated button; never auto-executes |

## 9. Build approach we'd like
1. **Design first against mock data** matching the shapes above (and `docs/api-types.ts`). Make it
   beautiful and alive before wiring anything.
2. **Then wire** screen-by-screen to the real endpoints; add auth + brand switching.
3. **Stack:** your call. (Our current reference app is React + Vite + Tailwind + shadcn, but you're
   free to choose — this is a fresh build, not a port.)

## 10. References (vibe only — do not copy)
Premium command decks / "calm cockpit" energy; the agents-as-team metaphor; cinematic-but-restrained
3D product sites. **Design something better than anything we've sketched** — you have the free hand.
