---
name: grid-control-dashboard
description: Use this skill for ANY work on the GRID CONTROL frontend dashboard for the OffGrid Marketing OS. This includes building new screens, adding components, wiring Flask API endpoints, debugging React/Vite issues, updating agent cards, approval queue logic, brand dashboard, content hub, meeting room, or any UI/UX work on the dashboard. Trigger this skill whenever the user mentions "GRID CONTROL", "dashboard", "frontend", "agent cards", "approval interface", "brand dashboard", "meeting room", or "content hub" in the context of the Marketing OS project. Read this BEFORE writing a single line of code or giving any Claude Code instructions.
---

# GRID CONTROL — Dashboard Skill

## What GRID CONTROL Is
The internal command-and-control frontend for OffGrid Marketing OS.
A dark-mode React dashboard that gives Gaurav full visibility and control over 15 AI agents,
content approval, brand health, and agent training — all running locally on Mac.

**App Name:** GRID CONTROL
**Tagline:** Your agents. Your brand. Your command.
**Owner:** Gaurav Khanna, CEO of OffGrid Creatives AI
**Status:** FULLY BUILT AND VERIFIED — all 8 screens live

---

## Tech Stack (Locked — Do Not Change)

| Layer | Technology | Notes |
|-------|-----------|-------|
| Frontend Framework | React 19 | |
| Build Tool | Vite | Latest |
| Language | TypeScript | Strict mode |
| UI Components | shadcn/ui | Default style, slate base, oklch color tokens |
| CSS | Tailwind CSS v4 | `@tailwindcss/vite` plugin ONLY. NO postcss config. NO tailwind.config.js |
| State Management | Zustand + persist | `grid-control-store` in localStorage |
| Data Fetching | TanStack Query v5 | `useQuery`, `useMutation`, `useQueryClient` |
| Backend API | Flask (Python) | `dashboard_api.py` |
| Port — Frontend | 5173 (Vite default) | |
| Port — Flask API | 5001 | |

---

## Project Locations

| Path | What It Is |
|------|-----------|
| `/Users/gauravoffgrid/offgrid-marketing-os/` | Root of Marketing OS |
| `/Users/gauravoffgrid/offgrid-marketing-os/dashboard/` | GRID CONTROL React app |
| `/Users/gauravoffgrid/offgrid-marketing-os/dashboard_api.py` | Flask API |
| `/Users/gauravoffgrid/offgrid-marketing-os/brands/{slug}/` | Per-brand data (isolated) |
| `/Users/gauravoffgrid/offgrid-marketing-os/agents/` | Python agent scripts |
| `/Users/gauravoffgrid/offgrid-marketing-os/ceo_brain/orchestrator.py` | CEO Brain |

---

## Architecture

```
GRID CONTROL React (port 5173)
        ↕  HTTP via Vite proxy (/api → localhost:5001)
Flask dashboard_api.py (port 5001)
        ↕  reads/writes
brands/{slug}/  (brand_profile.json, session_state.json, trends_live.json, outputs/)
agents/*.py     (subprocesses spawned per run, receive ACTIVE_BRAND env var)
ceo_brain/      (orchestrator, session state, Notion push)
```

---

## File Structure (Complete)

```
dashboard/src/
├── main.tsx                  Forces dark mode on html element
├── App.tsx                   Screen router — screens 1,2,3,4,5,6,8,9 (no Screen 7)
├── index.css                 HSL CSS variables, dark GRID CONTROL theme
├── types/index.ts            All shared TypeScript types
├── lib/utils.ts              cn() utility
├── store/
│   └── brandStore.ts         Zustand + persist. individualHistories, groupHistories,
│                             activeBrand, activeScreen survive refresh.
├── components/
│   ├── Sidebar.tsx           Collapsible nav, BrandSwitcher embedded
│   ├── BrandSwitcher.tsx     Dropdown + inline Add Brand form
│   ├── AgentCard.tsx         Per-agent status card
│   └── CEOBrainCard.tsx      CEO Brain orchestrator card
├── screens/
│   ├── AgentCommandCenter.tsx  Screen 1
│   ├── ApprovalQueue.tsx       Screen 2
│   ├── ContentHub.tsx          Screen 3
│   ├── BrandOnboarding.tsx     Screen 4
│   ├── BrandDashboard.tsx      Screen 5
│   └── MeetingRoom.tsx         Screen 8
└── pages/
    ├── OutputViewer.tsx        Screen 6 — LIVES IN pages/ NOT screens/
    └── WorkflowScreen.tsx      Screen 9 — LIVES IN pages/ NOT screens/
```

