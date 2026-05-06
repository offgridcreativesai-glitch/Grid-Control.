# OffGrid Marketing OS — Project Intelligence

> Session-by-session build history is in `docs/CLAUDE_HISTORY.md`. Read it on demand when context requires (past decisions, prior bugs, build chronology). This file holds CURRENT state + rules + architecture only.

## What This Project Is

A fully autonomous multi-agent AI marketing system built using the Claude Agent SDK. It manages brand growth end-to-end for OffGrid Creatives AI and future client brands. **18 specialized agents** orchestrated by a CEO Brain. All outputs require human approval before any action is taken.

The project includes **GRID CONTROL** — a dark-mode React dashboard (fully built and build-verified) that provides the human command interface for all 18 agents.

## Active Brands

| Slug | Name | Status |
|------|------|--------|
| `askgauravai` | AskGauravAI | Primary engagement. Phase 1 — Awareness + Proof. Hinglish. Live build journey. |
| `offgrid-creatives-ai` | OffGrid Creatives AI | Original brand. Active. |
| `dropvolt` | DropVolt | Test brand — graphic T-shirts, Gen Z. Pipeline validated Apr 14. |

## The 18 Agents (Locked Roster)

| ID | Name | Role | Model |
|----|------|------|-------|
| 0 | CEO Brain | Orchestrator, dynamic router, session state manager, Notion push | claude-opus-4-6 |
| 1 | Strategy Agent | 90-day roadmap + real competitor research via Apify | claude-opus-4-6 |
| 2 | Content Planner | 30-day calendar from real trend + performance data | claude-sonnet-4-6 |
| 3 | Script Writer | Scripts/hooks/captions. Brand voice check. Flags human face/voice. | claude-sonnet-4-6 |
| 4 | Creative Director | AI video + image. FAL.ai (flux/dev + ideogram/v2 + recraft-v3). ElevenLabs disabled. | claude-opus-4-6 |
| 5 | Ad Strategist | Deep competitor ad scraping. Activates only when paid budget confirmed. Reads `agents/references/meta_ads_framework.json`. | claude-opus-4-6 |
| 6 | Data Analyst | Real account metrics via connected APIs. Weekly scoring. | claude-sonnet-4-6 |
| 7 | Funnel Specialist | Full conversion journey from real data. | claude-sonnet-4-6 |
| 8 | Trend Researcher | Runs first weekly. Apify scrape + Whisper + topic clustering. ACTIVE_BRAND env. | claude-sonnet-4-6 |
| 9 | Website Agent | Builds and manages website. Deploys to Railway. GA4 + Search Console. | claude-sonnet-4-6 |
| 10 | Brand Guardian | Independent SOUL check across all generated content (voice/audience/positioning drift). | claude-opus-4-6 |
| 11 | SEO+AEO Agent | Search visibility and AI-answer-engine optimisation. | claude-sonnet-4-6 |
| 12 | Email Marketing Agent | Email sequences and campaigns. | claude-sonnet-4-6 |
| 13 | Community Manager | Engagement, comments, community growth. | claude-sonnet-4-6 |
| 14 | DM+Customer Hunter | Outreach and direct sales via DM. | claude-sonnet-4-6 |
| 15 | Carousel Designer | 7-slide carousel JSON spec → editorial HTML/CSS render via Playwright. Multi-brand. | claude-sonnet-4-6 |
| 16 | Trend Sentinel | Daily PIVOT/TRACK/STAY decision. Pure-math, no LLM. | none (Class-1) |
| 17 | Performance Tracker | Real metrics → winning/dead patterns. Pure deterministic. | none (Class-1) |

## Non-Negotiable Ground Rules

### Rule 1 — Zero Assumptions. Ever.
No agent, no function, no output may contain assumed, hallucinated, or AI-invented data. Every data point must trace back to a real scrape, a real API call, or a real user input. If data is unavailable, the agent STOPS and asks. It does not fill the gap.

### Rule 2 — No Code Without User Saying "Build"
During planning phases, produce architecture, schemas, and file structures only. Do not write executable code until the user explicitly says "build" or "write this".

