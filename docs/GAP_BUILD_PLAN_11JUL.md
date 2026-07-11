# Gap Build Plan — reference-driven, Claude Code builds (Jul 11 2026)

Follows [COMPETITOR_ANALYSIS_BACKEND_GAPS_10JUL.md](COMPETITOR_ANALYSIS_BACKEND_GAPS_10JUL.md).
Approach decision below, then repos + a phased plan per gap.

## The approach decision (and why)

**Chosen: study proven repos → Claude Code builds the integration into GC's existing patterns.**
NOT Fable-as-builder. NOT from-scratch-no-reference.

- **Fable is a storytelling model, not a coding agent.** Opus 4.8 in Claude Code is the builder.
  GC's own working rule: "Claude Code writes every line of code." The one Fable spawn failed on
  session limits + tool outages. Fable's real value = the creative/voice/narrative layers (content,
  creative briefs, report prose) — a *contributor to output*, not the systems builder.
- **Licenses force reference-only anyway.** The strongest OSS in these categories is **AGPL/GPL**
  (Apphera, Plausible, AtroDAM, Socioboard). Vendoring copyleft code into a proprietary SaaS is a
  legal trap (ties into the existing legal risk register). So we read them for architecture, borrow
  permissively-licensed pieces only, and write our own integration. This is exactly what the
  Perplexity PDF advised: copy the concept + table-stakes, build your own workflow/UX.
