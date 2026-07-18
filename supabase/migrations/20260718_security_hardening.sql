-- Phase 4.3 security hardening (applied Jul 18 2026 via Supabase MCP, two parts)
-- Advisor-driven. Verified after: RLS member-read intact (SQL probe), Flask+Railway 200.

-- Part 1: security_hardening_advisor_fixes
revoke execute on function public.handle_new_user() from anon, authenticated;
revoke execute on function public.rls_auto_enable() from anon, authenticated;
revoke execute on function public.mem_search_brand(public.vector, uuid, text, integer) from anon, authenticated;
revoke execute on function public.mem_search_grid_control(public.vector, text, integer) from anon, authenticated;
drop policy if exists "brands_insert" on public.brands;            -- was WITH CHECK (true)
drop policy if exists "Service insert brain_usage" on public.brain_usage;  -- was WITH CHECK (true)
do $$
declare f record;
begin
  for f in select p.oid::regprocedure as sig from pg_proc p join pg_namespace n on n.oid = p.pronamespace
    where n.nspname = 'public' and p.proname in ('search_brand_memory','handle_new_user','is_brand_member','is_brand_admin','mem_search_grid_control','mem_search_brand','rls_auto_enable')
  loop execute format('alter function %s set search_path = public, pg_temp', f.sig); end loop;
end $$;

-- Part 2: security_hardening_revoke_public_execute (per-role revokes are inert
-- while PUBLIC retains the default EXECUTE grant)
revoke execute on function public.handle_new_user() from public;
revoke execute on function public.rls_auto_enable() from public;
revoke execute on function public.mem_search_brand(public.vector, uuid, text, integer) from public;
revoke execute on function public.mem_search_grid_control(public.vector, text, integer) from public;

-- ACCEPTED (documented, not bugs):
--   is_brand_member/is_brand_admin stay PUBLIC-executable — 30+ RLS policies
--     evaluate them as the querying user; they leak only the caller's own membership.
--   brand_connections / grid_control_memory_vec: RLS on, zero policies = service-role only. Intentional.
--   vector extension in public schema: move deferred (breaks references; low real risk).
--   Leaked-password protection: Supabase dashboard toggle — Gaurav's click.