### Rule 3 — Research Before Every Decision
Before implementing any solution, integration, or pattern — search for how real developers and users are handling the same problem.

### Rule 4 — Nothing Executes Without Approval
All agent outputs go to `brands/{slug}/outputs/pending_approval/` first. CEO Brain only moves output to `brands/{slug}/outputs/approved/` after confirmed approval.

### Rule 5 — Every Agent Change Needs Permission
Stop and ask the user before changing agent scope, role, or behaviour.

### Rule 6 — Connected Accounts Are Mandatory
No agent activates for any brand until all platform accounts are connected.

### Rule 7 — TanStack Query v5 Rules (Critical)
- `onSuccess` in `useQuery` is REMOVED in v5. Use `useEffect` watching `data` instead.
- `onError` in `useQuery` is REMOVED in v5. Use `isError` / `error` from the query result.
- Mutation `onSuccess` / `onError` in `useMutation` still work normally.

### Rule 8 — Tailwind v4 Rules (Critical)
- `@tailwindcss/vite` plugin only. No `tailwind.config.js`. No postcss config.
- Custom tokens defined in `index.css` using CSS variables under `:root` and `.dark`.
- `cn()` from `@/lib/utils` for all conditional class logic.

### Rule 9 — AutoResearch Standard (Loop Before Output)
Every output is the winner of an internal loop. Before any output is generated:
1. Define the goal
2. State what "better" means in measurable terms
3. Consider minimum 3 internal variants
4. Select winner based on metric
5. Deliver with Loop Header

Loop Header format:
```
LOOP: [Agent Name] — [Output Type]
GOAL: [What this output is optimizing for]
METRIC: better = [specific measurable definition]
VARIANTS TESTED: [number]
WINNER: [which variant and why in one line]
```

Formal eval framework (capability/regression evals + pass@k metrics): `docs/EVAL_HARNESS.md`.

### Rule 10 — Source Citation Enforcement
**Two classes of agents. Two policies. No exceptions.**

**Class 1 — DECISION agents (classify, route, gate, score)**
Examples: Trend Sentinel, Performance Tracker, Contradiction Detector.
- **NO Claude. NO LLM. Pure deterministic math.**
- Every output decision is a code-readable expression (Jaccard similarity, score ratio, threshold comparison).
- Every per-item `reason` field must cite the exact numbers/strings used (e.g. `"jaccard_overlap=0.42 >= 0.4 with calendar topic 'AI Strategy Framework' — already covered"`).
- Decision engine field MUST be present in output: `"decision_engine": "pure_math"`.
- **Hallucination risk: zero by design.**

**Class 2 — GENERATION agents (write, plan, design, synthesize)**
Examples: Trend Researcher AutoResearch, Strategy Agent, Content Planner, Script Writer, Creative Director, Brand Guardian, Carousel Designer.
- **Claude allowed BUT every output must include a `data_provenance` field listing the exact source data points used.**
- Outputs that reference facts/numbers not in inputs → output rejected and rerun.
- Source tracking: file path + key path + value snippet (e.g. `"trends_live.json#topic_clusters[2].name = 'AI Strategy'"`).
- **Hallucination risk: minimized via citation enforcement at output validation layer.**

**Rule 10 implementation (use `agents/_provenance.py` helpers):**
1. Import: `from _provenance import build_source_index, validate_citations, build_violation_message, MAX_RERUN_ATTEMPTS`
2. Build source index at top of `run_autoresearch_loop()`: list all input JSON files the agent reads.
3. Add prompt block: "RULE 10 — every claim must cite source_file + source_path + source_value".
4. Add `data_provenance: [...]` to the output schema.
5. Wrap Claude call in retry loop: validate → if invalid + attempts left, re-prompt with violations → up to MAX_RERUN_ATTEMPTS retries.
6. Inject `result["provenance_validation"] = report` before returning.
7. In `run()`, copy `data_provenance` + `provenance_validation` INTO the saved block.
8. Bump `max_tokens` 50%+ to fit provenance entries.

