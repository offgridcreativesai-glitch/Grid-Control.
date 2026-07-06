# GRID CONTROL — Dashboard Design Prompt (for Lovable / Claude Design)

> Paste everything below the line into Lovable or Claude Design. Design/prototype ONLY — mock data,
> no backend, no auth, no API. Goal = a clickable visual preview of all sections to review.

---

Design a **dark, premium "command center" web dashboard** called **GRID CONTROL** — an AI marketing
operating system where a team of AI agents runs a brand's social media, and the owner reviews and
approves their work each morning. Think "calm cockpit / Chief of Staff," not a busy analytics tool.
The owner is a non-technical founder; clarity beats density.

## Design system
- **Theme:** dark only. Background `#0b0d10`, panels `#13161b`, panel-2 `#171b21`, hairline borders `#232831`.
- **Text:** primary `#e8ebef`, muted `#8b94a3`, faint `#5c6573`.
- **Accent (brand = "askgauravai"):** coral `#ff6a4d` (primary actions), coral-soft `rgba(255,106,77,.12)`.
- **Status colors:** green `#3ecf8e` (healthy / up), amber `#f5b544` (decisions / attention), red `#ff5d6c` (down / errors), blue `#5b9dff`.
- **Type:** system sans (SF/Inter). Tight headings (-0.3px tracking), generous line-height in body.
- **Shape:** card radius 14px, controls 9–10px. Subtle 1px borders, no heavy shadows. Thin sparkline bars, small pill badges.
- **Feel:** lots of breathing room, max content width ~1080px centered, soft gradients only on spotlight/decision cards.

## App shell (every page)
- **Left rail (64px):** square coral "G" logo at top; vertical icon nav — Today (active), Calendar, Insights, Agents, Connections; Settings pinned to bottom. Active item = coral-soft background + coral icon.
- **Top bar (60px):** left = brand switcher chip (rounded square brand avatar + "askgauravai" + caret, clickable dropdown). Right = green "All agents healthy" pill (live dot) + date/time ("Tue, 9 Jun · 8:42 AM").

---

## PAGE 1 — TODAY (the daily surface, default screen) ★ most important
A vertical scroll, three blocks:

**1. Greeting + brief line**
- "Morning, Gaurav." + muted "Here's what the team did overnight."
- One summary line: "Drafted **3 posts** for your yes/no · **1 decision** needs you · research refreshed across **5 competitors**." (Decision word in coral.)

**2. Brand Health — section label "BRAND HEALTH · this week"**
- Row of 4 metric cards: **Followers** 2,341 (▲+38), **Engagement rate** 6.2% (▲+0.8%),
  **Saves / post** 47 (▲+12) — this one is SPOTLIGHTED (coral-tinted gradient border, a ★) because it's the key KPI,
  **Reach this week** 18.4k (▲+22%).
- Each card: label, big number, small green/red change, a tiny 7-bar sparkline.
- (Note: cost/spend does NOT live here — it's on the Insights page.)

**3. Needs you — section label "NEEDS YOU · 4 items"**
A single unified queue mixing two card types, each with a leading badge:
- **● Decision** badge (amber) — a strategic direction choice with NO content yet. Example card:
  Trend Sentinel · PIVOT — "'AI ad fatigue' is spiking +240% this week. Ride the trend with a reactive post, or stay on the planned arc?" Two buttons: **Ride the trend** (amber) / **Stay on arc** (ghost). Amber-tinted card.
- **● Approve** badge (coral) — a finished draft awaiting yes/no. Each card has:
  - a **real visual preview thumbnail** on the left (~84px): for a carousel show the first slide artwork, for a reel show a video cover frame with a small ▶ overlay, for a text post show a rendered post card. Use realistic mock visuals, not icons.
  - platform tag (Instagram / Reel / LinkedIn), format tag (Carousel · 7 slides / 0:34 / Text post), and which agents made it.
  - title + 1-line description + a muted "Why this:" reasoning line.
  - action buttons (right, stacked): **Approve** (coral solid), **Change** (ghost), **Preview**/**Publish now** (green outline). The reel card shows a "Founder voice required" flag and an "Approve script" button instead of Approve.
  3 approve cards: IG carousel "3 Meta ad mistakes quietly burning your budget"; Reel "Why your CPM doubled in 2 weeks"; LinkedIn "The ad metric everyone reads wrong".

**4. Overnight activity** — a dashed-border strip: "Trend Researcher scraped 5 competitors · Script Writer drafted 3 · Carousel Designer rendered 2 · Data Analyst pulled IG insights · Brand Guardian soul-checked all · 0 errors."

---

## PAGE 2 — CALENDAR
- Month grid (current month). Each day cell shows small colored chips for scheduled/published/draft posts (coral=draft, green=published, amber=needs approval).
- Right side or top: a toggle for Month / Week. A legend. Clicking a day opens a side panel listing that day's posts with thumbnails + status. Show a realistic spread across the month.

## PAGE 3 — INSIGHTS (analytics + cost lives here)
- Top: 4 KPI tiles (Reach, Engagement, Saves, Follower growth) with trend lines.
- A larger line chart: "Engagement over 30 days."
- A "Top performing content" list: 3–4 posts ranked, each with thumbnail, platform, saves/reach, and a small "repurpose" action.
- **Cost & usage panel** (this is where weekly spend belongs): a card showing "This week ₹1,840" broken down by source (Anthropic API, FAL media, scraping) as a small bar/stacked breakdown, and a per-agent cost mini-table. Keep it calm, not alarming.

## PAGE 4 — AGENTS
- A grid of agent cards (the team). Each: agent name (e.g. Trend Researcher, Script Writer, Carousel Designer, Creative Director, Data Analyst, Brand Guardian, Community Manager, DM Hunter), a role one-liner, a status dot (idle / running / needs-input), last-run time, and a tiny "runs this week" count.
- Clicking a card → an **Agent detail** view: what it does, its recent runs (list with timestamps + outcome), and its latest output preview. One agent shown mid-run with a live "running…" state.

## PAGE 5 — CONNECTIONS
- A list of platforms (Instagram, LinkedIn, YouTube, X) each as a row/card: platform logo, connected account handle, a green "Connected" or grey "Not connected" status, last-verified time, and a "Manage"/"Reconnect" button. Never show tokens. Cockpit styling consistent with the rest.

## PAGE 6 — SETTINGS (light)
- Simple sections: Brand profile, Notifications (toggle: morning brief via email/WhatsApp), Trust dial (a single slider per brand: "Ask me everything" → "Full autopilot" — just the control, visual only), Team/members. Keep minimal.

---

## Interactions (visual only, no real logic)
- Hover states on all buttons/cards. Active nav highlighting. Brand switcher opens a dropdown with 2–3 brands (askgauravai, offgrid-creatives-ai, dropvolt).
- The "Needs you" cards can visually dismiss/animate out on Approve (optimistic), but no data persistence needed.

## Tone of all copy
Founder-to-founder, plain, confident, zero corporate fluff. Short. The app speaks like a sharp chief of staff: "Here's what we did, here's what needs you, here's the one call only you can make."

## Deliver
A responsive (desktop-first) multi-page prototype with the left-rail navigation switching between the 6 pages above, all populated with realistic mock data for "askgauravai" (an AI/Meta-ads strategist personal brand). Dark, premium, calm. **Design only — no backend.**
