# GC Post-Onboarding Flow — Redesign

> Jun 30 2026. Companion to `AGENCY_OPERATING_MODEL_RESEARCH.md`. Maps how real agencies
> operate onto GC's 18 agents, names the gap, and proposes the revised **after-onboarding**
> flow + an operating-model recommendation. **Direction doc — no code until "build".**

---

## 1. The gap (what you sensed was missing)

GC's onboarding arc is wired end-to-end and good: validate handles → generate brand report →
review/approve → write Foundation + seed Memory → **first-task handoff** (`FirstTaskCard`:
"Plan my first week / Create my first post / What's trending").

Then it **stops.** After approval, GC hands the owner three buttons and goes quiet. That's the
hole. A real agency's value is almost entirely in **what happens every week after onboarding** —
the phased program, the weekly review/build loop, the paid test→scale loop, the monthly
re-plan, the QBR. GC has all the *workers* for that and **none of the *clock*.**

Put bluntly: **today GC sells onboarding + on-request tasks. An agency sells an operating
system.** The redesign turns the "first task" moment into the **start of a running program.**

---

## 2. The agency operating system → GC's 18 agents (the roster is NOT the gap)

| Agency function | GC agent(s) | Today | Needs |
|---|---|---|---|
| Strategy / 90-day roadmap | strategy-agent (1) | runs once | re-run quarterly (QBR) |
| Phased plan + calendar | content-planner (2) | runs once | phase-aware, monthly re-plan |
| Content / scripts / hooks | script-writer (3) | on request | weekly build loop |
| Performance creative / video | creative-director (4) | on request | weekly asset batch (vol by phase) |
| Paid media | ad-strategist (5) | budget-gated | **continuous weekly paid loop** |
| Analytics / weekly score | data-analyst (6) | weekly-capable | feed the **review loop** |
| Funnel / CRO | funnel-specialist (7) | on request | per-phase CRO tests |
| Trends | trend-researcher (8) | weekly-capable | feed weekly build loop |
| Website / GA4 / GSC | website-agent (9) | on request | owned-channel tracking |
| Brand SOUL gate | brand-guardian (10) | per-output | unchanged (good) |
| SEO / AEO | seo-aeo-agent (11) | on request | growth/scale phases |
| Email + SMS/WhatsApp | email-marketing-agent (12) | on request | **lifecycle flows (retention)** |
| Community | community-manager (13) | on request | always-on |
| DM / lead hunt | dm-customer-hunter (14) | on request | always-on |
| Carousels | carousel-designer (15) | on request | weekly build loop |
| Pivot/track decision | trend-sentinel (16) | daily math | feed weekly review |
| Winning/dead patterns | performance-tracker (17) | math | feed **keep/cut/scale** |
| Orchestration + narration | **ceo-brain / Atlas (0)** | onboarding only | **run the program + QBR narration** |

The mapping is nearly 1:1 with a full-service agency. **The missing piece is the orchestration
layer that schedules these into a phased, cadenced loop** — i.e. give CEO-Brain/Atlas a clock
and a program to run, not just a chat to answer.

---

## 3. The redesign: an always-on **Operating Program**

Replace "onboarding → 3 buttons → silence" with **onboarding → Program**. Three components:

### A. Phase state (the spine)
On approve, the brand enters a **named phase** — `Foundation → Launch → Growth → Scale` —
derived from its real stage (revenue/followers/whether ads are on). Each phase carries:
- a phase-appropriate plan (content volume + **content:ads ratio** from research §3),
- which agents are active,
- the goal/exit-criteria to advance to the next phase (a gate, owner-approved).

So the "first task" becomes "**here's your Launch-phase plan for the next 30 days**", not a
generic button.

### B. The cadence engine (the clock) — *the core new thing to build*
A scheduler that fires GC's agents on the agency rhythm and surfaces each as an **approval
card** in the cockpit (keeps our approval gate intact):

- **Weekly — Review loop:** data-analyst + performance-tracker + trend-sentinel → Atlas posts a
  "**Last week + keep/cut/scale**" card. Owner approves the calls.
- **Weekly — Build loop:** trend-researcher → content-planner → script-writer + carousel-designer
  + creative-director produce the week's batch (volume set by phase) → approval → publish pipeline.
