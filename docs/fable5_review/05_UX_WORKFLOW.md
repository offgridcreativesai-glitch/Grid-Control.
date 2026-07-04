# UX / Workflow Pass — Making the Agency Cycle FELT (Jul 4 2026)

Second Fable 5 pass on branch `fable5-rebuild`. Closes gap #7 from
[01_GAP_RISK_REPORT.md](01_GAP_RISK_REPORT.md) with built UI (dashboard/ has
real changes this time), plus a full click-through as a non-technical founder,
plus the residual archetype wiring.

---

## 1. Built: the operating rhythm is now visible

### "Your week" panel — Command Center right rail
- **Backend**: `GET /api/week?brand_slug=` ([routes/system.py](../../routes/system.py))
  — one call returns `ran` (agent_runs last 7 days via new
  `get_brand_agent_runs()` in supabase/db.py), `waiting` (pending approvals,
  DB-first + disk fallback), `next` (this brand's jobs from
  scheduler/schedule_config.json). Auth-gated (verified 401 unauth).
- **Frontend**: `useWeek()` hook (60s refetch) + `WeekPulse` in
  [CommandCenterPage.tsx](../../dashboard/src/pages/CommandCenterPage.tsx):
  **What ran** (persona phrases — "Spark finished this week's research", never
  slugs/status codes), **Waiting on you: N decisions** (gold, links to Vault),
  **Coming up** ("Fresh research every morning · 07:30", "Weekly review lands
  Friday · 18:00"). THE SECRET holds throughout. `DEMO_WEEK` added so the demo
  walkthrough shows the rhythm.

### Approval queue split by decision weight — Vault
[ReviewPage.tsx](../../dashboard/src/pages/ReviewPage.tsx):
- **Two lanes in Drafts**: "Big decisions · steer the plan" (strategy-agent,
  content-planner, brand-guardian, weekly/monthly/quarterly composers,
  brand-book — the `STRATEGY_SLUGS` set) above "Content approvals". Strategy
  items get a primary left-border + FileText icon.
- **Plan items stopped rendering as tweets**: a plan-level output now renders
  as a "Plan for your sign-off" document card (was: X-mockup with brand handle
  — actively misleading). Header shows "Plan · Prepared:" not "x · Scheduled:".
- **Account-manager framing** on every pending item: one sentence saying who
  made it, why it exists, and what approving does ("Riveter drafted this
  LinkedIn post for Friday as part of this week's plan. Approving moves it to
  Ready — nothing publishes without you." / plan version: "…approving it steers
  what the team builds over the coming weeks.").
- Demo gets a plan-level item ("Week 3 content plan — barrier-repair education
  arc") so the lane is visible in walkthroughs.

## 2. Workflow pass as Gaurav — friction log

Route: sign-in → demo → onboarding (all 7 steps) → command → review/approve →
publish path → calendar/insights/memory/connections/team.

**Fixed this pass (cheap):**
1. **Onboarding step-3 dead end (REAL BUG)** — framer-motion
   `AnimatePresence mode="wait"` left the card EMPTY on step change (old
   fields unmounted, new never mounted; title said "Audience & goal", body
   showed nothing). A non-technical user is hard-stuck at step 3 of 7.
   Fix: dropped wait-mode exit animation; simple keyed fade-in can't strand.
   Verified: full 7-step traversal now works.
2. **Onboarding never asked the brand's KIND** — the one question the whole
   archetype reasoning layer wants. Added required "What kind of brand is
   this" (Product / Service / Personal brand) to Brand basics with a
   plain-English why-line; flows into `brand_profile.business_model_archetype`
   → STEP 0 classifies with confidence 1.0 instead of heuristics; shown on the
   Review & confirm step ("Kind").
3. **X auto-publish violated the standing manual-only rule** —
   `_publish_twitter_impl` ([core.py](../../core.py)) auto-posted when the 4
   OAuth keys were live, but the durable publish policy (May 2026) is "X →
   MANUAL upload, always." Now defaults to a `prepared` package ("copy this
   text and post it yourself"); auto-posting requires explicit
   `TWITTER_AUTO_PUBLISH=true` in the brand's `.env` (trust-dial-style opt-in).
4. Week-run phrases: per-persona past-tense lines (was "Spark finished trend
   researcher work").

**Found, NOT fixed (with cost):**
| Friction | Why it matters | Effort |
|---|---|---|
| Calendar shows only *pending* scheduled posts — published/past posts absent, so the month reads emptier than reality | Rhythm story breaks on the Calendar page | ~half day (merge usePublishedPosts into the grid + status colors) |
| "Verify accounts" card in Atlas chat has no completion state in demo | First-run demo dead-ends on the primary CTA | small, but demo-only; skipped as prod path works via API |
| Ready-stage publish for LinkedIn is real but YouTube returns needs_video honestly; no UI hint BEFORE clicking which platforms are auto vs manual | One extra confused click | ~1 hr (badge per platform on Ready cards) |
| Approval e-mail digest exists (`/api/notifications/*`) but nothing schedules it | "Waiting on you" only works if you open the app | blocked on NOTIFICATION_WEBHOOK_URL / Make scenario (already on the todo) |
| tsc `npm run build` warns 500kB+ chunk | slower first load | ~1 hr code-split, cosmetic for now |

## 3. Residual archetype wiring (from 01 §1)

- **carousel_designer.py** — STEP 0 classify + `directive_block` in slide
  prompt; last-slide CTA now obeys archetype CTA distance (was: hardcoded
  personal-brand "never hire-me" only).
- **email_marketing_agent.py** — directive in system prompt; Email 3 CTA
  bound to archetype CTA distance.
- **dm_customer_hunter.py** — directive in first-DM system prompt (product
  brand DMs ≠ service DMs ≠ personal); removed hardcoded "founder's voice"
  phrasing (wrong for product brands).
- **ad_strategist**: no agent file exists yet (roster row 16 "not yet built") —
  wire STEP 0 in on creation; noted here so it isn't forgotten.
- Still open (deliberate): performance_tracker's winning/dead scoring is
  archetype-blind (saves+DM for everyone). Needs a metric map per archetype —
  ~half day, touches pure-math Class-1 code, do with care + tests.

## 4. Verification
- `python3 tests/test_brand_archetype.py` + `tests/test_second_brain.py` — 12/12 pass.
- `npm run build` — clean (chunk-size warning only).
- `/api/week` — 401 unauthenticated (correct), registered on live Flask.
- Browser-verified in demo mode: Week panel, lanes, plan card, framing,
  onboarding 7-step traversal, all client pages render persona-clean (no raw
  JSON, no slugs anywhere).

Invariants check: approval gate untouched (framing copy reinforces it) ·
zero-fabrication (week view reads real runs/schedule only; X publish became
MORE honest) · per-brand isolation (week endpoint slug-validated + brand-scoped)
· THE SECRET (all new UI speaks persona) · cost caps (no new paid ops; week
endpoint is free reads).
