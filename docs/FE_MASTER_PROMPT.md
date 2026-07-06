# GRID CONTROL — Master Build Prompt (paste into Lovable / v0 / Emergent / Manus)

> **How to use this:** paste this whole file as your first message to the AI UI builder.
> It is self-contained. You have a **free hand on the visual design**; the *mental model*,
> the *secrecy rule*, and the *non-negotiable behaviors* are fixed.
>
> **Two audiences — keep them separate:**
> 1. **You, the builder** — you get the real backend contract (endpoints, data shapes) so you can wire it.
> 2. **The end client (a brand owner)** — the UI you build must **NEVER expose any of the backend
>    machinery to them** (see §4, THE SECRET). The client sees a polished team of people working for
>    them — not software, not models, not costs, not data plumbing.

---

## 1. The brief in one line
Build a **premium, alive command deck** where a non-technical brand owner watches their **AI marketing
team work like a real company** — a Chief of Staff they talk to, and a cast of specialist characters
who visibly do the work and bring it back **for the owner's approval**. Make it feel expensive, calm,
and *alive*. The technology behind it is invisible.

## 2. The mental model — THIS IS THE SPINE (everything flows from here)
Think of a real company the owner runs but doesn't micromanage:

- **The Owner** = the client/user. They give direction and approve. They never operate machinery.
- **The Chief of Staff (COS)** = the *single* persona the owner talks to. Warm, sharp, founder-to-founder.
  The COS takes intent in plain language, **assigns work to the team**, and **reports back up**:
  *"I had your Strategist map the next quarter — want to look?"*
- **The Team** = a cast of **specialist characters** (Strategist, Writer, Designer, Analyst, etc.),
  each with their **own avatar/persona**. The owner can *see them working on the factory floor* —
  idle, thinking, working, finished, waiting on you. Work is always **attributed to a character**:
  *"Your Content Writer drafted these 3 posts."*
- **The metaphor to feel:** an owner telling their manager what they want, then watching their team
  down on the factory floor actually build it — and signing off on the results. Corporate team
  structure, made warm and characterful.

**Why this matters:** the owner should feel *in command of a loyal team*, never like they're using
a tool. The "team of characters" is the emotional product. The COS is the one voice. Approval is the
owner's job.

## 3. The cast (humanized — give each a character + avatar)
Present the team as **people with jobs**, never as "agents," "bots," or "models." Suggested avatar
energy: a friendly, characterful mascot per role (think the warm, simple charm of Claude's orange
character — give each specialist their own personality + color, not generic icons).

