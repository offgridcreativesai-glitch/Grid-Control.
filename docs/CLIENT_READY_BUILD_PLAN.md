# Grid Control — Client-Ready Build Plan
> Updated: May 27, 2026. Build in progress.
> Safe word: **GRIDLOCK-BUILD-27MAY**

## Pre-Build: Token & Cost Optimization ✅
0a. ✅ **Memory persistence hooks** — `session_start()`, `session_save()`, `session_end()` in BaseAgent. Loads ~3KB compact state instead of 50-100KB.
0b. ✅ **Smart model routing** — Decision (Opus): CEO Brain, Strategy, Brand Guardian, Ad Strategist. Creative Core (Opus): Content Planner, Script Writer, Creative Director, Carousel Designer. Generation (Sonnet): 8 agents. Utility (Haiku): Cost Tracker, citation retries. Pure Math (None): 2.
0c. ✅ **Context budget audit** — CLAUDE.md 8.5KB (lean). Agent prompts embed full JSON — session_start hook provides 3KB alternative. Incremental migration.
0d. ⏳ **AgentShield security scan** — deferred to pre-deploy (not needed for building).

## Phase 1 — Minimum Client-Ready (5-7 days)
1. ✅ **Supabase schema + RLS** — 9 tables: profiles, brands, brand_members, agent_runs, agent_outputs, conversations, session_state, audit_log, brand_memory. RLS with is_brand_member()/is_brand_admin() helpers. Migration applied.
2. ✅ **Auth flow** — Supabase Auth. AuthPage (login/signup) in dashboard. JWT in API requests via apiFetch. Flask accepts Bearer JWT + legacy X-Dashboard-Secret. require_brand_access decorator. Sign-out in LeftRail.
3. ✅ **Brand onboarding wizard** — 3-step OnboardingPage: (a) brand name + product + audience + website, (b) connect IG/LinkedIn/YouTube/TikTok, (c) review + launch. Creates brand + brand_members row.
4. ✅ **Approval dashboard** — ReviewPage already wired to usePendingOutputs/useApproveOutput/useRejectOutput hooks → Flask → Supabase. Keyboard shortcuts (A/R/J/K). Platform-specific previews.
5. ✅ **SSE streaming** — Global event bus (broadcast_event) + /api/events endpoint + useSSE hook + appStore.activity feed. Auto-reconnect on error.
6. ⏳ **Browser-based publishing** — Chrome automation via computer-use MCP. Needs hands-on session.
7. ⏳ **Deploy** — Vercel for dashboard, Railway for Flask API. Custom domain.

### Blockers
- `SUPABASE_SERVICE_ROLE_KEY` must be added to .env (get from Supabase dashboard → Settings → API). Without it, Flask uses anon key (RLS restricts backend operations).

## Phase 2 — Revenue-Ready (+3-4 weeks)
8. **Stripe billing** — Per-tenant usage tracking. Emit cost events per agent run. Monthly invoicing.
9. **Langfuse integration** — Self-hosted observability. Per-client cost tracking, agent traces, latency.
10. **Revision loop** — Client feedback → agent re-run with constraint.
11. **Team roles** — Admin (full access), Editor (approve/reject), Viewer (read-only) per brand.
12. **Email notifications** — "3 posts awaiting your approval" via Gmail MCP.
13. **Continuous learning hooks** — Auto-capture agent patterns per brand (ECC instinct model). Show clients "your agents learned 47 things this month."

## Phase 3 — Competitive Moat (+4-6 weeks)
14. **LangGraph migration** — Checkpointing (survive crashes), retry logic, conditional routing.
15. **White-labeling** — Agency branding on dashboard (logo, colors, custom domain).
16. **One-brief orchestration** — Single client input → CEO Brain → full campaign.
17. **Client-facing analytics** — Weekly performance reports auto-generated.
18. **No-code agent config** — Let power-user clients tune agent parameters.
19. **MiniClaw sandboxing** — Container-level isolation per client agent run (from AgentShield).

## Smart Model Routing (CONFIRMED — updated May 27)
| Tier | Agent | Model | Rationale |
|------|-------|-------|-----------|
| Decision | CEO Brain | Opus 4.6 | Orchestration decisions, session state |
| Decision | Strategy Agent | Opus 4.6 | 90-day roadmap, high-stakes decisions |
| Decision | Brand Guardian | Opus 4.6 | Brand consistency = can't afford misses |
| Decision | Ad Strategist | Opus 4.6 | Paid budget decisions |
| Creative Core | Content Planner | Opus 4.6 | Calendar = creative backbone |
| Creative Core | Script Writer | Opus 4.6 | Scripts/hooks = brand voice quality |
| Creative Core | Creative Director | Opus 4.6 | Visual direction + FAL.ai calls |
| Creative Core | Carousel Designer | Opus 4.6 | Slide design = client-facing |
| Generation | Trend Researcher | Sonnet 4.6 | Data processing + Apify |
| Generation | Data Analyst | Sonnet 4.6 | Metrics analysis |
| Generation | Funnel Specialist | Sonnet 4.6 | Conversion copy |
| Generation | Website Agent | Sonnet 4.6 | Site generation |
| Generation | SEO/AEO Agent | Sonnet 4.6 | SEO analysis |
| Generation | Email Marketing | Sonnet 4.6 | Email sequences |
| Generation | Community Manager | Sonnet 4.6 | Reply drafting |
| Generation | DM Customer Hunter | Sonnet 4.6 | Outreach |
| Pure Math | Trend Sentinel | None | PIVOT/TRACK/STAY = no LLM |
| Pure Math | Performance Tracker | None | Win/dead patterns = no LLM |
| Utility | Cost Tracker | Haiku | Cheapest — this agent IS about saving money |
| Utility | Citation retries | Haiku | Cheap retry loop for Rule 10 |

## Infrastructure Already Connected
- Supabase MCP — project `mnivbrelhrwgndxcgega` (restored, empty DB)
- Meta Ads MCP — connected (ads management)
- Chrome/Computer-use MCP — for browser publishing
- Notion MCP — for approval pipeline (fix 400 error)
- Gmail MCP — for email notifications
- Apify MCP — for scraping
- Canva MCP — for design
- Make.com MCP — for automation

## Security Checklist (before first client)
- [ ] Run AgentShield scan, fix all CRITICAL/HIGH
- [ ] Supabase RLS on every table
- [ ] No API keys in client-visible code
- [ ] JWT auth on every API endpoint
- [ ] Brand data isolation verified (Client A cannot see Client B)
- [ ] Rate limiting on API endpoints
- [ ] CORS restricted to dashboard domain only

## Competitor Pricing Reference
- DOJO AI: $499/mo (closest competitor, 100+ brands)
- Jasper: $59/mo Pro, custom Business
- Gumloop: Free → $97 → $497/mo
- Grid Control target: ₹15-50K/mo services ($175-600)

## Repos to Study
- `langchain-ai/langgraph` (30K stars) — checkpointing, supervisor patterns
- `langfuse/langfuse` (22K stars) — self-hosted observability
- `affaan-m/ECC` (182K stars) — memory hooks, context budget, continuous learning, autonomous loops
- `affaan-m/agentshield` — security scanning, MiniClaw sandboxing
- `ComposioHQ/composio` — managed tool connectors
- `builderz-labs/mission-control` — self-hosted agent dashboard
