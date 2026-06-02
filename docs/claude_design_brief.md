# Grid Control — Claude Design Brief (Phase 2)

> **Purpose:** paste-ready prompts for building the cockpit's visual language in Claude Design
> (claude.ai web artifacts), separate from this CLI. Work on **look + layout only** here —
> placeholder data is fine. When a screen looks right, copy the component code back into the repo
> and Claude Code wires it to real endpoints in Phase 3.
> **This file survives compaction.** It is the source of truth for the cockpit's visual spec.

---

## Global taste guardrails (paste at the top of EVERY screen prompt)

```
Visual direction — non-negotiable:
- Calm, editorial, confident. Think a premium analytics product (Linear, Vercel, Things 3),
  NOT a crypto dashboard. No neon, no over-saturation, no glow, no rainbow gradients.
- Dark mode primary. Near-black background (not pure #000), soft elevated surfaces.
- ONE restrained accent color used sparingly for the most important action/state only.
  Everything else is neutral grays + good typographic hierarchy.
- Generous breathing room. Let modules sit apart. Whitespace is a feature.
- Typography does the work: clear sizes/weights, not borders and boxes everywhere.
- Rounded corners (~12-16px), subtle 1px borders, very soft shadows. No heavy drop shadows.
- Status colors muted, not loud: success = soft green, warning = soft amber, danger = soft red.
- Stack: React + Tailwind. Use shadcn/ui-style components. Lucide icons.
- It must feel like a place you OPERATE a brand from, not a marketing landing page.
```

---

## Screen 1 — Brand Cockpit (the command center, route "/")

This is the primary screen. Replaces the current chat-first dashboard.

```
[Paste global taste guardrails first]

Build a single-page "Brand Command Center" cockpit for a marketing operating system.
One brand in view at a time. Top-down scroll, no tabs. Layout:

TOP BAR (slim): brand name + small brand switcher dropdown on the left; on the right a small
"Operator mode" toggle (OFF by default, with a subtle lock icon) and a user avatar.

TOP ZONE — two columns, equal-ish width, side by side:

  LEFT COLUMN — "Daily Intelligence Digest" (this is the HERO module):
  - Header: "Daily Intelligence Digest" + a dateline ("Updated 2h ago · last pipeline run 9:14 AM").
  - A prominent verdict BADGE at the top: one of PIVOT / TRACK / STAY. Muted color-coded
    (PIVOT = soft amber, TRACK = soft blue, STAY = soft green). Big enough to read at a glance,
    with a one-line reason under it ("Engagement on Reels up 18% w/w — keep current direction").
  - "New trends" — a short list (3-5) of trend items, each with a name and a small relevance
    score chip (e.g. 0.82). Subtle, scannable.
  - "Flags" — 0-2 contradiction/conflict items in muted red, each one line.
  - A quiet "Run daily pipeline" text button at the bottom.
  - Empty state version: calm "No new intelligence yet — run the daily pipeline to populate."

  RIGHT COLUMN — "The Brain" (embedded chat driver):
  - A clean, inviting chat panel. Big input at the bottom: placeholder "Tell me what you need…".
  - 3-4 suggested quick-action chips above the input: "Plan this week", "Review pending",
    "What's trending", "Check performance".
  - Show one example exchange (a user message + a Brain reply with a small "proposed action"
    card that has Approve / Dismiss buttons) so the approval-gate pattern is visible.
  - Calm, lots of vertical space.

GRID BELOW — two modules side by side:

  LEFT — "Agent Activity":
  - A compact list of agents (Trend Researcher, Content Planner, Script Writer, Creative Director,
    Data Analyst, Brand Guardian — show ~6). Each row: agent name, last action ("Generated 3 scripts"),
    relative time ("2h ago"), and a small status dot (running = soft blue pulse, idle = gray,
    blocked = soft red).
  - A clear inline alert chip at the top of this module: "4 awaiting review →" that looks clickable.
  - One or two quiet backup buttons: "Run Trend Research", "Generate scripts".

  RIGHT — "Performance Snapshot":
  - Show TWO states stacked so I can compare:
    (a) Connected state: 3-4 small stat tiles (Reach, Engagement rate, Saves, Followers) with
        tiny sparkline trends. Muted, editorial.
    (b) Empty/connect state: a calm card "Connect Meta to see live performance" with a single
        primary button "Connect Meta". NO fake numbers in this state.

Make it feel premium and quiet. Prioritize hierarchy and spacing over decoration.
```

---

## Screen 2 — Admin Panel (owner-only, top altitude) — BUILD FIRST

The owner's (Gaurav's) top-level control tower. ONLY the owner ever sees this — gated by
super-admin role. It controls Grid Control itself AND lists all brands; selecting a brand drills
down into that brand's cockpit (Screen 1). A client never sees this layer.

Two altitudes:
  ADMIN PANEL (this screen, owner-only) → select a brand ↓ → BRAND PANEL (Screen 1 cockpit)

IMPORTANT — the System/Health strip is READ-ONLY. It shows what's wrong; it never edits or runs
code. Software changes to Grid Control are made by Claude Code (terminal), not from this panel.

