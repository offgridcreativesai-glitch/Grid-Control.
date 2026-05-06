#!/usr/bin/env python3
"""
Session Memory Hook — OffGrid Marketing OS
Lightweight port of ECC's continuous-learning observe.sh (we keep ~80 LOC instead of 460).

Captures tool-use events per session into JSONL so context survives /compact.
Lets future Claude sessions re-read what was done in the previous session
without paying for it in current context tokens.

Wire into ~/.claude/settings.json PostToolUse hook (alongside strategic_compact):
  "PostToolUse": [
    {"matcher": "Edit|Write|Bash",
     "hooks": [{"type": "command", "command": "python3 /Users/gauravoffgrid/offgrid-marketing-os/scripts/session_memory.py"}]}
  ]

Output: brands/_session_memory/<session_id>.jsonl
        Each line = {timestamp, tool, summary, file_path?, exit_code?}
        Capped at 200 lines per session — older lines auto-rotated.
"""

import os
import sys
import json
import re
from pathlib import Path
from datetime import datetime, timezone

if os.getenv("SESSION_MEMORY_DISABLE", "0") == "1":
    sys.exit(0)

OFFGRID_ROOT = Path("/Users/gauravoffgrid/offgrid-marketing-os")
MEMORY_DIR = OFFGRID_ROOT / "brands" / "_session_memory"
MEMORY_DIR.mkdir(parents=True, exist_ok=True)
MAX_LINES = 200

try:
    payload = json.loads(sys.stdin.read() or "{}")
except json.JSONDecodeError:
    sys.exit(0)

session_id = payload.get("session_id", "unknown")
tool_name = payload.get("tool_name") or payload.get("tool", "unknown")
tool_input = payload.get("tool_input") or payload.get("input", {})
tool_response = payload.get("tool_response") or {}

# Build a minimal summary — keep payload small
entry = {
    "ts": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    "tool": tool_name,
}

if tool_name in ("Edit", "Write", "Read"):
    fp = tool_input.get("file_path") if isinstance(tool_input, dict) else None
    if fp:
        # Keep only the path relative to project root if possible
        try:
            rel = str(Path(fp).resolve().relative_to(OFFGRID_ROOT))
            entry["file"] = rel
        except (ValueError, OSError):
            entry["file"] = str(fp)[-80:]

elif tool_name == "Bash":
    cmd = tool_input.get("command", "") if isinstance(tool_input, dict) else ""
    desc = tool_input.get("description", "") if isinstance(tool_input, dict) else ""
    # First 80 chars of description if present, else 80 chars of command
    entry["summary"] = (desc or cmd)[:120]
    if isinstance(tool_response, dict):
        entry["exit_code"] = tool_response.get("exit_code")

elif tool_name in ("Agent", "Task"):
    desc = tool_input.get("description", "") if isinstance(tool_input, dict) else ""
    entry["summary"] = desc[:120]

# Scrub obvious secrets
def scrub(s):
    if not isinstance(s, str):
        return s
    return re.sub(
        r"(?i)(api[_-]?key|token|secret|bearer)\s*[:=]\s*[^\s\"',]+",
        r"\1=[REDACTED]",
        s,
    )

for k, v in list(entry.items()):
    entry[k] = scrub(v)

# Append to per-session file (atomic append)
memory_file = MEMORY_DIR / f"{session_id}.jsonl"
try:
    with memory_file.open("a") as f:
        f.write(json.dumps(entry) + "\n")
except Exception:
    sys.exit(0)

# Rotate if over MAX_LINES
try:
    lines = memory_file.read_text().splitlines()
    if len(lines) > MAX_LINES:
        # Keep the last MAX_LINES, archive the rest
        archive_dir = MEMORY_DIR / "archive"
        archive_dir.mkdir(exist_ok=True)
        archive_path = archive_dir / f"{session_id}_{datetime.now().strftime('%Y%m%d%H%M%S')}.jsonl"
        archive_path.write_text("\n".join(lines[:-MAX_LINES]) + "\n")
        memory_file.write_text("\n".join(lines[-MAX_LINES:]) + "\n")
except Exception:
    pass

sys.exit(0)
