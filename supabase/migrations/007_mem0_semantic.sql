-- ============================================================
-- 007 · Mem0 semantic memory backbone (Phase 1a · Jun 18 2026)
-- ============================================================
-- 2 scopes, no mixing per Gaurav's call:
--   • grid_control_memory_vec  → parent (account-wide, cross-brand)
--   • brand_memory_vec         → child  (per-brand, isolated)
--
-- Embeddings: Voyage voyage-3-lite = 512 dims (not 1536 like OpenAI).
-- Existing brand_memory (KV, 1536 dim, unused embedding column) is left
-- alone — semantic layer is additive, not a replacement.
-- ============================================================

create extension if not exists vector;

-- ── Grid Control scope (Gaurav's account, cross-brand) ──────
create table if not exists grid_control_memory_vec (
  id         uuid primary key default gen_random_uuid(),
  agent_slug text not null,
  content    text not null,
  embedding  vector(512),
  metadata   jsonb default '{}'::jsonb,
  created_at timestamptz default now(),
  updated_at timestamptz default now()
);

create index if not exists idx_gc_mem_agent on grid_control_memory_vec(agent_slug);
create index if not exists idx_gc_mem_embedding
  on grid_control_memory_vec using ivfflat (embedding vector_cosine_ops)
  with (lists = 50);

-- ── Brand scope (per-brand, isolated) ───────────────────────
create table if not exists brand_memory_vec (
  id         uuid primary key default gen_random_uuid(),
  brand_id   uuid not null references brands(id) on delete cascade,
  agent_slug text not null,
  content    text not null,
  embedding  vector(512),
  metadata   jsonb default '{}'::jsonb,
  created_at timestamptz default now(),
  updated_at timestamptz default now()
);

create index if not exists idx_brand_mem_vec_brand on brand_memory_vec(brand_id, agent_slug);
create index if not exists idx_brand_mem_vec_embedding
  on brand_memory_vec using ivfflat (embedding vector_cosine_ops)
  with (lists = 100);

-- ── RLS ─────────────────────────────────────────────────────
-- service_role (Flask backend) bypasses RLS automatically.
-- Brand scope: only members of that brand can read; service_role writes.
-- Grid Control scope: service_role only for now (no org/user split yet).
alter table grid_control_memory_vec enable row level security;
alter table brand_memory_vec        enable row level security;

create policy "brand_memory_vec_select" on brand_memory_vec
  for select using (public.is_brand_member(brand_id));

-- No user-facing INSERT/UPDATE/DELETE policies → service_role only writes.
-- grid_control_memory_vec: service_role only, no auth-user policies.
