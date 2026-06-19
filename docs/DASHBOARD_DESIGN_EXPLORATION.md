# Dashboard Design Exploration — PARKED for after the system build (Jun 9 2026)

> **Status: REFERENCE ONLY. Not part of the build plan.** Decision (Gaurav, Jun 9): finish the SYSTEM
> build first (`docs/DASHBOARD_V2_BUILD_PLAN.md`), THEN rebuild the dashboard front-end with Emergent +
> Lovable on top of the finished system. This file exists so we don't re-derive any of it later.

## Paradigm decision (locked Jun 9 — supersedes Jun 8 "brief-first")
**Cockpit-as-home.** After studying competitor Sureflow (see `docs/COMPETITOR_SUREFLOW.md`), Gaurav chose a
Sean-style organized cockpit as the primary surface — BUT with our own premium identity and built better in
substance. The morning brief is NOT dropped; it becomes the **"Needs you" hero panel of the Command Center**.
Reason Gaurav preferred the cockpit: named sections, business-role agents, visible team status, one organized
place — feels systematic/user-friendly for a non-coder.

## Information architecture (the cockpit)
Left nav (named sections): **Command Center** (home) · **Content** · **Growth** · **The Team** · **Insights**
· **Memory & Brain** · (pinned: Connections, Settings). Top bar: brand switcher + a command box
("Tell your team what to focus on…" → Allocate / Queue) + "System operational" + clock.

## Client-facing 6 roles → our 18 agents (hybrid; admin can expand to 18)
| Client sees (6 roles) | Admin sees (our 18) |
|---|---|
| Chief of Staff | ceo-brain, trend-sentinel |
| Head of Strategy | strategy-agent, content-planner, trend-researcher, seo-aeo |
| Creative Director | script-writer, creative-director, carousel-designer, brand-guardian |
| Head of Growth | community-manager, dm-hunter, funnel-specialist, email-marketing, ad-strategist |
| Data Analyst | data-analyst, performance-tracker |
| Web & Tech | website-agent |

## Visual identity (the blend Gaurav chose — all three mixed)
Warm near-black charcoal (#0d0c10) + **coral #ff6a4d** primary + **muted gold #d8b478** luxe accent;
editorial serif headlines (Fraunces/Spectral), Inter body, **monospace for ALL data/numbers/models/costs**;
soft glass cards, rounded 16px, airy. Deliberately NOT cool-navy (that's Sean's). Must read as ours.

## Our two differentiators vs Sean (must stay visible in any rebuild)
1. **LIVE auto-tracked metrics** (his are "manual source of truth" / hand-typed). LIVE badge on health cards.
2. **Cost & tokens transparency** — by-source + per-role token/cost table. Answers his audience's #1 question
   ("how many tokens does it spend?") which he never shows.

## The two generated previews (design source-of-truth = decide at dashboard-build time)
- **Emergent** — `https://grid-control-6.preview.emergentagent.com/` (share link). **Strongest:** real photo
  thumbnails (approve cards + top content), data-driven "why this" (audience overlap 71% · saved-rate 3.4× ·
  window 48h), best Cost & tokens panel (by-source bar + by-role table + "transparent" badge), "Six roles.
  18 specialists." Team page. Generates a *fullstack* app (its own backend — we would NOT keep that).
- **Lovable** — project id `5928a078-82e3-4d3a-ad96-e62a5112abee` (preview token expires; regenerate from
  Lovable project). **Strongest:** richer **Memory & Brain** page ("What the system knows" + filtered
  append-only timeline), more refined serif, Team cards with working-now + recent-runs inline. React front-end.

**Tentative call (revisit at build time):** Emergent as base + port Lovable's richer Memory & Brain page.

## Wiring path (decided AT build time per Gaurav)
Likely: keep the chosen design's **front-end only** and wire it to our existing **Flask + Supabase + 18
agents + publishers** (the valuable part). Do NOT adopt Emergent's fullstack backend. Alternative: rebuild
screens in existing `dashboard/` (React+Vite+Tailwind v4+shadcn) using the output as pixel reference.

## Prompts used (reusable)
- `dashboard/mockups/COCKPIT_DESIGN_PROMPT_EMERGENT.md` — the cockpit prompt (used for Emergent).
- `dashboard/mockups/DASHBOARD_DESIGN_PROMPT.md` — earlier 6-page prompt (Lovable/Claude Design).
- `dashboard/mockups/daily-surface.html` — first static daily-surface mockup.
