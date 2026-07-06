# GRID CONTROL — Front-End Handoff

> Owner: **Senior (backend) Dev**. Audience: **an AI UI builder (Emergent / Manus / Lovable / Replit) or a designer.**
> The builder has a **free hand on the UI** — including 3D assets, animation, 3D objects. This package gives them
> (a) how our backend works + what data exists, and (b) a **design *direction*** — never a pixel spec.
> **Read `docs/FE_DESIGN_DIRECTION.md` for the creative brief; the rest of this package is the technical contract.**

## 1. What this project is
GRID CONTROL is the dashboard for an 18-agent autonomous marketing system. A founder reviews, directs, and
approves the agents' work from one cockpit. Backend = Flask (`core.py` + `routes/` blueprints) + Supabase
(Postgres/Auth/RLS) + 18 agent subprocesses. The cockpit front-end is a **new build** (React + Tailwind +
shadcn) that talks to the existing `/api/*` surface.

## 2. Status at handoff (Jun 17 2026)
- ✅ Backend **code-complete and deployed to prod** (Railway). Health: `GET /api/health` → 200.
- ✅ Auth, multi-brand isolation, approval gates, cost tracking, scheduler worker — all live.
- ✅ **CORS open** (`CORS(app)`) — verified: a Lovable-origin preflight to `/api/brands` returns
  `access-control-allow-origin` + `authorization` allowed. FE can call prod from any origin today.
- ⏳ One **paid validation run** pending — happens **after** the FE is designed + wired (not a blocker for FE work).
- ⚠️ Pre-launch hardening (not now): lock CORS to specific origins; IDOR pass on download/media routes.

**Prod URLs**
- API: `https://web-production-175d5.up.railway.app`
- Dashboard (current/old): `v0-grid-control-dashboard.vercel.app` (the new cockpit replaces this)
- Repo: `github.com/offgridcreativesai-glitch/Grid-Control` (branch `main`)

## 3. How we work (agency workflow)
Contract-first. Four phases, each with a Definition of Done (DoD):

| Phase | Owner | Definition of Done |
|---|---|---|
| **1. Contract** | Senior dev | API_REFERENCE.md + openapi.yaml + screen→endpoint map published and accurate (verified against live API). |
| **2. Build (design)** | FE dev | Cockpit screens built against the contract using mock data matching the documented shapes. Lovable prompt = `dashboard/mockups/COCKPIT_DESIGN_PROMPT_LOVABLE.md`. |
| **3. Integrate (wire)** | FE dev | Each screen swapped from mock → real endpoint per the screen→endpoint map. Auth + brand switching working end-to-end. |
| **4. QA / validate** | Both | All screens render real prod data; approval actions work; then the paid validation run exercises the full pipeline. |

Rule: **the contract is the source of truth.** If reality and the contract disagree, fix the contract (or the
code) — never let the FE silently depend on undocumented behavior.

## 4. Deliverables index
| ID | Deliverable | File | Status |
|----|-------------|------|--------|
| **D0** | **Master build prompt — PASTE THIS into the AI UI tool** | `docs/FE_MASTER_PROMPT.md` | ✅ |
| D0b | Design direction (longer creative brief) | `docs/FE_DESIGN_DIRECTION.md` | ✅ |
| D1 | This handoff doc | `HANDOFF.md` | ✅ |
| D2 | API contract (cockpit endpoints) | `docs/API_REFERENCE.md` | ✅ |
| D3 | OpenAPI spec | `docs/openapi.yaml` | deferred |
| D4 | Screen → endpoint map | `docs/SCREEN_ENDPOINT_MAP.md` | ✅ |
| D5 | Auth / conventions / env | `docs/FE_INTEGRATION_GUIDE.md` | ✅ |
| D6 | TypeScript types | `docs/api-types.ts` | ✅ |
| ref | Old cockpit concept (one reference, NOT the target) | `dashboard/mockups/COCKPIT_DESIGN_PROMPT_LOVABLE.md` | — |
| ref | Existing wired app (wiring example only, not the design) | `dashboard/` | — |

**Who builds the UI:** an AI tool (Emergent / Manus / Lovable / Replit) with a free hand — 3D + animation
encouraged. **What's fixed:** the backend contract + the non-negotiable product behaviors in
`FE_DESIGN_DIRECTION.md` §7. Everything visual is the builder's call.

## 5. Getting started (15 min, FE dev)
1. **Talk to prod directly** (no local backend needed): base URL = `https://web-production-175d5.up.railway.app`.
   Smoke test: `curl https://web-production-175d5.up.railway.app/api/health` → `{"status":"ok"}`.
2. **Auth:** Supabase Auth (email/password) → JWT → send as `Authorization: Bearer <jwt>` on every `/api/*` call.
   See `docs/FE_INTEGRATION_GUIDE.md`. Supabase project URL + anon key are FE env vars.
3. **Brand context:** every data call takes `?brand_slug=<slug>` (e.g. `askgauravai`). The brand switcher drives this.
4. **Never render raw JSON** — agent outputs are pre-formatted markdown (Rule 8). See the guide.
5. **Build order:** follow `docs/SCREEN_ENDPOINT_MAP.md` — build each screen against mocks, then wire it.

## 6. Conventions (full detail in D5)
- All endpoints under `/api/*`. JSON envelope: `{ "success": true, "data": ... }` or `{ "success": false, "error": "..." }`.
- Auth via Supabase JWT bearer. Multi-tenant: data is brand-scoped + RLS-enforced.
- `?brand_slug=` is required on brand data endpoints; TanStack queries are keyed by `activeBrand.slug`.
- Agent outputs are markdown, not JSON (Rule 8). SSE event bus streams run/approval updates.