**CRITICAL:** OutputViewer and WorkflowScreen are in `pages/` not `screens/`. Do not move them.

---

## 8 Screens — Current Status

| # | Name | File | Status |
|---|------|------|--------|
| 1 | Agent Command Center | screens/AgentCommandCenter.tsx | ✅ Run buttons wired to real agent subprocesses via Flask |
| 2 | Approval Queue | screens/ApprovalQueue.tsx | ✅ Approve / Reject / Request Changes fully wired |
| 3 | Content & Media Hub | screens/ContentHub.tsx | ✅ Filter + download wired |
| 4 | Brand Onboarding | screens/BrandOnboarding.tsx | ✅ Reads/writes brand_profile.json |
| 5 | Brand Dashboard | screens/BrandDashboard.tsx | ✅ Profile + session_state + trends_live |
| 6 | Agent Outputs | pages/OutputViewer.tsx | ✅ Reads /api/dashboard-output |
| 8 | Agent Meeting Room | screens/MeetingRoom.tsx | ✅ Chat wired to POST /api/agents/chat. History persists in session_state.json AND localStorage |
| 9 | Workflow Screen | pages/WorkflowScreen.tsx | ✅ 3-column: pipeline / output+approval / run log |

---

## What Is PENDING (Next Build Phase)

In priority order:
1. **Competitor post scraper** — Trend Researcher currently only uses hashtag scraper. Need `apify/instagram-scraper` on competitor handles from `competitors_db.json` to pull their actual post data and feed it into the analysis.
2. **Data quality gate** — Bot filter (min 500 followers, min 0.5% ER) before scraped data reaches any agent. Currently no filtering.
3. **Performance feedback loop** — After content is approved and posted, the results feed back into the next Trend Researcher run. Closes the loop.
4. **CEO Brain contradiction detector** — Cross-agent check: if Strategy Agent says "premium positioning" but Script Writer generates price-led hooks, flag it.
5. **ElevenLabs voice** — Agent voice in Meeting Room. Blocked on free tier limit. Code is correct. Resume when paid plan active.

---

## Flask API Endpoints (All Active)

| Method | Path | Purpose |
|--------|------|---------|
| GET | `/api/health` | Health check |
| GET | `/api/agents` | List 15 agents with config |
| GET | `/api/agents/status` | Live status of all agents |
| POST | `/api/agents/run` | Run agent subprocess (`ACTIVE_BRAND` set in env) |
| POST | `/api/agents/chat` | Chat with agent (calls Claude API with agent context) |
| POST | `/api/agents/train` | Append training note to agent context |
| GET | `/api/brands` | List all brands from brands/ directory |
| POST | `/api/brands/create` | Create new brand folder + bootstrap files |
| GET | `/api/outputs/pending?brand_slug=` | Pending approval queue |
| GET | `/api/outputs/all?brand_slug=` | All outputs |
| POST | `/api/outputs/approve` | Move to approved/ |
| POST | `/api/outputs/reject` | Delete pending file |
| POST | `/api/outputs/request-changes` | Save change note |
| GET | `/api/outputs/download/<filename>` | Stream download |
| GET | `/api/brand/profile?brand_slug=` | Read brand_profile.json |
| POST | `/api/brand/profile?brand_slug=` | Write brand_profile.json |
| GET | `/api/brand/dashboard?brand_slug=` | Combined profile + session_state + trends_live |
| GET | `/api/connections/check` | Validate all API tokens |
| GET | `/api/config/keys` | Show which keys are set |

---

## The 15 Agents (Current Models)