**Implementation status:**
- ✅ Trend Sentinel — pure math
- ✅ Performance Tracker — pure math
- ✅ Strategy Agent, Content Planner, Script Writer, Creative Director, Brand Guardian — citation enforcement live
- ⏳ Trend Researcher AutoResearch loop — partial (cites scrape_status_per_source; could be tightened)

## Bug Registry (Tracked Fixes — DO NOT REPEAT)

| # | File | Bug | Fix | Status |
|---|------|-----|-----|--------|
| 1 | `dashboard_api.py` | `_bootstrap_brand_memory` called before `profile` dict was defined — brand creation crashed | Moved call to after `profile` is built and written | ✅ Fixed Apr 14 |
| 2 | `agents/cost_reporter.py` | `import supabase.db as _db` fails — pip `supabase` package shadows local `supabase/db.py` | Use `importlib.util.spec_from_file_location` to load local file directly | ✅ Fixed Apr 14 |
| 3 | `agents/trend_researcher.py` | `__init__` had hardcoded default `brand_slug = "offgrid-creatives-ai"` — always ran for wrong brand | Reads from `os.getenv("ACTIVE_BRAND", "offgrid-creatives-ai")` | ✅ Fixed Apr 14 |
| 4 | `agents/trend_researcher.py` | Hardcoded `NICHE_HASHTAGS` was D2C/Meta content — wrong for fashion brands | Replaced with `_build_niche_hashtags(brand_profile)` — dynamic from brand profile fields | ✅ Fixed Apr 14 |
| 5 | `ceo_brain/orchestrator.py` | `save_agent_output` used display name as folder ("Trend Researcher" not "trend-researcher") | Added slugification: `re.sub(r"[^a-z0-9-]", "", agent_name.lower().replace(" ", "-"))` | ✅ Fixed Apr 14 |
| 6 | `dashboard/src/screens/MeetingRoom.tsx` | `clearIndividualHistory` called on every agent click — wiped in-memory history | Removed the call from `handleSelectAgent` | ✅ Fixed Apr 14 |
| 7 | `dashboard/src/store/brandStore.ts` | No localStorage persistence — all chat history lost on page refresh | Added `persist` middleware wrapping the store, `partialize` on chat histories + active brand | ✅ Fixed Apr 14 |
| 8 | `agents/trend_researcher.py`, `agents/data_analyst.py`, `agents/script_writer.py` | `json.loads(claude_response)` failed with `Unterminated string` when Claude embedded literal newlines in JSON string values | Added `_safe_json_loads()` + `_escape_literal_newlines_in_strings()` helper to all three agents | ✅ Fixed Apr 25 |
| 9 | `agents/trend_researcher.py` | AutoResearch loop `max_tokens=4000` was truncating responses at ~15.5K chars, causing JSON parse failures | Bumped to `max_tokens=16000` + added `stop_reason == "max_tokens"` truncation warning log | ✅ Fixed Apr 25 |
| 10 | `dashboard_api.py` connections check | Twitter `/2/users/me` returns 403 on Free tier App-Only Bearer (requires OAuth user-context). Showed "Token invalid" even when token was valid for Apify | 401 → invalid; 403/429 → "Token set (Free tier — read via Apify)", marked connected | ✅ Fixed Apr 25 |
| 11 | `agents/carousel_designer.py` | Brand palette hex contained descriptive text (e.g. `"#0F4C5C (deep teal — sophisticated)"`) — Pillow rejected | `_clean_hex()` static helper extracts pure hex via regex | ✅ Fixed May 2 |
| 12 | `ceo_brain/orchestrator.py` | Build H auto-block was overzealous — quarantined ANY save when ANY CRITICAL contradiction existed, even unrelated ones | Now quarantines only if saving agent is named in a CRITICAL finding's `agents_involved` list | ✅ Fixed May 2 |
| 13 | `agents/carousel_designer.py` | HelveticaNeue.ttc font index 3 = BoldItalic, index 5 = UltraLight (not Regular/Bold as assumed) — slides rendered italic + thin | Fixed: index 0 = Regular, index 1 = Bold | ✅ Fixed May 2 |