- **From-scratch-no-reference** wastes money reinventing solved problems (violates the "use the
  tools/repos given" rule).

Net: reference-driven CC-build is the same conclusion from three angles — model fit, license safety,
and cost. Fable plugs into the creative layer where it's genuinely better.

---

## Repos per gap (reference shelf)

### Gap #1 — Reputation / reviews / listings engine (we have zero)
- **Apphera** (via [social-media-monitoring-open-source](https://github.com/openstream/open-social-media-monitoring)) — review aggregation across Yelp/TripAdvisor/etc. **AGPL → reference only.**
- **[MantisClone/awesome-reputation-systems](https://github.com/MantisClone/awesome-reputation-systems)** — curated map of reputation-system designs (borrow the data model + scoring ideas).
- Borrow: the review-ingestion → sentiment → response-draft loop shape. Build: a GC `reputation` agent + `routes/reputation.py`, gated behind `GRID_PAID_OPS` for paid review-source pulls.

### Gap #2 — White-label / multi-tenant SaaS packaging (primitives exist, unpackaged)
- **[ixartz/SaaS-Boilerplate](https://github.com/ixartz/SaaS-Boilerplate)** — multi-tenancy + teams + roles/permissions + user impersonation + billing. Best *pattern* reference.
- **[nextjs/saas-starter](https://github.com/nextjs/saas-starter)** (15.8k★) + **LastSaaS** — white-label branding + tenant billing patterns.
- Note: these are **Next.js**; GC is React+Vite+Flask. So it's a **pattern** borrow (tenant model, RBAC, impersonation, per-seat billing, brand-your-own-theme), not a drop-in. We already have brand isolation + Supabase RLS + Razorpay — this packages them into an agency "reseller" tier.

### Gap #3 — Creative asset OS / library (CD generates, no library)
- **[AtroDAM](https://github.com/atrocore/atrodam)** (GPL → reference), **ResourceSpace** (BSD → some code reusable), **[unopim-DAM](https://github.com/unopim/unopim-digital-asset-management)** (Laravel).
- Borrow: asset model (metadata, tags, versions, variants), gallery UX, approval states. Build: a
  GC creative library over the existing per-brand file storage (`content.py` / `get_brand_dir`) +
  a Creative Library page. **Fable contributes here** (creative direction / variant copy), CD agent
  stays the generator (cd_guard hook), CC builds the store + UI.

### Gap #4 — Social listening / brand-mention monitoring (replies only today)
- **[openstream/open-social-media-monitoring](https://github.com/openstream/open-social-media-monitoring)** (keyword tracking, reference), **[brand-monitoring GitHub topic](https://github.com/topics/brand-monitoring)** — an AI social-listening tool tracking mentions across IG/FB/TikTok/Reddit/X via SERP API + LLM → structured insights + charts.
- Borrow: the mention → structured-insight → alert loop. Build: a GC `listening` agent feeding the
  situation/insight layer; paid sources gated by `GRID_PAID_OPS`. Overlaps Noimos's Social Listening Agent.

### Gap #5 — Analytics cockpit (data exists, UI thin)
- **[plausible/analytics](https://github.com/plausible/analytics)** (AGPL → UX reference), **[NafisRayan/Social-Media-Dashboard](https://github.com/NafisRayan/Social-Media-Dashboard)** (Next/React/TS, MIT-ish → component reference), **Socioboard** (reporting patterns).
- Borrow: dashboard layout + chart patterns. Build: upgrade the existing Insights page into a real
  cockpit over `data_analyst` output. Lowest risk — polish, not engine. Use the `dataviz` skill.

---

## Phased plan (aligned to the positioning wedge)

**Phase 1 (now) — finish the founder-facing core.** Already validated (onboarding→audit→approve→content).
Close **Gap #5 (analytics cockpit)** and **Gap #3 (creative library)** — both client-visible, moderate
lift, both support the flow Gaurav is dogfooding. Recommended FIRST: **Gap #3 creative library**
(approved visuals need a home; NoimosAI's edge; Fable can contribute creatively).

**Phase 2 — intelligence UX.** Close **Gap #4 (social listening)** → "next best move" cards (the Social
Lollipop angle) on top of intel we already scrape.

**Phase 3 — monetization + expansion.** Close **Gap #2 (white-label SaaS Mode)** = the agency reseller
tier (the real revenue unlock). **Gap #1 (reputation)** only if we pursue multi-location clients —
otherwise consciously out of scope for the D2C wedge.

Each gap ships GC-native: an agent (where relevant) + `routes/*` + a dashboard page, behind the
approval gate, paid sources behind `GRID_PAID_OPS`, provenance per Rule 10.

## CONFIRMED build sequence (Jul 11) — approach: Claude Code + repos as reference

Execute in order, one at a time, each behind Gaurav's explicit go and the approval gate. Every gap
ships GC-native: agent (where relevant) + `routes/*` + a `dashboard/src/pages/*` surface; paid
sources behind `GRID_PAID_OPS`; provenance per Rule 10.

**1. Creative Library (Gap #3) — Phase 1 · effort M**
- Goal: approved/generated visuals get a versioned, tagged home + reuse.
- CC builds: asset store over `content.py`/`get_brand_dir` (metadata, tags, variants, versions,
  approval state) + `routes/creative_library.py` + a Creative Library page. CD agent stays the
  generator (cd_guard). Reference: AtroDAM / ResourceSpace asset model + gallery UX.
- Fable: creative direction / variant copy for assets. CC: the store + UI.

**2. Analytics Cockpit (Gap #5) — Phase 1 · effort S–M**
- Goal: turn the thin Insights page into a real client dashboard over `data_analyst` output.
- CC builds: dashboard layout + charts (use the `dataviz` skill), no new engine. Reference:
  plausible + NafisRayan/Social-Media-Dashboard component patterns. Lowest risk.

**3. Social Listening (Gap #4) — Phase 2 · effort M–L**
- Goal: mention + sentiment tracking → "next best move" cards (Social Lollipop angle).
- CC builds: `listening` agent (mention→structured-insight→alert) + route + panel; feeds the
  situation/insight layer built today. Paid sources gated. Reference: open-social-media-monitoring +
  the brand-monitoring SERP+LLM pattern.

**4. White-label SaaS Mode (Gap #2) — Phase 3 · effort L**
- Goal: agency reseller tier — sub-accounts, per-seat pricing, brand-your-own cockpit (the revenue unlock).
- CC builds: tenant/role layer + reseller billing on top of existing brand isolation + RLS + Razorpay.
  Reference: ixartz/SaaS-Boilerplate + nextjs/saas-starter patterns (not drop-in; GC is React+Flask).

**5. Reputation Engine (Gap #1) — optional/last · effort L**
- Only if we pursue multi-location clients. Else consciously OUT for the D2C wedge.
- CC builds: `reputation` agent + `routes/reputation.py` (review ingest→sentiment→response-draft),
  paid pulls gated. Reference: awesome-reputation-systems data model; Apphera loop shape (AGPL, ref only).

## Fable's actual role from here
Creative + narrative generation *inside* the pipeline (creative briefs, variant copy, report prose,
voice) — where a storytelling model beats a coding model. Systems/integration = Claude Code. This
honors "let Fable do more" without making a creative model the backend engineer.
