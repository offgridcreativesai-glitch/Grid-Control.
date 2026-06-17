# GRID CONTROL — Screen → Endpoint Map

> Turns the Lovable cockpit mockup (`dashboard/mockups/COCKPIT_DESIGN_PROMPT_LOVABLE.md`) into a wiring spec.
> Each screen lists the endpoints that feed it. `✓` = shape documented in API_REFERENCE.md. `?` = endpoint
> exists, shape to verify next pass. Build order = top to bottom.

Legend: 🟢 GET (read) · 🟠 POST/action · all take `?brand_slug=` unless noted.

## Global (every screen)
- Brand switcher → 🟢 `/api/brands` ✓ , 🟢 `/api/auth/me` ✓
- Auth → Supabase JWT (see FE_INTEGRATION_GUIDE.md), 🟢 `/api/auth/brands` ✓
- Concierge (⌘J "The Brain") → 🟠 `/api/concierge` ✓ (tiered; trivial reads tokenless) → falls through to 🟠 `/api/brain/chat` ? for substantive

## 1. Command Center (home)
- Headline + summary line → 🟢 `/api/brand/summary` ✓ (posts_scripted, notion_*, completed_agents)
- **NEEDS YOU** queue → 🟢 `/api/brands/<slug>/needs-you` ? (pending items) + 🟢 `/api/outputs/pending` ?
  - Approve / Reject / Change actions → 🟠 `/api/outputs/approve` ? · `/api/outputs/reject` ? · `/api/outputs/revise` ✓(K3)
- Brand Health (Followers/Engagement/Saves/Reach, "LIVE") → 🟢 `/api/performance/history` ? + real social metrics (data-analyst) — **verify the live-metrics endpoint**
- Your Team (6 role cards) → 🟢 `/api/agents/status` ✓ (FE collapses 18 agents → 6 roles; mapping in API_REFERENCE Group C / CLAUDE.md)
- Overnight activity strip → 🟢 `/api/brand/summary` ✓ (`activity_feed`)

## 2. Content
- Month calendar (draft/published/needs-approval chips) → 🟢 content calendar — **verify endpoint** (likely `/api/dashboard-output` `calendar_formatted` or `/api/brand/dashboard`)
- Pipeline kanban → 🟢 `/api/outputs/all` ? (pending + approved buckets)
- Preview media → 🟢 `/api/outputs/media/<path>` ?
- Publish → 🟠 `/api/publish` ? (platform-routed; IG live, others prepared)

## 3. Growth
- Community (incoming + drafted replies) → 🟢 `/api/outputs/pending?agent=community-manager` ? → approve via outputs/* 
- Lead Pipeline (ICP-scored prospects) → 🟢 `/api/outputs/pending?agent=dm-customer-hunter` ?
- Funnel & Email → 🟢 subscribers/leads (`/api/leads` family) ? + email drafts `/api/outputs/pending?agent=email-marketing-agent` ?

## 4. The Team
- 6 roles ↔ 18 agents toggle → 🟢 `/api/agents/list` ✓ + 🟢 `/api/agents/status` ✓
- Agent detail (recent runs, output, cost) → 🟢 `/api/brands/<slug>/runs` ? + 🟢 `/api/agents/conversation` ✓ + 🟢 `/api/brands/<slug>/costs` ?
- Trigger a run → 🟠 `/api/agents/run` ✓ (cost-gated server-side) → poll 🟢 `/api/agents/run/status` ✓

## 5. Insights
- KPI tiles + 30-day chart → 🟢 `/api/performance/history` ? (+ metrics endpoint, verify)
- Top performing content → 🟢 `/api/published` ? / performance data
- **COST & TOKENS panel (signature)** → 🟢 `/api/brands/<slug>/costs` ? + 🟢 `/api/billing/usage` ?

## 6. Memory & Brain
- Story-so-far timeline → 🟢 `/api/brands/<slug>/narrative` ? (append-only entries)
- "What the system knows" card → 🟢 `/api/brands/<slug>/intelligence` ? / `/api/brands/<slug>/memory` ?
- Memory approve (pending suggestions) → 🟠 `/api/brands/<slug>/memory/approve` ?

## Connections
- Platform status rows → 🟢 `/api/brands/<slug>/connections` ? (live verify, never returns tokens)
- Connect/save token → 🟠 `/api/connections/save-token` ?

## Settings
- Brand profile → 🟢 `/api/brand/profile` ✓ / 🟠 `/api/brand/profile` (POST) ✓
- Notifications toggle → (config) ; morning brief uses `/api/brands/<slug>/notify` ?

---
**Scope:** ~30 endpoints across the cockpit. The remaining ~60 (admin, billing internals, webhooks,
onboarding/brand-book, n8n) are out of cockpit scope and documented only if a screen needs them.
**Next:** verify the `?`-marked metrics/calendar endpoints, then fill their shapes into API_REFERENCE.md.