- **Monthly — Mix review:** Atlas posts a "month in review + proposed budget/channel rebalance +
  next-30-day plan" card.
- **Quarterly — QBR:** strategy-agent re-runs the 90-day roadmap; Atlas narrates results and the
  next big bets; phase advance decided here.

Each card = a KPI/decision with **trigger + owner + playbook** attached (research §4/§8).

### C. The two loops, wired (the growth loop)
`plan → produce → brand-guardian gate → approve → publish → measure → learn → re-plan`, with
**winning organic promoted into paid creative** when budget is on. The paid sub-loop
(ad-strategist → creative-director → data-analyst → performance-tracker) runs weekly with
**explicit kill criteria**, budget-gated as today. This is the content→ads→sales pipeline from
research §5–6, made literal.

---

## 4. Operating model — recommendation (you leaned self-serve; here's what the research favors)

**Recommendation: Trust-dial hybrid that *defaults to done-for-you*** — not pure self-serve.

Why the evidence points here for **our specific buyer** (non-technical SMB/founder):

- Research flags **DIY/self-serve as the anti-pattern** for this buyer — they hire help precisely
  because they don't know the weekly plan. A "3 buttons + chat" model silently pushes the hardest
  job (knowing what to do each week) back onto them.
- Our own moat memory: white space = **chief-of-staff that curates + phases the team** for the
  non-technical owner; done-for-you + curation IP is the moat, not the orchestrator.
- The market is moving to **autonomous done-for-you** (Noimos = 24/7 command team) with
  **outcome-based pricing.** Pure self-serve competes on price against Jasper et al. and loses our differentiation.
- But full autonomy with no control = trust + cost risk (cf. the Jun-15 cost-drain incident).

So: **Atlas runs the phased program and proposes every weekly/monthly/quarterly move by default
(done-for-you), and the owner sets a per-agent trust dial — Consult / Automate / Direct — on top,
with the approval gate as the safety rail.** New brands start mostly on **Consult** (Atlas
proposes, owner approves each card); as trust builds they dial individual agents to **Automate**.

This gives us all three: the done-for-you value the buyer actually needs, the control/cost-safety
GC requires, and a **transparency wedge** (provenance + cost meter + approval cards) that beats
opaque-credit competitors like Noimos.

> Net: "self-serve assisted" is the *weakest* fit for who GC sells to. The same flexibility you
> liked about it is better delivered as a **dial on top of a done-for-you default** than as the default itself. Your call — flagged because it diverges from the initial lean.

---

## 5. What this implies to build (later, on your go)

Smallest first, each independently shippable:

1. **Phase state** on the brand (Foundation/Launch/Growth/Scale) + phase plan profile → render the post-approve card as a phase plan, not 3 generic buttons.
2. **Weekly Review-loop card** (data-analyst + performance-tracker → keep/cut/scale) — highest value, reuses agents we have.
3. **Weekly Build-loop** wiring (trend → planner → writers/creative → approval → publish).
4. **Cadence scheduler** (one scheduler, budget-capped — respect the cost-control rules; no repeat of the multi-scheduler drain) firing weekly/monthly/quarterly.
5. **Monthly review + Quarterly QBR** narration cards from Atlas.
6. **Trust dial** (Consult/Automate/Direct per agent) layered on the approval gate.

**Cost ladder stays intact:** onboarding (paid once) → weekly loop (cheap math + gated generation) → monthly/quarterly re-plans (scoped). One scheduler, in-flight lock, budget caps — per the cost-control standing rule.

---

## 6. Open decisions for Gaurav

1. **Operating model** — confirm trust-dial-hybrid-defaulting-to-done-for-you (recommended) vs your self-serve lean.
2. **Build order** — start with #1 (phase state + phase plan card) or #2 (weekly review loop)?
3. **Phase definitions** — agree the 4 phase gates/exit-criteria for our brands (TGT/askgauravai are pre-launch/launch).

No code until you pick. Related memory: [[market_validation_chief_of_staff]] · [[competitor_noimosai]] · [[project_onboarding_flow_spec]] · [[project_cost_control_incident]].