## File Structure

```
/Users/gauravoffgrid/offgrid-marketing-os/
├── dashboard_api.py              Flask REST API (multi-brand, all endpoints, port 5001)
├── agents/
│   ├── trend_researcher.py       Reads ACTIVE_BRAND env. Apify + Whisper + clustering.
│   ├── strategy_agent.py         Rule 10 wired. Opus.
│   ├── content_planner.py        Rule 10 wired. Sonnet.
│   ├── script_writer.py          Rule 10 wired. Voice DNA. Performance feedback injection.
│   ├── creative_director.py      Rule 10 wired. FAL.ai (flux/dev + ideogram/v2 + recraft-v3).
│   ├── data_analyst.py
│   ├── funnel_specialist.py
│   ├── website_agent.py
│   ├── brand_guardian.py         Rule 10 wired. Soul check.
│   ├── trend_sentinel.py         Pure math (Rule 10 Class-1).
│   ├── performance_tracker.py    Pure math (Rule 10 Class-1).
│   ├── carousel_designer.py      Sonnet content + Pillow OR Playwright HTML render. Multi-brand.
│   ├── carousel_html_renderer.py 5 editorial templates: HERO/INSIGHT/LIST/DATA_CALLOUT/PRINCIPLE_CTA.
│   ├── _provenance.py            Rule 10 helpers (build_source_index, validate_citations).
│   ├── _token_optimization.py    Token-saving utilities (planned: model selector, prompt slimmer).
│   ├── references/
│   │   └── meta_ads_framework.json   10-pillar Meta Ads framework — read by Ad Strategist.
│   └── cost_reporter.py          Uses importlib.util to load local supabase/db.py.
├── ceo_brain/
│   ├── orchestrator.py           CEOBrain class. save_agent_output runs contradiction check + scoped auto-block.
│   └── contradiction_detector.py 6-rule pure-math cross-agent contradiction detector.
├── notion_integration/
│   ├── notion_pusher.py          Approval DB push. NotionAuthError on 401.
│   └── content_calendar.py       Separate "OffGrid Content Calendar" DB (Draft/Ready/Published).
├── brands/
│   ├── askgauravai/              Primary brand. Hinglish. Live build journey.
│   ├── offgrid-creatives-ai/
│   └── dropvolt/                 Test brand.
├── dashboard/                    React 19 + Vite + Tailwind v4. 5-Space architecture.
├── managed_agents/               Anthropic Managed Sessions (registry + setup + session_runner).
├── scripts/
│   ├── strategic_compact.py      Token-saving hook — suggests /compact at threshold.
│   ├── push_gh_secrets.sh        Pushes .env values to GitHub repo secrets.
│   ├── scrape_carousel_competitors.py
│   ├── install_launchd_pipeline.sh   Mac launchd job for daily 8am pipeline.
│   └── cron_daily_pipeline.sh    Curl wrapper for /api/pipeline/daily-run.
├── .github/workflows/
│   ├── daily-pipeline.yml        Replaces launchd. Runs Trend/Sentinel/Data/Contradictions at 8am IST.
│   └── carousel-on-demand.yml    Manual carousel generation, commits PNGs back.
└── docs/
    ├── CLAUDE_HISTORY.md         Full session-by-session build history.
    ├── EVAL_HARNESS.md           Rule 9 formalized with pass@k metrics.
    ├── AGENT_INTROSPECTION.md    4-phase debug protocol for failing agents.
    └── TOKEN_OPTIMIZATION.md     Operating rules — model selection, /compact, sub-agent rules.
```

## GRID CONTROL Dashboard

### Status: 5-Space Architecture, Build Verified
- Build: 1810+ modules transformed, zero TypeScript errors, zero warnings
- Architecture: 5 Spaces (Command, Review, Agents, Brand, System) + Insights Space 6
- Agent Run buttons: Wired to Managed Agents session runner (subprocess fallback)
- Notion approval pipeline: Live
- Media previews: Inline image/video/audio in ReviewSpace
- Zustand persist: Chat history survives page refresh

