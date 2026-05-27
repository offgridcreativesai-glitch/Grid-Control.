-- ============================================================
-- Billing tables for Razorpay subscription management
-- Migration 002 — May 27, 2026
-- ============================================================

-- Subscription plans (mirrors Razorpay plans)
create table if not exists billing_plans (
  id uuid primary key default gen_random_uuid(),
  name text not null,
  slug text not null unique,
  description text,
  amount_paise integer not null,           -- price in paise (INR)
  currency text not null default 'INR',
  interval text not null default 'monthly', -- monthly | yearly
  razorpay_plan_id text unique,            -- plan_xxxxx from Razorpay
  features jsonb default '[]'::jsonb,      -- list of included features
  max_brands integer default 1,
  max_agent_runs_per_month integer default 100,
  is_active boolean default true,
  created_at timestamptz default now(),
  updated_at timestamptz default now()
);

-- Per-brand subscriptions
create table if not exists subscriptions (
  id uuid primary key default gen_random_uuid(),
  brand_id uuid not null references brands(id) on delete cascade,
  plan_id uuid references billing_plans(id),
  razorpay_subscription_id text unique,    -- sub_xxxxx from Razorpay
  razorpay_customer_id text,               -- cust_xxxxx
  status text not null default 'created',  -- created | authenticated | active | paused | cancelled | expired
  current_period_start timestamptz,
  current_period_end timestamptz,
  trial_end timestamptz,
  cancelled_at timestamptz,
  metadata jsonb default '{}'::jsonb,
  created_at timestamptz default now(),
  updated_at timestamptz default now(),
  unique(brand_id)                         -- one subscription per brand
);

-- Usage tracking per agent run (for metered billing)
create table if not exists usage_logs (
  id uuid primary key default gen_random_uuid(),
  brand_id uuid not null references brands(id) on delete cascade,
  agent_slug text not null,
  agent_run_id uuid references agent_runs(id),
  model_used text,                         -- opus-4-6, sonnet-4-6, haiku
  input_tokens integer default 0,
  output_tokens integer default 0,
  estimated_cost_usd numeric(10,6) default 0,
  created_at timestamptz default now()
);

-- Payment history
create table if not exists payments (
  id uuid primary key default gen_random_uuid(),
  brand_id uuid not null references brands(id) on delete cascade,
  subscription_id uuid references subscriptions(id),
  razorpay_payment_id text unique,         -- pay_xxxxx
  razorpay_order_id text,
  amount_paise integer not null,
  currency text not null default 'INR',
  status text not null default 'created',  -- created | authorized | captured | refunded | failed
  method text,                             -- card | upi | netbanking | wallet
  receipt_url text,
  metadata jsonb default '{}'::jsonb,
  created_at timestamptz default now()
);

-- Indexes
create index if not exists idx_subscriptions_brand on subscriptions(brand_id);
create index if not exists idx_subscriptions_status on subscriptions(status);
create index if not exists idx_usage_logs_brand on usage_logs(brand_id);
create index if not exists idx_usage_logs_created on usage_logs(created_at);
create index if not exists idx_payments_brand on payments(brand_id);
create index if not exists idx_payments_status on payments(status);

-- RLS
alter table billing_plans enable row level security;
alter table subscriptions enable row level security;
alter table usage_logs enable row level security;
alter table payments enable row level security;

-- Plans are readable by everyone (public pricing)
create policy "billing_plans_select" on billing_plans for select using (true);

-- Subscriptions scoped to brand members
create policy "subscriptions_select" on subscriptions
  for select using (public.is_brand_member(brand_id));

-- Usage logs scoped to brand members
create policy "usage_logs_select" on usage_logs
  for select using (public.is_brand_member(brand_id));

-- Payments scoped to brand members
create policy "payments_select" on payments
  for select using (public.is_brand_member(brand_id));

-- Insert default plans
insert into billing_plans (name, slug, description, amount_paise, interval, features, max_brands, max_agent_runs_per_month) values
  ('Starter', 'starter', 'Intelligence reports for 1 brand', 250000, 'monthly',
   '["Weekly competitor intel report", "Trend alerts", "Basic content calendar", "Email support"]'::jsonb,
   1, 50),
  ('Growth', 'growth', 'Full execution for 1 brand', 1500000, 'monthly',
   '["Everything in Starter", "18-agent content engine", "Script writing + creative direction", "Carousel generation", "Approval dashboard", "Priority support"]'::jsonb,
   1, 300),
  ('Agency', 'agency', 'Multi-brand execution', 5000000, 'monthly',
   '["Everything in Growth", "Up to 5 brands", "White-label reports", "Dedicated Slack channel", "Custom agent tuning", "Team roles (Admin/Editor/Viewer)"]'::jsonb,
   5, 1000)
on conflict (slug) do nothing;
