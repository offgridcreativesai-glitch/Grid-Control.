-- 008_brand_connections.sql
-- Durable per-brand platform-token storage (IG/LinkedIn/YouTube/X).
-- Applied to the live project (mnivbrelhrwgndxcgega) on 2026-07-08.
--
-- WHY: OAuth callbacks now land on the stable, deployed (Railway) backend
-- instead of an ephemeral Cloudflare quick tunnel. Tokens must persist
-- somewhere BOTH the deployed backend and the local app + agents can read.
-- brands/<slug>/.env is per-machine + wiped on Railway redeploy, so it can't be
-- the source of truth across machines. This table is. It's a flat KV mirror of
-- that .env file (env_key = value), so no per-platform schema coupling.
--
-- Values are stored exactly as core.py hands them over: token_crypto-encrypted
-- (enc:<fernet>) under GRID_TOKEN_ENCRYPTION_KEY, which MUST be identical on
-- every environment that writes/reads them (local + Railway) or ciphertext from
-- one won't decrypt on the other.

create table if not exists public.brand_connections (
  id         uuid primary key default gen_random_uuid(),
  brand_id   uuid not null references public.brands(id) on delete cascade,
  env_key    text not null,
  value      text not null,               -- encrypted (enc:<fernet>) or plaintext fallback
  updated_at timestamptz not null default now(),
  unique (brand_id, env_key)
);

create index if not exists brand_connections_brand_idx on public.brand_connections(brand_id);

-- RLS on, NO policies: platform tokens must never be reachable by client/anon
-- or even brand members via the API. Only the backend service_role (which
-- bypasses RLS) touches them. Intentionally stricter than the other brand tables.
alter table public.brand_connections enable row level security;

comment on table public.brand_connections is
  'Encrypted per-brand platform OAuth tokens (KV mirror of brands/<slug>/.env). service_role only.';
