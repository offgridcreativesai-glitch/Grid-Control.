# Grid Control — Scored Assessment vs CRED/Myntra/Canva Caliber (Jul 3 2026)

Scores are against "a product those teams would ship to paying users," not
against "impressive for a solo founder + Claude." That bar is deliberately
brutal; the numbers say where the distance is, not whether the work is good.

**Overall: 4.5 / 10** — a real system with a real moat-shaped core (approval
gate + provenance + cost metering + per-brand isolation are genuinely ahead of
the NoimosAI/Sureflow class), wrapped in pre-production reliability, security,
and product-feel.

| Area | Score | Why (specific, not diplomatic) |
|---|---|---|
| Agent architecture / orchestration | 6/10 | 18 agents mapped 1:1 to real agency jobs — the shape is right and rare. Orchestrator, trust dial, provenance validator, cost gateway all exist and work. Docked: content agents bypass their own BaseAgent (no memory hooks), duplicate boilerplate ×20, and until today reasoned identically for every brand type. |
| Product depth (does it feel like an agency?) | 4/10 | The full 16-step cycle exists in code — weekly/monthly/quarterly programs included, which competitors don't have. But the client can't FEEL the rhythm: no week view, one flat approval queue, outputs presented without the "here's what we did and why" account-manager wrapper. This is the CRED-caliber gap: they'd obsess the felt experience of "my team is working." |
| Security | 4/10 | Auth, RLS, path validation, rate limiting all present (more than most prototypes). But any-origin CORS + a static god header + shell=True in one endpoint + plaintext tokens is not a combination you take a paying client's Instagram into. All four are cheap fixes; that they're cheap is why the score isn't 2. |
| Reliability / ops | 3/10 | The worst unbuilt risk in the system: brand state on ephemeral Railway disk. One redeploy = client memory + pending approvals + tokens gone. No CI, no staging env, no error alerting (Make.com webhook pending). A Myntra-caliber team would call this a sev-1 design flaw. |
| Cost engineering | 6/10 | Genuinely better than the field: per-run cost rows, per-brand usage_logs, daily cap circuit breaker, fail-closed paid-ops switch, routed model tiers. Docked: script-writer on Opus violates the system's own routing rule (5×), cap is per-process not global, ledger on ephemeral disk. |
| Frontend polish | 6/10 | React 19 + the cinematic persona design is distinctive and mostly real (live API calls, demo mode cleanly isolated). Docked: 20 pages of varying wiring depth, no loading/error-state discipline audit, and the visual identity is ahead of the information architecture (see product depth). |
| Data/provenance integrity | 7/10 | Rule 10 with fuzzy-matched citation validation + rerun loop is the single most differentiated engineering in the repo — no competitor teardown shows anything like it. Docked: not yet on trend-researcher AutoResearch; validator thresholds (0.30 Jaccard) untested against adversarial paraphrase. |
| Testing / quality culture | 2/10 | 14 unit tests (12 added today) for ~20K LOC that spends real money and posts to real accounts. Invariant paths (approval transitions, cap math, publish) untested. This is the largest culture gap vs any reference-caliber team. |
| Multi-tenancy | 5/10 | RLS + brand_members + per-brand env overlay + slug validation: the bones are right. Docked: filesystem tenancy (brands/ dirs) undermines the DB tenancy; the static secret bypasses tenant identity entirely. |
| Docs / operability | 6/10 | CLAUDE.md + context packages + graphify vault are unusually good institutional memory. Docked: none of it is runbook-shaped for a second operator; bus-factor is exactly 1. |

## The three moves that close the most distance

1. **Make state durable and tenancy real** (reliability 3→6, multi-tenancy 5→7,
   security 4→6): Railway volume or Supabase Storage for `brands/`, ledger into
   usage_logs, CORS allowlist, kill the god header for client traffic. This is
   days, not weeks, and it converts "demo that can take a client" into
   "product that can keep one."

2. **Ship the operating rhythm to the client's eyes** (product depth 4→7): week
   view + queue lanes + the weekly review card as the emotional center of the
   product. GC's actual bet (brief §1) is judgment + cadence, not content
   volume — the UI should sell exactly that. This is the only item on this page
   competitors can't copy in a weekend, because GC already has the backend
   programs feeding it.

3. **Test the invariants + CI** (testing 2→6): one day of pure-unit tests on
   approval gate, trust dial, paid-ops math, provenance validator, publish
   runner + GitHub Actions. Every future rebuild session (like this one) gets
   10× safer, which compounds.

## On "THE SECRET" (8 personas hiding 18 agents) — keep it

Argued both ways per brief §6:
- *Show real agents:* transparency, debuggability, power users could target runs.
- *Keep personas:* a brand owner hires OUTCOMES, not org charts. A real agency
  doesn't introduce the client to all 18 staff either — they meet the account
  team. 18 tiles = 18 things to worry about; 8 characters = a team you can
  hold in your head. The trust dial + run log already expose the real machinery
  to whoever looks.
Verdict: personas stay for clients; add a "crew manifest" view under System
(super-admin only) mapping persona → real agents → last runs, so the secret
never blocks debugging with a client on a call.
