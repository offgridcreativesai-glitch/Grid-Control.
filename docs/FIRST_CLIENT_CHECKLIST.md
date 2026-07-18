# First Paying Client — Readiness Checklist

> Slices 4.3 + 4.4 (Jul 18 2026). Consolidates the Jun-24 security read + legal
> risk register with TODAY'S verified state. ✅ = verified in code/DB this date.
> 🧑 = only Gaurav can do it. ⚠️ = accepted risk, documented.

## Security — engineering side

| Item | Status |
|---|---|
| CORS restricted to dashboard origins (was any-origin) | ✅ core.py:57 allowlist (vercel + localhost + env-extendable) |
| Platform tokens encrypted at rest (was plaintext .env) | ✅ brand_connections encrypted KV; tests/test_token_crypto.py 7 green |
| Legacy X-Dashboard-Secret god-mode | ✅ retired Jul 6 (JWT-only require_auth) |
| brand_slug silent defaults (wrong-brand reads) | ✅ killed Jul 16 — 26 endpoints require slug, static net in CI |
| Supabase: mem_search cross-tenant leak | ✅ closed Jul 18 (EXECUTE revoked from PUBLIC) |
| Supabase: always-true insert policies (brands, brain_usage) | ✅ dropped Jul 18 |
| Supabase: function search_path pinned | ✅ Jul 18 |
| RLS on every table; brand isolation via membership predicates | ✅ verified via SQL probe as member user |
| `/brain/execute` shell behind super-admin operator wall | ⚠️ acceptable ONLY while operator mode is never client-reachable — re-verify at every auth change |
| vector extension in public schema | ⚠️ deferred (move breaks references; low real risk) |
| Leaked-password protection | 🧑 Supabase → Authentication → enable toggle (asked Jul 18) |
| Backups / point-in-time recovery | 🧑 check Supabase plan (Settings → Database → Backups) — free tier = daily only |

## Legal / compliance (NOT legal advice)

| Item | Status |
|---|---|
| ToS / Privacy Policy / DPA drafts | ✅ exist in `legal/` — 🧑 lawyer review BEFORE first signed client (biggest legal gap per register) |
| DPDP (India) + GDPR/CCPA basics | 🧑 covered in drafts; lawyer confirms scope for global clients |
| Platform App Review (Meta app → Live, Google OAuth → published, LinkedIn scopes) | 🧑 GAURAV_TODO "publishing prerequisites" — blocks reliable publishing, not the spine |
| Scraping via Apify (platform ToS) | ⚠️ accepted business risk — public data only, per-brand consent for own accounts |
| Browser-automation posting | ⚠️ standing preference; official APIs used where built (IG/LI/YT); X manual |
| Email sending (CAN-SPAM/unsubscribe) | ⚠️ email agent is draft-only, never auto-sends — revisit if sending automates |
| AI-content transparency + image-gen licenses | 🧑 check Higgsfield/FAL commercial terms when creative goes client-facing |
| "Grid Control" trademark clearance | 🧑 low priority, before serious marketing spend |

## Operational

| Item | Status |
|---|---|
| CI gates (frontend + backend) on every push | ✅ live, 90+ tests |
| Ops-auditor weekly health card | ✅ built; 🧑 enable the schedule when wanted |
| Cost caps | 🧑 set GRID_DAILY_USD_CAP on Railway + local .env (auditor flags it unset) |
| Custom domain | 🧑 buy + point at Vercel/Railway (pending list #1) |
| One repo / main / auto-deploy | ✅ |

**Bottom line:** engineering readiness is DONE except deferred-by-choice items.
The path to a signed client runs through Gaurav's list: lawyer review of the
legal drafts, App Review submissions, leaked-password toggle, cost cap, domain.
