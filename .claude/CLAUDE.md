# OffGrid Marketing OS — Project Intelligence

> Reference docs (load on demand, not auto):
> - `docs/CLAUDE_HISTORY.md` — session-by-session build chronology
> - `docs/CLAUDE_FILE_STRUCTURE.md` — full file tree
> - `docs/CLAUDE_BUG_REGISTRY.md` — fixed bugs (read when debugging similar)
> - `docs/CLAUDE_API_ROUTES.md` — Flask endpoints
> - `docs/CLAUDE_ENV.md` — env vars + data sources
> - `docs/CLAUDE_SLASH_MACROS.md` — `/ghost /godmode /layered /unpack /livecode /investigate`
> - `docs/EVAL_HARNESS.md`, `docs/AGENT_INTROSPECTION.md`, `docs/TOKEN_OPTIMIZATION.md`

## Response Style (apply to every reply)

1. **Default to terse.** Answer first, explanation only if asked. Skip preamble like "Let me…", "I'll…", "Great question".
2. **Cap response length:** simple Q ≤ 100 words, planning ≤ 250 words, technical deep-dive ≤ 600 words. Code blocks don't count.
3. **No celebratory headers** ("✅ Done!", "🎉 Phase X Complete!"). State the outcome plainly.
4. **No summary tables** unless comparing 3+ items. No restatement of what you just did.
5. **Ask 1 question at a time** when there's a fork.
6. **For investigation:** prefer `Grep` and `Read` with offset+limit over reading whole files. Use the `Explore` / `Agent` subagent for >3-query searches — sub-agent results don't bloat main context.
7. **Don't end-of-turn-summarize completed work.** The diff or tool output already shows it.
8. **NEVER show raw JSON to Gaurav. NEVER paste JSON in chat or render JSON-shaped previews in the dashboard.** All agent outputs must go through `utils/output_formatter.format_for_notion()` and become human-readable markdown. Files have a LOOP HEADER prefix → split on first `\n---\n` before parsing. This rule has regressed multiple times — `feedback_no_json_dumps.md` is the standing reminder.

## What This Project Is

A 18-agent autonomous AI marketing system on the Claude Agent SDK. CEO Brain orchestrates. All outputs gated by human approval. **GRID CONTROL** is the React dashboard at `dashboard/` — v0-ported, dark mode, with embedded Claude chat (The Brain).

## Active Brands

| Slug | Status |
|------|--------|
| `askgauravai` | Primary. Phase 1 — Awareness + Proof. |
| `offgrid-creatives-ai` | Original. Active. |
| `dropvolt` | Test brand — graphic tees, Gen Z. |

## The 18 Agents (Locked Roster)

| ID | Slug | Role | Model |
|----|------|------|-------|
| 0 | ceo-brain | Orchestrator + session state + Notion push | opus-4-6 |
| 1 | strategy-agent | 90-day roadmap + competitor research | opus-4-6 |
| 2 | content-planner | 30-day calendar | sonnet-4-6 |
| 3 | script-writer | Scripts/hooks/captions + voice check | sonnet-4-6 |
| 4 | creative-director | AI video/image (FAL.ai) | opus-4-6 |
| 5 | ad-strategist | Paid Meta/X funnels (only when budget confirmed) | opus-4-6 |
| 6 | data-analyst | Real-account metrics, weekly score | sonnet-4-6 |
| 7 | funnel-specialist | Conversion journey | sonnet-4-6 |
| 8 | trend-researcher | Apify + Whisper + clustering, ACTIVE_BRAND env | sonnet-4-6 |
| 9 | website-agent | Site + GA4 + Search Console | sonnet-4-6 |
| 10 | brand-guardian | SOUL check across all generated content | opus-4-6 |
| 11 | seo-aeo-agent | Search + answer-engine optimisation | sonnet-4-6 |
| 12 | email-marketing-agent | Email sequences | sonnet-4-6 |
| 13 | community-manager | Replies, mentions | sonnet-4-6 |
| 14 | dm-customer-hunter | Inbound + warm DMs | sonnet-4-6 |
| 15 | carousel-designer | 7-slide carousel JSON → editorial HTML/CSS via Playwright | sonnet-4-6 |
| 16 | trend-sentinel | Daily PIVOT/TRACK/STAY (pure math, Class-1) | none |
| 17 | performance-tracker | Winning/dead patterns (pure math, Class-1) | none |

## Non-Negotiable Ground Rules

1. **Zero assumptions.** Every data point traces to a real scrape, API call, or user input. If unavailable → STOP, ask. Never fabricate.
2. **No code without "build" / "write".** Plan first. Execute on explicit go.
3. **Research before deciding.** Search how others solve the same problem before implementing.
4. **Approval gate.** Every output → `brands/{slug}/outputs/pending_approval/`. Approved manually → `outputs/approved/`.
5. **Permission for agent changes.** Don't change agent scope/role/behaviour without asking.
6. **Connected accounts mandatory.** No agent runs for a brand until its platforms are connected.
7. **TanStack Query v5:** `onSuccess`/`onError` removed in `useQuery`. Use `useEffect` watching `data` / `isError`/`error`. Mutations still have them.
8. **Tailwind v4:** `@tailwindcss/vite` only. No `tailwind.config.js`, no postcss config. Tokens in `index.css` `:root` / `.dark`. `cn()` from `@/lib/utils`.
9. **AutoResearch loop.** Every output is a winner of an internal 3+ variant loop. Header format: `LOOP: [agent] — [type] / GOAL / METRIC / VARIANTS / WINNER`. Eval harness: `docs/EVAL_HARNESS.md`.
10. **Source citation enforcement.** Class-1 (decision) agents = pure math, `decision_engine: "pure_math"`. Class-2 (generation) agents = Claude allowed but every output has `data_provenance` field citing source_file + path + value. Helpers in `agents/_provenance.py`. Status: ✅ Trend Sentinel, Performance Tracker, Strategy, Content Planner, Script Writer, Creative Director, Brand Guardian. ⏳ Trend Researcher AutoResearch (partial).

