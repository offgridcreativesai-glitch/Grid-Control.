-- GRID CONTROL — Supabase Schema
-- Run this in Supabase SQL Editor

-- 1. Brands
create table if not exists brands (
  id uuid primary key default gen_random_uuid(),
  slug text unique not null,
  name text not null,
  profile jsonb not null default '{}',
  created_at timestamptz default now()
);

-- 2. Agent Runs
create table if not exists agent_runs (
  id uuid primary key default gen_random_uuid(),
  brand_id uuid references brands(id) on delete cascade,
  agent_slug text not null,
  status text not null default 'pending',
  loop_header jsonb,
  started_at timestamptz default now(),
  completed_at timestamptz,
  error text
);

-- 3. Agent Outputs
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

-- 4. Conversations (Meeting Room)
create table if not exists conversations (
  id uuid primary key default gen_random_uuid(),
  brand_id uuid references brands(id) on delete cascade,
  agent_slug text not null,
  messages jsonb not null default '[]',
  created_at timestamptz default now(),
  updated_at timestamptz default now()
);

-- 5. Session State
create table if not exists session_state (
  id uuid primary key default gen_random_uuid(),
  brand_id uuid references brands(id) on delete cascade,
  state jsonb not null default '{}',
  updated_at timestamptz default now()
);

-- 6. Audit Log
create table if not exists audit_log (
  id uuid primary key default gen_random_uuid(),
  brand_id uuid references brands(id) on delete cascade,
  action text not null,
  actor text not null default 'system',
  payload jsonb,
  created_at timestamptz default now()
);

-- Indexes
create index if not exists idx_agent_runs_brand on agent_runs(brand_id);
create index if not exists idx_agent_outputs_brand on agent_outputs(brand_id);
create index if not exists idx_agent_outputs_status on agent_outputs(approval_status);
create index if not exists idx_conversations_brand_agent on conversations(brand_id, agent_slug);

-- RLS (Row Level Security)
alter table brands enable row level security;
alter table agent_runs enable row level security;
alter table agent_outputs enable row level security;
alter table conversations enable row level security;
alter table session_state enable row level security;
alter table audit_log enable row level security;

-- Allow service role full access (for backend)
create policy "service_role_all" on brands for all using (true);
create policy "service_role_all" on agent_runs for all using (true);
create policy "service_role_all" on agent_outputs for all using (true);
create policy "service_role_all" on conversations for all using (true);
create policy "service_role_all" on session_state for all using (true);
create policy "service_role_all" on audit_log for all using (true);
