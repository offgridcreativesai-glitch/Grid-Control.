# Grid Control — Ranked Gap/Risk Report (Fable 5 final system review, Jul 3 2026)

Ranked by (impact on shipping to a real paying brand) × (likelihood of biting).
Status column: what this review session already fixed vs what remains.

---

## #1 — HEADLINE: One psychology applied to every brand — **FIXED this session (core), residual work remains**

**Was:** `script_writer.py` hardcoded one 12-pattern hook taxonomy, one fixed
Pain/Result/Curiosity variant split, one CTA rulebook (personal-brand week-1
freebie/hire-me rules baked into the prompt for every brand). `content_planner`,
`creative_director`, `strategy_agent` same shape. A T-shirt brand got a
personal-brand psychology with the nouns swapped.

**Now:** `agents/_lib/brand_archetype.py` — an explicit STEP 0 reasoning layer:
- Classifies product / service / personal (deterministic-first: human pin >
  `brand_profile.business_model_archetype` > field/keyword heuristics, each
  signal citing its profile field; refuses to guess on zero signal — outputs
  `unknown` and instructs the agent to write conservatively and flag).
- Persisted to `brands/{slug}/brand_archetype.json` (inspectable, human-overridable).
- A per-archetype strategy TABLE (data, not if-branches) rewires STEPPS lever
  priority, hook-pattern priority, CTA distance (SHORT/LONG/RELATIONSHIP),
  proof style, consideration cycle, and the AutoResearch variant frames themselves.
- Wired into script_writer, content_planner, creative_director, strategy_agent.
  Output JSON now echoes `brand_archetype`. 7 tests in `tests/test_brand_archetype.py`.

**Residual:** carousel_designer + ad_strategist + email/dm agents not yet wired
(1–2 lines each, same pattern). Selection metrics in performance_tracker still
score all brands on save+DM regardless of archetype — product brands should be
scored on click-through/session actions. Do this before the second brand onboards.

---

## #2 — Brand data lives on an ephemeral filesystem — **UNFIXED, highest unbuilt risk**

`brands/{slug}/` (profile, memory, approvals queue, tokens in `.env`, now the
second_brain vault) is plain local disk. Railway containers get a **fresh
filesystem on every deploy/restart** unless a volume is attached. The deployed
backend on Railway therefore loses every brand's memory, pending approvals, and
connection tokens on redeploy. Locally this is invisible; with the first real
client it is data loss + re-onboarding.

**Fix (pick one, ~half-day):** (a) attach a Railway volume and point `BRANDS_DIR`
at it — smallest change; (b) move the canonical copy to Supabase Storage with a
local cache — right long-term answer since Supabase already holds brands/RLS.
The paid-ops ledger (`.grid_state/paid_ledger.json`) has the same defect — the
web process and the 24×7 worker each keep their OWN ledger, so the $5 daily cap
is actually up to $5 × N processes. Move the ledger to the existing
`usage_logs` table (it already receives every spend row).

---

## #3 — Security: four concrete holes before first client — **UNFIXED (2 now mitigated by config)**

1. **`CORS(app)` any-origin** ([core.py:48](core.py)) — with the static-secret
   auth below, any website a logged-in user visits can call the API. Fix: allowlist
   Vercel domain + localhost:5280. (15 min.)
2. **`X-Dashboard-Secret` static god header** ([core.py:133-138](core.py)) — one
   long-lived string grants full access to every brand, bypassing RLS identity.
   Fine solo; unacceptable multi-tenant. Fix: JWT-only for client traffic, scope
   the secret to server-to-server (scheduler) routes, rotate it.
