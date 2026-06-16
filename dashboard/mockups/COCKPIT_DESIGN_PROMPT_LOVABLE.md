# GRID CONTROL — Cockpit Front-End Prompt (for Lovable)

> Paste everything below the line into Lovable as your first message.
> This builds a **design-only, mock-data** prototype (React + Tailwind + shadcn) — NO backend, NO auth,
> NO Supabase, NO API calls. We wire it to the real Flask + Supabase backend later. Goal: a clickable,
> premium multi-page cockpit you can click through and react to.

---

Build a **premium, dark "agentic command center" web app** called **GRID CONTROL** — an AI marketing
operating system where a team of AI agents runs a brand's social media / marketing, and the owner reviews,
directs, and approves their work from one organized cockpit. The user is a **non-technical founder**: it must
feel systematic, calm, and in-control — every function has a clearly named home, and you can SEE the team
working. Think "a sharp founder's command deck," not an engineer's tool.

**Tech + scope rules for this build:** React + Tailwind + shadcn/ui, react-router for the pages, lucide
icons, recharts for sparklines/charts. **Design only — mock data hard-coded in the front-end. Do NOT add a
backend, database, auth, or Supabase. Do NOT make network/API calls.** Desktop-first, responsive.

## VISUAL IDENTITY (this exact blend — warm + precision + luxe)
- **Base:** warm near-black. Bg #0d0c10, panels #16141a, panel-2 #1c1922, hairline borders #2a2630.
- **Text:** warm white #f0ece6, muted #9a93a3, faint #6b6470.
- **Primary accent:** coral #ff6a4d (actions, active nav, key highlights).
- **Luxe accent:** muted gold #d8b478 (decisions, premium / "needs attention" highlights).
- **Status:** green #4ad99a (working/up), gold #d8b478 (waiting/decision), faint grey (idle), red #ff5d6c (down/error).
- **Type:** editorial serif for big page headlines (Fraunces or Spectral); clean sans (Inter) for body/UI;
  **monospace (JetBrains Mono) for ALL numbers, metrics, model names, run counts, costs, timestamps** —
  this gives the "precision instrument" feel.
- **Cards:** soft glassmorphism (subtle top-lit gradient + 1px hairline), rounded 16px, generous padding,
  lots of whitespace (calm luxe). Thin sparklines. Small pill badges. Subtle, no heavy shadows.
- **Feel overall:** warm charcoal + coral, calm and airy, crisp mono data — premium and unmistakably its
  own (must NOT look like a generic cool-navy/blue dashboard).

## APP SHELL (every page)
- **Left nav rail (~220px, icon + LABEL — named sections):** Command Center, Content, Growth, The Team,
  Insights, Memory & Brain. Pinned bottom: Connections, Settings. Active item = coral-tinted background +
  coral icon/label.
- Below the nav, a **live "Your Team" mini-list:** 6 role rows, each with a colored status dot
  (working/waiting/idle) — so the team always feels alive in the periphery.
- **Top bar:** left = brand switcher chip (brand avatar + "askgauravai" + caret → dropdown: askgauravai /
  offgrid-creatives-ai / dropvolt). Center = a slim **command box** ("Tell your team what to focus on…" with
  "Allocate" + "Queue" buttons — visual only). Right = green "System operational" pill + live clock.

## PAGE 1 — COMMAND CENTER (home, most important). Vertical scroll, in this order:
1. **Headline + brief** — big editorial serif "Growth ops." + muted "Here's what your team did overnight."
   Then one summary line (mono numbers): "Drafted **3** posts for approval · **1** decision needs you ·
   research refreshed across **5** competitors · spend today **₹340**."
2. **NEEDS YOU** (the hero — the morning brief as a unified action queue). One list, two card types w/ badges:
   - **● Decision** (gold) — a strategic choice, no content yet. Card: "Trend Sentinel flagged a PIVOT —
     'AI ad fatigue' spiking +240% this week. Ride it with a reactive post, or stay on the planned arc?"
     Buttons: "Ride the trend" (gold) / "Stay on arc" (ghost).
   - **● Approve** (coral) — a finished draft. Each card has a **visual preview thumbnail** (carousel = first
     slide art; reel = video cover frame with ▶; post = rendered card), platform tag, format tag, which role
     made it, title, 1-line desc, a muted "Why this:" reasoning line, and buttons: Approve (coral) / Change
     (ghost) / Preview or Publish (green outline). 3 cards: IG carousel "3 Meta ad mistakes quietly burning
     your budget"; Reel "Why your CPM doubled in 2 weeks" (shows "Founder voice required" flag + "Approve
     script"); LinkedIn "The ad metric everyone reads wrong".