| Character (client-facing name) | What they do (in owner's words) |
|---|---|
| **Chief of Staff** | The one you talk to. Runs the team, brings you what needs your call. |
| **Strategist** | Plans the 90-day game plan, watches competitors. |
| **Content Planner** | Lays out what goes out and when. |
| **Writer** | Writes the posts, hooks, captions. |
| **Creative Director / Designer** | Makes the visuals, carousels, video. |
| **Trend Researcher** | Finds what's working right now in your space. |
| **Analyst** | Tells you what's landing and what's not. |
| **Funnel Specialist** | Designs how a viewer becomes a customer. |
| **Ads Specialist** | Builds paid campaigns (only when you've set a budget). |
| **SEO / AI-Search Specialist** | Gets you found on Google + AI search. |
| **Email Specialist** | Writes your email sequences. |
| **Community Manager** | Drafts replies to comments & DMs. |
| **Outreach Specialist** | Finds and warms up potential customers. |
| **Brand Guardian** | Makes sure everything sounds like *you*. |
| **Web Specialist** | Builds & tunes your site. |

> Exact count, grouping (you may cluster into departments), and which characters are "always on screen"
> vs. "summoned" is a **design choice** — pick from the references in §13. Some background roles can be
> ambient. Never show more than the owner needs to feel the team alive.

## 4. THE SECRET — what the client must NEVER see (hard non-negotiable)
The entire technical backend is **our trade secret**. The built UI must **never surface, label, or hint at**:
- ❌ **Model names / AI tiers** (no "Opus", "Sonnet", "Haiku", "Claude", "GPT", "LLM", token counts).
- ❌ **Costs / spend / tokens** in any client-facing screen. (We track cost internally — it is **not** a
  client feature. Remove any "cost transparency" panel. The owner never sees what a task costs to run.)
- ❌ **Raw data / JSON / provenance / "source_file" / pipeline steps / run logs / "AutoResearch variants".**
- ❌ **Technical agent identities** (slugs like `dm-customer-hunter`, "agent #14", "subprocess", "API").
- ❌ **Infra** (Railway, Supabase, Apify, endpoints, scrapers, queues, schedulers).
- ❌ **The fact that work is produced by a generation loop.** The owner sees a *person* who *made* something.

What the client **does** see: a Chief of Staff, a team of characters, finished work, results/growth in
plain language, and the **Approve / Change / Reject** decision. Outcomes and people — never the engine.

> Rule of thumb: if a NASA-style "instruments / telemetry / cost meter" feeling is creeping in, you've
> drifted. This is a *company of characters*, not a control panel of metrics.

## 5. Who uses it
A solo founder / small brand owner. **Non-technical.** Wants to feel **in command and in the loop**
without touching machinery. Calm > busy. Clarity > density. One clear *"here's what needs you"* per day.

## 6. The feeling to hit
- **Premium, warm, alive, characterful.** Expensive but not corporate-cold. The team feels *present* —
  loyal employees working in the background.
- **Calm but not static.** Motion signals life, not chaos. Stillness by default, energy on purpose.
- **Human, never technical.** Copy is founder-to-founder; the team are *people*. Zero jargon, zero telemetry.
- **Trustworthy.** Timestamps and honest status ("done this morning") instead of fake real-time.

## 7. Brand colors + design direction + the avatar/character system

### 7.1 Official brand palettes (these are OUR colors — use them, mix is a creative choice)
Three palettes. You don't use all 18 swatches flat — you assign **roles** (base / hero accent / luxe
accent / cool neutral / semantic). The chosen direction (7.2) sets the dominance.

**Palette A — Lava / Ember (warm, alive):**
`#0B0B0B` Rich Black · `#1A1A1D` Onyx Charcoal · `#FF4D00` Lava Orange · `#8B1E00` Burnt Ember ·
`#4A4746` Volcanic Stone · `#F2F1EE` Ash White.

**Palette B — Arctic / Steel (cool, precise):**
`#F5F8FA` Ice White · `#D6DEE6` Silver Mist · `#9DB4C6` Glacier Blue · `#5C7386` Steel Blue ·
`#1E2A39` Arctic Navy · `#0B0F14` Obsidian.

**Palette C — Emerald / Gold (luxe, premium):**
`#0A5E4E` Emerald Palace · `#093B33` Forest Depth · `#D8C08A` Champagne Gold · `#F2EDE1` Ivory Silk ·
`#103F46` Royal Teal · `#071B1E` Dynasty Shade.

### 7.2 CHOSEN DIRECTION (locked Jun 20) — "FORGE" tuned Gen-Z / millennial interactive
Energetic, vibrant, playful-premium — an *interactive* dashboard for a young founder, NOT old-money luxury.
High contrast, characterful, motion-rich. **Gold is the LEAST-used color** (rare sparkle only).
- **Base:** Rich Black `#0B0B0B` / Onyx Charcoal `#1A1A1D` (+ Obsidian `#0B0F14` for deepest layers).
- **Hero accent (primary energy):** Lava Orange `#FF4D00` — brand mark, primary CTAs, the team's energy,
  active states. This is THE signature color, used boldly.
- **Depth:** Burnt Ember `#8B1E00` (hover/pressed, shadows, gradients off the orange).
- **Secondary vibrant accent:** Emerald Palace `#0A5E4E` / Royal Teal `#103F46` — the complementary pop that
  makes it feel young + interactive (growth, success, secondary highlights, variety so it's not mono-orange).
- **Neutral surfaces:** Volcanic Stone `#4A4746` (borders/muted) · subtle cool greys (Silver Mist/Glacier)
  for calm panels where needed.
- **Text / light surfaces:** Ash White `#F2F1EE` / Ivory Silk `#F2EDE1`.
- **Champagne Gold `#D8C08A` — RARE.** Tiny premium/success micro-moments only (a sparkle on approve, a
  badge). Never a primary or structural color.

Feel: bold orange energy + emerald counter-pop on a rich-black base, expressive characters, chunky friendly
interactive components, lively-but-purposeful motion. Think "alive Gen-Z command deck," not "luxury report."

> Alternates considered + rejected: DYNASTY (gold-led, too old-money) · OBSERVATORY (cool, less energetic).

### 7.3 Typography (2026 — fresh, NOT stale)
**Banned (overused/stale):** Inter, Roboto, Poppins, Montserrat, Helvetica, Open Sans, Lato.
**Use this pairing (all free — Fontshare/Google Fonts, easy in Lovable):**
- **Display / headlines:** **Bricolage Grotesque** — expressive, characterful, slightly quirky; reads
  young + premium. The signature voice. (Alt: **Clash Display** for a bolder, more confident feel.)
- **UI / body:** **Satoshi** — clean modern grotesque that pairs perfectly and stays legible at small sizes.
  (Alt: **General Sans** or **Hanken Grotesk**.)
- **Statement serif (hero / big-moment headlines only):** **Instrument Serif** — high-contrast editorial
  serif, very on-trend for one or two oversized lines (e.g. the landing hero). Use sparingly.
- **Avoid a "data/monospace telemetry" look** — it reads technical, which we hide (§4). If you ever need
  a number to feel deliberate, style it in the display face, not a terminal mono.
- Lean on **variable-font weight play** (light→black in one family) for expressive, modern hierarchy.

### 7.4 Character system (design pillar)
Each specialist gets an avatar with personality, an idle / working / done / needs-you state, and a signature
color drawn from the palette. The "factory floor" where you watch them work is the signature screen. Lean
into characterful, expressive, slightly playful illustration — Gen-Z, not corporate clip-art.

## 8. 3D / motion / animation (wanted — make it earn its place)
- **The team as living characters.** Avatars that visibly idle / think / work / wait. **Status as motion**,
  not a colored dot. This is the signature moment.
- **The Chief of Staff** — a focal character you talk to; reacts when thinking vs. answering.
- **The "factory floor"** — a scene where the owner watches the team at work; a finished piece travels
  up to the owner as a "needs you" card.
- **Hero / empty / transition moments** — smooth, premium; the approved card animates away with a sense
  of completion.

**Guardrails:** purposeful, smooth motion (ease, ~150–400ms); never gimmicky; respect
`prefers-reduced-motion`; stay **performant** on a laptop. Premium = restraint + a few wow moments.

## 8.5 App architecture — public face vs. behind the curtain
GRID CONTROL is **gated**. Two distinct surfaces:
- **Public (no login):** a **marketing landing page** that sells GRID CONTROL + a **login**. This is the
  only thing the world sees. It markets the *outcome* ("a full marketing department on autopilot") — it
  still respects §4 (no backend internals; sell the team + results, not the tech).
- **Private (paying clients only):** after login, the client enters their account — the COS, the team,
  the command deck (screens 0–7 below). **The actual product lives entirely behind the login.** A client
  only reaches it once they've paid and have an account.

So the very first build artifact is the **Landing → Login → (auth) → Onboarding/Command Center** flow.

## 9. The screens (their INTENT — design them however you like)

-2. **Public Landing Page (pre-login, marketing).** Sells the product to a prospective brand owner.
   Premium hero ("your AI marketing department, on autopilot"), the team/character metaphor as the
   emotional hook, outcomes + social proof, pricing/CTA → sign-up/login. **No app data, no backend, no
   client data.** This is the public face; make it gorgeous and on-brand (palette + characters). Lean on
   the reference galleries (§13) for landing/hero/navbar/CTA patterns.
-1. **Login / Auth.** Email/password (Supabase Auth → JWT). Clean, premium, fast. Gate to everything below.
   Wrong/no auth → never reveal app internals. (Sign-up may be invite/paid-only — a paid client gets access.)

0. **Onboarding (first screen AFTER login for a new account).** A **chat with the Chief of Staff**,
   not a form. ~6 guided steps that progressively build the brand profile, then **introduce the team and
   start the first piece of work** — so the owner *meets their company* and sees it come alive before
   reaching the deck. Use guided buttons + a few free-text fields. Arc:
   1. **Use case** — Personal Brand vs Company Brand.
   2. **Goals** — multi-select (content & social, SEO/AI-search, competitors, sales/conversion, growth plan).
   3. **About you / the brand** — website URL + a "what you do" free-text.
   4. **Connect your accounts** — curated set below (skippable; each an OAuth **Connect**).
   5. **Build your brand profile** — the COS synthesizes a profile; owner confirms/edits.
   6. **Meet your team + first task** — the COS introduces the relevant specialists (avatars come online)
      and kicks off a first real piece of work, shown as a character starting to work. **Never** show
      "provisioning an agent / running a subprocess" — show *a teammate rolling up their sleeves*.
   **Connections shown here (ONLY these):** **X, Facebook, Instagram, LinkedIn, YouTube,** and **Google
   (one connection = "full package")** = Gmail + Google Calendar + Search Console + Analytics together.
   Frame **Google Calendar as the post-scheduling engine** (scheduled posts become calendar events that
   drive phone reminders) — so Google is core, not optional.

1. **Command Center (home)** — *"Here's what your team did, and the one thing that needs you."* The daily
   decision moment + hero. The **"Needs You" approval queue** is the emotional center; each item is
   attributed to a character ("Your Writer drafted this").
2. **Content** — the plan over time (calendar) + work moving through the team. Feel of momentum. No
   pipeline mechanics — show *people handing work along*.
3. **Growth** — community replies, leads, funnel — all **drafted by a character, awaiting your yes**.
4. **The Team (factory floor)** — meet your specialists; watch them work. Where the character/avatar
   system shines. Tap a character → what they're working on, in human terms (no logs, no internals).
5. **Results** — proof it's working in **plain language** (reach, engagement, what's landing). **No cost/
   token panel.** Honest timestamps. This replaces the old "Insights/cost transparency" screen.
6. **Your Brand's Story** — the brand's living narrative ("here's who we've become"), document-like and
   owner-facing. Outcomes and decisions in plain English — **not** the system's internal memory/provenance.
7. **Connections / Settings** — platform status, brand profile, notifications. Light, utilitarian.

## 10. Non-negotiable product behaviors (design MUST respect)
1. **Approval gate is sacred.** Nothing publishes / sends without an explicit human approve. Every piece
   of work is a reviewable card with **Approve / Change / Reject**, attributed to a character.
2. **Backend stays invisible (see §4).** No models, costs, tokens, JSON, provenance, infra, or agent
   slugs anywhere in the client UI. Ever.
3. **Never render raw JSON.** Outputs arrive as pre-formatted **markdown** — render as rich text.
4. **The Chief of Staff is the one voice.** Natural-language chat drives intent; **destructive / publish
   actions still go through explicit buttons** (chat suggests, buttons commit).
5. **Brand switching is global** (top-level). All data is per-brand; the switcher reframes the whole app.
6. **"Live" honesty.** Metrics may come from the last run, not real-time — label with timestamps, never
   fake live.

## 11. The backend (FOR YOU, THE BUILDER — never shown to the client)
A real REST API exists and is **deployed and validated**. Wire to it after designing. **This data powers
the UI but is translated into human/character language for the owner — never shown raw.**

- **Base URL (prod):** `https://web-production-175d5.up.railway.app` — routes under `/api/*`.
- **Auth:** Supabase Auth (email/password) → JWT; send `Authorization: Bearer <jwt>`. FE env:
  `VITE_API_BASE`, `VITE_SUPABASE_URL`, `VITE_SUPABASE_ANON_KEY`.
- **Brand scope:** every data call takes `?brand_slug=<slug>`. The brand switcher drives it.
- **Envelope:** most endpoints return `{ success, data }`; a few (`/api/auth/*`, `/api/brands`) return
  bare shapes — handle per-endpoint.
- **Live updates:** `GET /api/events` is a Server-Sent-Events stream (work status, approvals) — use it to
  animate characters, **without** exposing any technical detail it carries.

**Endpoints per screen (translate everything into character/outcome language):**
| Screen | Primary endpoints |
|---|---|
| Onboarding | `POST /api/auth/create-brand` · `POST /api/brand/profile` · connect-token per platform · `POST /api/agents/run` (first task) |
| Command Center | `GET /api/brand/summary` · `GET /api/brands/<slug>/needs-you` |
| Approve / Change / Reject | `POST /api/outputs/approve` · `/reject` · `/revise` |
| The Team (factory floor) | `GET /api/agents/list` · `GET /api/agents/status` · `POST /api/agents/run` → **map slugs/models to character names + human states; never display the raw fields** |
| Content (calendar) | `GET /api/dashboard-output` → `data.calendar_formatted` |
| Results | derive from run outputs/metrics → **plain-language only; do NOT use `/costs` in the client UI** |
| Your Brand's Story | `GET /api/brands/<slug>/narrative` → render as owner-facing story, strip any internal/provenance lines |
| Connections | `GET /api/brands/<slug>/connections` (never returns tokens). Curated set only (see §9.0). |
| Chief of Staff (chat) | `POST /api/concierge` — returns intent + points to the gated button; never auto-executes |

> Cost/usage endpoints (`/api/brands/<slug>/costs`) exist for **our internal ops only** — **do not wire
> them into the client UI.**

## 12. Build approach
1. **Design first against mock data** matching the shapes above. Make it beautiful, characterful, and
   alive before wiring anything.
2. **Then wire** screen-by-screen to the real endpoints; add auth + brand switching; **translate every
   technical field into character/outcome language at the boundary.**
3. **Stack:** your call (reference app is React + Vite + Tailwind + shadcn, but this is a fresh build).

## 13. Design references (owner-provided inspiration galleries)
Curated showcase galleries — mine them for patterns (premium hero/landing structure, navbar, CTA,
rebrand systems, motion/3D-forward trends). **Do not copy any 1:1** — synthesize something uniquely *ours*.

- **Landing / website systems:** fountn.design/design-resources · craftwork.design/curated/websites ·
  landing.love · saaspo.com
- **Components:** navbar.gallery (nav patterns) · cta.gallery (CTA patterns)
- **Brand systems:** rebrand.gallery (cohesive rebrand/identity references)

Trend signal observed: heavily motion/3D-forward premium SaaS — aligns with our living-character /
factory-floor ambition (§2, §8). Apply: a premium sticky navbar, a strong outcome-led hero, bold single
primary CTA, and restrained but present motion.