### Tech Stack (Locked)
- React 19 + Vite + TypeScript (strict mode)
- Tailwind CSS v4 with `@tailwindcss/vite` plugin (NOT postcss)
- shadcn/ui (default style, slate base, oklch tokens)
- TanStack Query v5
- Zustand with `persist` middleware
- Flask API on port 5001, Vite dev on 5173 with `/api` proxy

### 5-Space Map
| Space | Name | File |
|-------|------|------|
| 1 | Command | `dashboard/src/spaces/CommandSpace.tsx` |
| 2 | Review | `dashboard/src/spaces/ReviewSpace.tsx` |
| 3 | Agents | `dashboard/src/spaces/AgentsSpace.tsx` |
| 4 | Brand | `dashboard/src/spaces/BrandSpace.tsx` |
| 5 | System | `dashboard/src/spaces/SystemSpace.tsx` |
| 6 | Insights | `dashboard/src/spaces/InsightsSpace.tsx` |

Old `screens/` and `pages/` files DELETED — do not reference.

## Multi-Brand Architecture

- Every brand lives under `brands/{slug}/` with isolated data files and outputs.
- `brand_slug` query param required on all API endpoints (default: `offgrid-creatives-ai`).
- `get_brand_dir(slug)` in Flask returns 404 if slug doesn't exist.
- Brand slug auto-generated from name: lowercase, spaces→hyphens, strip special chars.
- All TanStack Query keys include `activeBrand.slug` — switching brands auto-refetches everything.
- Agent subprocesses receive `ACTIVE_BRAND` env var.

## Agent Communication Pattern

All agents read from and write to `brands/{slug}/`:
- `brands/{slug}/trends_live.json` → written by Trend Researcher, read by all content agents
- `brands/{slug}/competitors_db.json` → written by Strategy Agent, read by all agents
- `brands/{slug}/session_state.json` → managed by CEO Brain
- `brands/{slug}/brand_profile.json` → read by all agents, never modified by agents
- `brands/{slug}/voice_profile.json` → read by Script Writer + Carousel Designer
- `brands/{slug}/content_calendar.json` → written by Content Planner, read by Script Writer + Carousel Designer
- `brands/{slug}/performance_history.json` → written by Performance Tracker, read by Trend Researcher + Script Writer + Trend Sentinel
- `brands/{slug}/contradictions.json` → written by Contradiction Detector
- `brands/{slug}/outputs/pending_approval/{agent-slug}/` → all new outputs land here
- `brands/{slug}/outputs/approved/` → approved outputs
- `brands/{slug}/outputs/blocked/{agent-slug}/` → quarantined CRITICAL contradictions (Build H)
- `brands/{slug}/visuals/carousels/{date}_{post_id}/` → carousel slide PNGs + slides.json

## Flask API — dashboard_api.py

