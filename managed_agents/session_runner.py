"""
managed_agents/session_runner.py

Replaces the old _run_agent_subprocess pattern in dashboard_api.py.
Creates a Managed Agent session, streams events, captures final output,
saves to brands/{slug}/outputs/pending_approval/, and pushes to Notion.

Usage (from dashboard_api.py):
    from managed_agents.session_runner import run_agent_session, is_managed_ready

    if is_managed_ready(agent_name):
        output = run_agent_session(agent_name, brand_slug, task_prompt)
    else:
        # fallback to subprocess
        ...
"""

import os
import sys
import json
import pathlib
import datetime
import re
import threading
from typing import Generator

ROOT = pathlib.Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

import anthropic
from managed_agents.context_builder import build_context
from agents._lib._agent_framework import operating_framework as _operating_framework

REGISTRY_PATH = pathlib.Path(__file__).parent / "registry.json"
BRANDS_DIR    = ROOT / "brands"
BETA_HEADER   = {"anthropic-beta": "managed-agents-2026-04-01"}

# In-memory SSE event queues keyed by run_id — consumed by /api/agents/run/status
_sse_queues: dict[str, list[str]] = {}
_sse_lock   = threading.Lock()


# ── REGISTRY HELPERS ──────────────────────────────────────────────────────────

def load_registry() -> dict:
    try:
        with open(REGISTRY_PATH) as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def is_managed_ready(agent_name: str) -> bool:
    """
    Returns True only if:
    1. The registry has an agent_id for this agent
    2. A shared environment_id exists
    3. ANTHROPIC_API_KEY is set
    """
    if not os.getenv("ANTHROPIC_API_KEY"):
        return False
    registry = load_registry()
    if not registry.get("environment_id"):
        return False
    config = registry.get("agents", {}).get(agent_name, {})
    return bool(config.get("agent_id"))


# ── MEMORY STORES HELPERS ─────────────────────────────────────────────────────

def load_memory_stores(brand_slug: str) -> dict:
    path = BRANDS_DIR / brand_slug / "memory_stores.json"
    try:
        with open(path) as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def build_resources(stores: dict) -> list[dict]:
    """Build session resources list from memory store IDs."""
    resources = []
    if stores.get("brand_context"):
        resources.append({
            "type": "memory_store",
            "memory_store_id": stores["brand_context"],
            "access": "read_write",
        })
    if stores.get("agent_learnings"):
        resources.append({
            "type": "memory_store",
            "memory_store_id": stores["agent_learnings"],
            "access": "read_write",
        })
    if stores.get("market_data"):
        resources.append({
            "type": "memory_store",
            "memory_store_id": stores["market_data"],
            "access": "read_only",
        })
    return resources


# ── OUTPUT HELPERS ────────────────────────────────────────────────────────────

def _slugify(name: str) -> str:
    return re.sub(r"[^a-z0-9-]", "", name.lower().replace(" ", "-"))


def save_agent_output(agent_name: str, brand_slug: str, output: str) -> pathlib.Path:
    """Save agent output JSON (or raw text) to pending_approval directory."""
    agent_slug = _slugify(agent_name)
    out_dir    = BRANDS_DIR / brand_slug / "outputs" / "pending_approval" / agent_slug
    out_dir.mkdir(parents=True, exist_ok=True)

    ts       = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{agent_slug}_{ts}.json"
    out_path = out_dir / filename

    # Try to parse as JSON for pretty-printing; fall back to raw text
    try:
        parsed = json.loads(output)
        out_path.write_text(json.dumps(parsed, indent=2, ensure_ascii=False))
    except (json.JSONDecodeError, TypeError):
        out_path.write_text(output)

    return out_path


def push_to_notion(agent_name: str, brand_slug: str, output_path: pathlib.Path) -> None:
    """Push output to Notion approval database (mirrors existing behaviour)."""
    try:
        from notion_client import Client as NotionClient  # type: ignore
        notion_key = os.getenv("NOTION_API_KEY")
        db_id      = os.getenv("NOTION_DATABASE_ID")
        if not notion_key or not db_id:
            return

        client  = NotionClient(auth=notion_key)
        content = output_path.read_text()[:2000]  # Notion text property cap

        client.pages.create(
            parent={"database_id": db_id},
            properties={
                "Name":       {"title": [{"text": {"content": f"{agent_name} — {brand_slug}"}}]},
                "Agent":      {"rich_text": [{"text": {"content": agent_name}}]},
                "Brand":      {"rich_text": [{"text": {"content": brand_slug}}]},
                "Status":     {"select": {"name": "Pending Review"}},
                "OutputPath": {"rich_text": [{"text": {"content": str(output_path)}}]},
                "Preview":    {"rich_text": [{"text": {"content": content}}]},
            },
        )
    except Exception as e:
        # Notion push is non-critical — log and continue
        print(f"[session_runner] Notion push failed (non-fatal): {e}")