| # | Agent Name | Model |
|---|-----------|-------|
| 0 | CEO Brain | claude-opus-4-6 |
| 1 | Strategy Agent | claude-opus-4-6 |
| 2 | Content Planner | claude-sonnet-4-6 |
| 3 | Script Writer | claude-sonnet-4-6 |
| 4 | Creative Director | claude-opus-4-6 |
| 5 | Ad Strategist | claude-opus-4-6 |
| 6 | Data Analyst | claude-sonnet-4-6 |
| 7 | Funnel Specialist | claude-sonnet-4-6 |
| 8 | Trend Researcher | claude-sonnet-4-6 |
| 9 | Website Agent | claude-sonnet-4-6 |
| 10 | Brand Guardian | claude-opus-4-6 |
| 11 | SEO+AEO Agent | claude-sonnet-4-6 |
| 12 | Email Marketing Agent | claude-sonnet-4-6 |
| 13 | Community Manager | claude-sonnet-4-6 |
| 14 | DM+Customer Hunter | claude-sonnet-4-6 |

---

## Non-Negotiable Build Rules

1. **No assumed data** — every field reads from real JSON files. No hardcoded mock content.
2. **No generic placeholder UI** — every component is purpose-built for OffGrid agents.
3. **Flask API checks file existence** before returning data. Never crashes on missing file.
4. **Dark mode only** — `class="dark"` on `<html>`. No toggle. No light theme.
5. **Tailwind v4** — `@tailwindcss/vite` only. No postcss. No tailwind.config.js.
6. **TanStack Query v5** — No `onSuccess`/`onError` in `useQuery`. Use `useEffect` watching `data`.
7. **Zustand persist** — Store wraps `create()` with `persist()`. `partialize` on histories + activeBrand only.
8. **TypeScript strict** — No `any` types. Every data shape typed to match JSON structures.
9. **Flask API on port 5001** — no conflict with Railway or other dev servers.
10. **Claude Code writes code** — Gaurav and Claude plan only. Never reverse this.
11. **All agent subprocesses receive `ACTIVE_BRAND` env var** — agents must read brand from env, not hardcoded defaults.
12. **cost_reporter.py uses `importlib.util`** — do NOT use `import supabase.db` — pip package conflict.

---

## Known Critical Patterns

### Agent Subprocess Pattern (dashboard_api.py)
```python
env = os.environ.copy()
env["ACTIVE_BRAND"] = brand_slug
env["GRID_RUN_ID"] = run_id
env["GRID_BRAND_SLUG"] = brand_slug
subprocess.Popen(["python3", agent_script], env=env, ...)
```

### Trend Researcher Dynamic Hashtags
`_build_niche_hashtags(brand_profile)` reads `brand_profile["product"]` + `brand_profile["industry"]`
and returns appropriate hashtags for fashion/SaaS/food/beauty/fitness/generic.
Never use hardcoded `NICHE_HASHTAGS` constant.

### Output Folder Naming (orchestrator.py)
```python
import re as _re
agent_folder = _re.sub(r"[^a-z0-9-]", "", agent_name.lower().replace(" ", "-")).strip("-")
```
Always slugified. "Trend Researcher" → "trend-researcher".

### Zustand Store Persist (brandStore.ts)
```typescript
export const useBrandStore = create<BrandStore>()(
  persist(
    (set) => ({ ... }),
    {
      name: "grid-control-store",
      partialize: (state) => ({
        individualHistories: state.individualHistories,
        groupHistories: state.groupHistories,
        activeBrand: state.activeBrand,
        activeScreen: state.activeScreen,
      }),
    }
  )
)
```

### MeetingRoom handleSelectAgent (MeetingRoom.tsx)
```typescript
const handleSelectAgent = (agent: Agent) => {
  setSelectedAgent(agent)
  // DO NOT call clearIndividualHistory here — it wipes in-memory history on every click
}
```

---

## Before Writing Any Claude Code Instructions — Checklist

1. Is this reading real data from brands/{slug}/ — never assumed?
2. Is the Flask endpoint handling missing files gracefully?
3. Is the component typed with proper TypeScript interfaces?
4. Is dark mode preserved?
5. Is it using TanStack Query v5 patterns (no onSuccess in useQuery)?
6. Is Tailwind v4 pattern correct (no postcss, no config file)?
7. Does the agent subprocess receive ACTIVE_BRAND env var?
8. Is cost_reporter using importlib.util, not import supabase.db?