## GRID CONTROL Dashboard (Live)

- React 19 + Vite + Tailwind v4 + shadcn (oklch tokens) + TanStack Query v5 + Zustand + react-router-dom v7.
- Pages: `/`, `/review`, `/agents`, `/agents/:id`, `/calendar`, `/insights`, `/system` (in `dashboard/src/pages/`).
- Layout in `dashboard/src/components/layout/` (DashboardLayout, LeftRail, TopBar, TheBrain, CommandPalette).
- Brand switcher in left rail. ⌘K command palette. ⌘J The Brain.
- Flask `/api/*` on port 5001 with `/api` proxy on Vite 5173.
- The Brain backend: `/api/brain/chat` (Sonnet 4.6 default, opt `use_opus`) + `/api/brain/execute` (gated edit/bash). Tools: `read_file` `list_dir` (auto), `propose_edit` `propose_bash` (gated).

## Multi-Brand & File Layout (per-brand)

`brands/{slug}/` is fully isolated. Key files:
- `brand_profile.json` — read by all, never modified by agents
- `voice_profile.json` — read by Script Writer + Carousel Designer
- `content_calendar.json` — written by Content Planner; read by Script Writer + Carousel Designer
- `trends_live.json` — written by Trend Researcher; read by content agents
- `competitors_db.json` — written by Strategy Agent
- `performance_history.json` — written by Performance Tracker; read by Trend Researcher + Script Writer + Trend Sentinel
- `contradictions.json` — written by Contradiction Detector
- `session_state.json` — managed by CEO Brain
- `outputs/pending_approval/{agent-slug}/` (kebab-case)
- `outputs/approved/`, `outputs/blocked/{agent-slug}/`
- `visuals/carousels/{date}_{post_id}/`

All API endpoints take `?brand_slug=`. All TanStack queries keyed by `activeBrand.slug`. Subprocesses get `ACTIVE_BRAND` env.

## Pending in Priority Order

1. **Custom domain** — point a domain at Vercel (dashboard) and Railway (API).
2. **Browser publishing** — Chrome automation for posting approved content (needs Gaurav hands-on).
4. Apply Rule 10 fully to Trend Researcher AutoResearch (partial today).
5. **META_GRAPH_API_TOKEN** — unblocks live Data Analyst metrics + Performance Tracker.
6. Subagent orchestration upgrade in CEOBrain.
7. Parallelization (Trend Researcher + Data Analyst are independent).
8. AgentShield security scan before first client.

### Recently Completed (May 27, 2026)
- ✅ **Deploy LIVE** — Vercel (dashboard) + Railway (Flask API) + API proxy working
- ✅ Memory persistence hooks (session_start/save/end in BaseAgent)
- ✅ Smart model routing (8 Opus / 8 Sonnet / 1 Haiku / 2 None)
- ✅ Supabase schema + RLS (9 tables, brand_members, proper policies)
- ✅ Auth flow (Supabase Auth + JWT + login/signup page)
- ✅ Brand onboarding wizard (3-step)
- ✅ SSE streaming (global event bus + React hook)
- ✅ _state.json compact summary wired into BaseAgent

## Token Optimization Hooks

- `scripts/strategic_compact.py` suggests `/compact` after 50 tool calls then every 25.
- The Brain: Sonnet 4.6 default, `use_opus: true` for hard tasks. Slim brand context (~2KB). Prompt caching with `cache_control` on system blocks.
- Reference docs (slash macros, full file tree, full bug registry, full API table, env vars) loaded on demand only.
- More: `docs/TOKEN_OPTIMIZATION.md`.

## How to Run Locally

```bash
# Terminal 1
cd /Users/gauravoffgrid/offgrid-marketing-os && source .env && python3 dashboard_api.py

# Terminal 2
cd /Users/gauravoffgrid/offgrid-marketing-os/dashboard && npm run dev

# Browser
http://localhost:5173
```

Production build: `cd dashboard && npm run build`.

## Production URLs

- **Dashboard**: `v0-grid-control-dashboard.vercel.app`
- **API**: `web-production-175d5.up.railway.app`
- **API proxy**: Dashboard `/api/*` → Railway via Vercel rewrites
- **Git**: `github.com/offgridcreativesai-glitch/Grid-Control.`
- Railway project: `9a2157e3-ac1d-4e24-8573-a659302a492b`
- Vercel project: `grid-control` (team: `gauravkhanna110-1327s-projects`)

## What Never Changes

18-agent roster · Zero-assumption policy · Approval gate · Real-data mandate · `brands/{slug}/` isolation.

## Working Rule

Claude Code writes every line of code. Gaurav and Claude plan only.
