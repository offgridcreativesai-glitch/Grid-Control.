# GRID CONTROL — Front-End Design Direction (creative brief)

> For an AI UI builder (Emergent / Manus / Lovable / Replit) or a human designer.
> **This is DIRECTION, not a spec. You have a free hand on the actual UI** — layout, components, motion, and
> 3D are yours to invent. This brief tells you *what the product is, how it must behave, what data exists,
> and the feeling to hit*. Pair it with the technical contract: `HANDOFF.md`, `docs/API_REFERENCE.md`,
> `docs/SCREEN_ENDPOINT_MAP.md`, `docs/FE_INTEGRATION_GUIDE.md`, `docs/api-types.ts`.

## 1. What this product is
GRID CONTROL is a founder's **command deck** for an 18-agent AI marketing team. A non-technical founder
watches the team work, reviews what they made, and approves it. Think: *"a calm, premium mission control where
you can feel a team of specialists working for you."* Not an analytics dashboard, not an engineer's tool.

## 2. Who uses it
A solo founder / small brand owner. Non-technical. Wants to feel **in command and in the loop** without
operating machinery. Calm > busy. Clarity > density. One clear "here's what needs you" moment per day.

## 3. The feeling to hit
- **Premium, warm, alive.** Expensive-feeling, not corporate-cold. The team should feel *present* — like
  loyal employees working in the background.
- **Calm but not static.** Motion and 3D signal life, not chaos. Stillness by default, energy on purpose.
- **Trustworthy & precise.** Numbers/costs/models feel like instruments — exact, legible, honest.
- **Founder-to-founder voice** in copy: plain, confident, zero fluff.

## 4. Creative freedom + the few anchors we'd love kept
You own the design. Explore freely. The only **soft anchors** (evolve them if you have something better):
- **Warm dark** base (charcoal, not cool navy/black), with a **warm accent** (we've used coral) + a **luxe
  accent** (muted gold). Make it feel *ours*, not a generic SaaS blue.
- **Monospace for all data** (numbers, costs, model names, timestamps) — the "precision instrument" feel.
- **Editorial serif** for big headlines is welcome; clean sans for UI.
Everything else — layout, components, illustration, the 3D language — is your call.

## 5. 3D / motion / animation direction (wanted — go for it)
We *want* 3D assets, 3D objects, and animation. Where it earns its place:
- **The team as living entities.** The 18 agents (or 6 roles) can be 3D avatars/objects/orbs that visibly
  idle / think / work / wait. Status as motion, not just a dot. This is the signature moment.
- **"The Brain" / concierge** — a 3D focal object you talk to; reacts when thinking vs. answering.
- **Data as dimensional.** Cost/tokens, growth, reach can be 3D or richly-animated viz — but stay readable.
- **Hero / empty / transition moments** — a 3D scene on the home/command deck, smooth screen transitions,
  cards that animate in, the "Needs You" item that animates out on approve.
**Guardrails:** motion must be *purposeful and smooth* (ease, ~150–400ms), never gimmicky or seizure-y;
respect `prefers-reduced-motion`; keep it **performant** (a founder on a laptop — 3D should never jank the
data). Premium = restraint with a few wow moments, not a constant light show.

## 6. The screens (their INTENT — design them how you like)
Data + exact endpoints for each are in `docs/SCREEN_ENDPOINT_MAP.md`. Here's what each must *do/feel*:
1. **Command Center (home)** — "Here's what your team did overnight, and the one thing that needs you."
   The daily decision moment. Hero of the app. The "Needs You" approval queue is the emotional center.
2. **Content** — the plan over time (calendar) + work moving through a pipeline. Feel of momentum.
3. **Growth** — community replies, leads, funnel — all *drafted, awaiting your yes*. Human-in-the-loop.
4. **The Team** — meet your specialists. 6 roles ↔ 18 agents. This is where 3D agent-presence shines.
5. **Insights** — proof it's working + **a signature cost/tokens transparency panel** (answers "how much does
   this spend?" — a feature, not fine print).
6. **Memory & Brain** — the brand's "story so far," append-only, document-like. The system's memory made visible.
7. **Connections / Settings** — platform status, brand profile, notifications. Light, utilitarian.

## 7. Non-negotiable product behaviors (design must respect these)
1. **Approval gate is sacred.** Nothing publishes/sends without an explicit human approve. Every piece of
   agent work surfaces as a reviewable card with Approve / Change / Reject. Make that action obvious + safe.
2. **Never render raw JSON.** Agent outputs are pre-formatted markdown — render as rich text, never code blobs.
3. **Brand switching** is global (top-level). All data is per-brand; the switcher reframes the whole app.
4. **Cost transparency is a feature** — show spend/tokens proudly, not hidden.
5. **"Live" honesty.** Some metrics are from the last agent run, not real-time — label with timestamps, don't fake live.
6. **Chat drives intent, buttons guard actions.** A concierge ("Brain") takes natural language; destructive/
   publish actions still go through explicit buttons.

## 8. How it connects to the backend (so the design is buildable)
- Real REST API at `https://web-production-175d5.up.railway.app` (`/api/*`), Supabase JWT auth, per-brand data.
- ~30 cockpit endpoints already exist + are documented (`API_REFERENCE.md` + `SCREEN_ENDPOINT_MAP.md`).
- Live updates via SSE (`/api/events`). Types in `docs/api-types.ts`.
- **You design freely; wire to these endpoints.** If a screen wants data we don't expose yet, flag it — we'll add the endpoint.

## 9. References (vibe, do not copy)
Premium command decks / "calm cockpit" energy; the agents-as-team metaphor; cinematic-but-restrained 3D
product sites. Our prior static cockpit concept (`dashboard/mockups/COCKPIT_DESIGN_PROMPT_LOVABLE.md`) is **one
reference point, not the target** — feel free to depart from it entirely.
