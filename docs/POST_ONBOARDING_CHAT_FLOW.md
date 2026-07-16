# GC Post-Onboarding Chat Flow — What the Client Experiences

> Jul 15 2026. Companion to `POST_ONBOARDING_FLOW_REDESIGN.md` (direction) and
> `GC_WORKING_PROCESS.md` (lifecycle). This doc is the **moment-by-moment chat flow** after a
> brand's book is approved, mapped to components that already exist in code, with the
> Jul 14–15 frustration points designed out as enforced rules. **Spec doc — no new code until "build".**

---

## 0. Ground truth this flow is built on

- Program engine (Stages 0–5) is BUILT: phase state, weekly review + build loops, monthly/quarterly
  composers, trust dial, cost guard, in-flight lock. What's left is real-usage verification.
- Everything below names the real component so nothing here is invented:
  `ProgramPhaseCard.tsx` · `CommandCenterPage.tsx` (ApprovalCard + PROGRAM_CARD_SLUGS) ·
  `routes/brain.py` (Atlas + `run_agent`) · `core.py` (`run_weekly_program`, `_auto_advance_output`) ·
  `agents/weekly_review_composer.py` · `agents/monthly_mix_composer.py` ·
  `agents/_lib/phases.py` · `agents/_lib/trust_dial.py` · `scheduler/worker.py`.

---

## 1. The flow, moment by moment

### Moment 0 — Brand book approved (the handoff point)
What happened just before: client clicked **Approve** on the brand-book card.
System side: Foundation written (`brand_profile.json`, `voice_profile.json`, brand narrative),
Memory seeded, `program_phase` set (default `launch`; e.g. TGT = `foundation`).

**What the client sees in chat:** the **Program Phase Card** — "You're in the Foundation phase.
Goal: {phase goal}. This week: {N} posts, {content:ads ratio}." One CTA: **Start my weekly program**.
No more "3 buttons then silence" — the card IS the start of a running program.

### Moment 1 — Kick-off conversation (Atlas proposes, client approves)
Client clicks the CTA → it sends a chat prompt to Atlas.

**Atlas's reply must contain, in plain language (never JSON):**
1. What week 1 will do — which specialists run, in what order, and why (phase-scoped:
   a `foundation` brand skips Creative Director / Carousel Designer automatically).
2. An honest data inventory: "You have X connected, no trend data yet, voice profile empty —
   here's what that limits." Missing data is NAMED, never papered over.
3. Estimated cost of the run before anything paid fires.
4. An **Approve & run** card. Nothing runs until the click.

**Hard rules at this moment:**
- Atlas MUST dispatch via `run_agent` — it never answers a data question from its own head.
  If it can't run the agent, it says so; it never produces "based on my analysis" numbers.
- If the backend is unreachable, the client sees a "backend unreachable" state —
  NEVER a redirect to onboarding, NEVER the demo brand.

### Moment 2 — Week 1 runs (the build + review loops)
On approve, `run_weekly_program(brand_slug)` fires: in-flight lock → cost guard →
review loop (Data Analyst + Performance Tracker + Trend Sentinel → Weekly Review Composer)
and build loop (Trend Researcher → Content Planner → Script Writer → phase-gated
Creative Director / Carousel Designer).

**What the client sees:** the Live Work Feed shows each specialist as it runs. Every finished
output lands as an **approval card in chat** — human-readable narrative via
`format_for_notion` (headline, summary, recommendation). Program-driven cards carry the
emerald "Atlas ran your weekly program" banner so system moves are visually distinct from
manual asks.

**Hard rules at this moment:**
- Every agent type MUST have a `format_for_notion` branch. A missing branch = the raw-JSON
  key-dump bug (regressed 3+ times). Any new agent output type ships its formatter branch +
  test in the same commit.
- An agent with no real data HALTS and says "no data yet from: X" (composer already does this).
  It never invents plausible-looking stats. (Known violator: Data Analyst — see §3.)

### Moment 3 — Review: approve / request changes / reject
Each card: **Approve** → file moves `pending_approval/ → approved/`, Supabase updated,
next agent in the chain unlocks. **Request changes** → scoped re-run. **Reject** → file removed.

**Hard rules:** an action that changed nothing returns an honest error (404), never
`success: true`. The card the client acted on visibly disappears or updates — the UI state
always matches the filesystem state. (This was Bug 4; pinned by `test_reject_resolution.py`.)

