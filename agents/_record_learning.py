"""Single helper to persist an agent learning at run completion.

Writes to TWO places:
  1. Local file `brands/{slug}/agent_learnings.jsonl` (read by The Brain)
  2. Anthropic Managed Memory store `agent_learnings` (read by managed agents)

Both are best-effort — failure of either does NOT block the agent run.

Usage at end of an agent's run:

    from _record_learning import record
    record(brand_slug, "script-writer",
           "Wrote 5 scripts for week 1; flagged 1 for human face needed",
           kind="win")
"""
from __future__ import annotations
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def record(brand_slug: str, agent_slug: str, text: str,
           kind: str = "insight", context: dict | None = None) -> None:
    """Persist one learning. Best-effort. Never raises."""
    if not brand_slug or not agent_slug or not text:
        return

    # 1. Local file (always works)
    try:
        from _learnings import append as _file_append  # type: ignore
        _file_append(brand_slug, agent_slug, text, kind=kind, context=context)
    except Exception:
        pass

    # 2. Managed Memory (best-effort — needs SDK + memory_stores.json)
    try:
        if not os.getenv("ANTHROPIC_API_KEY"):
            return
        from managed_agents.memory_manager import record_agent_learning  # type: ignore
        record_agent_learning(brand_slug, agent_slug, text)
    except Exception:
        pass
