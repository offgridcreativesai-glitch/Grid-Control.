# GRIDLOCK-BUILD-27MAY — Build Handoff

> When Gaurav types **GRIDLOCK-BUILD-27MAY** in a new session, it means:
> "Full access. Build Grid Control client-ready. Don't stop until done or limit hit."

## What to do on activation

1. Read `docs/CLIENT_READY_BUILD_PLAN.md` — the full phased plan
2. Read memory files for context (MEMORY.md index)
3. Read `.claude/CLAUDE.md` for project rules
4. Start executing Pre-Build → Phase 1 in order
5. Do NOT stop for minor decisions. Only pause for:
   - Money decisions (new paid services)
   - Security decisions (exposing data)
   - Brand-defining decisions (client-facing copy/UX)
6. Commit after each major milestone

## Build order (execute sequentially)

### Pre-Build (do first, ~2 hours)
- [ ] Wire SessionStart/PreCompact/SessionEnd hooks into .claude/settings.json
- [ ] Update all agent model assignments per smart routing table
- [ ] Run AgentShield scan, fix CRITICAL/HIGH
- [ ] Slim CLAUDE.md (move verbose sections to lazy-load docs)

### Phase 1 (the real build, ~5-7 days)
- [ ] Supabase schema: users, brands, brand_members, agent_runs, outputs, approvals + RLS
- [ ] Auth: login/signup pages, JWT middleware on Flask, protected routes in React
- [ ] Onboarding wizard: 3-step form → auto brand_profile.json → auto brand_book.html
- [ ] Approval dashboard: DB-backed, inline preview, approve/reject/revise, batch
- [ ] SSE streaming: Flask endpoint + React EventSource for agent status
- [ ] Browser publishing: Chrome automation for approved content → social platforms
- [ ] Deploy: Vercel (dashboard) + Railway (API) + custom domain

## Connected services (already working)
- Supabase MCP (project mnivbrelhrwgndxcgega)
- Meta Ads MCP
- Chrome/Computer-use MCP
- Notion MCP (has 400 error — fix or replace with DB-backed approval)
- Gmail MCP
- Apify MCP
- Canva MCP
- Make.com MCP

## Critical context
- Gaurav records video content himself. Scripts are ready (both brands, 12 each).
- No Ayrshare — publish via browser automation
- Smart model routing (see build plan for full table)
- brands/{slug}/ file isolation works for MVP, migrate to Supabase RLS for production
- Dashboard: React 19 + Vite + Tailwind v4 + shadcn + TanStack Query v5 + Zustand
- API: Flask on port 5001, Vite proxy on 5173
