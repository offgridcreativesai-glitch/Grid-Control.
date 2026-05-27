-- GRID CONTROL — Supabase Schema (Multi-Tenant)
-- Updated: May 27, 2026
-- Project: mnivbrelhrwgndxcgega

-- ============================================================
-- 1. Profiles (mirrors auth.users for app-level data)
-- ============================================================
create table if not exists profiles (
  id uuid primary key references auth.users(id) on delete cascade,
  email text,
  full_name text,
  avatar_url text,
  is_super_admin boolean default false,
  created_at timestamptz default now(),
  updated_at timestamptz default now()
);

-- Auto-create profile on signup
create or replace function public.handle_new_user()
returns trigger as $$
begin
  insert into public.profiles (id, email, full_name)
  values (
    new.id,
    new.email,
    coalesce(new.raw_user_meta_data->>'full_name', split_part(new.email, '@', 1))
  );
  return new;
end;
$$ language plpgsql security definer;

drop trigger if exists on_auth_user_created on auth.users;
create trigger on_auth_user_created
  after insert on auth.users
  for each row execute function public.handle_new_user();

-- ============================================================
-- 2. Brands
-- ============================================================
create table if not exists brands (
  id uuid primary key default gen_random_uuid(),
  slug text unique not null,
  name text not null,
  profile jsonb not null default '{}',
  created_at timestamptz default now()
);

-- ============================================================
-- 3. Brand Members (user <-> brand with role)
-- ============================================================
create table if not exists brand_members (
  id uuid primary key default gen_random_uuid(),
  brand_id uuid not null references brands(id) on delete cascade,
  user_id uuid not null references auth.users(id) on delete cascade,
  role text not null default 'admin' check (role in ('admin', 'editor', 'viewer')),
  created_at timestamptz default now(),
  unique(brand_id, user_id)
);

create index if not exists idx_brand_members_user on brand_members(user_id);
create index if not exists idx_brand_members_brand on brand_members(brand_id);

-- ============================================================
-- 4. Agent Runs
-- ============================================================
create table if not exists agent_runs (
  id uuid primary key default gen_random_uuid(),
  brand_id uuid references brands(id) on delete cascade,
  agent_slug text not null,
  status text not null default 'pending',
  loop_header jsonb,
  started_at timestamptz default now(),
  completed_at timestamptz,
  error text,
  model text,
  input_tokens integer default 0,
  output_tokens integer default 0,
  api_cost_usd numeric default 0,
  fal_cost_usd numeric default 0,
  apify_cost_usd numeric default 0,
  fal_generations integer default 0,
  apify_runs integer default 0
);

-- ============================================================
-- 5. Agent Outputs
-- ============================================================
create table if not exists agent_outputs (
  id uuid primary key default gen_random_uuid(),
  agent_run_id uuid references agent_runs(id) on delete cascade,
  brand_id uuid references brands(id) on delete cascade,
  agent_slug text not null,
  output_type text not null,
  raw_output jsonb not null default '{}',
  formatted_output jsonb,
  approval_status text not null default 'pending',
  approved_at timestamptz,
  created_at timestamptz default now()
);

-- ============================================================
-- 6. Conversations (Meeting Room)
-- ============================================================
create table if not exists conversations (
  id uuid primary key default gen_random_uuid(),
  brand_id uuid references brands(id) on delete cascade,
  agent_slug text not null,
  messages jsonb not null default '[]',
  created_at timestamptz default now(),
  updated_at timestamptz default now()
);

-- ============================================================
-- 7. Session State
-- ============================================================
create table if not exists session_state (
  id uuid primary key default gen_random_uuid(),
  brand_id uuid references brands(id) on delete cascade,
  state jsonb not null default '{}',
  updated_at timestamptz default now()
);

-- ============================================================
-- 8. Audit Log
-- ============================================================
create table if not exists audit_log (
  id uuid primary key default gen_random_uuid(),
  brand_id uuid references brands(id) on delete cascade,
  action text not null,
  actor text not null default 'system',
  payload jsonb,
  created_at timestamptz default now()
);

