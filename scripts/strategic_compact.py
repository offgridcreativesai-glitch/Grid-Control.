#!/usr/bin/env python3
"""
Strategic Compact Hook — OffGrid Marketing OS
Ported pattern from Everything Claude Code (affaan-m/everything-claude-code).

Tracks tool-call count per session and prints a suggestion to /compact
at strategic thresholds. Reduces token waste from auto-compaction at
arbitrary boundaries.

Wire into ~/.claude/settings.json:
  {
    "hooks": {
      "PreToolUse": [
        {"matcher": "Edit|Write|Bash",
         "hooks": [{"type": "command", "command": "python3 /Users/gauravoffgrid/offgrid-marketing-os/scripts/strategic_compact.py"}]}
      ]
    }
  }

Env vars:
  COMPACT_THRESHOLD     — first suggestion (default 50)
  COMPACT_REMIND_EVERY  — periodic reminder (default 25)
  COMPACT_DISABLE       — set to "1" to disable
"""

import os
import sys
import json
from pathlib import Path
from datetime import datetime

THRESHOLD = int(os.getenv("COMPACT_THRESHOLD", "50"))
REMIND = int(os.getenv("COMPACT_REMIND_EVERY", "25"))
DISABLED = os.getenv("COMPACT_DISABLE", "0") == "1"

if DISABLED:
    sys.exit(0)

# State persists across hook invocations within a session
state_dir = Path.home() / ".claude" / "state" / "strategic_compact"
state_dir.mkdir(parents=True, exist_ok=True)

# Read hook stdin (Claude Code passes JSON)
try:
    payload = json.loads(sys.stdin.read() or "{}")
except json.JSONDecodeError:
    payload = {}

session_id = payload.get("session_id", "unknown")
state_file = state_dir / f"{session_id}.json"

# Load or init state
state = {"count": 0, "last_suggested_at": 0, "started": datetime.utcnow().isoformat()}
if state_file.exists():
    try:
        state = json.loads(state_file.read_text())
    except Exception:
        pass

state["count"] += 1
count = state["count"]
last = state.get("last_suggested_at", 0)

suggest = False
reason = ""
if count == THRESHOLD:
    suggest = True
    reason = f"Crossed {THRESHOLD} tool calls in this session"
elif count > THRESHOLD and (count - last) >= REMIND:
    suggest = True
    reason = f"Reminder — {count - last} calls since last compact suggestion"

if suggest:
    state["last_suggested_at"] = count
    msg = (
        f"\n[strategic_compact] {reason}.\n"
        f"  → Consider running /compact at the next logical boundary.\n"
        f"  → Compact AFTER planning, AFTER debugging, AFTER a milestone — NOT mid-implementation.\n"
        f"  → Use: /compact Focus on <next phase> next\n"
    )
    print(msg, file=sys.stderr)

# Save state
try:
    state_file.write_text(json.dumps(state))
except Exception:
    pass

sys.exit(0)
