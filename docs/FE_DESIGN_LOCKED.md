# Grid Control — FE Design LOCKED (Jun 21 2026)

> Gaurav-approved direction. "Glass Cockpit." Lock this; do not lose it.
> Built in Claude design (visualize/show_widget); port to React client app next.

## Feel
Dark glass + ambient 3D + drifting aurora + sequenced motion. Premium, alive, calm-but-energetic.

## Tokens
- Base `#0A0C0B` · glass panel `rgba(18,22,23,.5)` + `backdrop-filter: blur(20px) saturate(1.3)` + inner top-highlight + soft drop shadow.
- Ink `#F2EEE6` · muted `#8C9491` · hairline `rgba(242,238,230,.1)`.
- Accents: **lava `#FF4D00`** = SCARCE (hero word, CTA, Approve, active/working only) · **emerald `#16A07E`** + **teal `#2A8E80`** = structure/ready · **blue `#2E6BFF`** = NEW ambient/background accent (aurora, secondary links, info). **NO GOLD, ever.**
- Fonts: Bricolage Grotesque (display) · Instrument Serif (italic accent words) · Geist (UI/body).

## Signature elements
- **Glassmorphism** panels everywhere (needs light behind → aurora/orb provide it).
- **Ambient 3D**: Three.js wireframe icosahedron orbs, counter-rotating shells (lava + blue/emerald), low opacity, behind glass. (cdnjs three r128.)
- **Aurora**: 2–3 blurred drifting color blobs (lava/emerald/blue) on slow keyframes.
- **Motion**: sequenced rise-in on load, pulsing+glowing status dots, hover-lift cards, shimmer sweep on "Working" rows, floating Atlas avatar, breathing-glow Approve button.
- **Character avatars**: rounded-square tile, accent-tinted, an accent "visor" bar + 2 eyes (robot cast — Atlas lava, Scout/Echo/Sentry emerald, Riveter/Gauge/Finch teal, Lumen lava-soft). Real illustrated art = later (FAL).

## Patterns (locked)
- **Chat-console PRIMARY** (Atlas, chief of staff) + **Live Work Feed** right rail (Noimos). Work appears INLINE in chat as approve cards.
- **THE SECRET**: client UI never shows model/cost/token/JSON/slug/infra. Human/outcome language only.
- **Approval-gated**: nothing ships without the owner's yes.
- **Single client view** — admin panel removed.

## The 9 pages (reference widget titles)
1. Landing — `grid_control_landing_v5_glass3d` (centered hero, crew, work grid, glass CTA).
2. Sign in — `gc_p2_signin` (centered glass card, magic-link option).
3. Onboarding — `gc_p3_onboarding` (guided chat w/ Atlas, new-vs-active option cards, progress rail).
4. Command Center — `grid_control_chat_console_v4_glass3d` (chat console + Live Work Feed).
5. Review — `gc_p5_review` (approval queue, maker avatars, filter chips).
6. Your team — `gc_p6_team` (9 character cards, live status).
7. Calendar — `gc_p7_calendar` (week grid, platform-colored post chips).
8. Insights — `gc_p8_insights` (plain-English stat tiles, Atlas narrative, mini trend).
9. Connections — `gc_p9_connections` (channel cards, Live/Connect states).

## Next
Port to React client app (`dashboard/`), page by page, on `grid-tokens.css` (`.gc-cockpit` dark vars + the glass/aurora/3D utilities). Robot art via FAL drops into the avatar slots later.