-- ============================================================
-- 9. Brand Memory (with pgvector)
-- ============================================================
create table if not exists brand_memory (
  id uuid primary key default gen_random_uuid(),
  brand_id uuid not null references brands(id) on delete cascade,
  agent_slug text not null,
  memory_key text not null,
  content text not null,
  embedding vector(1536),
  created_at timestamptz default now(),
  updated_at timestamptz default now(),
  unique(brand_id, agent_slug, memory_key)
);

-- ============================================================
-- Indexes
-- ============================================================
create index if not exists idx_agent_runs_brand on agent_runs(brand_id);
create index if not exists idx_agent_outputs_brand on agent_outputs(brand_id);
create index if not exists idx_agent_outputs_status on agent_outputs(approval_status);
create index if not exists idx_conversations_brand_agent on conversations(brand_id, agent_slug);

-- ============================================================
-- RLS — enabled on all tables
-- ============================================================
alter table profiles enable row level security;
alter table brands enable row level security;
alter table brand_members enable row level security;
alter table agent_runs enable row level security;
alter table agent_outputs enable row level security;
alter table conversations enable row level security;
alter table session_state enable row level security;
alter table audit_log enable row level security;
alter table brand_memory enable row level security;

-- ============================================================
-- RLS Helper Functions
-- ============================================================
create or replace function public.is_brand_member(check_brand_id uuid)
returns boolean as $$
  select exists (
    select 1 from brand_members
    where brand_id = check_brand_id
    and user_id = auth.uid()
  );
$$ language sql security definer stable;

create or replace function public.is_brand_admin(check_brand_id uuid)
returns boolean as $$
  select exists (
    select 1 from brand_members
    where brand_id = check_brand_id
    and user_id = auth.uid()
    and role = 'admin'
  );
$$ language sql security definer stable;

-- ============================================================
-- RLS Policies — scoped to brand_members
-- Service role (Flask backend) bypasses RLS automatically
-- ============================================================

-- PROFILES
create policy "profiles_own" on profiles for all using (id = auth.uid());

-- BRAND_MEMBERS
create policy "brand_members_select" on brand_members
  for select using (user_id = auth.uid() or public.is_brand_member(brand_id));
create policy "brand_members_insert" on brand_members
  for insert with check (public.is_brand_admin(brand_id));
create policy "brand_members_delete" on brand_members
  for delete using (public.is_brand_admin(brand_id));

-- BRANDS
create policy "brands_select" on brands
  for select using (public.is_brand_member(id));
create policy "brands_insert" on brands
  for insert with check (true);
create policy "brands_update" on brands
  for update using (public.is_brand_admin(id));

-- AGENT_RUNS
create policy "agent_runs_select" on agent_runs
  for select using (public.is_brand_member(brand_id));
create policy "agent_runs_insert" on agent_runs
  for insert with check (public.is_brand_member(brand_id));
create policy "agent_runs_update" on agent_runs
  for update using (public.is_brand_member(brand_id));

-- AGENT_OUTPUTS
create policy "agent_outputs_select" on agent_outputs
  for select using (public.is_brand_member(brand_id));
create policy "agent_outputs_insert" on agent_outputs
  for insert with check (public.is_brand_member(brand_id));
create policy "agent_outputs_update" on agent_outputs
  for update using (public.is_brand_member(brand_id));

-- CONVERSATIONS
create policy "conversations_select" on conversations
  for select using (public.is_brand_member(brand_id));
create policy "conversations_insert" on conversations
  for insert with check (public.is_brand_member(brand_id));
create policy "conversations_update" on conversations
  for update using (public.is_brand_member(brand_id));

-- SESSION_STATE
create policy "session_state_select" on session_state
  for select using (public.is_brand_member(brand_id));
create policy "session_state_insert" on session_state
  for insert with check (public.is_brand_member(brand_id));
create policy "session_state_update" on session_state
  for update using (public.is_brand_member(brand_id));

-- AUDIT_LOG (read-only for members, inserts via service role)
create policy "audit_log_select" on audit_log
  for select using (public.is_brand_member(brand_id));

-- BRAND_MEMORY
create policy "brand_memory_select" on brand_memory
  for select using (public.is_brand_member(brand_id));
create policy "brand_memory_insert" on brand_memory
  for insert with check (public.is_brand_member(brand_id));
create policy "brand_memory_update" on brand_memory
  for update using (public.is_brand_member(brand_id));
