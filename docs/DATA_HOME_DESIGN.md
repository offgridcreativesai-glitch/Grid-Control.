# Data Home Design — Supabase as the single source of truth (Phase 1)

> Slice 1.1 output, Jul 16 2026. Implements the locked decision "Supabase for
> everything" with the least-risk mechanism.

## For Gaurav (plain words)

Today every brand's files live only on your laptop. If the laptop dies, brands
die; the deployed server can't serve anyone. After this phase: **the cloud
database you already pay for (Supabase) holds everything.** Any server, on
boot, pulls a brand's data down, works on it locally (that's just a working
copy, safe to lose), and pushes every change back up immediately. Your laptop
becomes just another machine — nothing lives only there anymore. You verify it
worked when the DEPLOYED app shows the sample brand's data without your laptop
running (that test is slice 1.6/2.2).

## Why hydrate/write-back, not direct DB calls everywhere

30+ modules read `brand_profile.json`; 12 read `_state.json`; every agent
reads/writes several files (map below). Rewriting all of that to direct DB
calls in one pass is the break-everything move. Instead ONE module owns sync:

- **Read path:** `brand_store.hydrate(slug)` pulls all brand state from
  Supabase into `brands/<slug>/` (skips if fresh). Called on brand access
  (API) and agent start. Agents/routes keep reading files — unchanged.
- **Write path:** `brand_store.push(slug, file_key)` upserts the file's
  content to Supabase. Called from the few chokepoints that WRITE brand state
  (save_agent_output, approve/reject moves, profile/calendar writers,
  BaseAgent teardown). Disk is never authoritative — DB timestamp wins.
- **Deleted/missing locally** = rehydrate. A wiped `brands/` dir is a cache
  miss, not data loss. (This is the exact bug class of the "Flask down →
  onboarding restart" gotcha — designed out.)

## Schema (slice 1.2)

- `brand_state` — one row per (brand, file): `brand_id uuid FK → brands`,
  `file_key text` ('brand_profile', 'voice_profile', 'content_calendar',
  'trends_live', 'competitors_db', 'performance_history', 'contradictions',
  'session_state', '_state', 'brand_narrative', 'pivot_decision',
  'agent_trust_settings'), `content jsonb`, `updated_at timestamptz`,
  `updated_by text`. UNIQUE(brand_id, file_key). RLS: brand members SELECT;
  writes via service role only (backend).
- **Vault** (pending/approved outputs): reuse the existing `agent_outputs`
  table as source of truth (slice 1.5) — rows already modeled, disk copies
  become cache.
- **Binaries** (carousel PNGs, voice samples, videos): Supabase Storage bucket
  `brand-assets`, path `<slug>/<kind>/<file>`. Slice 1.2 creates the bucket;
  binary sync can land after the finish line if size demands staging.
- **Tokens**: `brand_connections` table already exists (encrypted KV mirror of
  `brands/<slug>/.env`) — reused as-is, disk `.env` becomes the cache.

## Reader/writer map (grep-verified Jul 16)

| file_key | writers | notable readers |
|---|---|---|
| brand_profile | onboarding (auth_create_brand), brand-book approve, save_brand_profile | ALL agents, phases.py, archetype, routes |
| voice_profile | brand-book approve, connections (voice sample) | script_writer, carousel, community, email, dm |
| content_calendar | content_planner | script_writer, carousel, CD, sentinel, publish_runner |
| trends_live | trend_researcher | planner, strategy, script_writer, sentinel, provenance |
| competitors_db | strategy_agent | CD, trend_researcher |
| performance_history | performance_tracker | sentinel, composers, script_writer, routes |
| contradictions | contradiction_detector | brain, brands, agents routes |
| session_state | CEOBrain | data_analyst, base_agent, routes |
| _state | _state.py builder | brain, brands, agents, connections, phases |
| brand_narrative | brand-book approve | brands routes |
| pivot_decision | trend_sentinel | weekly composer, brain |
| agent_trust_settings | trust_dial (routes POST) | trust_dial |

## Migration order (slices 1.3–1.6)

1.3 `supabase/brand_store.py` (hydrate/push + freshness) + tests (mocked DB).
1.4 Wire hydrate into brand access chokepoints (`get_brand_dir` callers via
    one seam) + push into the write chokepoints. Feature flag
    `GRID_BRAND_STORE=on|off` (off = today's behavior) until 1.6 verifies.
1.5 Vault: `agent_outputs` becomes source of truth for pending/approved;
    approve/reject update rows first, files second. Smoke tests updated.
1.6 Seed: push sample brand (TGT) up; verify deployed Railway serves it with
    the laptop's Flask stopped. That proof = Phase 1 done.
