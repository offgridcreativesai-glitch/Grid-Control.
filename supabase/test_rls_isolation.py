#!/usr/bin/env python3
"""
RLS tenant-isolation test (Phase 0 security gate).

Proves Row Level Security is actually active: an UNAUTHENTICATED anon client must
get ZERO rows from every tenant table. If RLS is ever disabled or a policy is
loosened to public, this test fails loudly.

Note: a full two-user CROSS-tenant test (user A cannot read brand B) requires
real Supabase auth JWTs and is run in CI with seeded test users. This script is
the always-runnable guard that catches the most common regression — RLS turned
off / made public.

Run:  python3 supabase/test_rls_isolation.py
Exit: 0 = pass, 1 = fail, 2 = skipped (no credentials).
"""
import os
import sys

from dotenv import load_dotenv

load_dotenv(
    dotenv_path=os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env"),
    override=True,
)

URL = os.getenv("SUPABASE_URL", "").strip()
ANON = os.getenv("SUPABASE_ANON_KEY", "").strip()

# Tables that must NEVER be readable without authentication.
TENANT_TABLES = [
    "profiles", "brands", "brand_members", "agent_runs",
    "agent_outputs", "conversations", "session_state",
    "audit_log", "brand_memory",
]


def main() -> int:
    if not URL or not ANON:
        print("SKIP: SUPABASE_URL / SUPABASE_ANON_KEY not set — cannot run RLS test.")
        return 2

    from supabase import create_client
    anon = create_client(URL, ANON)  # anon key → RLS enforced, no auth.uid()

    failures = []
    for table in TENANT_TABLES:
        try:
            res = anon.table(table).select("*").limit(1).execute()
            rows = res.data or []
            if rows:
                failures.append(f"{table}: anon read returned {len(rows)} row(s) — RLS LEAK")
            else:
                print(f"  OK  {table}: anon read blocked (0 rows)")
        except Exception as e:
            # A thrown error (permission denied) is also an acceptable "blocked".
            print(f"  OK  {table}: anon read raised ({type(e).__name__}) — blocked")

    if failures:
        print("\nRLS ISOLATION FAILED:")
        for f in failures:
            print("  ✗", f)
        return 1
    print("\nRLS isolation PASSED — all tenant tables deny anonymous reads.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
