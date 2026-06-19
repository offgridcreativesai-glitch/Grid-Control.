# AI Setter System — Deep Study + Build Plan

> Source: FitProCEO Setter Guide.pdf (6 pages)
> Studied: Jun 6, 2026
> Purpose: Implement for AskGauravAI + all OffGrid social handles

---

## WHAT THIS IS

An **AI-powered Instagram DM automation system** that replaces human "setters" (people who qualify leads via DMs and book calls). The system uses:

- **ManyChat** — automation platform that triggers on Instagram comments/keywords
- **Claude API** — powers the actual DM conversation (qualification, objection handling, booking)
- **Instagram Business/Creator Account** — connected to Facebook Page for API access

### The Flow
1. User comments a **keyword** on a post/reel (e.g., "GUIDE", "INFO", "FREE")
2. ManyChat triggers → sends a **public reply** (3-4 variations to feel organic)
3. ManyChat sends a **private DM** powered by Claude
4. Claude runs the full qualification conversation: voice/tone match, offer presentation, objection handling, CTA (book call / purchase link / application form)
5. All automatic, 24/7, 3-second response time, ~$0.05 per full conversation

### Why It's Powerful
- Human setter: $300-600/month + management + turnover risk
- AI setter: $10-20/month even handling hundreds of leads — **95% cheaper**
- Never misses a message, never forgets follow-up, runs forever once configured

---

## 6-PART SETUP (from the PDF)

### Part 1 — Create ManyChat Account & Connect Instagram
1. Go to manychat.com, sign in with IG Business/Creator account
2. Authorize Instagram access (send/receive DMs on your behalf)
- Requirement: IG must be linked to a Facebook Page

### Part 2 — Get Claude API Key
3. Visit console.anthropic.com → API Keys → Generate Key
4. Copy and store securely (shown only once)
- Cost: ~$0.05 per full lead qualification conversation

### Part 3 — Connect Claude to ManyChat
5. ManyChat → Settings → Integrations → find Claude AI option
6. Paste API key → ManyChat verifies automatically

### Part 4 — Build the DM Automation Flow
7. Automation tab → New Automation → Start From Scratch
8. Set trigger: "User comments on your Post or Reel" → define keyword → apply to specific or any post
9. Add public reply (optional): 3-4 variations so it feels organic
10. Configure Claude DM response: Add Send Message block → insert Action block → select Claude

### Part 5 — Write the Prompt (THE MAGIC)
The prompt has 5 components:
- **Voice & Tone** — slang, energy, sentence length. AI mirrors this exactly.
- **Your Offer** — programs, pricing tiers, payment options, current promos.
- **Qualification Flow** — scripted questions to separate browsers from buyers.
- **Objection Handling** — feed it your most common pushbacks + how you overcome them.
- **Call to Action** — the next step: book a call, purchase link, application form.

**Pro Tip:** Paste your best real DM conversations into the prompt. Include exact words you use when a lead says they can't afford it or need to think. Claude learns your patterns and replicates with scary accuracy.

### Part 6 — Launch and Test
11. Click Set Live → comment on your own post with the trigger keyword → verify DM arrives naturally → have 3-4 friends test and refine the prompt

---

## PRICING REALITY

| Component | Cost |
|-----------|------|
| ManyChat Free | 25 contacts, 3 keywords, 4 automations |
| ManyChat Pro | $15/mo (500+ contacts) |
| Claude API | ~$0.05 per full conversation ($3/M input, $15/M output tokens) |
| **Total AI setter** | **$10-20/month** |
| Human setter comparison | $300-600/month + taxes + management + turnover |

---

## ADVANCED TIPS (from the PDF)

1. **Use best conversations as training data** — paste highest-converting DM threads into prompt
2. **Test with 3-4 friends before going wide** — watch how Claude handles it
3. **Create 3+ public reply variations** — rotating responses feel human
4. **Monitor conversations first 2 weeks** — identify missed opportunities, refine prompt
5. **Scale with ManyChat Pro** — upgrade when past 25 contacts

---

## HOW WE ADAPT THIS FOR ASKGAURAVAI + ALL HANDLES

### The Opportunity
This is NOT just a fitness coaching tool. This is a **universal lead qualification + DM sales system** that works for ANY business with an Instagram presence. For Gaurav's brands:

### AskGauravAI (Primary — personal brand)
- **Trigger keywords on reels/posts:** "REPORT", "AUDIT", "FREE", "AI", "STRATEGY"
- **What Claude does in DMs:**
  1. Greets with Gaurav's founder-to-founder voice
  2. Asks what brand they run + their biggest ad/content challenge
  3. Qualifies: are they D2C/ecom? Running or about to run ads?
  4. Presents the right offer: Reporting SaaS (Rs.2,500-6,999) for intelligence, Grid Control services (Rs.15-50k) for full execution
  5. Handles objections (price, timing, "I'll think about it")
  6. CTA: sends report purchase link OR books a strategy call
- **Voice:** Direct, no-BS, capital-builder. Not salesy. Founder helping founder.