### Moment 4 — Publish (only after explicit approval)
Approved content → publish card per platform. Standing rules unchanged: IG / LinkedIn /
YouTube Shorts via automation, **X always manual**, carousels IG+LinkedIn only. Nothing
auto-publishes; `direct` trust level is reserved for a future fully-built publish pipeline.
Today only the Instagram publisher exists — LinkedIn/YouTube/X publishers are the top
pending build (CLAUDE.md priority #2).

### Moment 5 — The rhythm (what next week looks like)
- **Weekly:** review card ("Last week + keep / cut / scale") + the next build-loop batch.
- **Monthly:** mix-review card (`monthly_mix_composer`, $0 pure-math; budget split stays
  null-with-reason until real ad spend exists — no fabricated budget math).
- **Quarterly:** QBR — Strategy Agent re-runs the 90-day roadmap; phase advance decided here,
  client-approved like everything else.
- Scheduler jobs for all three exist in `scheduler/schedule_config.json` but are **DISABLED**.
  Gaurav enables them deliberately, one brand at a time — no repeat of the Jun-15 cost drain.

### Moment 6 — Trust dial (earned, not default)
Every agent on every brand starts at **consult** (human click on every card). As the client
builds trust, the per-persona dial (super-admin only, fail-safe to consult) moves specific
agents to **automate**. The dial never breaks THE SECRET — clients see 8 personas, never 18 slugs.

---

## 2. Failure states — what the client sees when things go wrong

The Jul 14–15 lesson: silent failure is what destroyed trust. Every failure mode has a
visible, honest state:

| Situation | Client sees | Never |
|---|---|---|
| Flask/API down | "Backend unreachable — your data is safe" screen | Bounce to onboarding (Bug 1, pinned: `onboardingDecision.test.ts`) |
| Stale demo flag + real login | Their real brand | Aurora demo data (Bug 2, pinned: `demo.test.ts`) |
| Agent output arrives | Human narrative | Raw JSON key-dump (Bug 3, pinned: `test_output_formatter.py`) |
| Reject a card that can't resolve | Honest error, card stays with reason | `success: true` + card lingering (Bug 4, pinned: `test_reject_resolution.py`) |
| Agent has no real data | "No data yet from: X" + what to connect | Fabricated plausible stats |
| Cost gate trips mid-run | "Paused: daily budget cap reached" card | Silent partial run |
| Handle doesn't resolve at pre-flight | Atlas asks to confirm/correct in chat | A paid run on a guessed handle |

---

## 3. Corrections — frustration points → what's fixed vs. still open

### Fixed and pinned (Jul 14–15, each with a fail-on-old/pass-on-fix test + CI):
1. **Onboarding restart on API-down** — `onboardingDecision.ts` + test (commit 392899c).
2. **Aurora demo leak over real login** — `demoDecision()` + test (commit 084269f).
3. **Vault raw-JSON dump** — brand-book formatter branch + test (commit 4e4ae9e).
4. **Reject/approve silent no-op** — `_find_pending_output` + honest 404 + test (commit 9237b9b).
CI (`.github/workflows/ci.yml`: tsc + vitest; pytest job landing via Fable) blocks regressions.
Verification = green/red in GitHub → Actions, not anyone's word.

### Open — must close for the flow above to be trustworthy (priority order):
1. **Data Analyst fabricates when a brand has no connections** (found Jul 1: invented
   "16 followers / 460 reach / 3 posts"). This feeds Moment 2's weekly review card —
   the single worst thing to show a new client. Fix = hard no-data HALT in
   `agents/data_analyst.py` + test.
2. **~25 endpoints default `brand_slug` to a hardcoded brand** — wrong-brand reads/writes.
   With Fable (parallel window) + backend pytest CI job.
3. **Atlas `run_agent` full UI click-through never verified** (model-level only, commit
   b532a69). Needs one real logged-in session: ask Atlas something data-shaped → watch it
   dispatch → card appears.
4. **Build loop (Stage 3) never run for real** — first real run is Gaurav-triggered from the
   UI (TGT, phase `foundation`), with pre-flight + cost cap. Creative Director implies real
   image/video spend — separate explicit approval.
5. **SSE 401 hammering in real auth sessions** (found in UAT Jul 7, unconfirmed as fixed) —
   re-check once, pin with a test if still live.
6. **TGT `voice_profile.json` is empty** — Script Writer's voice check runs blind. Seed it
   from the approved brand book before the first build loop.
7. **LinkedIn/YouTube/X publishers** — Moment 4 is IG-only until built.
8. **Local-vs-Railway data split** (deepest, unresolved) — `brands/` lives only on this
   laptop; the production flow can't run for a real remote client until brand data has a
   server-side home. Needs its own design session.

---

## 4. Standing rules this flow encodes (never re-litigate)

- Atlas proposes, the human clicks. Nothing paid or published without a click (Mode A, locked).
- Every claim in chat traces to a real agent run (`run_agent` + provenance) — zero fabrication.
- Every output is human narrative through the formatter. No JSON reaches a human, ever.
- Every failure is visible and honest. No `success: true` lies, no silent skips.
- Every bug fix ships with a test wired into the real code path; CI is the door guard.
- One scheduler, in-flight lock, budget caps. Cost gates run BEFORE spend, not after.
- Client sees personas (8), never the 18-agent roster. THE SECRET holds.
