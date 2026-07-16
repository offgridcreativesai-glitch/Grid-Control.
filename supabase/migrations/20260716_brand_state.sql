-- Phase 1.2 (applied Jul 16 2026 via Supabase MCP): single durable home for
-- per-brand JSON state; disk becomes a rehydratable cache. See docs/DATA_HOME_DESIGN.md
create table if not exists public.brand_state (
  brand_id uuid not null references public.brands(id) on delete cascade,
  file_key text not null,
  content jsonb not null default '{}'::jsonb,
  updated_at timestamptz not null default now(),
  updated_by text not null default 'system',
  primary key (brand_id, file_key)
);
alter table public.brand_state enable row level security;
create policy "brand members read brand_state" on public.brand_state
  for select using (
    exists (select 1 from public.brand_members bm
            where bm.brand_id = brand_state.brand_id and bm.user_id = auth.uid())
  );
insert into storage.buckets (id, name, public)
values ('brand-assets', 'brand-assets', false)
on conflict (id) do nothing;