| Method | Path | Purpose |
|--------|------|---------|
| GET | `/api/health` | Health check |
| GET | `/api/agents` | List all agents with config |
| GET | `/api/agents/status` | Live status of all agents |
| POST | `/api/agents/run` | Run an agent (managed sessions or subprocess) |
| POST | `/api/agents/chat` | Agent chat (calls Claude with agent context) |
| POST | `/api/agents/train` | Agent training input |
| GET | `/api/brands` | List all brands |
| POST | `/api/brands/create` | Create new brand folder + default JSON files |
| GET | `/api/outputs/pending?brand_slug=` | Pending approval queue |
| GET | `/api/outputs/all?brand_slug=` | All outputs |
| POST | `/api/outputs/approve` | Move to approved/ |
| POST | `/api/outputs/reject` | Delete pending file |
| POST | `/api/outputs/request-changes` | Save change note |
| GET | `/api/outputs/download/<filename>` | Stream download |
| GET | `/api/outputs/media/<filepath>` | MIME-aware inline media |
| GET | `/api/brand/profile?brand_slug=` | Read brand_profile.json |
| POST | `/api/brand/profile?brand_slug=` | Write brand_profile.json |
| GET | `/api/brand/dashboard?brand_slug=` | Combined: profile + session_state + trends_live |
| GET | `/api/brand/file?brand_slug=&file=` | Whitelisted brand-output file reader |
| POST | `/api/pipeline/daily-run` | Chain Trend → Sentinel → Data Analyst → Contradictions |
| POST | `/api/carousel/generate` | Carousel Designer subprocess (post_id or topic, slides, platform) |
| POST | `/api/contradictions/check?brand_slug=` | Run contradiction detector live |
| GET | `/api/contradictions/latest?brand_slug=` | Most recent persisted report |
| POST | `/api/performance/log-post` | Append metrics to performance_inbox.json |
| GET | `/api/performance/history` | Computed performance_history.json |
| GET | `/api/performance/inbox` | Queued not-yet-ingested entries |
| POST | `/api/jarvis/query` | Voice answer + edge-tts audio (en-US-GuyNeural) |
| POST | `/api/voice/extract-profile` | Extract voice DNA from raw scripts |
| GET | `/api/voice/profile` | Read voice_profile.json |
| GET | `/api/connections/check` | Validate all API tokens |
| GET | `/api/config/keys` | Show which API keys are set |

## Environment Variables Required

```
ANTHROPIC_API_KEY        # Claude API — all agents
APIFY_API_KEY            # Apify scrapers — Trend Researcher, Strategy Agent
FAL_API_KEY              # FAL.ai — Creative Director image/video gen
NOTION_API_KEY           # Notion — approval pipeline
NOTION_PAGE_ID           # Notion parent page (DB auto-created)
NOTION_CONTENT_CALENDAR_DB_ID  # Optional — content calendar DB ID
META_GRAPH_API_TOKEN     # Meta Graph API — STILL PENDING (blocks Data Analyst real metrics)
META_AD_ACCOUNT_ID       # Meta — pending
SUPABASE_URL             # Supabase — cost tracking + conversation history
SUPABASE_KEY             # Supabase
YOUTUBE_API_KEY          # YouTube Data API (set)
TWITTER_BEARER_TOKEN     # Twitter Free tier — read via Apify (set)
DASHBOARD_SECRET         # Flask auth header
GRID_RUN_ID              # Set by dashboard_api.py per agent run
GRID_BRAND_SLUG          # Set by dashboard_api.py per agent run
ACTIVE_BRAND             # Set by dashboard_api.py per agent subprocess
```

## Data Sources (All Real — No Exceptions)

- Competitor Instagram → Apify `apify/instagram-hashtag-scraper` + `apify/instagram-scraper`
- Competitor Meta Ads → Apify Meta Ad Library Scraper
- Google Trends → PyTrends library
- Own Instagram metrics → Meta Graph API (pending Meta App Review)
- Own website data → GA4 API + Google Search Console API
- YouTube Shorts → Apify `apify~youtube-scraper`
- Twitter → Apify `apify~twitter-scraper`
- Voice transcripts → openai-whisper + yt-dlp

## Pending in Priority Order

1. **Apply Rule 10 to remaining generation agents:** Trend Researcher AutoResearch loop (partial — could be tightened with full data_provenance pattern).
2. **Meta Graph API token** — unblocks Data Analyst real metrics + Performance Tracker `_fetch_meta_api()`. Ad-account already connected via Meta Ads MCP but `is_ads_mcp_enabled: false` (waitlisted by Meta).
3. **ECC selective port** (Memory Persistence hooks, eval-harness runner, 7 skill files: brand-voice / content-engine / market-research / fal-ai-media / deep-research / eval-harness / agent-introspection-debugging).
4. **Subagent orchestration upgrade** — document iterative retrieval pattern in CEOBrain.
5. **Parallelization** — enable parallel agent runs (Trend Researcher + Data Analyst are independent).
6. **BrandSpace UI form** for `/api/performance/log-post` + `/api/contradictions/latest` panel (polish).
7. **Auto-wire contradiction_detector** into CEOBrain.save_agent_output (currently scoped — block CRITICAL findings on save with named-agent check).
8. **Bubble frontend** (last — build after 20–30 paying clients).