3. **`shell=True`** at [routes/brain.py:234](routes/brain.py) — brain/execute runs
   shell strings. It is behind super-admin, but it is remote code execution one
   leaked secret away (see #2). Fix: argv-list subprocess, command allowlist.
4. **Plaintext platform tokens** in `brands/{slug}/.env` — combined with #2's
   filesystem issue these are both leakable and losable. Fix: encrypt at rest or
   move to Supabase with column encryption; never return them from any endpoint
   (already true).

Legal register (Jun 24) still stands: scraping ToS exposure (Apify against IG),
browser-automation posting ToS, DPDP/GDPR posture — lawyer before first paying client.

---

## #4 — Cost: routing table contradicts its own policy — **PARTIALLY DEFENSIBLE, one clear error**

Policy (CLAUDE.md + hard-earned feedback): *Opus for decisions, Sonnet for
generation.* The routing table gives **script-writer Opus/high** — a pure
generation agent, the highest-volume LLM consumer in the system (3 variants ×
5 hooks × every calendar slot × retry loop). Opus $15/$75 per MTok vs Sonnet
$3/$15 = **5× cost** on the biggest line item, against the system's own rule.
Estimated: a 30-post month at ~15K in/10K out per post ≈ $13 Opus vs $2.60
Sonnet per brand per month for script generation alone; multiply by rerun loops.

**Recommendation:** script-writer → `("sonnet", "high")` (extended thinking
stays). Keep Opus: ceo-brain, strategy-agent, brand-guardian (genuine judgment).
creative-director medium-effort Opus is arguable — try Sonnet A/B when Higgsfield
rebuild lands. Also: content agents call `anthropic.Anthropic` directly instead
of `model_gateway.complete()` — they get the routed model name but bypass the
LiteLLM path and per-call paid_ops guard; unify when convenient.

---

## #5 — Architecture debt: the agents don't use their own base class — **UNFIXED, refactor-scale**

`ScriptWriter`, `ContentPlanner`, `CreativeDirector`, `StrategyAgent` are
standalone classes wrapping `CEOBrain()`; they do NOT inherit `BaseAgent` — so
the memory hooks (session_start/end, learnings, narrative, now second_brain)
exist but the four most important agents never call them. Each also carries its
own copy of JSON-repair/prompt-boilerplate (~200 lines × 20 agents). core.py is
3,062 lines doing bootstrap+auth+rate-limit+brand-files. None of this blocks a
first client, but it is why every cross-cutting fix (like this review's STEP 0)
costs 4 edits instead of 1. Refactor direction: make content agents subclass
BaseAgent, hoist `_safe_json_loads`/prompt scaffold into `_lib`, split core.py
into app.py + auth.py + brand_files.py. Do it as the Wave-2 agents are built,
not as a big-bang.

---

## #6 — Testing: 14 tests for a system that spends money — **PARTIALLY IMPROVED**

Before today: 2 Supabase tests, no CI. This session added 12 (archetype 7,
second brain 5). Still zero coverage on: approval gate transitions, trust_dial
auto-advance, paid_ops cap math, publish_runner, provenance validator. Those
five are the invariant-bearing code paths — a regression there breaks a
non-negotiable silently. ~1 day to cover with pure-unit tests (no API calls),
plus a GitHub Actions workflow (`python3 -m pytest tests/ && cd dashboard && npm run build`).

---

## #7 — Product depth: the cycle exists, the client can't feel it — **UNFIXED, design work**

Backend implements the full 16-step agency cycle (weekly review, monthly mix,
QBR — all present). But the client-facing surface shows outputs, not the
OPERATING RHYTHM: nothing tells the client "your week: research ran Mon,
3 scripts await you Wed, review lands Fri". The single approval queue treats a
90-day strategy and one caption as the same size decision. This is the gap
between "AI dashboard" and "agency you can feel working for you" — the thing
the brief says failure looks like. Concrete: add a Week view to the Command
page fed by `schedule_config.json` + agent_runs, and split the approval queue
into strategy-level vs content-level lanes. The 8-persona "SECRET" is the right
call — keep it (detailed argument in 02_SCORED_ASSESSMENT.md).

---

## #8 — Publishing: YouTube stub + X manual — **KNOWN, sequenced**

instagram/linkedin/twitter publishers real; youtube_publisher.py minimal.
Per standing decision X is manual-upload anyway. YouTube OAuth refresh expires
~7 days while the Google app stays in Testing — "Publish app" on the audience
page before first client with YouTube. Not a launch blocker if the first brand
is IG/LinkedIn-first.

---

## Fixed-this-session summary
- #1 core: brand_archetype layer + 4 agents wired + 7 tests.
- Second brain (brief §7): `agents/_lib/second_brain.py` + BaseAgent glue + 5 tests
  (see 04_SECOND_BRAIN.md).
- Hardcoded OffGrid brand assumptions in creative_director/script_writer prompts
  (found mid-review as uncommitted work, kept + extended).

## Do-next order (after this review merges)
1. Railway volume or Supabase storage for `brands/` + ledger→usage_logs (#2).
2. CORS allowlist + secret scoping (#3.1, #3.2) — under an hour combined.
3. script-writer → Sonnet (#4) — one line in model_gateway.py, watch one week of output quality.
4. Invariant tests + CI (#6).
5. Week-view + queue lanes (#7) — first real UX investment after wiring.