# ── SSE HELPERS ───────────────────────────────────────────────────────────────

def _emit(run_id: str, event: str) -> None:
    with _sse_lock:
        if run_id not in _sse_queues:
            _sse_queues[run_id] = []
        _sse_queues[run_id].append(event)


def get_sse_events(run_id: str) -> Generator[str, None, None]:
    """Generator that yields SSE lines for a run_id. Called by Flask /status endpoint."""
    import time
    emitted = 0
    max_wait = 600  # 10 min max
    waited   = 0
    while waited < max_wait:
        with _sse_lock:
            queue = _sse_queues.get(run_id, [])
            while emitted < len(queue):
                yield queue[emitted]
                emitted += 1
            done = any("done" in e or "error" in e for e in queue)
        if done:
            break
        time.sleep(0.5)
        waited += 0.5


# ── MAIN RUNNER ───────────────────────────────────────────────────────────────

def run_agent_session(
    agent_name: str,
    brand_slug: str,
    task_prompt: str,
    run_id: str | None = None,
) -> str:
    """
    Create and stream a Managed Agent session.

    - Prepends brand context to task_prompt
    - Attaches memory stores if available
    - Streams events back via _sse_queues[run_id]
    - Saves final output to pending_approval/
    - Pushes to Notion
    - Returns the raw output text
    """
    if not run_id:
        run_id = f"{_slugify(agent_name)}-{datetime.datetime.now().strftime('%Y%m%d%H%M%S')}"

    client   = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
    registry = load_registry()

    agent_id = registry["agents"][agent_name]["agent_id"]
    env_id   = registry["environment_id"]
    stores   = load_memory_stores(brand_slug)
    resources = build_resources(stores)

    # Build full prompt: operating framework + brand context + task
    context     = build_context(brand_slug)
    full_prompt = _operating_framework(2) + context + task_prompt

    _emit(run_id, f"data: {json.dumps({'type': 'start', 'agent': agent_name, 'brand': brand_slug})}\n\n")

    # Create session
    session = client.beta.sessions.create(
        agent=agent_id,
        environment_id=env_id,
        title=f"{agent_name} — {brand_slug} — {datetime.datetime.now().isoformat()}",
        resources=resources if resources else None,
        extra_headers=BETA_HEADER,
    )

    _emit(run_id, f"data: {json.dumps({'type': 'session_created', 'session_id': session.id})}\n\n")

    # Stream session events
    output_chunks: list[str] = []

    with client.beta.sessions.stream(
        session.id,
        input=full_prompt,
        extra_headers=BETA_HEADER,
    ) as stream:
        for event in stream:
            event_type = getattr(event, "type", "unknown")

            if event_type == "content_block_delta":
                delta = getattr(event, "delta", None)
                if delta and hasattr(delta, "text"):
                    chunk = delta.text
                    output_chunks.append(chunk)
                    _emit(run_id, f"data: {json.dumps({'type': 'chunk', 'text': chunk})}\n\n")

            elif event_type == "message_stop":
                _emit(run_id, f"data: {json.dumps({'type': 'done'})}\n\n")

            elif event_type == "error":
                err_msg = str(getattr(event, "error", "unknown error"))
                _emit(run_id, f"data: {json.dumps({'type': 'error', 'message': err_msg})}\n\n")
                raise RuntimeError(f"Session error: {err_msg}")

    output = "".join(output_chunks)

    # Save + push
    out_path = save_agent_output(agent_name, brand_slug, output)
    _emit(run_id, f"data: {json.dumps({'type': 'saved', 'path': str(out_path)})}\n\n")

    push_to_notion(agent_name, brand_slug, out_path)

    return output


def run_agent_session_async(
    agent_name: str,
    brand_slug: str,
    task_prompt: str,
    run_id: str,
) -> None:
    """
    Wrapper that runs run_agent_session in a thread.
    Mirrors the existing subprocess pattern in dashboard_api.py.
    """
    def _run():
        try:
            run_agent_session(agent_name, brand_slug, task_prompt, run_id=run_id)
        except Exception as e:
            _emit(run_id, f"data: {json.dumps({'type': 'error', 'message': str(e)})}\n\n")

    t = threading.Thread(target=_run, daemon=True)
    t.start()