### OffGrid Creatives AI (Reporting SaaS brand)
- **Trigger keywords:** "REPORT", "INTEL", "AUDIT", "PRICE", "HOW"
- **Claude DM flow:**
  1. Acknowledges their interest
  2. Asks about their brand category + whether they're pre-launch or running ads
  3. Explains what the report delivers (10 sections of real scraped intelligence)
  4. Handles price objections (early access Rs.2,500 vs strategy consultant Rs.50k+)
  5. CTA: direct purchase link or sample report

### Cross-Handle Setup (ALL platforms)
- Instagram: ManyChat + Claude (native integration exists)
- LinkedIn: No ManyChat equivalent — use Grid Control's dm-customer-hunter agent (Agent 14) for manual-approval DM flows
- X/Twitter: No ManyChat equivalent — same agent-based approach
- YouTube: Comment replies only (no DM system) — use community-manager agent

---

## MONDAY BUILD PLAN

### Phase 1: AskGauravAI Instagram AI Setter (Day 1 — Monday Jun 9)
**Goal:** Live AI setter on @askgauravai IG by end of day

| Step | Task | Time | Owner |
|------|------|------|-------|
| 1 | Create ManyChat account, connect @askgauravai IG | 15 min | Gaurav |
| 2 | Get Claude API key (or use existing from console.anthropic.com) | 5 min | Gaurav |
| 3 | Connect Claude to ManyChat via Integrations | 5 min | Gaurav |
| 4 | Build first automation: trigger = comment keyword "REPORT" on any post | 10 min | Gaurav |
| 5 | Write the Claude prompt (Claude Code drafts, Gaurav approves) | 30 min | Claude Code + Gaurav |
| 6 | Add 3-4 public reply variations | 10 min | Claude Code drafts |
| 7 | Test with 3-4 friends | 15 min | Gaurav |
| 8 | Go live | — | Gaurav |

### Phase 2: Expand Keywords + Flows (Day 2 — Tuesday Jun 10)
- Add trigger keywords: "FREE", "AI", "STRATEGY", "AUDIT", "HOW"
- Create separate automation flows for different intent levels
- Build follow-up sequences (if lead goes cold after 24h)

### Phase 3: OffGrid Creatives AI IG Setter (Day 3 — Wednesday Jun 11)
- Same ManyChat + Claude setup for @offgrid.creatives handle
- Different prompt (product-focused, not personal brand)
- Keywords: "REPORT", "INTEL", "PRICE"

### Phase 4: Prompt Refinement (Week 1 ongoing)
- Monitor all DM conversations
- Identify where Claude drops the ball
- Feed winning conversations back into prompt
- A/B test different qualification flows

### Phase 5: LinkedIn + X Integration (Week 2)
- LinkedIn: Wire dm-customer-hunter (Agent 14) with similar qualification logic
- X: Same approach via Agent 14
- These won't use ManyChat — they'll use Grid Control's existing agent infrastructure

---

## WHAT CLAUDE CODE PREPARES FOR MONDAY

1. **Draft the AskGauravAI setter prompt** — Gaurav's voice, offer stack, qualification flow, objection handling, CTA. Ready for paste into ManyChat.
2. **Draft 4 public reply variations** — for the comment trigger responses.
3. **Draft the OffGrid Creatives AI setter prompt** — product-focused version.
4. **Document the ManyChat setup steps** with screenshots for Gaurav to follow.

---

## INTEGRATION WITH EXISTING GRID CONTROL AGENTS

This AI Setter system is NOT a replacement for existing agents — it's a **new layer**:

| Existing Agent | Role | AI Setter Relationship |
|----------------|------|----------------------|
| Agent 13 (Community Manager) | Replies to comments/DMs | AI Setter handles the SALES DMs; Community Manager handles non-sales engagement |
| Agent 14 (DM Customer Hunter) | Finds + DMs prospects | AI Setter handles INBOUND; Agent 14 handles OUTBOUND prospecting |
| Agent 7 (Funnel Specialist) | Conversion journey design | AI Setter is a new funnel entry point — Funnel Specialist designs the post-DM journey |
| Agent 12 (Email Marketing) | Nurture sequences | Leads qualified by AI Setter feed into email nurture |

The AI Setter becomes the **top-of-funnel DM capture layer** — it catches inbound interest from content, qualifies, and routes to the right next step.

---

## POSTIZ — SELF-HOSTED SOCIAL MEDIA SCHEDULING (Added Jun 6)

> Source: github.com/gitroomhq/postiz-app (31.5K stars, AGPL-3.0)
> No feature difference between SaaS and self-hosted.

### What It Is
Open-source social media scheduling tool with AI features, analytics, team collaboration, and API/webhook support. Supports: Instagram, LinkedIn, YouTube, X, TikTok, Threads, Reddit, Pinterest, Facebook, Slack, Discord, Mastodon, Bluesky.

### Tech Stack
Next.js + NestJS + PostgreSQL + Prisma + Redis + Temporal. TypeScript monorepo.

### Deployment: Hetzner Cloud VPS
- **Server:** CX22 (2 vCPU, 4GB RAM, 40GB SSD) — €4.35/month (~$5)
- **Method:** Docker Compose (ships with the repo)
- **SSL:** Nginx reverse proxy + Let's Encrypt
- **Domain:** subdomain of askgauravai.com or offgridcreatives.ai
- **Backups:** Automated daily PostgreSQL dumps

