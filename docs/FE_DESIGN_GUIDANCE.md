# Grid Control — FE Design Guidance (Tier C, adopted from agency-agents)

Distilled from the agency-agents `design/` division + `specialized/chief-of-staff` +
`strategy/runbooks/scenario-marketing-campaign`, mapped to OUR front end. This is the
checklist the landing + Command Center get held to. Pairs with `dashboard/src/styles/grid-tokens.css`.

## 1. UX architecture (from `design-ux-architect`)
- One primary job per screen. Landing → "understand + start". Command Center → "talk to Atlas + approve".
- Information scent: the owner should always know what the team is doing and what needs them, in ≤2s.
- No dead ends. Every state (empty, working, waiting, done) is designed, not an afterthought.

## 2. UI craft (from `design-ui-designer`)
- Tokens first, always (grid-tokens.css). No hardcoded hex, no one-off spacing.
- Restraint = premium (helloelva bar): whitespace and type do the work; lava is scarce and earns attention.
- Light landing → dark cockpit at sign-in = the "behind the curtain" crossing.

## 3. The Chief-of-Staff model (from `specialized/chief-of-staff`)
- The owner talks to ONE persona (Atlas). Atlas narrates the team's work in human terms.
- THE SECRET (hard rule): never expose model names, cost, tokens, JSON, agent slugs, infra.
  Translate everything to outcomes + character language. "Lumen shipped your carousel" — never a slug.
- Atlas carries the thread week to week (the narrative brain): see `executive_summary_generator`.

## 4. Visual storytelling + whimsy (from `design-visual-storyteller`, `design-whimsy-injector`)
- The robot cast is the soul. Characters > generic cards. The "Lovable look" = card-grids + step-lists + pill badges → avoid.
- One signature delight per screen (a character blink, a cursor reaction, a worker "waking up"). Not noise — one moment.
- Motion is hand-tuned (Lenis weight + GSAP easing), never default ease.

## 5. Accessibility (from `testing/accessibility-auditor`)
- Contrast: body text ≥ 4.5:1 on both cream and cockpit-dark. Lava on cream passes for large text only — never lava body text on cream.
- Touch targets ≥ 44px. Focus rings on every interactive element. Respect `prefers-reduced-motion` (kill the 3D/scroll motion when set).
- Every avatar/character image needs alt text in human terms ("Atlas, your chief of staff").

## 6. Research discipline (from `design-ux-researcher`)
- Clone the real reference, don't approximate from memory (helloelva structure was extracted, not guessed).
- Validate against the benchmark per screen before calling it done; run `design:design-critique` on our own output first.

## 7. Campaign-narrative arc (from `scenario-marketing-campaign` runbook)
- The Command Center should read like a campaign in motion: goal set → crew working → pieces for approval → shipped → results.
- Mirror the team-assembly sequence so the owner sees the same flow our agents actually run.

## Applies to (current FE)
- `dashboard/src/landing/*` — helloelva-cloned landing (light, centered, work-grid spine).
- `dashboard/src/pages/BrandCockpitPage` — existing dark Command Center (Atlas + approvals + floor); retool against §3 + §7.
- Robot cast prompts (via `creative_director` + `design-image-prompt-engineer`) — full-body, animatable, drop into landing + floor.