```
[Paste global taste guardrails first]

Build an owner-only "Admin Panel" — the top-level control tower for a marketing operating system
called Grid Control. This sits ABOVE the individual brand cockpits. Only the owner sees it.

TOP BAR: "Grid Control · Admin" on the left; owner avatar on the right. No brand switcher here
(this IS the level above brands).

SECTION 1 — "System Health" (a slim READ-ONLY status strip, full width):
  - 4-5 compact status tiles: API status (green "Operational"), Last deploy ("2h ago · success"),
    Daily pipeline ("ran 9:14 AM · ok"), Errors (24h) ("0"), Background jobs ("2 running").
  - Muted, glanceable. NO action buttons — this only reports state, it does not change anything.
  - If something is wrong, that one tile turns soft-amber/red with a one-line reason.

SECTION 2 — summary strip: total pending approvals across all brands, total agents running,
count of brands needing attention.

SECTION 3 — "Your Brands" — a grid of BRAND CARDS (3-4 cards). Each card:
  - Brand name + tiny logo placeholder.
  - Health indicator (soft green / amber / red dot + one word: Healthy / Attention / Blocked).
  - 3 small stats: "Pending: 4", "Trends: 5 new", "Last run: 2h ago".
  - Trend Sentinel verdict badge (PIVOT / TRACK / STAY), muted.
  - The whole card is clickable: "Open cockpit →" (this is the drill-down into the brand panel).

SECTION 4 — a slim "Recent activity across all brands" feed: 5-6 lines like
"[DropVolt] Script Writer generated 3 scripts · 1h ago".

Calm, dense-but-breathable. A control tower, not a sales page. Same visual language as the
brand cockpit (reuse the saved design system).
```

---

## Screen 3 — Managed-Client Restricted View

What a brand owner (managed-client) sees — approve/reject + insights ONLY. No agent triggering,
no operator tools, no Brain write-actions.

```
[Paste global taste guardrails first]

Build a restricted "Client View" of a brand for a brand OWNER who is NOT the operator. They can
only review work and read insights. They CANNOT trigger agents or run anything.

LAYOUT, top-down:

  1. A warm one-line header: "Here's what your team prepared for [Brand]."

  2. "Awaiting your approval" — the hero. A clean review queue: 3-4 cards, each = a content piece
     (caption/script/carousel) rendered HUMAN-READABLE (never raw JSON). Each card has a small
     preview, the content type, who/what made it, and two buttons: "Approve" (primary) and
     "Request changes" (secondary, opens a small note field). Calm, confidence-inspiring.

  3. "Insights" — a read-only digest: this week's performance highlights (a few muted stat tiles)
     + 2-3 plain-English takeaways ("Your Reels are outperforming static posts 3:1"). No controls,
     no buttons that change anything.

  4. A minimal Brain input at the bottom labeled "Ask about your brand" — but framed as
     read-only/Q&A only (placeholder: "Ask about your content or performance…"). No proposed
     actions, no run buttons.

NO agent activity module, NO pipeline buttons, NO operator toggle. This person reviews and reads.
Keep it reassuring and simple — like a beautiful client portal.
```

---

## Screen 4 — Subscriber Cockpit + Agent Customization (optional, can defer to Phase 4)

Self-serve brand on subscription: full cockpit (like Screen 1) PLUS a per-brand agent on/off panel.

```
[Paste global taste guardrails first]

Reuse the Brand Cockpit layout (Screen 1), then add ONE extra surface: an "Agents" settings panel
for a self-serve subscriber to turn individual agents on/off for their brand.

The panel: a list of all 18 agents grouped by function (Research, Content, Creative, Growth,
Ops). Each row: agent name, one-line description, and a clean toggle (on/off). A few are ON by
default. A small note at top: "Customize which agents run for your brand." A "Save changes" button.

Keep it consistent with the cockpit's calm editorial style — toggles muted, generous row spacing.
```

---

## Working method (how to iterate efficiently in Claude Design)

1. Do **Screen 1 first** and get the visual language exactly right — it sets the system.
2. Once Screen 1's aesthetic is locked, tell Claude Design: *"Keep this exact visual style for the
   next screen"* and paste Screen 2's prompt. The style cascades.
3. For each finished screen: top-right of the artifact → **Copy** the code → save it somewhere
   (or paste straight back into this CLI). Note which screen it is.
4. **Don't** wire real data, routing, or auth in Claude Design. That's Phase 3 here.
5. Bring all screens back together; Claude Code extracts shared pieces (`<BrainPanel>`,
   digest module, agent rows) and wires them to `/api/digest`, `/api/brain/chat`, `useAgentStatus`,
   `usePerformanceHistory`, `usePendingOutputs`, plus the operator-mode toggle from Phase 1.

## Endpoint map (for Phase 3 wiring — reference only, not used in Claude Design)

| Module | Real source |
|--------|-------------|
| Daily Intelligence Digest | `GET /api/digest?brand_slug=` |
| The Brain | `POST /api/brain/chat` + approve/run flow |
| Agent Activity | `useAgentStatus` + `session_state` |
| "N awaiting review" | `usePendingOutputs` → `/review` |
| Performance Snapshot | `usePerformanceHistory` + `/api/connections/check` |
| Operator-mode toggle | `GET/POST /api/operator-mode` (super-admin only) |
| Agent customization | `GET/PUT /api/agent-config?brand_slug=` |
```
