# OffGrid Marketing OS — Project Context File

## TODAY'S MISSION: BUILD GRID CONTROL DASHBOARD — PHASE 1

## Two Products (NEVER MIX)
- Brain Sync = Marketing OS (local Mac, multi-agent system)
- Brain Sync Report = Railway SaaS pipeline (Google Forms→Make→Apify→Claude→Railway→Gmail)

## Marketing OS Status
BUILT AND RUNNING. 20 agents confirmed. All packages installed.
Path: /Users/gauravoffgrid/offgrid-marketing-os
Python: 3.14.3 | Claude Code: 2.1.80

## GRID CONTROL Dashboard — What We're Building
Internal command dashboard for the Marketing OS.
- App name: GRID CONTROL
- Stack: React 19 + Vite + TypeScript + shadcn/ui + Tailwind v4
- Base template: satnaing/shadcn-admin (GitHub, free, MIT)
- Backend: Flask API (dashboard_api.py) on port 5001
- Frontend: Vite dev server on port 5173
- Dark mode ONLY. No light mode. No toggle.
- Skill file: .claude/skills/grid-control-dashboard/SKILL.md

## 6 Screens
1. Agent Command Center — 14 agent cards, run buttons, live status
2. Approval Queue — review/approve/reject agent outputs
3. Brand Dashboard — platform health, content pipeline, calendar
4. Brand Onboarding Form — reads/writes data/brand_profile.json
5. Content & Media Hub — all assets, download, share
6. Agent Meeting Room — chat with agents, train them, standups

## Phase Build Order
Phase 1 (NOW): Foundation — clone template, dark mode, Flask API, sidebar nav, boot confirmed
Phase 2: Agent Command Center + Approval Queue
Phase 3: Brand Dashboard + Brand Onboarding
Phase 4: Content Hub + Meeting Room
Phase 5: Voice (ElevenLabs) — future

## Next Steps After Dashboard
1. Meta Graph API — payment pending (1-2 days), then add META_GRAPH_API_TOKEN to .env
2. ManyChat Free — Instagram DM automation (replaces OpenClaw)
3. Dux-Soup $11.25/mo — LinkedIn outreach (replaces OpenClaw)
4. OpenClaw — SKIPPED permanently (security risk + creator left project)
5. Fire Trend Researcher — first live agent run AFTER Phase 1 done

## Ground Rules (Non-Negotiable)
- Zero assumptions. All data from real files. No hardcoded mock data.
- Nothing posts without Gaurav's approval.
- Claude Code writes ALL code. Gaurav + Claude = planners only.
- Terminal method: cat > file << EOF. Always verify with ls.
- Flask API checks file existence before reading. Never crashes on missing file.
- Every agent change needs Gaurav's permission.
- Short conversations. Start fresh each session.

## Key File Paths
- Agents: .claude/agents/ (14 .md files)
- Data: data/brand_profile.json, session_state.json, trends_live.json
- Pending outputs: outputs/pending_approval/
- Approved outputs: outputs/approved/
- Dashboard: dashboard/ (to be created in Phase 1)
- Flask API: dashboard_api.py (to be created in Phase 1)

## Tool Decisions Made
- Instagram DMs: ManyChat Free (official Meta API, zero ban risk)
- LinkedIn outreach: Dux-Soup ($11.25/mo, safest, 300k+ users)
- Data scraping: Apify (already connected, replaces PhantomBuster)
- UI: GRID CONTROL (React local, not Lovable — full ownership, zero cost)
- Lovable: use only for future client-facing landing pages

## Memory Keywords
- "Brain Sync" = resume Marketing OS session
- "Brain Sync Report" = resume Railway SaaS session
- "Brain Sync Build" = start GRID CONTROL Phase 1 build