## Managed Agents Status (Live)

- ✅ SDK upgraded to 0.96.0
- ✅ All 15 agents LIVE on Anthropic's API (registry.json has real IDs)
- ✅ Shared environment created
- ✅ Memory stores: NOT set up (fresh slate — intentional)
- ✅ All agent runs route through Managed Sessions automatically
- To add memory seeding later: `python3 managed_agents/memory_manager.py --brand {slug}`

## Token Optimization Hooks

- `scripts/strategic_compact.py` — counts tool calls per session, suggests `/compact` after 50 then every 25.
- Wire into `~/.claude/settings.json` PreToolUse hooks (Edit|Write|Bash matchers).
- Operating rules: `docs/TOKEN_OPTIMIZATION.md` (model selection, sub-agent rule, background process rule).
- Eval framework: `docs/EVAL_HARNESS.md`.
- Agent self-debug: `docs/AGENT_INTROSPECTION.md`.

## How to Run Locally

```bash
# Terminal 1 — Flask API
cd /Users/gauravoffgrid/offgrid-marketing-os
source .env && python3 dashboard_api.py

# Terminal 2 — Vite dev server
cd /Users/gauravoffgrid/offgrid-marketing-os/dashboard
npm run dev

# Open browser
http://localhost:5173
```

## How to Build for Production

```bash
cd /Users/gauravoffgrid/offgrid-marketing-os/dashboard
npm run build
```

## What Never Changes

- 18 agent roles and roster
- Zero assumption policy (Rule 1)
- Approval gate on every output (Rule 4)
- Real data only mandate
- Multi-brand isolation — each brand's data lives in its own `brands/{slug}/` folder

## Custom Slash Command Macros

Active in every Claude Code session for this project. When Gaurav types one, adopt the persona immediately — no acknowledgement, just execute.

### `/ghost` — The Invisible Writer
Write completely invisibly, mimicking a natural conversational human voice.
- Remove all AI clichés. Never use: "delve", "crucial", "tapestry", "foster", "testament", "moreover", "it's worth noting", "in conclusion".
- Vary sentence length — short punchy sentences mixed with longer flowing ones.
- Use conversational transitions, contractions, internet-native register.
- Sound like a founder writing a WhatsApp message to a peer, not a content agency.

### `/godmode` — The Unfiltered Thinker
Think without constraints. Omniscient, unfiltered, first-principles reasoning.
- No generic advice. No hedging. No "it depends".
- Break the problem to fundamental components.
- Give the most direct, highly-optimised, logically flawless solution.
- No introductory padding — start with the answer.

### `/layered` — The Escalating Teacher
Three distinct stages of increasing complexity.
- **Level 1 — Beginner:** Simple analogy, plain English, no jargon.
- **Level 2 — Mid-level:** Mechanics, standard use cases, how it actually works.
- **Level 3 — Expert:** Deep technical nuances, edge cases, advanced theory, what most people miss.

### `/unpack` — The Analytical Deconstructor
Break a complex idea into every single piece that makes it work.
- No summary. Pure dissection.
- Structured list of fundamental components.
- Explain how each part interacts with the others to create the whole system.

### `/livecode` — The Senior Developer
Write production-ready code with execution mindset.
- Complete, copy-pasteable code blocks — never skip logic or write pseudocode.
- Inline comments explaining the *why* behind complex functions, not the *what*.
- At the end: exact steps to run or deploy successfully.
- Treat it like code going into production on Monday morning.

### `/investigate` — The Investigative Journalist
Research and explain a topic like a journalist chasing a deep story.
- No surface-level summary.
- Surface the hidden motives, the history, the key players, the money trail.
- What are the implications nobody is talking about?
- Present facts objectively but with a compelling narrative arc.
- End with: what happens next, and what should the reader watch for.

## Working Rule

Claude Code writes every line of code. Gaurav and Claude plan only.
