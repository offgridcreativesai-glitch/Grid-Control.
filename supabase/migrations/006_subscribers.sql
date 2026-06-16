-- 006_subscribers.sql — Lead-magnet funnel (Phase F4) subscriber capture.
-- NOT YET APPLIED. Review + run together (zero-assumption: do not auto-apply to prod).
-- Captured by POST /api/leads/capture (server-side / service role) → nurtured by
-- agents/email_marketing_agent.py (#12). Brand-isolated, RLS member-scoped reads.

create table if not exists subscribers (
  id uuid primary key default gen_random_uuid(),
  brand_id uuid not null references brands(id) on delete cascade,
  email text not null,
  name text,
  product_interest text,           -- e.g. "report" | "grid-control" | free-text
  source text,                     -- e.g. "lead_magnet:3-mistakes" | "ig_bio_link"
  captured_at timestamptz not null default now(),
  unique(brand_id, email)
);

create index if not exists idx_subscribers_brand on subscribers(brand_id);

alter table subscribers enable row level security;

-- Brand members can read/manage their own brand's subscribers.
-- (The capture endpoint writes via the service role, which bypasses RLS.)
create policy "subscribers_member_select" on subscribers
  for select using (public.is_brand_member(brand_id));
create policy "subscribers_member_insert" on subscribers
  for insert with check (public.is_brand_member(brand_id));
create policy "subscribers_member_update" on subscribers
  for update using (public.is_brand_member(brand_id));
