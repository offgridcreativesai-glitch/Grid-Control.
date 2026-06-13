"""Agent learnings — file-based persistent memory across runs.

Stand-in for Anthropic Managed Memory until SDK supports it. Stored as
newline-delimited JSON at `brands/{slug}/agent_learnings.jsonl`.

Each entry:
  {
    "ts": 1715000000.123,
    "agent": "script-writer",
    "kind": "insight" | "decision" | "failure" | "win",
    "text": "...",
    "context": {...}   # optional
  }

Agents append at end of each run with the key insights they want to
persist. The Brain reads the last N entries to give continuity across
sessions.
"""
from __future__ import annotations
import json
import time
from pathlib import Path
from typing import Any, Iterable

BASE_DIR = Path(__file__).resolve().parent.parent.parent


def _path(brand_slug: str) -> Path:
    return BASE_DIR / "brands" / brand_slug / "agent_learnings.jsonl"


def append(brand_slug: str, agent: str, text: str, kind: str = "insight",
           context: dict | None = None) -> None:
    """Append a learning entry. Safe — creates file if missing."""
    p = _path(brand_slug)
    p.parent.mkdir(parents=True, exist_ok=True)
    entry = {
        "ts": time.time(),
        "agent": agent,
        "kind": kind,
        "text": text[:2000],
    }
    if context:
        entry["context"] = context
    with p.open("a") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")


def recent(brand_slug: str, n: int = 20, agent_filter: str | None = None) -> list[dict]:
    """Return last N learnings (newest first), optionally filtered by agent."""
    p = _path(brand_slug)
    if not p.exists():
        return []
    out: list[dict] = []
    try:
        lines = p.read_text().splitlines()
    except Exception:
        return []
    for line in reversed(lines):
        if not line.strip():
            continue
        try:
            entry = json.loads(line)
        except Exception:
            continue
        if agent_filter and entry.get("agent") != agent_filter:
            continue
        out.append(entry)
        if len(out) >= n:
            break
    return out


def render_recent_for_prompt(brand_slug: str, n: int = 8,
                              agent_filter: str | None = None) -> str:
    """Format recent learnings as a short text block for system prompts."""
    items = recent(brand_slug, n=n, agent_filter=agent_filter)
    if not items:
        return ""
    lines = ["RECENT LEARNINGS:"]
    for e in items:
        ts = time.strftime("%Y-%m-%d", time.localtime(e.get("ts", 0)))
        lines.append(f"  · [{ts}] {e.get('agent','?')} ({e.get('kind','insight')}): {e.get('text','')[:300]}")
    return "\n".join(lines)


if __name__ == "__main__":
    import sys
    if len(sys.argv) >= 4 and sys.argv[1] == "add":
        append(sys.argv[2], sys.argv[3], " ".join(sys.argv[4:]) or "(empty)")
        print("appended")
    elif len(sys.argv) >= 3 and sys.argv[1] == "list":
        for e in recent(sys.argv[2]):
            print(e)
    else:
        print("Usage: python3 agents/_learnings.py add <slug> <agent> <text>")
        print("       python3 agents/_learnings.py list <slug>")