### Why Not Railway
Postiz needs 4+ services (app, API, PostgreSQL, Redis, workers). Railway charges per service per hour — expensive and fighting the container model. Docker Compose on a VPS is what Postiz is designed for.

### Integration with Grid Control
- Grid Control agents CREATE content → approved content
- Postiz PUBLISHES on schedule across all platforms
- ManyChat + Claude AI Setter captures INBOUND leads from posts
- Grid Control agents NURTURE qualified leads (email, DM, funnel)

```
CONTENT CREATION (Grid Control agents)
        ↓ approved content
PUBLISHING (Postiz — self-hosted VPS)
        ↓ posts go live on IG/LinkedIn/YouTube/X
INBOUND CAPTURE (ManyChat + Claude AI Setter)
        ↓ qualified leads
NURTURE (Grid Control Agent 12 email + Agent 14 DM)
```

### Monday Build Plan — Postiz Setup (alongside AI Setter)

| Step | Task | Time | Owner |
|------|------|------|-------|
| 1 | Create Hetzner Cloud account + CX22 VPS | 10 min | Gaurav |
| 2 | SSH into VPS, install Docker + Docker Compose | 15 min | Claude Code guides |
| 3 | Clone Postiz repo, configure .env | 15 min | Claude Code |
| 4 | `docker compose up -d` — all services start | 5 min | Claude Code |
| 5 | Set up Nginx + SSL on custom subdomain | 15 min | Claude Code |
| 6 | Connect AskGauravAI social accounts (IG/LinkedIn/YouTube/X) | 20 min | Gaurav |
| 7 | Connect OffGrid Creatives AI social accounts | 15 min | Gaurav |
| 8 | Test: schedule a post from Postiz → verify it publishes | 10 min | Both |
| 9 | Set up API integration point for Grid Control | 30 min | Claude Code |

### What This Replaces
- Our hand-built publishers (publishing/ig_publisher.py, linkedin_publisher.py, etc.)
- Manual cron-based publish_runner.py scheduling
- The need for per-platform OAuth token management in our code (Postiz handles this)
- We keep publishers as FALLBACK but Postiz becomes primary

---

## OBSIDIAN + GRAPHIFY — MEMORY & KNOWLEDGE LAYER (Added Jun 6)

> Decision basis: docs/GRAPHIFY_VS_OBSIDIAN_RESEARCH.md
> Obsidian = shared knowledge/memory for Gaurav + agents + Claude Code.
> Graphify = on-demand code X-ray (run on code changes, not always-on).
> Both committed — BUT commitment enforced by HOOKS, not by Claude remembering.

### The Enforcement Principle (why this won't go stale like graphify did)
A verbal promise from Claude failed before because each session starts cold.
The fix: the harness enforces usage automatically. Claude's memory is NOT the
mechanism. Three layers:

1. **SessionStart hook** — auto-runs every session. Reads Obsidian vault memory +
   reminds to query graphify before touching code. Harness-executed, unforgettable.
2. **CLAUDE.md hard rule** — short blunt rule at top of project CLAUDE.md:
   "Obsidian vault = memory source of truth. Read on start, write on every decision.
   Run graphify on code changes." Loads into context every session.
3. **PostToolUse / Stop hook** — after code edits, nudges `graphify update`. After a
   decision is written, nudges an Obsidian vault note.

### Monday Build Plan — Obsidian + Graphify

| Step | Task | Owner |
|------|------|-------|
| 1 | Install Obsidian app on Mac | Gaurav |
| 2 | Create vault pointing at our existing memory dir (already markdown + [[wikilinks]]) | Claude Code |
| 3 | Install Local REST API & MCP plugin (FREE — skip Smart Connections $20/mo) | Claude Code guides |
| 4 | Wire the Obsidian MCP server into Claude Code (.mcp.json) | Claude Code |
| 5 | Give agents read/write access to vault via the MCP | Claude Code |
| 6 | Install core free plugins: Dataview, obsidian-git, Templater, Tasks | Claude Code guides |
| 7 | Write SessionStart hook (reads vault, reminds graphify) | Claude Code |
| 8 | Write PostToolUse hook (graphify update on code change) | Claude Code |
| 9 | Add the hard rule to project CLAUDE.md | Claude Code |
| 10 | Refresh graphify graph once (it's stale since May 28) | Claude Code |
| 11 | Verify: new session auto-reads vault + graphify nudge fires | Both |

### What Stays Free
- Obsidian app: free (personal use)
- Local REST API + MCP plugin: free
- Dataview / Templater / Git / Tasks: free (open source)
- Graphify: free (AST, no API cost)
- Smart Connections ($20/mo): SKIPPED until semantic recall is proven necessary

### Division of Labour (locked)
- **Obsidian** answers: brand state, past outputs, decisions, memory, "what did we decide about X"
- **Graphify** answers: code structure, "what writes trends_live.json", dependency tracing
- Never confuse the two. Obsidian for knowledge, Graphify for code.
