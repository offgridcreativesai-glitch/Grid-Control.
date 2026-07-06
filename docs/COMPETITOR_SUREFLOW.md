# Competitor Teardown — Sureflow Systems (seanpurvis.ai)

> Studied Jun 9 2026 via IG (@seanpurvis.ai, 7,596 followers, 13 posts) + site info.sureflowautomation.com.
> Screenshots captured from his reels (saved this session). He is building the SAME thing we are.

## Who / offer
- **Sean Purvis**, founder of **Sureflow Systems**. "I build and install Agentic Systems for Business
  Owners doing $20k+/month."
- Site headline: **"Your Agentic Growth System that autonomously scales your business."**
- Sells *installed infrastructure you own*, not a SaaS subscription, not an agency retainer.
  Positions against agencies (templates), contractors (voice off), generic AI tools (still your time).
- Claims: 40h→8h, "3x efficiency," "month 6 better than month 1." Min $2k/mo revenue to qualify.
- Funnel: IG link-in-bio → 2-min application → 30-min discovery call. **Custom pricing, none shown.**

## His system = "Sureflow Agentic OS" (6 agents)
Hook image across reels: **"CLAUDE CODE + Obsidian = 6 Agent Agentic OS."** Built on Claude Code + Obsidian.
- **CEO / Orchestrator** (Command Layer) — routes work, reviews context, returns "operator debrief."
- **CMO** (Content + Market Voice) — stage-aware posts, hooks, platform versions.
- **Researcher / Market Research Analyst** (Intel) — competitor moves, trend signals, market language.
- **Sales Development Rep** (Lead Qualification) — scores replies/comments for ICP fit + buying stage.
- **Account Executive** (Outbound Follow-up) — drafts personalized DM follow-ups, manual approval in loop.
- **Business Analyst** (Performance Reporting) — turns perf data into weekly reporting + next actions.
- (Dev/Build agent also shown in one cut — builds dashboards/integrations.)

## Dashboard UI (from reel screen-recordings)
- Dark, premium. Left nav: **Command Center · Content Pipeline · Lead Pipeline · Agent Console ·
  Analytics · Knowledge Vault**. Below: live AGENTS list with waiting/working/idle status dots.
- **Command Center "Growth ops"** = 4 metric cards (Posts This Week 5, Active Leads 47, Calls Booked 11,
  Follow-Up Emails Sent 120) + "Chat with an agent" row + "Needs Review" queue + "Primary Workflows."
- **Agent Network** view = orchestrator card + 5 specialist cards, each showing ROLE, description,
  **and the MODEL it runs** (gpt-5.5, gemini-2.5-pro, claude-sonnet-4 in one cut; Claude Sonnet/Haiku/
  Opus-4.7 in another) + **run counts** per agent. "Agentic System Operational" + live clock.
- **Agent Console "Allocate work"** = a command box ("Assign the next highest-leverage task to each
  specialist agent") → **Allocate work / Queue Command** buttons.

## What this VALIDATES in our plan
1. **Per-agent model routing** (our Phase D LiteLLM gateway) — he routes a different model per agent and
   *shows the model badge in the UI.* Multi-model is real, not over-engineering.
2. **Orchestrator + specialists + approval-in-the-loop** — same spine as ours.
3. **Knowledge Vault = persistent memory** — he ships memory as a first-class surface (our Phase A).
4. **Chat-drives-intent + buttons-guard-actions** — his command box + Needs Review = our exact hybrid.
5. **Demand is hot** — comments flooded with "I want to learn," "Help," "Sent," "how does it work,"
   and "this is the exact architecture I'm building." Big, validated market.

## His WEAKNESSES = our wedges
1. **His metrics are MANUAL.** On-screen labels: "Manual source of truth," "Manually marked sent."
   His beautiful dashboard is partly hand-entered. → **Our wedge: auto-bound REAL run data** (the very
   ₹0-bug fix in Phase B/C). "Theirs is typed in; ours is live" is a demo-killer differentiator.
2. **Token cost is the audience's #1 question** — "How much tokens do they spend?" recurs on every reel,
   unanswered on-screen. → **Our cost panel + Ollama $0 local tier directly answers the market's top
   objection.** Both a product feature AND a content angle they're ceding.
3. **Cockpit paradigm only.** His surface is a Command Center the operator drives (the "Mission Control"
   we scored 4.4 and chose to demote). → **Our Chief-of-Staff morning brief (push, one-tap) is a
   genuinely different bet** for non-coder owners/clients. He validates the audit layer; we lead with the brief.
4. **He shows model + run-count per agent** (good trust feature). → **We should copy it AND go further:
   show per-agent COST,** since cost is what the audience actually asks about.

## Decisions this should inform (for discussion — not changing the plan yet)
- **Client-facing roster abstraction.** He uses 6 legible *business roles* (CEO/CMO/Researcher/Sales/
  AE/Analyst). We have 18 technical agents — likely confusing for a non-coder client. Consider a
  client-facing "team of ~6 roles" view that maps onto our 18 under the hood.
- **Lead with what he can't:** live auto-tracked metrics + transparent token cost. Make both visible on
  the daily surface (cost lives on Insights per Gaurav, but a single "spend" chip on the brief may be the
  one number that wins the demo).
- **Re-examine Obsidian (he uses it).** He runs Claude Code + Obsidian. We dropped Obsidian-as-memory for
  Supabase because we're hosted/multi-tenant. His Obsidian works because it's *installed per client on
  their machine* (his "you own the infrastructure" model) — a different deployment than our hosted app.
  Our reasoning still holds for UC1 hosted; note the divergence is deployment-model, not "he's right."
