# Grid Control — Per-Page Image Prompts (FAL / GPT-image reference gen)

Workflow: Gaurav generates one reference image per page using the STYLE BLOCK + that
page's PAGE PROMPT → hands the image to Claude Code → Claude codes it natively in
`dashboard/` on grid-tokens + wires to the live Flask `/api`.

Cast (client-facing, locked): Atlas (chief of staff, lead — LAVA ORANGE) ·
Scout · Cadence · Riveter · Lumen · Gauge · Echo · Sentry · Finch (all EMERALD).
NEVER show: model names, cost, tokens, JSON, slugs, infra, or the word "NOIMOS".

---

## REFERENCE LOCK (paste FIRST, above the STYLE BLOCK, with the attached image)

> **Use the attached reference image as the single source of truth. Reproduce its exact
> layout, structure, panel placement, and composition — do not reinvent or rearrange.** The
> STYLE BLOCK below only refines color, mood, lighting, and type. If the reference and the
> text ever conflict, the attached image wins on layout; this prompt wins on color/style.

---

## STYLE BLOCK (paste at the TOP of every page prompt)

> A dark, cinematic AI-marketing command center called **Grid Control**. Feel: a living
> spaceship cockpit fused with premium SaaS — like a calmer Linear meets sci-fi. Alive,
> never flat or corporate-stock.
> Deep near-black base (#0A0C0B). Glass panels with blur (rgba(18,22,23,.5)). Warm ink
> text (#F2EEE6). ONE scarce **lava-orange** accent (#FF4D00) for primary actions only.
> **Emerald** (#16A07E) for agent / online / success states. Teal (#2A8E80) + a soft
> ambient **blue** (#2E6BFF) as secondary glows. **No gold, ever.**
> Soft drifting aurora in the deep background. Subtle film grain. Generous negative space.
> Display type: Bricolage Grotesque. Accent serif: Instrument Serif. Body: Geist.
> 16:9, ultra-crisp, high-end product-shot lighting.

---

## 1. LANDING  (= public hero; the "Orchestrator" screen)
> Centerpiece: a large glowing animated **soul energy-orb** dead center — liquid plasma,
> emerald/teal core with lava-orange filaments, slow rotation, light bloom. Headline above:
> **"The Orchestrator of Your Marketing."** Below the orb, a row of small glass agent cards
> (Atlas highlighted orange, others emerald). Bottom: live-feel mission stats (campaigns /
> spend / ROAS) and one lava-orange **"Take Control"** button. Hex "GC" logo top-left.
> Wide cinematic vignette.

## 2. SIGN-IN
> Split screen. LEFT: the Atlas robot mascot (cream + orange WALL·E-style) standing in soft
> light beside an aurora globe. RIGHT: a centered glass auth card — hex "GC" logo, tagline
> **"TAKE CONTROL."**, a primary lava-orange **"Send Magic Link"** button, and a small
> "use password instead" fallback link below. Minimal, premium, lots of dark space.

## 3. ONBOARDING (guided chat, step 1/4)
> A guided chat console center-stage. Atlas robot avatar (small, orange) with a greeting
> bubble: **"Welcome, I am Atlas."** Below the message, two large selectable glass choice
> cards: **"New Venture"** and **"Active Brand."** A slim 1/4 progress indicator at top.
> Warm, human, calm — onboarding not dashboard.

## 4. COMMAND CENTER  (the daily driver)
> Three-column app shell.
> LEFT RAIL: vertical nav — Command, Ventures, Brand Engine, Intelligence, Vault — with the
> hex GC logo top and a small "SOUL CORE ONLINE" status dot (emerald) bottom.
> CENTER (primary, largest): a **chat console** with Atlas — conversation thread plus one
> inline **approval card** titled "Ad Concept v1" with **Approve** (lava-orange) and
> **Request Changes** (ghost) buttons.
> RIGHT RAIL: a **"Live Work Feed"** — a vertical list of running agent task chips (Riveter,
> Lumen, Cadence, Finch…) each with an emerald progress state. (NO "NOIMOS" label.)

## 5. REVIEW  (approval queue)
> A focused review surface: a stack/grid of pending work cards (a reel thumbnail, a carousel,
> a caption block) each with Approve / Request Changes / Block actions. One card expanded
> large center showing the asset preview. Calm, gallery-like, dark glass frames, emerald
> "ready" badges, lava-orange primary action.

## 6. YOUR TEAM  (agent roster)
> A constellation/grid of the 9 agents as glowing robot-visor avatar cards: Atlas (center,
> orange, larger — "Chief of Staff"), the other 8 emerald in orbit around it (Scout, Cadence,
> Riveter, Lumen, Gauge, Echo, Sentry, Finch), each card showing name + one-line role + an
> online dot. Faint connecting light-lines between them (a living team, not an org chart).

## 7. CALENDAR  (content calendar)
> A 30-day content calendar in dark glass. Day cells hold small platform-tinted content chips
> (reel / carousel / post) with tiny status dots (drafted / approved / scheduled). A right
> side-panel previews the selected day's posts. Clean grid, emerald for scheduled, lava-orange
> for "needs you," soft aurora behind.

## 8. INSIGHTS  (performance)
> An analytics cockpit: one hero metric (ROAS or reach) as a large glowing number, a primary
> line/area chart with emerald + blue gradients on dark, a row of stat tiles below, and a
> "what changed / what to do" insight callout card. Data-dense but breathable — instrument
> panel, not spreadsheet.

## 9. CONNECTIONS  (channels)
> A grid of platform connection tiles — Instagram, LinkedIn, YouTube, X, Google — each a glass
> card with the platform mark, a live status (emerald "Connected" / dim "Connect"), and a
> connect button. Cockpit feel, secure/premium. Never displays any token or secret text.
