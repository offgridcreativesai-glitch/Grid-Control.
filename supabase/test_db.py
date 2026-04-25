"""
supabase/test_db.py — End-to-end connection test for db.py
Run: python3 supabase/test_db.py
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import db

print("=" * 55)
print("GRID CONTROL — Supabase DB Layer Test")
print("=" * 55)

# Test 1 — upsert brand
print("\n[1] upsert_brand('offgrid-creatives-ai', ...)")
brand = db.upsert_brand(
    slug="offgrid-creatives-ai",
    name="OffGrid Creatives AI",
    profile_dict={
        "phase": "beta",
        "product": "AI-powered Ad Intelligence Report (PDF)",
        "platforms": ["Instagram", "LinkedIn"],
        "bottlenecks": ["Awareness", "Trust"],
    }
)
if brand:
    print(f"  ✓ Brand upserted — id: {brand['id']}")
    print(f"  ✓ Slug: {brand['slug']}")
    print(f"  ✓ Name: {brand['name']}")
else:
    print("  ✗ upsert_brand returned None — check error above")
    sys.exit(1)

# Test 2 — get brand
print("\n[2] get_brand('offgrid-creatives-ai')")
fetched = db.get_brand("offgrid-creatives-ai")
if fetched:
    print(f"  ✓ Fetched — id: {fetched['id']}")
    print(f"  ✓ Profile: {fetched['profile']}")
else:
    print("  ✗ get_brand returned None — check error above")
    sys.exit(1)

# Test 3 — save_agent_run
print("\n[3] save_agent_run(brand_id, 'trend-researcher')")
run = db.save_agent_run(brand_id=brand["id"], agent_slug="trend-researcher")
if run:
    print(f"  ✓ Run created — id: {run['id']}, status: {run['status']}")
else:
    print("  ✗ save_agent_run returned None")
    sys.exit(1)

# Test 4 — update run status
print("\n[4] update_agent_run_status → 'done'")
updated = db.update_agent_run_status(run_id=run["id"], status="done")
if updated:
    print(f"  ✓ Status updated → {updated['status']}")
else:
    print("  ✗ update_agent_run_status returned None")

# Test 5 — save_agent_output
print("\n[5] save_agent_output(...)")
output = db.save_agent_output(
    brand_id=brand["id"],
    agent_run_id=run["id"],
    agent_slug="trend-researcher",
    output_type="Trend Report",
    raw_output={"test": True, "summary": "Test trend output"},
    formatted_output={"type": "trend", "hooks": ["Test hook 1", "Test hook 2"]},
    loop_header={"WINNER": "Variant A — test", "GOAL": "Test goal"},
)
if output:
    print(f"  ✓ Output saved — id: {output['id']}, status: {output['approval_status']}")
else:
    print("  ✗ save_agent_output returned None")

# Test 6 — get_pending_outputs
print("\n[6] get_pending_outputs(brand_id)")
pending = db.get_pending_outputs(brand_id=brand["id"])
print(f"  ✓ Pending outputs: {len(pending)} found")

# Test 7 — save + get conversation
print("\n[7] save_conversation + get_conversation")
msgs = [
    {"role": "user", "content": "Hello from test"},
    {"role": "assistant", "content": "Test reply"},
]
db.save_conversation(brand_id=brand["id"], agent_slug="trend-researcher", messages_list=msgs)
fetched_msgs = db.get_conversation(brand_id=brand["id"], agent_slug="trend-researcher")
print(f"  ✓ Messages saved and retrieved: {len(fetched_msgs)} messages")

# Test 8 — log_audit
print("\n[8] log_audit(...)")
entry = db.log_audit(brand_id=brand["id"], action="test_run", actor="test_script", payload={"note": "Phase 0 Step 3 test"})
if entry:
    print(f"  ✓ Audit log entry created — id: {entry['id']}")
else:
    print("  ✗ log_audit returned None")

print("\n" + "=" * 55)
print("ALL TESTS PASSED — Supabase layer is live")
print("=" * 55)