3. **BRAND HEALTH · this week** — 4 glass metric cards, all with a small green **"LIVE"** badge (auto-tracked,
   real-time): Followers 2,341 (▲+38); Engagement 6.2% (▲+0.8%); **Saves/post 47 (▲+12) — SPOTLIGHTED** with
   coral-tint border + ★ (key KPI); Reach 18.4k (▲+22%). Big mono numbers + 7-bar sparklines. (No cost here —
   cost lives on Insights.)
4. **YOUR TEAM · today** — 6 role cards (the business-role abstraction). Each card: role name, a 1-line "what
   they do", a status dot + label, and a mono footer row: **runs today · model · cost today**:
   - Chief of Staff — "Routes work, reviews everything, briefs you." · working · Opus 4.8 · 12 runs · ₹110
   - Head of Strategy — "Market signals, trends, the plan." · researching · Sonnet 4.6 · 8 runs · ₹40
   - Creative Director — "Scripts, carousels, reels, brand voice." · drafting · Sonnet 4.6 · 14 runs · ₹120
   - Head of Growth — "Community, DMs, funnel, email." · waiting · Sonnet 4.6 · 6 runs · ₹30
   - Data Analyst — "Performance + signal, no guessing." · idle · pure-math · 22 runs · ₹0
   - Web & Tech — "Site, SEO, plumbing." · idle · Sonnet 4.6 · 2 runs · ₹40
5. **Overnight activity** — a dashed-border strip, mono: "Head of Strategy scraped 5 competitors + cached ·
   Creative Director drafted 3 · Data Analyst pulled live IG insights · Chief of Staff soul-checked all · 0 errors."

## PAGE 2 — CONTENT
Month calendar grid; day cells show colored post chips (coral=draft, green=published, gold=needs approval).
Month/Week toggle + legend. Click a day → side panel of that day's posts with thumbnails + status. A second
tab "Pipeline" = a kanban (Idea → Drafting → Needs approval → Scheduled → Published) with content cards.

## PAGE 3 — GROWTH
Three columns: Community (incoming comments/DMs to reply, each with a drafted reply + Approve/Edit), Lead
Pipeline (prospects scored by ICP fit 1–10 with status), Funnel & Email (opt-in stats + nurture sequence
drafts). All "manual approval in the loop." Mock data for an AI / Meta-ads strategist brand.

## PAGE 4 — THE TEAM
Default view = the **6 business roles** as rich cards (status, what they do, runs, model, **cost**, last run,
recent outputs). A toggle **"Advanced (18 agents)"** top-right that expands each role into its underlying
specialist agents (e.g. Creative Director → Script Writer, Creative Director, Carousel Designer, Brand
Guardian). Clicking any → detail: description, recent runs list (mono timestamps + outcome), latest output
preview, and a small per-agent cost chart. Show one role mid-run ("working…").

## PAGE 5 — INSIGHTS (analytics + the COST story — our signature)
KPI tiles (Reach, Engagement, Saves, Follower growth) with trend lines; a 30-day engagement line chart; "Top
performing content" ranked list (thumbnail + saves/reach + "repurpose"). Then a prominent **COST & TOKENS**
panel — "This week ₹1,840" with a breakdown by source (Claude API, FAL media, scraping) AND a per-role /
per-agent cost table with token counts. Make this transparent and calm — it's the thing users always ask
("how many tokens does it spend?") and we answer it clearly.

## PAGE 6 — MEMORY & BRAIN
A readable timeline of the brand's "story so far" — append-only entries the team wrote (decisions, actions,
results) with mono timestamps and the role that wrote each. A left filter by role/type. A search box. Top: a
short "What the system knows about this brand" summary card (positioning, audience, what's working). This is
the persistent brain made visible — calm, document-like, premium.

## Connections + Settings (light)
Connections: rows for Instagram / LinkedIn / YouTube / X — logo, account handle, green "Connected" / grey
"Not connected", last-verified time, Manage/Reconnect. Never show tokens. Settings: Brand profile,
Notifications (morning brief via email/WhatsApp toggle), **Trust Dial** (one slider: "Ask me everything" →
"Full autopilot", visual only), Team/members.

## INTERACTIONS (visual only)
Hover states everywhere; active nav highlight; brand switcher dropdown; "Needs you" cards animate out on
Approve; "Advanced (18 agents)" toggle expands/collapses. No data persistence needed.

## TONE OF COPY
Founder-to-founder, plain, confident, zero corporate fluff. The app speaks like a sharp chief of staff:
"Here's what we did, here's what needs you, here's the one call only you can make."

## DELIVER
A responsive, desktop-first, multi-page prototype with the left-rail nav switching all 6 pages (+ Connections,
Settings), fully populated with realistic mock data for "askgauravai" (an AI / Meta-ads strategist personal
brand). Premium, warm-dark, calm, mono-precise data. **Design only — no backend, no API, no auth.**
