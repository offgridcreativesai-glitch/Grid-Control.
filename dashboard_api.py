"""
GRID CONTROL — Flask Dashboard API
Port: 5001
Serves real data from brands/ folder. Multi-brand support.
"""

import os
import re
import sys
import json
import time
import shutil
import tempfile
import subprocess
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from dotenv import load_dotenv
from flask import Flask, jsonify, request, send_file, abort, Response, stream_with_context
from flask_cors import CORS

load_dotenv(override=True)

# ── Managed Agents (Phase 4) — optional, graceful fallback to subprocess ──────
try:
    from managed_agents.session_runner import (
        is_managed_ready,
        run_agent_session_async as _run_managed_async,
    )
    _MANAGED_AGENTS_AVAILABLE = True
except ImportError:
    _MANAGED_AGENTS_AVAILABLE = False
    def is_managed_ready(_name: str) -> bool:  # type: ignore[override]
        return False
    def _run_managed_async(*_a, **_kw) -> None:  # type: ignore[override]
        pass

app = Flask(__name__)
CORS(app)

# ── Authentication ─────────────────────────────────────────────────────────────
# All mutating / sensitive endpoints require X-Dashboard-Secret header.
# Set DASHBOARD_SECRET in .env — frontend sends it with every request.
_DASHBOARD_SECRET = os.getenv("DASHBOARD_SECRET", "").strip()

def _safe_path(base: Path, user_input: str) -> Path | None:
    """
    Resolve user-supplied path relative to base and verify it stays inside base.
    Returns None if the resolved path escapes base (path traversal attempt).
    """
    try:
        resolved = (base / user_input).resolve()
        if not str(resolved).startswith(str(base.resolve())):
            return None
        return resolved
    except Exception:
        return None


def _validate_brand_slug(slug: str) -> bool:
    """Only allow lowercase alphanumerics and hyphens, max 80 chars.
    Prevents path traversal (../../etc) and Supabase injection via brand_slug."""
    return bool(re.match(r'^[a-z0-9][a-z0-9-]{0,79}$', slug))


def require_auth(f):
    """Decorator — rejects requests missing a valid X-Dashboard-Secret header."""
    from functools import wraps
    @wraps(f)
    def decorated(*args, **kwargs):
        if _DASHBOARD_SECRET:
            token = request.headers.get("X-Dashboard-Secret", "")
            if token != _DASHBOARD_SECRET:
                return jsonify({"success": False, "error": "Unauthorized"}), 401
        return f(*args, **kwargs)
    return decorated

# ── JSON repair utility (ported from offgrid-pdf-api/app.py) ──────────────────
def escape_literal_newlines_in_strings(json_str: str) -> str:
    """
    Escape literal newline/tab/CR characters that appear inside JSON string
    values (Claude API sometimes emits these). Walks character-by-character
    so it only touches chars that are genuinely inside a string literal.
    """
    result = []
    in_string = False
    i = 0
    while i < len(json_str):
        c = json_str[i]
        if in_string:
            if c == '\\':
                result.append(c)
                i += 1
                if i < len(json_str):
                    result.append(json_str[i])
            elif c == '"':
                in_string = False
                result.append(c)
            elif c == '\n':
                result.append('\\n')
            elif c == '\r':
                result.append('\\r')
            elif c == '\t':
                result.append('\\t')
            else:
                result.append(c)
        else:
            if c == '"':
                in_string = True
            result.append(c)
        i += 1
    return ''.join(result)

# ── Supabase DB layer (Step 5) ─────────────────────────────────────────────────
sys.path.insert(0, str(Path(__file__).parent / "supabase"))
try:
    import db as _db
    _DB_AVAILABLE = True
    print("[GRID CONTROL] ✅ Supabase db.py loaded")
except Exception as _db_err:
    _DB_AVAILABLE = False
    print(f"[GRID CONTROL] ⚠️  Supabase db.py not loaded: {_db_err}")

# ── API Key Startup Verification ───────────────────────────────────────────────
_ANTHROPIC_KEY  = os.getenv("ANTHROPIC_API_KEY", "").strip()
_ELEVENLABS_KEY = os.getenv("ELEVENLABS_API_KEY", "").strip()
_NOTION_KEY     = os.getenv("NOTION_API_KEY", "").strip()
_FAL_KEY        = os.getenv("FAL_API_KEY", "").strip()

print("[GRID CONTROL] ── API Key Status ───────────────────────────────")
print(f"[GRID CONTROL] {'✅' if _ANTHROPIC_KEY  else '❌'} ANTHROPIC_API_KEY  {'(' + _ANTHROPIC_KEY[:8]  + '...)' if _ANTHROPIC_KEY  else 'NOT SET'}")
print(f"[GRID CONTROL] {'✅' if _ELEVENLABS_KEY else '❌'} ELEVENLABS_API_KEY {'(' + _ELEVENLABS_KEY[:8] + '...)' if _ELEVENLABS_KEY else 'NOT SET'}")
print(f"[GRID CONTROL] {'✅' if _NOTION_KEY     else '❌'} NOTION_API_KEY     {'(' + _NOTION_KEY[:8]     + '...)' if _NOTION_KEY     else 'NOT SET'}")
print(f"[GRID CONTROL] {'ℹ️ ' if not _FAL_KEY else '✅'} FAL_API_KEY        {'(' + _FAL_KEY[:8]  + '...)' if _FAL_KEY  else 'not set — image/video generation optional'}")
print("[GRID CONTROL] ─────────────────────────────────────────────────")

BASE_DIR = Path(__file__).parent
BRANDS_DIR = BASE_DIR / "brands"
AGENTS_DIR = BASE_DIR / ".claude" / "agents"

# Locked roster — exactly 9 agents in pipeline order
AGENTS = [
    {"id": 0, "name": "Trend Researcher",  "role": "Weekly trends",    "model": "claude-sonnet-4-6", "agentFile": "trend-researcher.md"},
    {"id": 1, "name": "Strategy Agent",    "role": "90-day roadmap",   "model": "claude-opus-4-6",   "agentFile": "strategy-agent.md"},
    {"id": 2, "name": "Content Planner",   "role": "30-day calendar",  "model": "claude-sonnet-4-6", "agentFile": "content-planner.md"},
    {"id": 3, "name": "Script Writer",     "role": "Scripts/captions", "model": "claude-sonnet-4-6", "agentFile": "script-writer.md"},
    {"id": 4, "name": "Creative Director", "role": "AI video/image",   "model": "claude-opus-4-6",   "agentFile": "creative-director.md"},
    {"id": 5, "name": "Ad Strategist",     "role": "Paid ads",         "model": "claude-opus-4-6",   "agentFile": "ad-strategist.md"},
    {"id": 6, "name": "Data Analyst",      "role": "Metrics",          "model": "claude-sonnet-4-6", "agentFile": "data-analyst.md"},
    {"id": 7, "name": "Funnel Specialist", "role": "Conversion",       "model": "claude-sonnet-4-6", "agentFile": "funnel-specialist.md"},
    {"id": 8, "name": "Website Agent",     "role": "Site/Railway",     "model": "claude-sonnet-4-6", "agentFile": "website-agent.md"},
    {"id": 9, "name": "Cost Tracker",      "role": "Monthly spend",    "model": "claude-haiku-4-5-20251001", "agentFile": ""},
]

# Locked slug set — any agent not in this list is filtered before response
_ACTIVE_SLUGS = {
    "trend-researcher", "strategy-agent", "content-planner", "script-writer",
    "creative-director", "ad-strategist", "data-analyst", "funnel-specialist", "website-agent",
    "cost-tracker",
}


# Maps agent name → persona .md file in .claude/agents/
AGENT_PERSONA_FILES: dict[str, str] = {
    "Trend Researcher":  "trend-researcher.md",
    "Strategy Agent":    "strategy-agent.md",
    "Content Planner":   "content-planner.md",
    "Script Writer":     "script-writer.md",
    "Creative Director": "creative-director.md",
    "Ad Strategist":     "ad-strategist.md",
    "Data Analyst":      "data-analyst.md",
    "Funnel Specialist": "funnel-specialist.md",
    "Website Agent":     "website-agent.md",
}

# Maps agent name → Python script path (relative to BASE_DIR)
# coming_soon=True means no script yet — show locked card in dashboard
AGENT_SCRIPTS: dict[str, Any] = {
    "Trend Researcher":    "agents/trend_researcher.py",
    "Trend Sentinel":      "agents/trend_sentinel.py",
    "Strategy Agent":      "agents/strategy_agent.py",
    "Content Planner":     "agents/content_planner.py",
    "Script Writer":       "agents/script_writer.py",
    "Creative Director":   "agents/creative_director.py",
    "Ad Strategist":       {"coming_soon": True},
    "Data Analyst":        "agents/data_analyst.py",
    "Performance Tracker": "agents/performance_tracker.py",
    "Funnel Specialist":   "agents/funnel_specialist.py",
    "Website Agent":       "agents/website_agent.py",
    "Cost Tracker":        "agents/cost_tracker.py",
}

# Agents enriched with coming_soon flag for the frontend
def _enrich_agents_with_flags() -> list[dict]:
    enriched = []
    for agent in AGENTS:
        entry = dict(agent)
        script_val = AGENT_SCRIPTS.get(agent["name"])
        if isinstance(script_val, dict) and script_val.get("coming_soon"):
            entry["coming_soon"] = True
        else:
            entry["coming_soon"] = False
        enriched.append(entry)
    return enriched

AGENTS_ENRICHED = _enrich_agents_with_flags()

# Reverse mapping: display folder name → agent slug used in Supabase
_FOLDER_TO_SLUG: dict[str, str] = {
    "Trend Researcher":    "trend-researcher",
    "Trend Sentinel":      "trend-sentinel",
    "Strategy Agent":      "strategy-agent",
    "Content Planner":     "content-planner",
    "Script Writer":       "script-writer",
    "Creative Director":   "creative-director",
    "Data Analyst":        "data-analyst",
    "Performance Tracker": "performance-tracker",
    "Funnel Specialist":   "funnel-specialist",
    "Website Agent":       "website-agent",
    "Cost Tracker":        "cost-tracker",
    "CEO Brain":           "ceo-brain",
}


# Pipeline unlock order — strict sequence (Step 4)
PIPELINE_UNLOCK_ORDER = [
    "trend-researcher",
    "strategy-agent",
    "content-planner",
    "script-writer",
    "creative-director",
    "data-analyst",
    "funnel-specialist",
    "website-agent",
    # ad-strategist is gated: only unlocked when paid_budget_confirmed: true
]


def _agent_name_to_slug(name: str) -> str:
    return re.sub(r"[^a-z0-9-]", "", name.lower().replace(" ", "-"))


# ── Brand Memory Architecture ──────────────────────────────────────────────────
# Two-layer system:
#   brand_memory/      — permanent, approval-gated. Agents read. Cannot auto-overwrite.
#   market_intelligence/ — refreshes on schedule. Agents write freely.
#
# Rule: fresh market data can SUGGEST changes to brand_memory.
# It can NEVER directly overwrite brand_memory. Only Gaurav's approval does that.

_MEMORY_FILES = {
    "positioning":       "brand_memory/positioning.json",
    "strategy_90day":    "brand_memory/strategy_90day.json",
    "content_calendar":  "brand_memory/content_calendar.json",
    "decisions_log":     "brand_memory/decisions_log.json",
    "goals":             "brand_memory/goals.json",
    "recording_map":     "brand_memory/recording_map.json",
}

_INTELLIGENCE_FILES = {
    "trends_live":        "market_intelligence/trends_live.json",
    "competitor_moves":   "market_intelligence/competitor_moves.json",
    "suggestions":        "market_intelligence/suggestions.json",
    "task_scrapes":       "market_intelligence/task_scrapes.json",
}

# How stale before auto-refresh (seconds)
_INTELLIGENCE_TTL = {
    "trends_live":      86400,   # 24 hours
    "competitor_moves": 172800,  # 48 hours
}


def _bootstrap_brand_memory(brand_dir: Path, profile: dict) -> None:
    """
    Create brand_memory/ and market_intelligence/ folders with empty initial files.
    Called once on brand creation. Never overwrites existing files.
    """
    (brand_dir / "brand_memory").mkdir(exist_ok=True)
    (brand_dir / "market_intelligence").mkdir(exist_ok=True)

    now = datetime.now().isoformat()
    name = profile.get("brand_name", "")

    # ── brand_memory initial files ────────────────────────────────────────────
    positioning_file = brand_dir / "brand_memory" / "positioning.json"
    if not positioning_file.exists():
        _atomic_write_json(positioning_file, {
            "_note": "Locked. Only updated when Gaurav approves a strategy change.",
            "_last_updated": now,
            "brand_name": name,
            "one_line": "",
            "origin_story": "",
            "positioning_statement": "",
            "what_we_never_say": profile.get("what_to_never_say", ""),
            "tone_of_voice": profile.get("tone_of_voice", ""),
            "tone_specifics": profile.get("tone_specifics", ""),
            "approved": False,
        })

    strategy_file = brand_dir / "brand_memory" / "strategy_90day.json"
    if not strategy_file.exists():
        _atomic_write_json(strategy_file, {
            "_note": "90-day roadmap. Read-only for agents. Changes need Gaurav approval.",
            "_last_updated": now,
            "approved": False,
            "phases": [],
            "platform_priority": [],
            "content_pillars": [],
            "monetization_plan": "",
            "goal_90d": "",
        })

    calendar_file = brand_dir / "brand_memory" / "content_calendar.json"
    if not calendar_file.exists():
        _atomic_write_json(calendar_file, {
            "_note": "Content calendar. Agents mark items done/pending. New items need approval.",
            "_last_updated": now,
            "posts": [],
            "recordings_scheduled": [],
            "published": [],
            "pending": [],
        })

    decisions_file = brand_dir / "brand_memory" / "decisions_log.json"
    if not decisions_file.exists():
        _atomic_write_json(decisions_file, {
            "_note": "Append-only log of every approved decision, timestamped.",
            "decisions": [],
        })

    goals_file = brand_dir / "brand_memory" / "goals.json"
    if not goals_file.exists():
        _atomic_write_json(goals_file, {
            "_note": "Active goals locked by Gaurav. Agents build everything around these.",
            "_last_updated": now,
            "active_goals": [],
            "completed_goals": [],
            "content_goal_90d": profile.get("content_goal_90d", ""),
            "weekly_post_target": profile.get("weekly_post_target", ""),
        })

    recording_file = brand_dir / "brand_memory" / "recording_map.json"
    if not recording_file.exists():
        _atomic_write_json(recording_file, {
            "_note": "Maps each recording to its platform destinations. Updated when content is planned.",
            "recordings": [],
        })

    # ── market_intelligence initial files ─────────────────────────────────────
    for fname in ["trends_live", "competitor_moves", "suggestions", "task_scrapes"]:
        intel_file = brand_dir / "market_intelligence" / f"{fname}.json"
        if not intel_file.exists():
            _atomic_write_json(intel_file, {
                "_note": f"Auto-refreshed. Last updated: never.",
                "_last_updated": None,
                "data": [],
            })


def _atomic_write_json(path: Path, data: dict) -> None:
    """Write JSON atomically — temp file + os.replace() prevents corruption."""
    tmp_fd, tmp_path = tempfile.mkstemp(dir=path.parent, suffix=".tmp")
    try:
        with os.fdopen(tmp_fd, "w") as f:
            json.dump(data, f, indent=2)
        os.replace(tmp_path, path)
    except Exception:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass
        raise


def _read_memory(brand_slug: str, key: str) -> dict:
    """Read a brand_memory file by key. Returns {} if missing or unreadable."""
    rel = _MEMORY_FILES.get(key)
    if not rel:
        return {}
    path = BRANDS_DIR / brand_slug / rel
    try:
        if path.exists():
            with open(path) as f:
                return json.load(f)
    except Exception:
        pass
    return {}


def _read_intelligence(brand_slug: str, key: str) -> dict:
    """Read a market_intelligence file by key. Returns {} if missing or unreadable."""
    rel = _INTELLIGENCE_FILES.get(key)
    if not rel:
        return {}
    path = BRANDS_DIR / brand_slug / rel
    try:
        if path.exists():
            with open(path) as f:
                return json.load(f)
    except Exception:
        pass
    return {}


def _write_intelligence(brand_slug: str, key: str, data: dict) -> None:
    """Update a market_intelligence file. Safe to call from agent threads."""
    rel = _INTELLIGENCE_FILES.get(key)
    if not rel:
        return
    path = BRANDS_DIR / brand_slug / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    data["_last_updated"] = datetime.now().isoformat()
    _atomic_write_json(path, data)


def _add_suggestion(brand_slug: str, agent_name: str, suggestion: str, context: dict | None = None) -> None:
    """
    Agent adds a suggestion for Gaurav to review. NEVER writes to brand_memory directly.
    All suggestions land in market_intelligence/suggestions.json only.
    """
    sugg_path = BRANDS_DIR / brand_slug / "market_intelligence" / "suggestions.json"
    existing = _read_intelligence(brand_slug, "suggestions")
    items = existing.get("data", []) if isinstance(existing, dict) else []
    items.append({
        "id":         f"s_{int(datetime.now().timestamp())}",
        "agent":      agent_name,
        "suggestion": suggestion,
        "context":    context or {},
        "status":     "pending_review",
        "created_at": datetime.now().isoformat(),
    })
    _write_intelligence(brand_slug, "suggestions", {"data": items})


def _approve_memory_update(brand_slug: str, memory_key: str, updates: dict) -> None:
    """
    Apply approved updates to a brand_memory file.
    Logs the change to decisions_log.json.
    Only called from the /api/brands/<slug>/memory/approve endpoint.
    """
    rel = _MEMORY_FILES.get(memory_key)
    if not rel:
        raise ValueError(f"Unknown memory key: {memory_key}")
    path = BRANDS_DIR / brand_slug / rel
    existing = _read_memory(brand_slug, memory_key)
    existing.update(updates)
    existing["_last_updated"] = datetime.now().isoformat()
    existing["approved"] = True
    _atomic_write_json(path, existing)

    # Append to decisions_log
    log = _read_memory(brand_slug, "decisions_log")
    decisions = log.get("decisions", [])
    decisions.append({
        "timestamp":  datetime.now().isoformat(),
        "memory_key": memory_key,
        "updates":    updates,
        "approved_by": "Gaurav",
    })
    log["decisions"] = decisions
    log_path = BRANDS_DIR / brand_slug / _MEMORY_FILES["decisions_log"]
    _atomic_write_json(log_path, log)


def _intelligence_is_stale(brand_slug: str, key: str) -> bool:
    """Return True if the intelligence file is missing or older than its TTL."""
    data = _read_intelligence(brand_slug, key)
    last = data.get("_last_updated")
    if not last:
        return True
    try:
        age = (datetime.now() - datetime.fromisoformat(last)).total_seconds()
        return age > _INTELLIGENCE_TTL.get(key, 86400)
    except Exception:
        return True


def _build_agent_context(brand_slug: str, agent_name: str) -> str:
    """
    Build the real-data context block injected into every agent chat prompt.
    Each agent gets its relevant memory + intelligence files.
    Returns a formatted string block.
    """
    slug = _agent_name_to_slug(agent_name)
    sections: list[str] = []

    # All agents get goals + positioning
    goals      = _read_memory(brand_slug, "goals")
    positioning = _read_memory(brand_slug, "positioning")
    if goals.get("active_goals") or goals.get("content_goal_90d"):
        sections.append(f"=== ACTIVE GOALS ===\n{json.dumps(goals, indent=2)}")
    if positioning.get("positioning_statement") or positioning.get("origin_story"):
        sections.append(f"=== BRAND POSITIONING (LOCKED) ===\n{json.dumps(positioning, indent=2)}")

    # Agent-specific data
    if slug in ("trend-researcher",):
        intel = _read_intelligence(brand_slug, "trends_live")
        if intel.get("data"):
            sections.append(f"=== YOUR LATEST SCRAPED TRENDS ===\n{json.dumps(intel, indent=2)}")

    if slug in ("strategy-agent", "ceo-brain"):
        strat = _read_memory(brand_slug, "strategy_90day")
        if strat.get("phases") or strat.get("goal_90d"):
            sections.append(f"=== APPROVED 90-DAY STRATEGY (LOCKED) ===\n{json.dumps(strat, indent=2)}")
        intel = _read_intelligence(brand_slug, "trends_live")
        if intel.get("data"):
            sections.append(f"=== LATEST MARKET TRENDS ===\n{json.dumps(intel, indent=2)}")
        comp = _read_intelligence(brand_slug, "competitor_moves")
        if comp.get("data"):
            sections.append(f"=== COMPETITOR INTELLIGENCE ===\n{json.dumps(comp, indent=2)}")

    if slug in ("content-planner",):
        strat = _read_memory(brand_slug, "strategy_90day")
        cal   = _read_memory(brand_slug, "content_calendar")
        if strat.get("content_pillars"):
            sections.append(f"=== APPROVED STRATEGY ===\n{json.dumps(strat, indent=2)}")
        if cal.get("posts") or cal.get("pending"):
            sections.append(f"=== CONTENT CALENDAR (DO NOT REBUILD — UPDATE ONLY) ===\n{json.dumps(cal, indent=2)}")
        intel = _read_intelligence(brand_slug, "trends_live")
        if intel.get("data"):
            sections.append(f"=== CURRENT TRENDS ===\n{json.dumps(intel, indent=2)}")

    if slug in ("script-writer",):
        cal = _read_memory(brand_slug, "content_calendar")
        pos = _read_memory(brand_slug, "positioning")
        if cal.get("pending"):
            sections.append(f"=== PENDING CONTENT TO SCRIPT ===\n{json.dumps(cal.get('pending'), indent=2)}")
        if pos:
            sections.append(f"=== BRAND VOICE & POSITIONING ===\n{json.dumps(pos, indent=2)}")

    if slug in ("creative-director",):
        rec = _read_memory(brand_slug, "recording_map")
        if rec.get("recordings"):
            sections.append(f"=== RECORDING MAP ===\n{json.dumps(rec, indent=2)}")

    if slug in ("data-analyst",):
        cal = _read_memory(brand_slug, "content_calendar")
        if cal.get("published"):
            sections.append(f"=== PUBLISHED CONTENT (ANALYSE THIS) ===\n{json.dumps(cal.get('published'), indent=2)}")

    # CEO gets everything relevant
    if slug == "ceo-brain":
        cal = _read_memory(brand_slug, "content_calendar")
        sugg = _read_intelligence(brand_slug, "suggestions")
        if cal.get("posts"):
            sections.append(f"=== CONTENT CALENDAR STATUS ===\n{json.dumps(cal, indent=2)}")
        if sugg.get("data"):
            pending = [s for s in sugg.get("data", []) if s.get("status") == "pending_review"]
            if pending:
                sections.append(f"=== PENDING SUGGESTIONS FOR YOUR REVIEW ===\n{json.dumps(pending, indent=2)}")
        task_scrapes = _read_intelligence(brand_slug, "task_scrapes")
        if task_scrapes.get("data"):
            sections.append(f"=== LATEST TASK SCRAPE RESULTS ===\n{json.dumps(task_scrapes, indent=2)}")

    if not sections:
        return (
            "⚠️  No real data found for this brand yet.\n"
            "Trend Researcher has not completed a live scrape.\n"
            "DO NOT invent or assume any market data, trends, or competitor information.\n"
            "Tell Gaurav: 'I don't have live data yet — please run Trend Researcher from the Agent Command Center first.'"
        )

    header = (
        "=== REAL DATA ONLY — STRICT RULES ===\n"
        "You MUST answer ONLY from the data provided below.\n"
        "You MUST NOT invent trends, competitor details, follower counts, or market insights.\n"
        "If you don't have data for something, say: 'I don't have current data on that yet.'\n"
        "The approved brand_memory files are LOCKED — do not suggest rebuilding strategy or calendar.\n"
        "You may suggest updates via the suggestions process only.\n"
        "=====================================\n\n"
    )
    return header + "\n\n".join(sections)


def _unlock_next_agent(brand_id: str, completed_slug: str) -> str | None:
    """
    After completed_slug is approved: mark it done, set next_agent in session_state.
    Returns the next agent slug (or None if pipeline complete).
    Phase 1 Step 4.
    """
    try:
        idx = PIPELINE_UNLOCK_ORDER.index(completed_slug)
        next_slug = PIPELINE_UNLOCK_ORDER[idx + 1] if idx + 1 < len(PIPELINE_UNLOCK_ORDER) else None
    except ValueError:
        next_slug = None

    if not _DB_AVAILABLE or not brand_id:
        return next_slug

    try:
        state = _db.get_session_state(brand_id) or {}
        if "completed_agents" not in state or not isinstance(state["completed_agents"], list):
            state["completed_agents"] = []
        if completed_slug not in state["completed_agents"]:
            state["completed_agents"].append(completed_slug)
        state["last_completed"] = completed_slug
        state["next_agent"] = next_slug
        _db.upsert_session_state(brand_id, state)
    except Exception as e:
        print(f"[dashboard_api] _unlock_next_agent failed: {e}")

    return next_slug


def _get_brand_id(brand_slug: str) -> str | None:
    """Resolve brand_slug → Supabase brand_id. Returns None if db unavailable or brand not found."""
    # DB-WIRED Step 5
    if not _DB_AVAILABLE:
        return None
    try:
        row = _db.get_brand(brand_slug)
        return row["id"] if row else None
    except Exception:
        return None


def _update_session_agent_status(brand_slug: str, agent_name: str, status: str, last_output: str | None = None) -> None:
    """Write per-agent status into session_state.json for the brand, and append to agent_log."""
    try:
        brand_dir = BRANDS_DIR / brand_slug
        session_file = brand_dir / "session_state.json"
        session: dict = {}
        if session_file.exists():
            with open(session_file) as f:
                session = json.load(f)
        session[agent_name] = {
            "status": status,
            "last_run": datetime.now().isoformat(),
            "last_output": last_output,
        }
        # Keep completed_agents list in sync — no Supabase required
        if status == "done":
            agent_slug_for_list = _agent_name_to_slug(agent_name)
            completed = session.get("completed_agents", [])
            if agent_slug_for_list not in completed:
                completed.append(agent_slug_for_list)
            session["completed_agents"] = completed
            session["last_completed"]   = agent_slug_for_list
            session["last_updated"]     = datetime.now().isoformat()
        # Append to agent_log[]
        log_entry = {
            "agent": agent_name,
            "event": status,
            "timestamp": datetime.now().isoformat(),
            "detail": last_output or "",
        }
        if "agent_log" not in session or not isinstance(session["agent_log"], list):
            session["agent_log"] = []
        session["agent_log"].append(log_entry)
        # Atomic write — prevents corruption if two agents finish concurrently
        tmp_fd, tmp_path = tempfile.mkstemp(dir=session_file.parent, suffix=".tmp")
        try:
            with os.fdopen(tmp_fd, "w") as f:
                json.dump(session, f, indent=2)
            os.replace(tmp_path, session_file)
        except Exception:
            try:
                os.unlink(tmp_path)
            except OSError:
                pass
            raise

        # DB-WIRED Step 5 — dual-write session state to Supabase
        if _DB_AVAILABLE:
            brand_id = _get_brand_id(brand_slug)
            if brand_id:
                _db.upsert_session_state(brand_id, session)
                _db.log_audit(brand_id, f"agent_{status}", agent_name, {"last_output": last_output or ""})
    except Exception as e:
        print(f"[dashboard_api] session update failed for {agent_name}: {e}")


def _update_notion_card_status(brand_slug: str, page_id: str, status: str) -> None:
    """Flip the status field on a notion_card entry in session_state.json."""
    try:
        brand_dir = BRANDS_DIR / brand_slug
        session_file = brand_dir / "session_state.json"
        if not session_file.exists():
            return
        with open(session_file) as f:
            session = json.load(f)
        for card in session.get("notion_cards", []):
            if card.get("page_id") == page_id:
                card["status"] = status
                break
        # Atomic write — same pattern as _update_session_agent_status
        tmp_fd, tmp_path = tempfile.mkstemp(dir=session_file.parent, suffix=".tmp")
        try:
            with os.fdopen(tmp_fd, "w") as f:
                json.dump(session, f, indent=2)
            os.replace(tmp_path, session_file)
        except Exception:
            try:
                os.unlink(tmp_path)
            except OSError:
                pass
            raise
    except Exception as e:
        print(f"[dashboard_api] notion card update failed: {e}")


def _run_agent_subprocess(script_path: str, brand_slug: str, agent_name: str, db_run_id: str | None = None) -> None:
    """Background thread: run agent script, update session state + Supabase on finish."""
    # DB-WIRED Step 5 + Phase 1 Step 2
    agent_slug_key = _agent_name_to_slug(agent_name)
    try:
        # Pass run context to agent via env so it can record costs + use memory
        agent_env = os.environ.copy()
        agent_env["GRID_RUN_ID"]     = db_run_id or ""
        agent_env["GRID_BRAND_SLUG"] = brand_slug
        # ACTIVE_BRAND is the env var all agent scripts read — must match GRID_BRAND_SLUG
        agent_env["ACTIVE_BRAND"]    = brand_slug
        # Ensure local supabase/db.py wins over the installed pip 'supabase' package
        existing_pypath = agent_env.get("PYTHONPATH", "")
        agent_env["PYTHONPATH"] = str(BASE_DIR) + (":" + existing_pypath if existing_pypath else "")
        result = subprocess.run(
            [sys.executable, script_path],
            cwd=str(BASE_DIR),
            capture_output=True,
            text=True,
            timeout=600,  # 10-minute hard cap
            env=agent_env,
        )
        if result.returncode == 0:
            lines = [l.strip() for l in result.stdout.splitlines() if l.strip()]
            last_out = lines[-1] if lines else "Completed successfully"
            _update_session_agent_status(brand_slug, agent_name, "done", last_out)
            if _DB_AVAILABLE and db_run_id:
                _db.update_agent_run_status(db_run_id, "done")
            # Phase 1 Step 2 — write next_agent recommendation to session_state
            if _DB_AVAILABLE:
                brand_id = _get_brand_id(brand_slug)
                if brand_id:
                    _unlock_next_agent(brand_id, agent_slug_key)
            # Phase 3 Step 1 — push latest agent output to Notion
            if _NOTION_KEY and _DB_AVAILABLE:
                try:
                    from notion_integration.notion_pusher import push_to_notion as _push_notion
                    n_brand_id = _get_brand_id(brand_slug)
                    if n_brand_id:
                        n_outputs = _db.get_outputs_by_agent(n_brand_id, agent_slug_key, "pending")
                        if n_outputs:
                            latest = n_outputs[0]
                            raw = latest.get("raw_output") or {}
                            loop_hdr = (latest.get("formatted_output") or {}).get("loop_header", {})
                            notion_res = _push_notion(
                                agent_name=agent_name,
                                brand=brand_slug,
                                output_type=latest.get("output_type", "Output"),
                                loop_header=loop_hdr,
                                content=raw,
                            )
                            if notion_res.get("success") and notion_res.get("page_id"):
                                _db.update_output_notion_id(latest["id"], notion_res["page_id"])
                                print(f"[dashboard_api] Notion page created: {notion_res.get('notion_url', '')}")
                except Exception as _notion_err:
                    print(f"[dashboard_api] Notion push skipped: {_notion_err}")
        else:
            err_lines = (result.stderr or "").strip().splitlines()
            last_err = err_lines[-1] if err_lines else "Non-zero exit"
            _update_session_agent_status(brand_slug, agent_name, "error", last_err)
            if _DB_AVAILABLE and db_run_id:
                _db.update_agent_run_status(db_run_id, "error", last_err)
    except subprocess.TimeoutExpired:
        _update_session_agent_status(brand_slug, agent_name, "error", "Timed out after 10 minutes")
        if _DB_AVAILABLE and db_run_id:
            _db.update_agent_run_status(db_run_id, "error", "Timed out after 10 minutes")
    except Exception as exc:
        _update_session_agent_status(brand_slug, agent_name, "error", str(exc))
        if _DB_AVAILABLE and db_run_id:
            _db.update_agent_run_status(db_run_id, "error", str(exc))


def get_brand_dir(brand_slug: str) -> Path:
    brand_dir = BRANDS_DIR / brand_slug
    if not brand_dir.exists():
        abort(404, description=f"Brand '{brand_slug}' not found")
    return brand_dir


def list_brands() -> list:
    if not BRANDS_DIR.exists():
        return []
    result = []
    for folder in sorted(BRANDS_DIR.iterdir()):
        if folder.is_dir():
            profile_file = folder / "brand_profile.json"
            # Skip incomplete brand folders — must have brand_profile.json to appear
            if not profile_file.exists():
                continue
            name = folder.name
            try:
                with open(profile_file) as f:
                    data = json.load(f)
                name = data.get("brand_name") or folder.name
            except Exception:
                pass
            result.append({"slug": folder.name, "name": name})
    return result


# ── Agents ────────────────────────────────────────────────────────────────────

@app.route("/api/agents/status", methods=["GET"])
@require_auth
def get_agents_status():
    # DB-WIRED Step 5
    brand_slug = request.args.get("brand_slug", "offgrid-creatives-ai")
    session: dict = {}

    # Try Supabase first
    if _DB_AVAILABLE:
        brand_id = _get_brand_id(brand_slug)
        if brand_id:
            session = _db.get_session_state(brand_id) or {}

    # Fall back to local JSON if Supabase returned nothing
    if not session:
        brand_dir = get_brand_dir(brand_slug)
        session_file = brand_dir / "session_state.json"
        if session_file.exists():
            with open(session_file) as f:
                session = json.load(f)

    result = []
    for agent in AGENTS_ENRICHED:
        state = session.get(agent["name"], {})
        result.append({
            **agent,
            "status": state.get("status", "idle"),
            "lastRun": state.get("last_run", None),
            "lastOutput": state.get("last_output", None),
        })
    return jsonify({"success": True, "data": result})


@app.route("/api/agents/list", methods=["GET"])
def get_agents_list():
    return jsonify({"success": True, "data": AGENTS_ENRICHED})


@app.route("/api/agents/run", methods=["POST"])
@require_auth
def run_agent():
    body = request.get_json() or {}
    agent_name = body.get("agentName", "").strip()
    brand_slug = body.get("brand_slug", "offgrid-creatives-ai")
    if not _validate_brand_slug(brand_slug):
        return jsonify({"success": False, "error": "Invalid brand_slug"}), 400

    # Phase 5 Step 4 — key gates
    if not _ANTHROPIC_KEY:
        return jsonify({"success": False, "error": "ANTHROPIC_API_KEY not configured — cannot run agents"}), 400

    _apify_key = os.getenv("APIFY_API_KEY", "").strip()
    if not _apify_key:
        return jsonify({"success": False, "error": "Connect Anthropic and Apify before running agents"}), 400

    # Ad Strategist additionally requires Meta token
    if agent_name == "Ad Strategist" and not os.getenv("META_GRAPH_API_TOKEN", "").strip():
        return jsonify({"success": False, "error": "Ad Strategist requires META_GRAPH_API_TOKEN — connect Meta first"}), 400

    script_val = AGENT_SCRIPTS.get(agent_name)
    if not script_val:
        return jsonify({
            "success": False,
            "error": f"No script built yet for '{agent_name}'. Add it to AGENT_SCRIPTS when ready."
        }), 400

    if isinstance(script_val, dict) and script_val.get("coming_soon"):
        return jsonify({
            "success": False,
            "error": f"'{agent_name}' is coming soon — script not yet built."
        }), 400

    script_rel = script_val
    script_path = BASE_DIR / script_rel
    if not script_path.exists():
        return jsonify({
            "success": False,
            "error": f"Script file not found on disk: {script_rel}"
        }), 404

    # Phase 5 Step 4 — rate limit: block duplicate runs
    agent_slug_key_check = _agent_name_to_slug(agent_name)
    if _DB_AVAILABLE:
        try:
            brand_id_check = _get_brand_id(brand_slug)
            if brand_id_check:
                existing = (
                    _db._client.table("agent_runs")
                    .select("id")
                    .eq("brand_id", brand_id_check)
                    .eq("agent_slug", agent_slug_key_check)
                    .eq("status", "running")
                    .execute()
                )
                if existing.data:
                    return jsonify({"success": False, "error": "This agent is already running — wait for it to complete"}), 409
        except Exception as _rate_err:
            print(f"[dashboard_api] rate limit check failed: {_rate_err}")

    # Mark running immediately so the dashboard reflects it within the next 10s poll
    _update_session_agent_status(brand_slug, agent_name, "running")

    # DB-WIRED Step 5 — create Supabase run row
    db_run_id: str | None = None
    if _DB_AVAILABLE:
        brand_id = _get_brand_id(brand_slug)
        if brand_id:
            agent_slug_key = re.sub(r"[^a-z0-9-]", "", agent_name.lower().replace(" ", "-"))
            run_row = _db.save_agent_run(brand_id, agent_slug_key)
            if run_row:
                db_run_id = run_row["id"]

    # Fire in background — HTTP request returns immediately
    # Phase 4: prefer Managed Agents session if setup is complete, else fall back to subprocess
    if _MANAGED_AGENTS_AVAILABLE and is_managed_ready(agent_name):
        task_prompt = f"Run the full {agent_name} workflow for brand: {brand_slug}. Follow your system instructions exactly. Return VALID JSON ONLY as specified."
        _run_managed_async(agent_name, brand_slug, task_prompt, run_id=db_run_id or "")
        run_mode = "managed"
    else:
        thread = threading.Thread(
            target=_run_agent_subprocess,
            args=(str(script_path), brand_slug, agent_name, db_run_id),
            daemon=True,
        )
        thread.start()
        run_mode = "subprocess"

    # Phase 1 Step 1 — return run_id for SSE polling
    return jsonify({"success": True, "data": {
        "message": f"{agent_name} started",
        "agent": agent_name,
        "run_id": db_run_id or "",
        "run_mode": run_mode,
    }})


@app.route("/api/agents/run/status", methods=["GET"])
def agent_run_status():
    """
    SSE endpoint. Polls Supabase agent_run row every 2s.
    Closes stream when status is 'done' or 'error'.
    Phase 1 Step 1.
    """
    run_id = request.args.get("run_id", "").strip()
    if not run_id:
        return jsonify({"success": False, "error": "run_id required"}), 400

    def generate():
        max_polls = 180  # 6 minutes max
        for _ in range(max_polls):
            row = _db.get_agent_run(run_id) if _DB_AVAILABLE else None
            if not row:
                payload = json.dumps({"status": "unknown", "run_id": run_id, "message": "Run not found"})
                yield f"data: {payload}\n\n"
                return
            status = row.get("status", "running")
            msg = row.get("error") or ""
            payload = json.dumps({"status": status, "run_id": run_id, "message": msg})
            yield f"data: {payload}\n\n"
            if status in ("done", "error"):
                return
            time.sleep(2)
        # Timeout
        yield f"data: {json.dumps({'status': 'error', 'run_id': run_id, 'message': 'Poll timeout'})}\n\n"

    return Response(
        stream_with_context(generate()),
        mimetype="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


# ── DAILY PIPELINE RUN ─────────────────────────────────────────────────────────

@app.route("/api/pipeline/daily-run", methods=["POST"])
@require_auth
def daily_pipeline_run():
    """
    Chain Trend Researcher → Data Analyst → Script Writer in a background thread.
    Each agent runs sequentially (subprocess.run is blocking).
    Returns immediately with pipeline_run_id. Client polls /api/agents/status.
    """
    data       = request.get_json(silent=True) or {}
    brand_slug = data.get("brand_slug", "").strip() or request.args.get("brand_slug", "").strip()
    if not brand_slug:
        return jsonify({"success": False, "error": "brand_slug required"}), 400
    if not get_brand_dir(brand_slug):
        return jsonify({"success": False, "error": f"Brand '{brand_slug}' not found"}), 404

    pipeline_run_id = f"daily-{brand_slug}-{datetime.now().strftime('%Y%m%d%H%M%S')}"

    # Daily pipeline (Apr 25 update — Build B + Trend Sentinel):
    #   1. Trend Researcher  — fresh data + quality gate
    #   2. Trend Sentinel    — STAY/TRACK/PIVOT decision; auto-triggers Content Planner if SENTINEL_AUTO_PIVOT=true
    #   3. Data Analyst      — weekly metrics
    # Script Writer + Creative Director NOT in daily-run — they run after Content Planner approval.
    pipeline_agents = [
        ("Trend Researcher", AGENT_SCRIPTS.get("Trend Researcher")),
        ("Trend Sentinel",   AGENT_SCRIPTS.get("Trend Sentinel")),
        ("Data Analyst",     AGENT_SCRIPTS.get("Data Analyst")),
    ]

    def _run_pipeline():
        for agent_name, script_rel in pipeline_agents:
            if not script_rel:
                print(f"[daily-run] Skipping {agent_name} — no script path configured")
                continue
            script_path = BASE_DIR / script_rel
            if not script_path.exists():
                print(f"[daily-run] Skipping {agent_name} — script not found: {script_path}")
                continue
            print(f"[daily-run] Starting: {agent_name} for {brand_slug}")
            _run_agent_subprocess(str(script_path), brand_slug, agent_name, None)
            print(f"[daily-run] Completed: {agent_name}")

    t = threading.Thread(target=_run_pipeline, daemon=True)
    t.start()

    return jsonify({
        "success": True,
        "data": {
            "pipeline_run_id": pipeline_run_id,
            "agents": [name for name, _ in pipeline_agents],
            "brand_slug": brand_slug,
            "message": "Pipeline started. Poll /api/agents/status for progress.",
        }
    })


# ── JARVIS QUERY ───────────────────────────────────────────────────────────────

@app.route("/api/jarvis/query", methods=["POST"])
@require_auth
def jarvis_query():
    """
    Jarvis spoken query endpoint.
    Takes a natural language question, answers in 1-3 spoken sentences,
    generates edge-tts audio, returns base64-encoded mp3.
    """
    import base64

    data       = request.get_json(silent=True) or {}
    query      = data.get("query", "").strip()
    brand_slug = data.get("brand_slug", "").strip()

    if not query:
        return jsonify({"success": False, "error": "query required"}), 400

    anthropic_key = os.getenv("ANTHROPIC_API_KEY", "").strip()
    if not anthropic_key:
        return jsonify({"success": False, "error": "ANTHROPIC_API_KEY not set"}), 500

    # Build live context from brand session state + pending outputs
    context_lines = []
    if brand_slug:
        brand_dir = BRANDS_DIR / brand_slug
        ss_path   = brand_dir / "session_state.json"
        if ss_path.exists():
            try:
                with open(ss_path) as f:
                    ss = json.load(f)
                context_lines.append(f"Session state: {json.dumps(ss)[:500]}")
            except Exception:
                pass

        # Count pending outputs
        pending_dir = brand_dir / "outputs" / "pending_approval"
        if pending_dir.exists():
            pending_count = sum(
                1 for f in pending_dir.rglob("*")
                if f.is_file() and f.suffix in (".json", ".txt", ".md")
            )
            context_lines.append(f"Pending approvals: {pending_count} outputs")

    context_str = "\n".join(context_lines) if context_lines else "No brand context available."

    system_prompt = (
        "You are Jarvis, an AI assistant for GRID Control — an AI marketing OS. "
        "Answer in 1-3 spoken sentences. No markdown. No bullet points. "
        "Sound natural, direct, and confident — like JARVIS from Iron Man. "
        "If you don't have enough data to answer precisely, say so in one sentence."
    )

    user_message = f"Context:\n{context_str}\n\nQuestion: {query}"

    try:
        import anthropic as _anthropic
        _client = _anthropic.Anthropic(api_key=anthropic_key)
        response = _client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=200,
            system=system_prompt,
            messages=[{"role": "user", "content": user_message}]
        )
        spoken_response = response.content[0].text.strip()
    except Exception as e:
        return jsonify({"success": False, "error": f"Claude call failed: {e}"}), 500

    # Generate TTS audio (graceful skip if edge-tts not installed)
    audio_b64 = None
    try:
        import asyncio
        import tempfile
        import edge_tts  # type: ignore

        async def _tts(text: str) -> bytes:
            communicate = edge_tts.Communicate(text, "en-US-GuyNeural")
            with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as tmp:
                tmp_path = tmp.name
            await communicate.save(tmp_path)
            with open(tmp_path, "rb") as f:
                audio_bytes = f.read()
            import os as _os
            _os.unlink(tmp_path)
            return audio_bytes

        audio_bytes = asyncio.run(_tts(spoken_response))
        audio_b64   = base64.b64encode(audio_bytes).decode("utf-8")
    except ImportError:
        pass  # edge-tts not installed — audio skipped gracefully
    except Exception as e:
        print(f"[jarvis] TTS generation failed (non-fatal): {e}")

    return jsonify({
        "success":   True,
        "response":  spoken_response,
        "audio_b64": audio_b64,
    })


# ── VOICE PROFILE ENDPOINTS ───────────────────────────────────────────────────

@app.route("/api/voice/extract-profile", methods=["POST"])
@require_auth
def voice_extract_profile():
    """
    Extract voice DNA from raw script samples.
    Calls Claude to analyze writing patterns, saves voice_profile.json.
    Body: {brand_slug, raw_scripts}
    """
    data        = request.get_json(silent=True) or {}
    brand_slug  = data.get("brand_slug", "").strip()
    raw_scripts = data.get("raw_scripts", "").strip()

    if not brand_slug:
        return jsonify({"success": False, "error": "brand_slug required"}), 400
    if not raw_scripts:
        return jsonify({"success": False, "error": "raw_scripts required"}), 400
    if not get_brand_dir(brand_slug):
        return jsonify({"success": False, "error": f"Brand '{brand_slug}' not found"}), 404

    anthropic_key = os.getenv("ANTHROPIC_API_KEY", "").strip()
    if not anthropic_key:
        return jsonify({"success": False, "error": "ANTHROPIC_API_KEY not set"}), 500

    prompt = f"""Analyze the following brand scripts and extract a precise voice DNA profile.
Return valid JSON only. No markdown.

SCRIPTS TO ANALYZE:
{raw_scripts[:5000]}

Extract this exact schema:
{{
  "extracted_at": "ISO timestamp",
  "sentence_length": "short|medium|long|mixed",
  "avg_words_per_sentence": 0,
  "energy": "high|medium|calm|intense",
  "tone": "direct|conversational|educational|provocative|empathetic",
  "hinglish_pattern": "never|occasional|frequent",
  "vocabulary": {{
    "power_words": ["words used often for emphasis"],
    "never_use": ["words that break brand voice"],
    "signature_phrases": ["unique phrases this brand uses"]
  }},
  "structure": {{
    "typical_opening": "how scripts usually open",
    "typical_close": "how scripts usually close",
    "uses_questions": true,
    "uses_numbers": true
  }},
  "cta_style": "comment trigger|dm trigger|link in bio|save this",
  "platform_voice_delta": {{
    "instagram": "any adjustments for Instagram",
    "linkedin": "any adjustments for LinkedIn"
  }},
  "brand_personality": "3 adjectives that define this brand's voice"
}}"""

    try:
        import anthropic as _anthropic
        _client = _anthropic.Anthropic(api_key=anthropic_key)
        response = _client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=1000,
            messages=[{"role": "user", "content": prompt}]
        )
        raw = response.content[0].text.strip()

        # Strip markdown fences
        if "```" in raw:
            for part in raw.split("```"):
                part = part.strip()
                if part.startswith("json"):
                    part = part[4:].strip()
                if part.startswith("{"):
                    raw = part
                    break

        profile = json.loads(raw)
        profile["extracted_at"] = datetime.now().isoformat()

    except Exception as e:
        return jsonify({"success": False, "error": f"Voice extraction failed: {e}"}), 500

    # Save to brands/{slug}/voice_profile.json
    out_path = BRANDS_DIR / brand_slug / "voice_profile.json"
    _atomic_write_json(out_path, profile)

    return jsonify({"success": True, "data": profile})


@app.route("/api/voice/profile", methods=["GET"])
def voice_get_profile():
    """Return voice_profile.json for a brand, or {exists: false} if not created yet."""
    brand_slug = request.args.get("brand_slug", "").strip()
    if not brand_slug:
        return jsonify({"success": False, "error": "brand_slug required"}), 400

    path = BRANDS_DIR / brand_slug / "voice_profile.json"
    if not path.exists():
        return jsonify({"success": True, "data": {"exists": False}})

    try:
        with open(path) as f:
            profile = json.load(f)
        return jsonify({"success": True, "data": {"exists": True, **profile}})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


# ── BUILD C — PERFORMANCE FEEDBACK LOOP ──────────────────────────────────────

@app.route("/api/performance/log-post", methods=["POST"])
@require_auth
def performance_log_post():
    """
    Manual-paste path for logging real published-post metrics.
    Works while META_GRAPH_API_TOKEN is pending Meta approval.

    Appends entry to brands/{slug}/performance_inbox.json (queue file).
    Performance Tracker agent ingests + clears the inbox on its next run.

    Body schema:
      {
        "brand_slug": "askgauravai",
        "post_id":         "ig_xxxxx",       # required (use IG short URL slug if no ID)
        "published_at":    "2026-04-20T12:00:00Z",
        "platform":        "instagram"|"linkedin"|"twitter",
        "format":          "Reel"|"Carousel"|"Static"|"Text",
        "topic":           "AI Strategy Framework",
        "hook_pattern_used": "Contrarian Truth",
        "hook_text":       "...",
        "trend_signal_id_origin": "angle::...",  # optional: which trends_live signal it came from
        "metrics": {
          "impressions": 12400, "reach": 9800,
          "saves": 87, "likes": 320, "shares": 23, "comments": 14,
          "dm_inquiries": 6
        }
      }

    Returns: {success, queued_count} — entry queued, will be processed on next Performance Tracker run.
    """
    body = request.get_json(silent=True) or {}
    brand_slug = body.get("brand_slug", "").strip()
    if not brand_slug:
        return jsonify({"success": False, "error": "brand_slug required"}), 400
    if not _validate_brand_slug(brand_slug):
        return jsonify({"success": False, "error": "Invalid brand_slug"}), 400
    brand_dir = BRANDS_DIR / brand_slug
    if not brand_dir.exists():
        return jsonify({"success": False, "error": f"Brand '{brand_slug}' not found"}), 404

    post_id = body.get("post_id", "").strip()
    if not post_id:
        return jsonify({"success": False, "error": "post_id required"}), 400

    # Build canonical entry (strip brand_slug from saved entry — it's implicit in the file path)
    entry = {k: v for k, v in body.items() if k != "brand_slug"}
    entry["logged_at"] = datetime.now(timezone.utc).isoformat()
    entry["data_source"] = "manual_paste"

    # Append to inbox queue
    inbox_path = brand_dir / "performance_inbox.json"
    if inbox_path.exists():
        try:
            with open(inbox_path) as f:
                inbox = json.load(f)
            queue = inbox.get("queue", []) if isinstance(inbox, dict) else []
        except Exception:
            queue = []
    else:
        queue = []

    queue.append(entry)
    with open(inbox_path, "w") as f:
        json.dump({"queue": queue, "last_updated": entry["logged_at"]}, f, indent=2)

    return jsonify({
        "success": True,
        "data": {
            "post_id":           post_id,
            "queued_count":      len(queue),
            "next_action":       "Run Performance Tracker (manual or via /api/agents/run) to ingest the queue and update performance_history.json",
        }
    })


@app.route("/api/performance/history", methods=["GET"])
def performance_history():
    """Return current performance_history.json or empty skeleton if not yet computed."""
    brand_slug = request.args.get("brand_slug", "").strip()
    if not brand_slug:
        return jsonify({"success": False, "error": "brand_slug required"}), 400
    if not _validate_brand_slug(brand_slug):
        return jsonify({"success": False, "error": "Invalid brand_slug"}), 400

    history_path = BRANDS_DIR / brand_slug / "performance_history.json"
    if not history_path.exists():
        return jsonify({"success": True, "data": {
            "exists": False,
            "posts": [], "rolling_baselines": {},
            "winning_patterns": {}, "dead_patterns": [],
        }})
    try:
        with open(history_path) as f:
            data = json.load(f)
        return jsonify({"success": True, "data": {"exists": True, **data}})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


# ── BUILD D — CROSS-AGENT CONTRADICTION DETECTOR ─────────────────────────────

@app.route("/api/contradictions/check", methods=["POST", "GET"])
def contradictions_check():
    """
    Run the cross-agent contradiction detector on a brand's current outputs.
    PURE DETERMINISTIC (Rule 10 — Class-1 decision agent, no Claude).

    Reads:
      brands/{slug}/brand_profile.json
      brands/{slug}/strategy_90day.json
      brands/{slug}/content_calendar.json
      brands/{slug}/outputs/pending_approval/script-writer/*.json

    Returns full report with:
      - findings[]: list of contradictions (severity: CRITICAL/WARNING/INFO)
      - counts: per-severity totals
      - blocking: True if any CRITICAL findings (caller should refuse to ship)
      - decision_engine: "pure_math" (Rule 10 audit field)

    Also persists report to brands/{slug}/contradictions.json for human review.
    """
    brand_slug = (
        request.args.get("brand_slug", "").strip()
        or (request.get_json(silent=True) or {}).get("brand_slug", "").strip()
    )
    if not brand_slug:
        return jsonify({"success": False, "error": "brand_slug required"}), 400
    if not _validate_brand_slug(brand_slug):
        return jsonify({"success": False, "error": "Invalid brand_slug"}), 400
    if not (BRANDS_DIR / brand_slug).exists():
        return jsonify({"success": False, "error": f"Brand '{brand_slug}' not found"}), 404

    try:
        sys.path.insert(0, str(BASE_DIR / "ceo_brain"))
        from contradiction_detector import detect_contradictions, save_contradictions_report
        report = detect_contradictions(brand_slug, project_root=BASE_DIR)
        save_contradictions_report(brand_slug, report, project_root=BASE_DIR)
        return jsonify({"success": True, "data": report})
    except Exception as e:
        return jsonify({"success": False, "error": f"Detector failed: {e}"}), 500


@app.route("/api/contradictions/latest", methods=["GET"])
def contradictions_latest():
    """Return the most recent contradictions.json report for a brand (or empty if never run)."""
    brand_slug = request.args.get("brand_slug", "").strip()
    if not brand_slug:
        return jsonify({"success": False, "error": "brand_slug required"}), 400
    if not _validate_brand_slug(brand_slug):
        return jsonify({"success": False, "error": "Invalid brand_slug"}), 400

    path = BRANDS_DIR / brand_slug / "contradictions.json"
    if not path.exists():
        return jsonify({"success": True, "data": {
            "exists": False,
            "findings": [], "counts": {"CRITICAL": 0, "WARNING": 0, "INFO": 0},
            "blocking": False,
        }})
    try:
        with open(path) as f:
            return jsonify({"success": True, "data": {"exists": True, **json.load(f)}})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/performance/inbox", methods=["GET"])
def performance_inbox():
    """Return current performance_inbox.json (queued, not-yet-ingested entries)."""
    brand_slug = request.args.get("brand_slug", "").strip()
    if not brand_slug:
        return jsonify({"success": False, "error": "brand_slug required"}), 400
    if not _validate_brand_slug(brand_slug):
        return jsonify({"success": False, "error": "Invalid brand_slug"}), 400

    inbox_path = BRANDS_DIR / brand_slug / "performance_inbox.json"
    if not inbox_path.exists():
        return jsonify({"success": True, "data": {"queue": [], "queued_count": 0}})
    try:
        with open(inbox_path) as f:
            data = json.load(f)
        queue = data.get("queue", []) if isinstance(data, dict) else []
        return jsonify({"success": True, "data": {"queue": queue, "queued_count": len(queue)}})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


def _load_conversation(brand_slug: str, agent_slug: str) -> list:
    """Load conversation history — Supabase primary, JSON fallback."""
    # DB-WIRED Step 5
    if _DB_AVAILABLE:
        brand_id = _get_brand_id(brand_slug)
        if brand_id:
            msgs = _db.get_conversation(brand_id, agent_slug)
            if msgs:
                return msgs
    # Fallback: session_state.json
    try:
        session_file = BRANDS_DIR / brand_slug / "session_state.json"
        if not session_file.exists():
            return []
        with open(session_file) as f:
            session = json.load(f)
        return session.get("conversations", {}).get(brand_slug, {}).get(agent_slug, [])
    except Exception:
        return []


def _save_conversation(brand_slug: str, agent_slug: str, history: list) -> None:
    """Persist conversation history — Supabase primary, JSON dual-write."""
    # DB-WIRED Step 5
    if _DB_AVAILABLE:
        brand_id = _get_brand_id(brand_slug)
        if brand_id:
            _db.save_conversation(brand_id, agent_slug, history)
    # Always also write to JSON for local fallback
    try:
        brand_dir = BRANDS_DIR / brand_slug
        session_file = brand_dir / "session_state.json"
        session: dict = {}
        if session_file.exists():
            with open(session_file) as f:
                session = json.load(f)
        if "conversations" not in session:
            session["conversations"] = {}
        if brand_slug not in session["conversations"]:
            session["conversations"][brand_slug] = {}
        session["conversations"][brand_slug][agent_slug] = history
        with open(session_file, "w") as f:
            json.dump(session, f, indent=2)
    except Exception as e:
        print(f"[dashboard_api] conversation json-save failed: {e}")


@app.route("/api/agents/conversation", methods=["GET"])
def get_conversation():
    """Return persisted conversation history for a brand+agent pair."""
    brand_slug = request.args.get("brand_slug", "offgrid-creatives-ai")
    agent_slug = request.args.get("agent_slug", "")
    if not agent_slug:
        return jsonify({"success": False, "error": "agent_slug required"}), 400
    history = _load_conversation(brand_slug, agent_slug)
    return jsonify({"success": True, "data": history})


@app.route("/api/agents/chat", methods=["POST"])
@require_auth
def agent_chat():
    import anthropic as _anthropic

    body = request.get_json() or {}
    agent_name  = body.get("agentName", "").strip()
    user_msg    = body.get("message", "").strip()
    brand_slug  = body.get("brand_slug", "offgrid-creatives-ai")
    if not _validate_brand_slug(brand_slug):
        return jsonify({"success": False, "error": "Invalid brand_slug"}), 400
    # agent_slug used as key for conversation persistence
    agent_slug  = re.sub(r"[^a-z0-9-]", "", agent_name.lower().replace(" ", "-"))

    if not agent_name or not user_msg:
        return jsonify({"success": False, "error": "agentName and message required"}), 400

    # Resolve agent config
    agent_cfg = next((a for a in AGENTS if a["name"] == agent_name), None)
    if not agent_cfg:
        return jsonify({"success": False, "error": f"Agent '{agent_name}' not found"}), 404

    # 1. Load existing conversation history from session_state
    persisted_history = _load_conversation(brand_slug, agent_slug)

    # 2. Append new user message
    user_entry = {"role": "user", "content": user_msg, "timestamp": datetime.now().isoformat()}
    persisted_history.append(user_entry)

    # Load persona body from .md file (strip YAML frontmatter between --- markers)
    persona_body = ""
    persona_file = AGENT_PERSONA_FILES.get(agent_name)
    if persona_file:
        persona_path = AGENTS_DIR / persona_file
        if persona_path.exists():
            raw = persona_path.read_text()
            parts = raw.split("---", 2)
            persona_body = parts[2].strip() if len(parts) >= 3 else raw.strip()

    # Load brand profile for context
    brand_context = ""
    try:
        profile_path = BRANDS_DIR / brand_slug / "brand_profile.json"
        if profile_path.exists():
            with open(profile_path) as f:
                p = json.load(f)
            # Build platform handles string for agent context
            ph_list = p.get("platform_handles", [])
            if ph_list:
                handles_str = ", ".join(
                    f"{h.get('platform','?')}: @{h.get('handle','?')}"
                    for h in ph_list if h.get("handle")
                )
            else:
                ig = p.get("instagram_handle", "")
                handles_str = f"Instagram: @{ig}" if ig else "Not set"
            competitors = ", ".join(
                f"@{h}" for h in p.get("competitor_handles", []) if h
            ) or "Not set"
            brand_context = (
                f"\n\n## Current Brand Context\n"
                f"Brand: {p.get('brand_name', brand_slug)}\n"
                f"Product: {p.get('product', 'Not set')}\n"
                f"Website: {p.get('website_url', 'Not set')}\n"
                f"Phase: {p.get('phase', 'Beta')}\n"
                f"Audience: {', '.join(p.get('audience', []))}\n"
                f"Platforms: {', '.join(p.get('platforms', []))}\n"
                f"Handles: {handles_str}\n"
                f"Competitors: {competitors}\n"
                f"90-day goal: {p.get('content_goal_90d', 'Not set')}\n"
                f"NEVER say: {p.get('what_to_never_say', 'Not specified')}"
            )
    except Exception:
        pass

    # Build real-data context from brand_memory + market_intelligence
    real_data_context = _build_agent_context(brand_slug, agent_name)

    # Build system prompt
    plain_english_rule = (
        "\n\nIMPORTANT: Respond in plain, conversational English only. "
        "Never output raw JSON, code blocks, or structured data formats in your replies. "
        "Use bullet points and headings where helpful, but never output JSON objects or arrays."
    )
    if persona_body:
        system_prompt = persona_body + plain_english_rule + brand_context + "\n\n" + real_data_context
    else:
        system_prompt = (
            f"You are {agent_name}, {agent_cfg['role']} in the OffGrid Marketing OS. "
            f"You are a specialised AI marketing agent. Be specific, practical, and direct. "
            f"Never produce vague recommendations. Always root answers in real data or ask for it."
            + plain_english_rule
            + brand_context
            + "\n\n" + real_data_context
        )

    # 3. Build Claude API messages from persisted history (role "agent" → "assistant")
    messages = []
    for h in persisted_history:
        role = "user" if h.get("role") == "user" else "assistant"
        content = h.get("content", "").strip()
        if content:
            messages.append({"role": role, "content": content})

    # Call Claude
    api_key = os.getenv("ANTHROPIC_API_KEY", "").strip()
    if not api_key:
        return jsonify({"success": False, "error": "ANTHROPIC_API_KEY not set"}), 500

    try:
        client = _anthropic.Anthropic(api_key=api_key)
        resp = client.messages.create(
            model=agent_cfg["model"],
            max_tokens=4096,
            system=system_prompt,
            messages=messages,
        )
        reply = re.sub(r'^\s*\[[^\]]+\]:\s*', '', resp.content[0].text)

        # 4. Append Claude response to history
        agent_entry = {"role": "agent", "content": reply, "timestamp": datetime.now().isoformat()}
        persisted_history.append(agent_entry)

        # 5. Save updated history
        _save_conversation(brand_slug, agent_slug, persisted_history)

        return jsonify({"success": True, "data": {"message": reply}})
    except Exception as exc:
        return jsonify({"success": False, "error": str(exc)}), 500


@app.route("/api/agents/group-chat", methods=["POST"])
@require_auth
def agent_group_chat():
    """
    Group Meeting Room — dynamic @mention routing.
    Body: { brand_slug: str, message: str }

    Flow:
    1. CEO Brain always replies first.
    2. CEO Brain may end its reply with:  CALL: @AgentSlug, @AgentSlug
    3. User message may contain @AgentSlug mentions.
    4. Union of CEO's CALL list + user @mentions → those agents reply after CEO.
    The CALL line stays visible in CEO's response.
    """
    import anthropic as _anthropic
    import re as _re

    body       = request.get_json() or {}
    user_msg   = body.get("message", "").strip()
    brand_slug = body.get("brand_slug", "offgrid-creatives-ai")
    if not _validate_brand_slug(brand_slug):
        return jsonify({"success": False, "error": "Invalid brand_slug"}), 400

    if not user_msg:
        return jsonify({"success": False, "error": "message is required"}), 400

    # ── @mention helpers ───────────────────────────────────────────────────────

    def _mention_slug(name: str) -> str:
        """'Trend Researcher' → 'TrendResearcher'"""
        parts = name.split()
        return parts[0] + "".join(p.capitalize() for p in parts[1:])

    def _match_mention(slug: str) -> str | None:
        slug_lower = slug.lower()
        for a in AGENTS:
            if _mention_slug(a["name"]).lower() == slug_lower:
                return a["name"]
        return None

    def _extract_mentions(text: str) -> list[str]:
        names = []
        for s in _re.findall(r'@(\w+)', text):
            n = _match_mention(s)
            if n and n not in names:
                names.append(n)
        return names

    def _extract_call_line(text: str) -> list[str]:
        m = _re.search(r'CALL:\s*(.+?)(?:\n|$)', text, _re.IGNORECASE)
        return _extract_mentions(m.group(1)) if m else []

    # ── Load group history from Supabase ───────────────────────────────────────

    group_history: list[dict] = []
    if _DB_AVAILABLE:
        try:
            brand_id_h = _get_brand_id(brand_slug)
            if brand_id_h:
                raw_hist = _db.get_conversation(brand_id_h, "group-chat")
                group_history = raw_hist[-40:] if raw_hist else []
        except Exception:
            pass

    # ── Brand context ──────────────────────────────────────────────────────────

    brand_context = ""
    try:
        profile_path = BRANDS_DIR / brand_slug / "brand_profile.json"
        if profile_path.exists():
            with open(profile_path) as f:
                p = json.load(f)
            ph_list = p.get("platform_handles", [])
            if ph_list:
                handles_str = ", ".join(
                    f"{h.get('platform','?')}: @{h.get('handle','?')}"
                    for h in ph_list if h.get("handle")
                )
            else:
                ig = p.get("instagram_handle", "")
                handles_str = f"Instagram: @{ig}" if ig else "Not set"
            competitors = ", ".join(
                f"@{h}" for h in p.get("competitor_handles", []) if h
            ) or "Not set"
            brand_context = (
                f"\n\nActive brand: {p.get('brand_name', brand_slug)} | "
                f"Product: {p.get('product', 'Not set')} | "
                f"Phase: {p.get('phase', 'Beta')} | "
                f"Handles: {handles_str} | "
                f"Competitors: {competitors} | "
                f"90-day goal: {p.get('content_goal_90d', 'Not set')}"
            )
    except Exception:
        pass

    api_key = os.getenv("ANTHROPIC_API_KEY", "").strip()
    if not api_key:
        return jsonify({"success": False, "error": "ANTHROPIC_API_KEY not set"}), 500

    # ── Real-data context (shared across all agents in this session) ───────────
    # Pre-build per-agent context so each agent only sees its own relevant files.
    # CEO Brain gets a unified view of all memory layers.
    _agent_ctx_cache: dict[str, str] = {}
    def _get_agent_ctx(aname: str) -> str:
        if aname not in _agent_ctx_cache:
            _agent_ctx_cache[aname] = _build_agent_context(brand_slug, aname)
        return _agent_ctx_cache[aname]

    # ── Tone rules — all agents ────────────────────────────────────────────────

    human_voice_rule = (
        "\n\nTONE — MANDATORY RULES:"
        "\nYou are speaking out loud in a live meeting, not writing a document or report."
        "\nWrite exactly like a sharp, confident person talks. Short sentences. Direct."
        "\nNEVER use ## headers, # headings, or --- dividers."
        "\nNEVER bold more than one thing per response."
        "\nNEVER write bullet lists unless listing 3+ specific items that genuinely need it."
        "\nNEVER start with your own name, title, or 'CEO Brain here'."
        "\nNEVER write a preamble or 'here is my take'. Just say the take."
        "\nNEVER output JSON, code blocks, tables, or structured data."
        "\nIf you can say it in 3 sentences, say it in 3 sentences."
        "\nIf asked a yes/no question, answer yes or no first, then explain in 2 sentences max."
    )

    # ── Build Claude messages from history ─────────────────────────────────────

    def _build_messages(history: list[dict], current: str) -> list[dict]:
        msgs: list[dict] = []
        pending_asst: list[str] = []

        def flush():
            if pending_asst:
                msgs.append({"role": "assistant", "content": "\n\n".join(pending_asst)})
                pending_asst.clear()

        for h in history:
            role    = h.get("role", "")
            content = (h.get("content") or "").strip()
            if not content:
                continue
            if role == "user":
                flush()
                if msgs and msgs[-1]["role"] == "user":
                    msgs[-1]["content"] += f"\n{content}"
                else:
                    msgs.append({"role": "user", "content": content})
            elif role == "agent":
                # Strip any [AgentName]: prefix the model may have stored so we
                # don't accumulate [CEO Brain]: [CEO Brain]: ... across turns.
                clean = _re.sub(r'^\s*\[[^\]]+\]:\s*', '', content)
                pending_asst.append(f"[{h.get('agent', 'Agent')}]: {clean}")

        flush()
        if msgs and msgs[-1]["role"] == "user":
            msgs[-1]["content"] += f"\n{current}"
        else:
            msgs.append({"role": "user", "content": current})
        return msgs

    messages = _build_messages(group_history, user_msg)
    client   = _anthropic.Anthropic(api_key=api_key)

    # ── Parse user @mentions ───────────────────────────────────────────────────

    user_mentioned = _extract_mentions(user_msg)

    # ── CEO Brain speaks first — always ───────────────────────────────────────

    available_slugs = ", ".join(f"@{_mention_slug(a['name'])}" for a in AGENTS)
    ceo_system = (
        "You are the CEO Brain — strategic coordinator of the OffGrid Marketing OS. "
        "You lead this meeting. Give sharp strategic direction and own the room."
        "\n\nWhen the user's question needs a specialist, end your reply with a blank line then:"
        "\nCALL: @AgentSlug, @AgentSlug"
        f"\nAvailable specialists: {available_slugs}"
        "\nOnly CALL when the question genuinely needs their domain expertise."
        "\nDon't call agents to look thorough. 1–2 agents max unless truly necessary."
        "\nThe CALL line stays visible to the user — keep it natural."
        "\n\nNEVER start your reply with '[CEO Brain]:' or any bracketed label."
        " Your first word must be your actual response."
        + human_voice_rule + brand_context
        + "\n\n" + _get_agent_ctx("CEO Brain")
    )

    responses = []
    ceo_text  = ""
    try:
        ceo_resp = client.messages.create(
            model="claude-opus-4-6",
            max_tokens=1024,
            system=ceo_system,
            messages=messages,
        )
        ceo_text = _re.sub(r'^\s*\[[^\]]+\]:\s*', '', ceo_resp.content[0].text)
        responses.append({
            "agent":     "CEO Brain",
            "message":   ceo_text,
            "timestamp": datetime.now().isoformat(),
        })
    except Exception as exc:
        responses.append({
            "agent":     "CEO Brain",
            "message":   f"[Error: {str(exc)}]",
            "timestamp": datetime.now().isoformat(),
        })

    # ── Determine additional agents to call ────────────────────────────────────

    ceo_called = _extract_call_line(ceo_text)
    to_call    = list(user_mentioned)      # user @mentions take priority
    for name in ceo_called:
        if name not in to_call:
            to_call.append(name)

    # ── Call each additional agent ─────────────────────────────────────────────

    for agent_name in to_call:
        try:
            agent_cfg = next((a for a in AGENTS if a["name"] == agent_name), None)
            model     = agent_cfg["model"] if agent_cfg else "claude-sonnet-4-6"

            persona_body = ""
            persona_file = AGENT_PERSONA_FILES.get(agent_name)
            if persona_file:
                persona_path = AGENTS_DIR / persona_file
                if persona_path.exists():
                    raw_p = persona_path.read_text()
                    parts = raw_p.split("---", 2)
                    persona_body = parts[2].strip() if len(parts) >= 3 else raw_p.strip()

            agent_real_data = _get_agent_ctx(agent_name)
            identity_lock = (
                f"\n\nYou are {agent_name}. You have been called into this meeting."
                f" Give your specialist view concisely."
                f"\nNEVER start your reply with '[{agent_name}]:' or any bracketed label."
                f" Never pretend to be CEO Brain or any other agent."
                f" Your first word must be your actual response, not your name."
            )
            if persona_body:
                system_prompt = (
                    persona_body
                    + identity_lock
                    + human_voice_rule + brand_context
                    + "\n\n" + agent_real_data
                )
            else:
                role_desc = agent_cfg["role"] if agent_cfg else "specialist"
                system_prompt = (
                    f"You are {agent_name}, {role_desc} in the OffGrid Marketing OS."
                    + identity_lock
                    + human_voice_rule + brand_context
                    + "\n\n" + agent_real_data
                )

            resp = client.messages.create(
                model=model,
                max_tokens=1024,
                system=system_prompt,
                messages=messages,
            )
            responses.append({
                "agent":     agent_name,
                "message":   _re.sub(r'^\s*\[[^\]]+\]:\s*', '', resp.content[0].text),
                "timestamp": datetime.now().isoformat(),
            })
        except Exception as exc:
            responses.append({
                "agent":     agent_name,
                "message":   f"[Error: {str(exc)}]",
                "timestamp": datetime.now().isoformat(),
            })

    # ── Persist to Supabase ────────────────────────────────────────────────────

    if _DB_AVAILABLE:
        try:
            brand_id_s = _get_brand_id(brand_slug)
            if brand_id_s:
                updated = list(group_history)
                updated.append({"role": "user", "content": user_msg})
                for r in responses:
                    updated.append({"role": "agent", "agent": r["agent"], "content": r["message"]})
                _db.save_conversation(brand_id_s, "group-chat", updated[-100:])
        except Exception:
            pass

    return jsonify({"success": True, "data": {"responses": responses}})


@app.route("/api/agents/request-changes", methods=["POST"])
def agent_request_changes():
    """Save feedback for an agent, reset its status to idle so it can be re-run."""
    body = request.get_json() or {}
    brand_slug = body.get("brand_slug", "offgrid-creatives-ai")
    agent_slug = body.get("agent_slug", "")
    feedback   = body.get("feedback", "").strip()

    if not agent_slug:
        return jsonify({"success": False, "error": "agent_slug required"}), 400

    try:
        brand_dir = BRANDS_DIR / brand_slug
        session_file = brand_dir / "session_state.json"
        session: dict = {}
        if session_file.exists():
            with open(session_file) as f:
                session = json.load(f)

        # Save feedback
        if "feedback" not in session:
            session["feedback"] = {}
        session["feedback"][agent_slug] = {
            "text": feedback,
            "timestamp": datetime.now().isoformat(),
        }

        # Reset agent status to idle
        # Find matching agent name by slug
        agent_name = next(
            (a["name"] for a in AGENTS if re.sub(r"[^a-z0-9-]", "", a["name"].lower().replace(" ", "-")) == agent_slug),
            agent_slug
        )
        if agent_name in session and isinstance(session[agent_name], dict):
            session[agent_name]["status"] = "idle"

        # Append to agent_log
        if "agent_log" not in session or not isinstance(session["agent_log"], list):
            session["agent_log"] = []
        session["agent_log"].append({
            "agent": agent_name,
            "event": "changes_requested",
            "timestamp": datetime.now().isoformat(),
            "detail": feedback,
        })

        with open(session_file, "w") as f:
            json.dump(session, f, indent=2)

        return jsonify({"success": True, "data": {"message": "Feedback saved, agent reset to idle."}})
    except Exception as exc:
        return jsonify({"success": False, "error": str(exc)}), 500


@app.route("/api/agents/train", methods=["POST"])
def agent_train():
    body = request.get_json() or {}
    agent_name  = body.get("agentName", "unknown").strip()
    note        = body.get("note", "").strip()
    brand_slug  = body.get("brand_slug", "offgrid-creatives-ai")

    if not note:
        return jsonify({"success": False, "error": "note is required"}), 400

    try:
        training_dir = BRANDS_DIR / brand_slug / "training_notes"
        training_dir.mkdir(parents=True, exist_ok=True)
        slug = re.sub(r"[^a-z0-9-]", "", agent_name.lower().replace(" ", "-"))
        training_file = training_dir / f"{slug}_notes.jsonl"
        entry = json.dumps({
            "agent": agent_name,
            "note": note,
            "timestamp": datetime.now().isoformat(),
        })
        with open(training_file, "a") as f:
            f.write(entry + "\n")
        return jsonify({"success": True, "data": {"message": f"Note saved for {agent_name}"}})
    except Exception as exc:
        return jsonify({"success": False, "error": str(exc)}), 500


# ── Cost Tracking ─────────────────────────────────────────────────────────────

@app.route("/api/brands/<brand_slug>/costs", methods=["GET"])
def brand_costs(brand_slug: str):
    """
    Return monthly cost breakdown for a brand.
    Query params: year (int, default current), month (int, default current).
    """
    from datetime import datetime as _dt
    now   = _dt.utcnow()
    year  = int(request.args.get("year",  now.year))
    month = int(request.args.get("month", now.month))

    if not _DB_AVAILABLE:
        return jsonify({"success": False, "error": "Database not available"}), 503

    brand_id = _get_brand_id(brand_slug)
    if not brand_id:
        return jsonify({"success": False, "error": f"Brand '{brand_slug}' not found"}), 404

    data = _db.get_brand_monthly_costs(brand_id, year, month)
    return jsonify({"success": True, "data": data})


@app.route("/api/brands/<brand_slug>/costs/record", methods=["POST"])
def record_agent_cost(brand_slug: str):
    """
    Called by agent scripts at end of each run to record token counts.
    Body: { run_id, model, input_tokens, output_tokens, fal_generations, apify_runs }
    """
    if not _DB_AVAILABLE:
        return jsonify({"success": True, "data": {}}), 200  # silent no-op

    body            = request.get_json() or {}
    run_id          = body.get("run_id", "")
    model           = body.get("model", "claude-sonnet-4-6")
    input_tokens    = int(body.get("input_tokens", 0))
    output_tokens   = int(body.get("output_tokens", 0))
    fal_generations = int(body.get("fal_generations", 0))
    apify_runs      = int(body.get("apify_runs", 0))

    if not run_id:
        return jsonify({"success": False, "error": "run_id required"}), 400

    result = _db.update_agent_run_costs(
        run_id, model, input_tokens, output_tokens, fal_generations, apify_runs
    )
    return jsonify({"success": True, "data": result or {}})


# ── n8n Webhook Receiver ───────────────────────────────────────────────────────

@app.route("/api/webhooks/n8n", methods=["POST"])
def n8n_webhook():
    """
    n8n → GRID CONTROL trigger endpoint.
    n8n sends: { brand_slug, agent_name, trigger_source, payload }
    GRID CONTROL starts the agent run in the background and returns run_id.

    n8n setup:
      POST https://your-domain/api/webhooks/n8n
      Body: application/json
      Supported trigger_source values: "n8n", "schedule", "form", "manual"
    """
    body           = request.get_json() or {}
    brand_slug     = body.get("brand_slug", "").strip()
    agent_name     = body.get("agent_name", "").strip()
    trigger_source = body.get("trigger_source", "n8n")

    if not brand_slug or not agent_name:
        return jsonify({"success": False, "error": "brand_slug and agent_name are required"}), 400

    # Validate brand exists
    brand_dir = BRANDS_DIR / brand_slug
    if not brand_dir.exists():
        return jsonify({"success": False, "error": f"Brand '{brand_slug}' not found"}), 404

    # Validate agent exists and has a script
    script_val = AGENT_SCRIPTS.get(agent_name)
    if not script_val:
        return jsonify({"success": False, "error": f"Agent '{agent_name}' not found"}), 404
    if isinstance(script_val, dict) and script_val.get("coming_soon"):
        return jsonify({"success": False, "error": f"Agent '{agent_name}' is coming soon"}), 400

    script_path = BASE_DIR / script_val
    if not script_path.exists():
        return jsonify({"success": False, "error": f"Agent script not found: {script_val}"}), 404

    # Rate-limit check
    agent_slug_key = _agent_name_to_slug(agent_name)
    if _DB_AVAILABLE:
        try:
            brand_id_check = _get_brand_id(brand_slug)
            if brand_id_check:
                existing = (
                    _db._client.table("agent_runs")
                    .select("id")
                    .eq("brand_id", brand_id_check)
                    .eq("agent_slug", agent_slug_key)
                    .eq("status", "running")
                    .execute()
                )
                if existing.data:
                    return jsonify({"success": False, "error": "Agent already running"}), 409
        except Exception:
            pass

    # Mark running + create DB row
    _update_session_agent_status(brand_slug, agent_name, "running")
    db_run_id: str | None = None
    if _DB_AVAILABLE:
        brand_id = _get_brand_id(brand_slug)
        if brand_id:
            run_row = _db.save_agent_run(brand_id, agent_slug_key)
            if run_row:
                db_run_id = run_row["id"]

    # Log webhook trigger in audit
    if _DB_AVAILABLE and brand_id:
        _db.log_audit(brand_id, "webhook_trigger", trigger_source, {
            "agent": agent_name, "brand_slug": brand_slug
        })

    # Fire agent in background
    thread = threading.Thread(
        target=_run_agent_subprocess,
        args=(str(script_path), brand_slug, agent_name, db_run_id),
        daemon=True,
    )
    thread.start()

    return jsonify({"success": True, "data": {
        "message":        f"{agent_name} triggered via n8n",
        "agent":          agent_name,
        "brand_slug":     brand_slug,
        "trigger_source": trigger_source,
        "run_id":         db_run_id or "",
    }})


# ── Brand Memory API ──────────────────────────────────────────────────────────

@app.route("/api/brands/<brand_slug>/memory/db", methods=["GET"])
def get_brand_memory_db(brand_slug: str):
    """Return all stored memory entries from Supabase for a brand (all agents or filtered by agent_slug)."""
    if not _DB_AVAILABLE:
        return jsonify({"success": True, "data": []}), 200

    brand_id = _get_brand_id(brand_slug)
    if not brand_id:
        return jsonify({"success": False, "error": f"Brand '{brand_slug}' not found"}), 404

    agent_slug = request.args.get("agent_slug", "")
    if agent_slug:
        memories = _db.get_brand_memory(brand_id, agent_slug)
    else:
        memories = _db.get_all_brand_memory(brand_id)

    return jsonify({"success": True, "data": memories})


# ── Brands ────────────────────────────────────────────────────────────────────

@app.route("/api/brands", methods=["GET"])
def get_brands():
    # DB-WIRED Step 5 — try Supabase first, fall back to filesystem
    if _DB_AVAILABLE:
        try:
            res = _db._client.table("brands").select("slug, name").order("created_at").execute()
            if res.data:
                return jsonify({"success": True, "data": res.data})
        except Exception as e:
            print(f"[dashboard_api] Supabase brands list failed: {e}")
    return jsonify({"success": True, "data": list_brands()})


@app.route("/api/brands/create", methods=["POST"])
@require_auth
def create_brand():
    body = request.get_json() or {}
    name               = (body.get("brand_name") or body.get("name") or "").strip()
    product_desc       = (body.get("product_description") or body.get("product") or "").strip()
    brand_brief        = (body.get("brand_brief") or "").strip()
    business_type      = (body.get("business_type") or "").strip()
    industry           = (body.get("industry") or "").strip()
    phase              = (body.get("phase") or "Beta").strip()
    target_audience    = (body.get("target_audience") or "").strip()
    primary_bottleneck = (body.get("primary_bottleneck") or "").strip()
    railway_url        = (body.get("railway_url") or "").strip()
    existing_pipeline  = (body.get("existing_pipeline") or "").strip()
    tone_of_voice      = (body.get("tone_of_voice") or "Professional").strip()
    platforms_raw      = body.get("platforms", [])
    audience_raw       = body.get("audience", [])
    # New agent-first onboarding fields
    instagram_handle        = (body.get("instagram_handle") or "").strip().lstrip("@")
    competitor_handles_raw  = body.get("competitor_handles", [])
    platform_handles_raw    = body.get("platform_handles", [])
    website_url             = (body.get("website_url") or "").strip()
    brand_face              = (body.get("brand_face") or "Person").strip()
    tone_specifics          = (body.get("tone_specifics") or "").strip()
    content_goal_90d        = (body.get("content_goal_90d") or "Followers").strip()
    weekly_post_target      = (body.get("weekly_post_target") or "3x").strip()
    past_content_worked     = (body.get("past_content_worked") or "").strip()
    what_to_never_say       = (body.get("what_to_never_say") or "").strip()
    has_existing_pipeline   = bool(body.get("has_existing_pipeline", False))

    # Validate required fields
    errors = []
    if not name:
        errors.append("brand_name is required")
    if not product_desc and not body.get("product_description"):
        # Allow empty product_desc if target_audience is provided (new form)
        pass
    if errors:
        return jsonify({"success": False, "error": "; ".join(errors)}), 400

    # Normalise arrays
    if isinstance(platforms_raw, str):
        platforms = [s.strip() for s in platforms_raw.split(",") if s.strip()]
    else:
        platforms = list(platforms_raw)
    if isinstance(audience_raw, str):
        audience = [s.strip() for s in audience_raw.split(",") if s.strip()]
    else:
        audience = list(audience_raw)
    # If no legacy audience array, build from target_audience string
    if not audience and target_audience:
        audience = [target_audience]

    # Normalise competitor handles — strip @, drop blanks
    if isinstance(competitor_handles_raw, list):
        competitor_handles = [h.strip().lstrip("@") for h in competitor_handles_raw if str(h).strip()]
    elif isinstance(competitor_handles_raw, str):
        competitor_handles = [h.strip().lstrip("@") for h in competitor_handles_raw.split(",") if h.strip()]
    else:
        competitor_handles = []

    # Slug: prefer explicit brand_slug from body, else auto-generate
    # Always strip the name first to avoid trailing-hyphen bugs (e.g. "Brand Name " → "brand-name-")
    explicit_slug = (body.get("brand_slug") or "").strip()
    if explicit_slug:
        slug = re.sub(r"[^a-z0-9-]", "", explicit_slug).strip("-")
    else:
        slug = re.sub(r"[^a-z0-9-]", "", name.strip().lower().replace(" ", "-")).strip("-")
    if not slug:
        slug = re.sub(r"[^a-z0-9-]", "", name.strip().lower().replace(" ", "-")).strip("-")

    brand_dir = BRANDS_DIR / slug

    # Create output dirs
    (brand_dir / "outputs" / "pending_approval").mkdir(parents=True, exist_ok=True)
    (brand_dir / "outputs" / "approved").mkdir(parents=True, exist_ok=True)

    # Create per-agent subfolders in both output dirs
    for agent_slug_dir in PIPELINE_UNLOCK_ORDER:
        (brand_dir / "outputs" / "pending_approval" / agent_slug_dir).mkdir(parents=True, exist_ok=True)
        (brand_dir / "outputs" / "approved" / agent_slug_dir).mkdir(parents=True, exist_ok=True)

    # Write brand_profile.json
    profile_file = brand_dir / "brand_profile.json"
    profile = {
        "brand_name":          name,
        "product":             product_desc,
        "price_india":         body.get("price_india", ""),
        "price_international": body.get("price_international", ""),
        "price_beta":          body.get("price_beta", ""),
        "audience":            audience,
        "platforms":           platforms,
        "bottlenecks":         body.get("bottlenecks", [primary_bottleneck] if primary_bottleneck else []),
        "business_type":       business_type,
        "industry":            industry,
        "brand_brief":         brand_brief,
        "phase":               phase,
        "target_audience":     target_audience,
        "primary_bottleneck":  primary_bottleneck,
        "railway_url":         railway_url,
        "existing_pipeline":   existing_pipeline,
        "tone_of_voice":       tone_of_voice,
        # Agent-first onboarding fields
        "instagram_handle":      instagram_handle,
        "competitor_handles":    competitor_handles,
        "platform_handles":      platform_handles_raw if isinstance(platform_handles_raw, list) else [],
        "website_url":           website_url,
        "brand_face":            brand_face,
        "tone_specifics":        tone_specifics,
        "content_goal_90d":      content_goal_90d,
        "weekly_post_target":    weekly_post_target,
        "past_content_worked":   past_content_worked,
        "what_to_never_say":     what_to_never_say,
        "has_existing_pipeline": has_existing_pipeline,
    }
    _atomic_write_json(profile_file, profile)

    # Bootstrap brand memory + market intelligence folders (all brands get this)
    _bootstrap_brand_memory(brand_dir, profile)

    # Phase 4 — create Managed Agent memory stores for new brand (non-blocking, best-effort)
    if _MANAGED_AGENTS_AVAILABLE:
        def _setup_memory_bg():
            try:
                from managed_agents.memory_manager import setup_brand_memory
                setup_brand_memory(slug)
            except Exception as _mm_err:
                print(f"[dashboard_api] Memory store setup skipped (non-fatal): {_mm_err}")
        threading.Thread(target=_setup_memory_bg, daemon=True).start()

    # DB-WIRED Step 5 — upsert brand into Supabase
    if _DB_AVAILABLE:
        _db.upsert_brand(slug, name, profile)

    # Write initial session_state with pipeline bootstrap
    initial_session: dict = {
        "current_agent": None,
        "next_agent": "trend-researcher",
        "pipeline_status": "not_started",
        "completed_agents": [],
        "last_completed": None,
    }
    session_file = brand_dir / "session_state.json"
    _atomic_write_json(session_file, initial_session)

    # Write initial Supabase session_state
    if _DB_AVAILABLE:
        brand_row = _db.get_brand(slug)
        if brand_row:
            brand_id = brand_row["id"]
            _db.upsert_session_state(brand_id, initial_session)

    return jsonify({"success": True, "data": {"slug": slug, "brand_slug": slug, "name": name}})


@app.route("/api/brands/<brand_slug>", methods=["DELETE"])
@require_auth
def delete_brand(brand_slug: str):
    if not _validate_brand_slug(brand_slug):
        return jsonify({"success": False, "error": "Invalid brand_slug"}), 400
    brand_dir = BRANDS_DIR / brand_slug
    if not brand_dir.exists():
        return jsonify({"success": False, "error": "Brand not found"}), 404
    remaining = [d for d in BRANDS_DIR.iterdir() if d.is_dir() and d.name != brand_slug]
    if not remaining:
        return jsonify({"success": False, "error": "Cannot delete the last brand"}), 400
    shutil.rmtree(brand_dir)
    return jsonify({"success": True, "deleted": brand_slug})


@app.route("/api/brands/<brand_slug>/memory", methods=["GET"])
@require_auth
def get_brand_memory(brand_slug: str):
    """Return all brand_memory files for a brand."""
    if not _validate_brand_slug(brand_slug):
        return jsonify({"success": False, "error": "Invalid brand_slug"}), 400
    result = {}
    for key in _MEMORY_FILES:
        result[key] = _read_memory(brand_slug, key)
    return jsonify({"success": True, "data": result})


@app.route("/api/brands/<brand_slug>/intelligence", methods=["GET"])
@require_auth
def get_brand_intelligence(brand_slug: str):
    """Return market_intelligence files + staleness info."""
    if not _validate_brand_slug(brand_slug):
        return jsonify({"success": False, "error": "Invalid brand_slug"}), 400
    result = {}
    for key in _INTELLIGENCE_FILES:
        data = _read_intelligence(brand_slug, key)
        result[key] = {
            "data": data,
            "stale": _intelligence_is_stale(brand_slug, key) if key in _INTELLIGENCE_TTL else False,
        }
    return jsonify({"success": True, "data": result})


@app.route("/api/brands/<brand_slug>/memory/approve", methods=["POST"])
@require_auth
def approve_memory_update(brand_slug: str):
    """
    Gaurav approves a change to brand_memory.
    Body: { memory_key: str, updates: dict }
    This is the ONLY way brand_memory files get updated.
    """
    if not _validate_brand_slug(brand_slug):
        return jsonify({"success": False, "error": "Invalid brand_slug"}), 400
    body = request.get_json() or {}
    memory_key = body.get("memory_key", "")
    updates    = body.get("updates", {})
    if not memory_key or not updates:
        return jsonify({"success": False, "error": "memory_key and updates required"}), 400
    try:
        _approve_memory_update(brand_slug, memory_key, updates)
        return jsonify({"success": True, "data": {"updated": memory_key}})
    except ValueError as e:
        return jsonify({"success": False, "error": str(e)}), 400
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/brands/<brand_slug>/goals", methods=["POST"])
@require_auth
def set_brand_goal(brand_slug: str):
    """
    Gaurav sets or updates an active goal (e.g. '500 followers in 30 days').
    Immediately stored in brand_memory/goals.json.
    Triggers a task-specific scrape in background.
    """
    if not _validate_brand_slug(brand_slug):
        return jsonify({"success": False, "error": "Invalid brand_slug"}), 400
    body = request.get_json() or {}
    goal_text   = (body.get("goal") or "").strip()
    goal_metric = (body.get("metric") or "").strip()
    deadline    = (body.get("deadline") or "").strip()
    if not goal_text:
        return jsonify({"success": False, "error": "goal is required"}), 400

    goals = _read_memory(brand_slug, "goals")
    active = goals.get("active_goals", [])
    new_goal = {
        "id":         f"g_{int(datetime.now().timestamp())}",
        "goal":       goal_text,
        "metric":     goal_metric,
        "deadline":   deadline,
        "set_at":     datetime.now().isoformat(),
        "status":     "active",
    }
    active.append(new_goal)
    goals["active_goals"] = active
    goals_path = BRANDS_DIR / brand_slug / _MEMORY_FILES["goals"]
    goals_path.parent.mkdir(parents=True, exist_ok=True)
    _atomic_write_json(goals_path, goals)

    # Log the decision
    _approve_memory_update(brand_slug, "decisions_log", {})  # trigger log append
    decisions_path = BRANDS_DIR / brand_slug / _MEMORY_FILES["decisions_log"]
    log = _read_memory(brand_slug, "decisions_log")
    log.setdefault("decisions", []).append({
        "timestamp":  datetime.now().isoformat(),
        "type":       "goal_set",
        "goal":       new_goal,
        "approved_by": "Gaurav",
    })
    _atomic_write_json(decisions_path, log)

    return jsonify({"success": True, "data": {"goal": new_goal}})


# ── Outputs ───────────────────────────────────────────────────────────────────

@app.route("/api/outputs/pending", methods=["GET"])
def get_pending_outputs():
    from utils.output_formatter import format_for_notion
    brand_slug = request.args.get("brand_slug", "offgrid-creatives-ai")

    # DB-WIRED Step 7 — Supabase primary, but only return if it has rows
    if _DB_AVAILABLE:
        brand_id = _get_brand_id(brand_slug)
        if brand_id:
            rows = _db.get_pending_outputs(brand_id)
            if rows:
                items = []
                for row in rows:
                    agent_slug_key = row.get("agent_slug", "unknown")
                    agent_name = next(
                        (a["name"] for a in AGENTS
                         if re.sub(r"[^a-z0-9-]", "", a["name"].lower().replace(" ", "-")) == agent_slug_key),
                        agent_slug_key,
                    )
                    raw = row.get("raw_output") or {}
                    preview = ""
                    try:
                        preview = format_for_notion(agent_name, raw)[:500]
                    except Exception:
                        preview = str(raw)[:500]
                    formatted_out = row.get("formatted_output") or {}
                    notion_page_id = formatted_out.get("notion_page_id", "")
                    notion_url = formatted_out.get("notion_url", "")
                    if notion_page_id and not notion_url:
                        notion_url = f"https://notion.so/{notion_page_id.replace('-', '')}"
                    items.append({
                        "output_id": row["id"],
                        "filename": f"{agent_slug_key}_{row['id'][:8]}.json",
                        "filepath": "",
                        "agentName": agent_name,
                        "contentType": (row.get("output_type") or "JSON").upper(),
                        "preview": preview,
                        "timestamp": row.get("created_at", ""),
                        "notion_page_id": notion_page_id,
                        "notion_url": notion_url,
                    })
                return jsonify({"success": True, "data": items})

    # Fallback: disk scan
    brand_dir = get_brand_dir(brand_slug)
    pending_dir = brand_dir / "outputs" / "pending_approval"
    if not pending_dir.exists():
        return jsonify({"success": True, "data": []})
    items = []
    for filepath in pending_dir.rglob("*"):
        if filepath.is_file():
            stat = filepath.stat()
            agent_name = filepath.parent.name if filepath.parent != pending_dir else "unknown"
            preview = ""
            if filepath.suffix == ".json":
                try:
                    with open(filepath) as f:
                        raw = json.load(f)
                    preview = format_for_notion(agent_name, raw)[:500]
                except Exception:
                    # Not valid JSON — read as plain text
                    try:
                        preview = filepath.read_text(errors="replace")[:500]
                    except Exception:
                        pass
            elif filepath.suffix in (".txt", ".md"):
                try:
                    preview = filepath.read_text(errors="replace")[:500]
                except Exception:
                    pass
            items.append({
                "output_id": None,
                "filename": filepath.name,
                "filepath": str(filepath.relative_to(BASE_DIR)),
                "agentName": agent_name,
                "contentType": filepath.suffix.lstrip(".").upper() or "FILE",
                "preview": preview,
                "timestamp": datetime.fromtimestamp(stat.st_mtime).isoformat(),
            })
    items.sort(key=lambda x: x["timestamp"], reverse=True)
    return jsonify({"success": True, "data": items})


@app.route("/api/outputs/content", methods=["GET"])
@require_auth
def get_output_content():
    """Return the full text content of an output file for in-dashboard reading."""
    filepath = request.args.get("filepath", "").strip()
    if not filepath:
        return jsonify({"success": False, "error": "filepath required"}), 400
    # Resolve relative to BASE_DIR, prevent path traversal
    full = (BASE_DIR / filepath).resolve()
    if not str(full).startswith(str(BASE_DIR.resolve())):
        return jsonify({"success": False, "error": "Invalid path"}), 403
    if not full.exists() or not full.is_file():
        return jsonify({"success": False, "error": "File not found"}), 404
    try:
        content = full.read_text(errors="replace")
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500
    return jsonify({"success": True, "data": {"content": content, "filename": full.name}})


# ── Per-agent output endpoint ──────────────────────────────────────────────────

_AGENT_FOLDER: dict[str, str] = {
    "trend-researcher":  "Trend Researcher",
    "strategy-agent":    "Strategy Agent",
    "content-planner":   "Content Planner",
    "script-writer":     "Script Writer",
    "creative-director": "Creative Director",
    "data-analyst":      "Data Analyst",
    "funnel-specialist": "Funnel Specialist",
    "website-agent":     "Website Agent",
    "ceo-brain":         "CEO Brain",
}


def _parse_agent_output_file(filepath: Path) -> dict | None:
    """Parse an agent output file that may contain Loop Header + '---' + JSON."""
    try:
        raw = filepath.read_text()
        # Split on the separator between Loop Header and JSON payload
        if "\n---\n" in raw:
            parts = raw.split("\n---\n", 1)
            loop_header_text = parts[0].strip()
            payload_text = parts[1].strip() if len(parts) > 1 else ""
        else:
            loop_header_text = ""
            payload_text = raw.strip()

        loop_header: dict = {}
        for line in loop_header_text.splitlines():
            if ":" in line:
                key, _, val = line.partition(":")
                loop_header[key.strip().upper()] = val.strip()

        payload: Any = None
        if payload_text.startswith("{") or payload_text.startswith("["):
            try:
                payload = json.loads(payload_text)
            except Exception:
                # Attempt JSON repair for literal newlines inside string values
                try:
                    repaired = escape_literal_newlines_in_strings(payload_text)
                    payload = json.loads(repaired)
                except Exception:
                    payload = None

        return {"loop_header": loop_header, "payload": payload, "raw": raw}
    except Exception:
        return None


@app.route("/api/agents/output/history", methods=["GET"])
def get_agent_output_history():
    """Return version history for an agent's outputs. Phase 1 Step 3."""
    brand_slug = request.args.get("brand_slug", "offgrid-creatives-ai")
    agent_slug = request.args.get("agent_slug", "")
    if not agent_slug:
        return jsonify({"success": False, "error": "agent_slug required"}), 400

    if _DB_AVAILABLE:
        brand_id = _get_brand_id(brand_slug)
        if brand_id:
            rows = _db.get_output_history(brand_id, agent_slug)
            return jsonify({"success": True, "data": rows})

    return jsonify({"success": True, "data": []})


@app.route("/api/agents/output", methods=["GET"])
def get_agent_output():
    # DB-WIRED Step 5 + Phase 1 Step 3
    from utils.output_formatter import format_for_notion, format_scripts, format_calendar, format_strategy
    brand_slug = request.args.get("brand_slug", "offgrid-creatives-ai")
    agent_slug = request.args.get("agent_slug", "")
    output_id  = request.args.get("output_id", "").strip()  # Phase 1 Step 3 — specific version

    folder_name = _AGENT_FOLDER.get(agent_slug)
    if not folder_name:
        return jsonify({"success": False, "error": f"Unknown agent slug: {agent_slug}"}), 400

    payload: Any = None
    loop_header: dict = {}
    raw: str = ""
    source_filename = "supabase"
    returned_output_id: str | None = None
    returned_approval_status: str | None = None

    # Try Supabase first
    if _DB_AVAILABLE:
        brand_id = _get_brand_id(brand_slug)
        if brand_id:
            row: dict | None = None
            if output_id:
                # Fetch specific version by ID
                try:
                    res = _db._client.table("agent_outputs").select("*").eq("id", output_id).single().execute()
                    row = res.data
                except Exception:
                    row = None
            else:
                rows = _db.get_outputs_by_agent(brand_id, agent_slug)
                if not rows:
                    # Also try pending
                    rows = _db.get_pending_outputs(brand_id)
                    rows = [r for r in rows if r.get("agent_slug") == agent_slug]
                row = rows[0] if rows else None

            if row:
                payload = row.get("raw_output") or {}
                fmtd = row.get("formatted_output") or {}
                loop_header = fmtd.get("loop_header", {})
                source_filename = f"supabase:{row['id'][:8]}"
                returned_output_id = row["id"]
                returned_approval_status = row.get("approval_status")

    # Fallback to filesystem if Supabase had nothing
    if payload is None:
        brand_dir = get_brand_dir(brand_slug)
        target_file: Path | None = None
        for sub in ["pending_approval", "approved"]:
            search_dir = brand_dir / "outputs" / sub / folder_name
            if search_dir.exists():
                candidates = [f for f in search_dir.iterdir() if f.is_file() and not f.name.endswith(".changes.txt")]
                if candidates:
                    target_file = max(candidates, key=lambda f: f.stat().st_mtime)
                    break
            flat_dir = brand_dir / "outputs" / sub
            if flat_dir.exists():
                candidates = [f for f in flat_dir.iterdir() if f.is_file() and folder_name.lower().replace(" ", "_") in f.name.lower()]
                if candidates:
                    target_file = max(candidates, key=lambda f: f.stat().st_mtime)
                    break

        if not target_file:
            return jsonify({"success": False, "error": "No output found for this agent in Supabase or filesystem"}), 404

        parsed = _parse_agent_output_file(target_file)
        if not parsed:
            return jsonify({"success": False, "error": "Could not parse output file"}), 500
        payload = parsed["payload"]
        loop_header = parsed["loop_header"]
        raw = parsed["raw"]
        source_filename = target_file.name

    # Determine output type and format accordingly
    slug = agent_slug.lower()
    formatted: dict[str, Any] = {}

    if slug == "script-writer" and payload:
        try:
            frames = format_scripts(payload)
            formatted = {"type": "scripts", "frames": frames}
        except Exception:
            formatted = {"type": "markdown", "text": format_for_notion(folder_name, payload)}
    elif slug == "content-planner" and payload:
        try:
            posts = format_calendar(payload)
            formatted = {"type": "calendar", "posts": posts}
        except Exception:
            formatted = {"type": "markdown", "text": format_for_notion(folder_name, payload)}
    elif slug == "strategy-agent" and payload:
        try:
            phases = format_strategy(payload)
            strategic_angle = payload.get("strategic_angle", "") if isinstance(payload, dict) else ""
            north_star = payload.get("north_star_metric", "") if isinstance(payload, dict) else ""
            formatted = {"type": "strategy", "phases": phases, "strategic_angle": strategic_angle, "north_star": north_star}
        except Exception:
            formatted = {"type": "markdown", "text": format_for_notion(folder_name, payload)}
    elif slug == "trend-researcher":
        md = format_for_notion(folder_name, payload) if payload else raw
        # Extract hooks if present
        hooks: list[str] = []
        if isinstance(payload, dict):
            hooks = payload.get("hooks", payload.get("hook_ideas", payload.get("content_hooks", [])))
            if not isinstance(hooks, list):
                hooks = []
        formatted = {"type": "trend", "hooks": hooks, "markdown": md}
    else:
        md = format_for_notion(folder_name, payload) if payload else raw
        formatted = {"type": "markdown", "text": md}

    return jsonify({
        "success": True,
        "data": {
            "agent_slug": agent_slug,
            "folder_name": folder_name,
            "filename": source_filename,
            "output_id": returned_output_id,
            "approval_status": returned_approval_status,
            "loop_header": loop_header,
            "formatted": formatted,
        }
    })


@app.route("/api/outputs/all", methods=["GET"])
def get_all_outputs():
    brand_slug = request.args.get("brand_slug", "offgrid-creatives-ai")
    brand_dir = get_brand_dir(brand_slug)
    items = []
    folders = [
        (brand_dir / "outputs" / "pending_approval", "pending"),
        (brand_dir / "outputs" / "approved", "approved"),
    ]
    for folder, status in folders:
        if not folder.exists():
            continue
        for filepath in folder.rglob("*"):
            if filepath.is_file():
                stat = filepath.stat()
                items.append({
                    "filename": filepath.name,
                    "filepath": str(filepath.relative_to(BASE_DIR)),
                    "agentName": filepath.parent.name if filepath.parent != folder else "unknown",
                    "contentType": filepath.suffix.lstrip(".").upper() or "FILE",
                    "status": status,
                    "timestamp": datetime.fromtimestamp(stat.st_mtime).isoformat(),
                })
    items.sort(key=lambda x: x["timestamp"], reverse=True)
    return jsonify({"success": True, "data": items})


@app.route("/api/outputs/approve", methods=["POST"])
@require_auth
def approve_output():
    # DB-WIRED Step 5 + Phase 1 Step 4
    body = request.get_json()
    brand_slug = body.get("brand_slug", "offgrid-creatives-ai")
    filepath = body.get("filepath", "")
    output_id = body.get("output_id", "")  # Supabase UUID — optional
    next_agent_slug: str | None = None

    # Supabase approval
    if _DB_AVAILABLE:
        brand_id = _get_brand_id(brand_slug)
        if brand_id:
            resolved_agent_slug: str | None = None
            if output_id:
                _db.approve_output(output_id)
                _db.log_audit(brand_id, "output_approved", "user", {"output_id": output_id})
                # Look up agent_slug for this output so we can unlock the next one
                try:
                    res = _db._client.table("agent_outputs").select("agent_slug").eq("id", output_id).single().execute()
                    resolved_agent_slug = res.data.get("agent_slug") if res.data else None
                except Exception:
                    pass
            elif filepath:
                parts = Path(filepath).parts
                folder_nm = parts[-2] if len(parts) >= 2 else ""
                resolved_agent_slug = _FOLDER_TO_SLUG.get(folder_nm, "")
                if resolved_agent_slug:
                    rows = _db.get_pending_outputs(brand_id)
                    match = next((r for r in rows if r.get("agent_slug") == resolved_agent_slug), None)
                    if match:
                        _db.approve_output(match["id"])
                        _db.log_audit(brand_id, "output_approved", "user", {"agent": resolved_agent_slug, "file": Path(filepath).name})

            # Phase 1 Step 4 — unlock next agent in pipeline
            if resolved_agent_slug:
                next_agent_slug = _unlock_next_agent(brand_id, resolved_agent_slug)

    # Also move the file for filesystem consistency
    if filepath:
        src = _safe_path(BASE_DIR, filepath)
        if src and src.exists():
            brand_dir = get_brand_dir(brand_slug)
            approved_dir = brand_dir / "outputs" / "approved"
            approved_dir.mkdir(parents=True, exist_ok=True)
            dest = approved_dir / src.name
            shutil.move(str(src), str(dest))

    # Return next_agent so frontend can show toast + highlight
    next_agent_name = next(
        (a["name"] for a in AGENTS if _agent_name_to_slug(a["name"]) == next_agent_slug),
        next_agent_slug,
    ) if next_agent_slug else None

    return jsonify({"success": True, "data": {
        "message": "Approved and moved.",
        "next_agent": next_agent_slug,
        "next_agent_name": next_agent_name,
    }})


@app.route("/api/outputs/reject", methods=["POST"])
@require_auth
def reject_output():
    # DB-WIRED Step 5
    body = request.get_json()
    brand_slug = body.get("brand_slug", "offgrid-creatives-ai")
    filepath = body.get("filepath", "")
    output_id = body.get("output_id", "")  # Supabase UUID — optional

    if _DB_AVAILABLE:
        brand_id = _get_brand_id(brand_slug)
        if brand_id:
            if output_id:
                _db.reject_output(output_id)
                _db.log_audit(brand_id, "output_rejected", "user", {"output_id": output_id})
            elif filepath:
                parts = Path(filepath).parts
                folder_name = parts[-2] if len(parts) >= 2 else ""
                agent_slug_key = _FOLDER_TO_SLUG.get(folder_name, "")
                if agent_slug_key:
                    rows = _db.get_pending_outputs(brand_id)
                    match = next((r for r in rows if r.get("agent_slug") == agent_slug_key), None)
                    if match:
                        _db.reject_output(match["id"])
                        _db.log_audit(brand_id, "output_rejected", "user", {"agent": agent_slug_key, "file": Path(filepath).name})

    if filepath:
        src = _safe_path(BASE_DIR, filepath)
        if src and src.exists():
            src.unlink()
    return jsonify({"success": True, "data": {"message": "Rejected and removed."}})


@app.route("/api/outputs/request-changes", methods=["POST"])
@require_auth
def request_changes():
    body = request.get_json()
    filepath = body.get("filepath", "")
    note = body.get("note", "")
    src = _safe_path(BASE_DIR, filepath)
    if src and src.exists():
        note_file = src.with_suffix(".changes.txt")
        note_file.write_text(f"[{datetime.now().isoformat()}]\n{note}\n")
    return jsonify({"success": True, "data": {"message": "Change note saved."}})


def _resolve_output_file(filepath_param: str) -> Path | None:
    """
    Resolve a filepath parameter to an absolute path, searching both
    BASE_DIR/outputs/ (legacy) and BASE_DIR/brands/*/outputs/ (current).
    Returns None if the path escapes the project root or doesn't exist.
    """
    import urllib.parse
    decoded = urllib.parse.unquote(filepath_param)
    # Try as relative to BASE_DIR first (filepath may already include brands/...)
    candidate = (BASE_DIR / decoded).resolve()
    if str(candidate).startswith(str(BASE_DIR.resolve())) and candidate.exists():
        return candidate
    # Try just the filename across all brand output folders
    fname = Path(decoded).name
    for brand_dir in BRANDS_DIR.iterdir():
        if not brand_dir.is_dir():
            continue
        for subfolder in ["outputs/pending_approval", "outputs/approved"]:
            for match in (brand_dir / subfolder).rglob(fname):
                if match.is_file():
                    return match
    return None


_MIME_MAP: dict[str, str] = {
    ".png":  "image/png",
    ".jpg":  "image/jpeg",
    ".jpeg": "image/jpeg",
    ".webp": "image/webp",
    ".gif":  "image/gif",
    ".mp4":  "video/mp4",
    ".mov":  "video/quicktime",
    ".webm": "video/webm",
    ".mp3":  "audio/mpeg",
    ".wav":  "audio/wav",
    ".m4a":  "audio/mp4",
    ".ogg":  "audio/ogg",
    ".pdf":  "application/pdf",
    ".json": "application/json",
    ".txt":  "text/plain",
    ".md":   "text/markdown",
}


@app.route("/api/outputs/download/<path:filepath>", methods=["GET"])
def download_file(filepath):
    """Force-download any output file."""
    fpath = _resolve_output_file(filepath)
    if not fpath:
        return jsonify({"success": False, "error": "File not found"}), 404
    mime = _MIME_MAP.get(fpath.suffix.lower(), "application/octet-stream")
    return send_file(str(fpath), mimetype=mime, as_attachment=True,
                     download_name=fpath.name)


@app.route("/api/outputs/media/<path:filepath>", methods=["GET"])
def serve_media(filepath):
    """Serve an output file inline (for browser preview — images, video, audio)."""
    fpath = _resolve_output_file(filepath)
    if not fpath:
        return jsonify({"success": False, "error": "File not found"}), 404
    mime = _MIME_MAP.get(fpath.suffix.lower(), "application/octet-stream")
    return send_file(str(fpath), mimetype=mime, as_attachment=False)


# ── Brand profile / dashboard ─────────────────────────────────────────────────

@app.route("/api/brand/profile", methods=["GET"])
def get_brand_profile():
    # DB-WIRED Step 5
    brand_slug = request.args.get("brand_slug", "offgrid-creatives-ai")
    if _DB_AVAILABLE:
        row = _db.get_brand(brand_slug)
        if row and row.get("profile"):
            return jsonify({"success": True, "data": row["profile"]})
    # Fallback to local file
    brand_dir = get_brand_dir(brand_slug)
    profile_file = brand_dir / "brand_profile.json"
    if not profile_file.exists():
        return jsonify({"success": False, "error": "brand_profile.json not found"}), 404
    with open(profile_file) as f:
        data = json.load(f)
    return jsonify({"success": True, "data": data})


@app.route("/api/brand/profile", methods=["POST"])
def save_brand_profile():
    # DB-WIRED Step 5
    body = request.get_json()
    brand_slug = body.pop("brand_slug", "offgrid-creatives-ai")
    brand_dir = get_brand_dir(brand_slug)
    profile_file = brand_dir / "brand_profile.json"
    with open(profile_file, "w") as f:
        json.dump(body, f, indent=2)
    # Also upsert to Supabase
    if _DB_AVAILABLE:
        brand_name = body.get("brand_name", brand_slug)
        _db.upsert_brand(brand_slug, brand_name, body)
    return jsonify({"success": True, "data": {"message": "Brand profile saved."}})


@app.route("/api/brand/dashboard", methods=["GET"])
def get_brand_dashboard():
    brand_slug = request.args.get("brand_slug", "offgrid-creatives-ai")
    brand_dir = get_brand_dir(brand_slug)
    data = {}
    for fname in ["brand_profile.json", "trends_live.json", "session_state.json"]:
        fpath = brand_dir / fname
        if fpath.exists():
            with open(fpath) as f:
                data[fname.replace(".json", "")] = json.load(f)
    return jsonify({"success": True, "data": data})


# ── Brand Summary ─────────────────────────────────────────────────────────────

@app.route("/api/brand/summary", methods=["GET"])
def get_brand_summary():
    """
    Returns a flat summary card for the Brand Dashboard screen:
    brand_profile fields + computed key metrics from session_state.
    """
    brand_slug = request.args.get("brand_slug", "offgrid-creatives-ai")
    brand_dir = get_brand_dir(brand_slug)

    # Load brand_profile
    profile: dict = {}
    profile_path = brand_dir / "brand_profile.json"
    if profile_path.exists():
        with open(profile_path) as f:
            profile = json.load(f)

    # Load session_state
    session: dict = {}
    session_path = brand_dir / "session_state.json"
    if session_path.exists():
        with open(session_path) as f:
            session = json.load(f)

    # Compute key metrics
    # Posts scripted = count JSON files in Script Writer pending + approved
    scripts_pending = list((brand_dir / "outputs" / "pending_approval" / "Script Writer").glob("*.json")) if (brand_dir / "outputs" / "pending_approval" / "Script Writer").exists() else []
    scripts_approved = list((brand_dir / "outputs" / "approved" / "Script Writer").glob("*.json")) if (brand_dir / "outputs" / "approved" / "Script Writer").exists() else []
    posts_scripted = len(scripts_pending) + len(scripts_approved)

    # Agents run = session_state keys that look like per-agent dicts with "status"
    agent_statuses = {k: v for k, v in session.items() if isinstance(v, dict) and "status" in v}
    agents_run = len([v for v in agent_statuses.values() if v.get("status") in ("done", "error", "running")])
    agents_approved = len(session.get("notion_cards", []) and [c for c in session.get("notion_cards", []) if c.get("status") == "approved"])

    # Notion cards counts
    notion_cards = session.get("notion_cards", [])
    notion_pending  = len([c for c in notion_cards if c.get("status") == "pending_approval"])
    notion_approved = len([c for c in notion_cards if c.get("status") == "approved"])
    notion_rejected = len([c for c in notion_cards if c.get("status") == "rejected"])

    # Completed agents list
    completed_agents = session.get("completed_agents", [])

    # Build activity feed — last 20 events from session_state agent log entries
    activity_feed: list = []
    for agent_key, agent_val in session.items():
        if isinstance(agent_val, dict) and "status" in agent_val:
            ts = agent_val.get("updated_at") or agent_val.get("started_at") or ""
            status = agent_val.get("status", "")
            icon = "✅" if status == "done" else "❌" if status == "error" else "🔄"
            activity_feed.append({
                "agent": agent_key,
                "status": status,
                "icon": icon,
                "summary": (agent_val.get("last_output") or "")[:200],
                "timestamp": ts,
            })
    # Sort newest first
    activity_feed.sort(key=lambda x: x.get("timestamp") or "", reverse=True)
    activity_feed = activity_feed[:20]

    return jsonify({"success": True, "data": {
        # Brand identity
        "brand_name":   profile.get("brand_name", brand_slug),
        "product":      profile.get("product", ""),
        "phase":        profile.get("phase", "Beta"),
        "platforms":    profile.get("platforms", []),
        "bottlenecks":  profile.get("bottlenecks", []),
        "audience":     profile.get("audience", []),
        "price_india":  profile.get("price_india", ""),
        "price_international": profile.get("price_international", ""),
        "railway_url":  profile.get("railway_url", ""),
        # Agent-first onboarding fields
        "instagram_handle":   profile.get("instagram_handle", ""),
        "competitor_handles": profile.get("competitor_handles", []),
        "brand_face":         profile.get("brand_face", ""),
        "tone_specifics":     profile.get("tone_specifics", ""),
        "content_goal_90d":   profile.get("content_goal_90d", ""),
        "what_to_never_say":  profile.get("what_to_never_say", ""),
        "weekly_post_target": profile.get("weekly_post_target", "3x"),

        # Key metrics
        "posts_scripted":    posts_scripted,
        "agents_run":        agents_run,
        "agents_approved":   notion_approved,
        "notion_pending":    notion_pending,
        "notion_approved":   notion_approved,
        "notion_rejected":   notion_rejected,
        "completed_agents":  completed_agents,

        # Activity feed (last 20 agent events)
        "activity_feed": activity_feed,

        # API key health
        "keys": {
            "anthropic":  bool(os.getenv("ANTHROPIC_API_KEY", "").strip()),
            "elevenlabs": bool(os.getenv("ELEVENLABS_API_KEY", "").strip()),
            "notion":     bool(os.getenv("NOTION_API_KEY", "").strip()),
            "fal":        bool(os.getenv("FAL_API_KEY", "").strip()),
        }
    }})


# ── Dashboard Output Bundle ───────────────────────────────────────────────────

@app.route("/api/dashboard-output", methods=["GET"])
def get_dashboard_output():
    from utils.output_formatter import format_scripts, format_calendar, format_strategy

    brand_slug = request.args.get("brand_slug", "offgrid-creatives-ai")

    # Try brand-specific output first, fall back to legacy global file
    brand_output_path = BRANDS_DIR / brand_slug / "data" / "dashboard_output.json"
    legacy_path = BASE_DIR / "data" / "dashboard_output.json"
    output_path = brand_output_path if brand_output_path.exists() else legacy_path

    if not output_path.exists():
        return jsonify({"success": False, "error": "dashboard_output.json not found. Run the output bundler first."})

    with open(output_path) as f:
        data = json.load(f)

    # Apply formatter to scripts, calendar, strategy sections
    result = dict(data)
    if "scripts" in data and isinstance(data["scripts"], dict):
        result["scripts_formatted"] = format_scripts(data["scripts"])
    if "calendar" in data and isinstance(data["calendar"], dict):
        result["calendar_formatted"] = format_calendar(data["calendar"])
    if "strategy" in data and isinstance(data["strategy"], dict):
        result["strategy_formatted"] = format_strategy(data["strategy"])

    return jsonify({"success": True, "data": result})


# ── Agent Log ─────────────────────────────────────────────────────────────────

@app.route("/api/ceo/next-agent", methods=["GET"])
def ceo_next_agent():
    """
    Return CEO Brain's recommended next agent and reason.
    Phase 1 Step 2.
    """
    brand_slug = request.args.get("brand_slug", "offgrid-creatives-ai")
    state: dict = {}

    if _DB_AVAILABLE:
        brand_id = _get_brand_id(brand_slug)
        if brand_id:
            state = _db.get_session_state(brand_id) or {}

    if not state:
        brand_dir = BRANDS_DIR / brand_slug
        session_file = brand_dir / "session_state.json"
        if session_file.exists():
            try:
                with open(session_file) as f:
                    state = json.load(f)
            except Exception:
                pass

    # Use stored recommendation first (written by _unlock_next_agent)
    next_agent = state.get("next_agent")
    last_completed = state.get("last_completed")
    completed = state.get("completed_agents", []) if isinstance(state.get("completed_agents"), list) else []
    blocked_on: str | None = None

    # Compute from pipeline if no stored recommendation
    if not next_agent:
        for slug in PIPELINE_UNLOCK_ORDER:
            if slug not in completed:
                next_agent = slug
                break
        # Ad-strategist gate
        if next_agent == "ad-strategist" and not state.get("paid_budget_confirmed", False):
            blocked_on = "Set paid_budget_confirmed: true in brand profile to unlock Ad Strategist"
            next_agent = None
            for slug in PIPELINE_UNLOCK_ORDER:
                if slug not in completed and slug != "ad-strategist":
                    next_agent = slug
                    break

    # Handle ad-strategist gate even when stored
    if next_agent == "ad-strategist" and not state.get("paid_budget_confirmed", False):
        blocked_on = "Set paid_budget_confirmed: true in brand profile to unlock Ad Strategist"

    # Build human-readable reason
    reason = ""
    if next_agent:
        agent_display = next((a["name"] for a in AGENTS if _agent_name_to_slug(a["name"]) == next_agent), next_agent)
        if last_completed:
            completed_display = next((a["name"] for a in AGENTS if _agent_name_to_slug(a["name"]) == last_completed), last_completed)
            reason = f"{completed_display} completed — {agent_display} is next in pipeline"
        elif not completed:
            reason = f"{agent_display} is the starting point for this brand"
        else:
            reason = f"{agent_display} is next in the pipeline"

    return jsonify({"success": True, "data": {
        "next_agent": next_agent,
        "reason": reason,
        "blocked_on": blocked_on,
    }})


@app.route("/api/agents/log", methods=["GET"])
def get_agent_log():
    brand_slug = request.args.get("brand_slug", "offgrid-creatives-ai")
    brand_dir = get_brand_dir(brand_slug)
    session_file = brand_dir / "session_state.json"
    if not session_file.exists():
        return jsonify({"success": True, "data": []})
    with open(session_file) as f:
        session = json.load(f)
    log = session.get("agent_log", [])
    # Return newest first
    log_sorted = sorted(log, key=lambda x: x.get("timestamp", ""), reverse=True)
    return jsonify({"success": True, "data": log_sorted})


# ── Notion Approval Cards ─────────────────────────────────────────────────────

@app.route("/api/notion/cards", methods=["GET"])
def get_notion_cards():
    brand_slug = request.args.get("brand_slug", "offgrid-creatives-ai")
    brand_dir = get_brand_dir(brand_slug)
    session_file = brand_dir / "session_state.json"
    if not session_file.exists():
        return jsonify({"success": True, "data": []})
    with open(session_file) as f:
        session = json.load(f)
    cards = session.get("notion_cards", [])
    return jsonify({"success": True, "data": cards})


@app.route("/api/notion/approve", methods=["POST"])
def approve_notion_card():
    body = request.get_json() or {}
    page_id = body.get("page_id", "")
    brand_slug = body.get("brand_slug", "offgrid-creatives-ai")

    if not page_id:
        return jsonify({"success": False, "error": "page_id required"}), 400

    try:
        from notion_integration.notion_pusher import update_notion_status
        update_notion_status(page_id, "Approved", approved=True)
    except Exception as e:
        print(f"[dashboard_api] Notion approve failed: {e}")

    _update_notion_card_status(brand_slug, page_id, "approved")
    return jsonify({"success": True, "data": {"message": "Approved in Notion"}})


@app.route("/api/notion/reject", methods=["POST"])
def reject_notion_card():
    body = request.get_json() or {}
    page_id = body.get("page_id", "")
    brand_slug = body.get("brand_slug", "offgrid-creatives-ai")

    if not page_id:
        return jsonify({"success": False, "error": "page_id required"}), 400

    try:
        from notion_integration.notion_pusher import update_notion_status
        update_notion_status(page_id, "Rejected", rejected=True)
    except Exception as e:
        print(f"[dashboard_api] Notion reject failed: {e}")

    _update_notion_card_status(brand_slug, page_id, "rejected")
    return jsonify({"success": True, "data": {"message": "Rejected in Notion"}})


@app.route("/api/notion/sync", methods=["GET"])
def sync_notion_approvals():
    """
    Phase 3 Step 2 — Check Notion for approved pages, sync status back to Supabase.
    For each pending output with a notion_page_id, fetches its Notion status.
    If approved, calls db.approve_output() and _unlock_next_agent().
    """
    brand_slug = request.args.get("brand_slug", "offgrid-creatives-ai")

    if not _NOTION_KEY:
        return jsonify({"success": False, "error": "NOTION_API_KEY not configured"}), 400

    if not _DB_AVAILABLE:
        return jsonify({"success": False, "error": "Supabase not available"}), 500

    brand_id = _get_brand_id(brand_slug)
    if not brand_id:
        return jsonify({"success": False, "error": "Brand not found"}), 404

    try:
        import requests as _req
        pending_rows = _db.get_pending_outputs(brand_id)
        synced = 0
        errors = []
        for row in pending_rows:
            formatted = row.get("formatted_output") or {}
            notion_page_id = formatted.get("notion_page_id", "")
            if not notion_page_id:
                continue
            try:
                resp = _req.get(
                    f"https://api.notion.com/v1/pages/{notion_page_id}",
                    headers={
                        "Authorization": f"Bearer {_NOTION_KEY}",
                        "Notion-Version": "2022-06-28",
                    },
                    timeout=5,
                )
                if resp.status_code != 200:
                    continue
                page_data = resp.json()
                props = page_data.get("properties", {})
                status_prop = props.get("Status", {})
                status_val = (status_prop.get("select") or {}).get("name", "")
                if status_val == "Approved":
                    _db.approve_output(row["id"])
                    agent_slug_key = row.get("agent_slug", "")
                    if agent_slug_key:
                        _unlock_next_agent(brand_id, agent_slug_key)
                    synced += 1
            except Exception as _row_err:
                errors.append(str(_row_err))
        return jsonify({"success": True, "data": {"synced": synced, "errors": errors}})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


# ── Health + Config ───────────────────────────────────────────────────────────

@app.route("/api/health", methods=["GET"])
def health():
    return jsonify({"success": True, "data": {"status": "GRID CONTROL API running", "port": 5001}})


@app.route("/api/config/keys", methods=["GET"])
def get_key_status():
    """Returns which API keys are configured (never exposes the keys themselves)."""
    return jsonify({"success": True, "data": {
        "anthropic":  bool(os.getenv("ANTHROPIC_API_KEY", "").strip()),
        "elevenlabs": bool(os.getenv("ELEVENLABS_API_KEY", "").strip()),
        "notion":     bool(os.getenv("NOTION_API_KEY", "").strip()),
        "fal":        bool(os.getenv("FAL_API_KEY", "").strip()),
        "apify":      bool(os.getenv("APIFY_API_KEY", "").strip()),
        "runway":     bool(os.getenv("RUNWAY_API_KEY", "").strip()),
        "kling":      bool(os.getenv("KLING_API_KEY", "").strip()),
        "meta":       bool(os.getenv("META_ACCESS_TOKEN", "").strip()) or bool(os.getenv("META_GRAPH_API_TOKEN", "").strip()),
        "linkedin":   bool(os.getenv("LINKEDIN_ACCESS_TOKEN", "").strip()),
        "ga4":        bool(os.getenv("GA4_PROPERTY_ID", "").strip()),
    }})


@app.route("/api/connections/check", methods=["GET"])
def check_connections():
    """
    Phase 4 Step 1 — Live connection validator. Each check has a 5s timeout.
    Runs real API calls for Meta, Notion, Apify. Env-var check for Anthropic + ElevenLabs.
    """
    import requests as _req
    results: dict[str, dict] = {}

    # Anthropic — env var check only (no live call needed)
    ak = _ANTHROPIC_KEY
    results["anthropic"] = {"connected": bool(ak), "account": "API key set" if ak else "Not configured"}

    # ElevenLabs — env var check
    ek = _ELEVENLABS_KEY
    results["elevenlabs"] = {"connected": bool(ek), "account": "API key set" if ek else "Not configured"}

    # Notion — live call
    nk = _NOTION_KEY
    if nk:
        try:
            resp = _req.get(
                "https://api.notion.com/v1/users/me",
                headers={"Authorization": f"Bearer {nk}", "Notion-Version": "2022-06-28"},
                timeout=5,
            )
            if resp.status_code == 200:
                data = resp.json()
                name = data.get("name") or data.get("bot", {}).get("owner", {}).get("user", {}).get("name", "")
                results["notion"] = {"connected": True, "account": name or "Connected"}
            else:
                results["notion"] = {"connected": False, "account": f"Auth failed ({resp.status_code})"}
        except Exception as e:
            results["notion"] = {"connected": False, "account": f"Timeout: {e}"}
    else:
        results["notion"] = {"connected": False, "account": "NOTION_API_KEY not set"}

    # Apify — live call
    apify_key = os.getenv("APIFY_API_KEY", "").strip()
    if apify_key:
        try:
            resp = _req.get(
                f"https://api.apify.com/v2/users/me?token={apify_key}",
                timeout=5,
            )
            if resp.status_code == 200:
                data = resp.json().get("data", {})
                username = data.get("username", "")
                results["apify"] = {"connected": True, "account": username or "Connected"}
            else:
                results["apify"] = {"connected": False, "account": f"Auth failed ({resp.status_code})"}
        except Exception as e:
            results["apify"] = {"connected": False, "account": f"Timeout: {e}"}
    else:
        results["apify"] = {"connected": False, "account": "APIFY_API_KEY not set"}

    # Meta (Instagram) — live call
    meta_token = os.getenv("META_GRAPH_API_TOKEN", "").strip() or os.getenv("META_ACCESS_TOKEN", "").strip()
    if meta_token:
        try:
            resp = _req.get(
                f"https://graph.facebook.com/me?access_token={meta_token}&fields=name",
                timeout=5,
            )
            if resp.status_code == 200:
                data = resp.json()
                name = data.get("name", "")
                results["meta"] = {"connected": True, "account": name or "Connected"}
            else:
                results["meta"] = {"connected": False, "account": f"Token invalid ({resp.status_code})"}
        except Exception as e:
            results["meta"] = {"connected": False, "account": f"Timeout: {e}"}
    else:
        results["meta"] = {"connected": False, "account": "META_GRAPH_API_TOKEN not set"}

    # LinkedIn — live call
    li_token = os.getenv("LINKEDIN_ACCESS_TOKEN", "").strip()
    if li_token:
        try:
            resp = _req.get(
                "https://api.linkedin.com/v2/me",
                headers={"Authorization": f"Bearer {li_token}"},
                timeout=5,
            )
            if resp.status_code == 200:
                data = resp.json()
                first = data.get("localizedFirstName", "")
                last  = data.get("localizedLastName", "")
                name  = f"{first} {last}".strip() or "Connected"
                results["linkedin"] = {"connected": True, "account": name}
            else:
                results["linkedin"] = {"connected": False, "account": f"Token invalid ({resp.status_code})"}
        except Exception as e:
            results["linkedin"] = {"connected": False, "account": f"Timeout: {e}"}
    else:
        results["linkedin"] = {"connected": False, "account": "LINKEDIN_ACCESS_TOKEN not set"}

    # YouTube — live call (validates API key via channels endpoint)
    yt_key = os.getenv("YOUTUBE_API_KEY", "").strip()
    if yt_key:
        try:
            resp = _req.get(
                f"https://www.googleapis.com/youtube/v3/channels?part=snippet&forHandle=AskGauravAI&key={yt_key}",
                timeout=5,
            )
            if resp.status_code == 200:
                data = resp.json()
                items = data.get("items", [])
                title = items[0]["snippet"]["title"] if items else "Key valid"
                results["youtube"] = {"connected": True, "account": title}
            elif resp.status_code == 400:
                results["youtube"] = {"connected": False, "account": "API key invalid"}
            else:
                results["youtube"] = {"connected": False, "account": f"Error ({resp.status_code})"}
        except Exception as e:
            results["youtube"] = {"connected": False, "account": f"Timeout: {e}"}
    else:
        results["youtube"] = {"connected": False, "account": "YOUTUBE_API_KEY not set"}

    # Twitter / X — live call
    # Note: Free tier App-Only Bearer tokens get 403 on /2/users/me (OAuth user-context only).
    # We use Twitter via Apify actor anyway, so a 403 here is OK as long as the token is well-formed.
    tw_token = os.getenv("TWITTER_BEARER_TOKEN", "").strip()
    if tw_token:
        try:
            resp = _req.get(
                "https://api.twitter.com/2/users/me",
                headers={"Authorization": f"Bearer {tw_token}"},
                timeout=5,
            )
            if resp.status_code == 200:
                data = resp.json().get("data", {})
                name = data.get("name", "") or data.get("username", "") or "Connected"
                results["twitter"] = {"connected": True, "account": f"@{data.get('username', name)}"}
            elif resp.status_code in (401,):
                # 401 = token actually invalid/revoked
                results["twitter"] = {"connected": False, "account": "Token invalid (401)"}
            elif resp.status_code in (403, 429):
                # 403 = Free tier restriction on /users/me (token still works via Apify)
                # 429 = rate limited (token still valid)
                results["twitter"] = {"connected": True, "account": "Token set (Free tier — read via Apify)"}
            else:
                results["twitter"] = {"connected": False, "account": f"Unexpected ({resp.status_code})"}
        except Exception as e:
            results["twitter"] = {"connected": False, "account": f"Timeout: {e}"}
    else:
        results["twitter"] = {"connected": False, "account": "TWITTER_BEARER_TOKEN not set"}

    # WhatsApp — env var check (Business API token)
    wa_token = os.getenv("WHATSAPP_ACCESS_TOKEN", "").strip()
    results["whatsapp"] = {
        "connected": bool(wa_token),
        "account": "Token set" if wa_token else "WHATSAPP_ACCESS_TOKEN not set",
    }

    return jsonify({"success": True, "data": results})


# ── Connections — Save Token ───────────────────────────────────────────────────

# Mapping from platform name → .env variable name
_PLATFORM_ENV_MAP: dict[str, str] = {
    "instagram": "META_GRAPH_API_TOKEN",
    "meta":      "META_GRAPH_API_TOKEN",
    "linkedin":  "LINKEDIN_ACCESS_TOKEN",
    "youtube":   "YOUTUBE_API_KEY",
    "twitter":   "TWITTER_BEARER_TOKEN",
    "x":         "TWITTER_BEARER_TOKEN",
    "whatsapp":  "WHATSAPP_ACCESS_TOKEN",
}

_ENV_FILE = BASE_DIR / ".env"


def _write_env_token(env_key: str, value: str) -> None:
    """Update or append a key=value line in the .env file, then reload into os.environ."""
    content = _ENV_FILE.read_text(encoding="utf-8") if _ENV_FILE.exists() else ""
    lines   = content.splitlines(keepends=True)
    pattern = re.compile(rf"^{re.escape(env_key)}\s*=.*$", re.MULTILINE)

    new_line = f"{env_key}={value}\n"
    if pattern.search(content):
        new_content = pattern.sub(new_line.rstrip("\n"), content)
    else:
        new_content = content.rstrip("\n") + ("\n" if content else "") + new_line

    _ENV_FILE.write_text(new_content, encoding="utf-8")
    os.environ[env_key] = value   # live-reload in current process


@app.route("/api/connections/save-token", methods=["POST"])
@require_auth
def save_connection_token():
    """
    Persist a platform API token to .env and reload it immediately.
    Body: { "platform": "instagram"|"linkedin"|"youtube"|"twitter"|"whatsapp",
            "token": "<token value>" }
    """
    body     = request.get_json() or {}
    platform = (body.get("platform") or "").strip().lower()
    token    = (body.get("token")    or "").strip()

    if not platform:
        return jsonify({"success": False, "error": "platform is required"}), 400
    if platform not in _PLATFORM_ENV_MAP:
        return jsonify({"success": False, "error": f"Unknown platform '{platform}'"}), 400
    if not token:
        return jsonify({"success": False, "error": "token is required"}), 400

    env_key = _PLATFORM_ENV_MAP[platform]
    try:
        _write_env_token(env_key, token)
    except Exception as exc:
        return jsonify({"success": False, "error": f"Failed to write .env: {exc}"}), 500

    return jsonify({
        "success": True,
        "data": {
            "platform": platform,
            "env_key":  env_key,
            "message":  f"{env_key} saved and live-reloaded",
        },
    })


# ── Team Standup ──────────────────────────────────────────────────────────────

@app.route("/api/standup", methods=["POST"])
def team_standup():
    """Generate a brief team standup summary from session state + recent agent activity."""
    import anthropic as _anthropic

    body = request.get_json() or {}
    brand_slug = body.get("brand_slug", "offgrid-creatives-ai")

    # Gather agent status context
    status_context = ""
    try:
        brand_dir = BRANDS_DIR / brand_slug
        session_file = brand_dir / "session_state.json"
        if session_file.exists():
            with open(session_file) as f:
                session = json.load(f)
            lines = []
            for agent in AGENTS:
                name = agent["name"]
                agent_data = session.get(name, {})
                status = agent_data.get("status", "idle") if isinstance(agent_data, dict) else "idle"
                last_run = agent_data.get("last_run", "never") if isinstance(agent_data, dict) else "never"
                lines.append(f"- {name}: {status} (last run: {last_run})")
            status_context = "\n".join(lines)
    except Exception:
        status_context = "No session state available."

    api_key = os.getenv("ANTHROPIC_API_KEY", "").strip()
    if not api_key:
        return jsonify({"success": False, "error": "ANTHROPIC_API_KEY not set"}), 500

    try:
        client = _anthropic.Anthropic(api_key=api_key)
        resp = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=512,
            system=(
                "You are the CEO Brain of the OffGrid Marketing OS. "
                "Generate a concise daily standup summary in plain English. "
                "Cover: what was completed, what is in progress, and any blockers. "
                "Maximum 150 words. Never output JSON."
            ),
            messages=[{
                "role": "user",
                "content": (
                    f"Here is the current agent status for brand '{brand_slug}':\n\n"
                    f"{status_context}\n\n"
                    "Please give me a brief team standup summary."
                ),
            }],
        )
        summary = resp.content[0].text
        return jsonify({"success": True, "data": {"summary": summary}})
    except Exception as exc:
        return jsonify({"success": False, "error": str(exc)}), 500


# ── Phase 5 Step 2 — Global error handler ─────────────────────────────────────

@app.errorhandler(Exception)
def handle_exception(e):
    """Return standard error envelope for any unhandled exception."""
    print(f"[GRID CONTROL] Unhandled exception: {e}")
    return jsonify({"success": False, "error": str(e)}), 500


@app.errorhandler(404)
def handle_404(e):
    return jsonify({"success": False, "error": str(e)}), 404


@app.errorhandler(405)
def handle_405(e):
    return jsonify({"success": False, "error": "Method not allowed"}), 405


# ── Phase 5 Step 3 — Session state integrity on startup ───────────────────────

def _verify_session_states() -> None:
    """For each brand in Supabase, ensure session_state has all required keys."""
    if not _DB_AVAILABLE:
        return
    required_defaults: dict = {
        "current_agent": None,
        "next_agent": "trend-researcher",
        "pipeline_status": "not_started",
        "completed_agents": [],
        "last_completed": None,
    }
    try:
        res = _db._client.table("brands").select("id, name, slug").execute()
        brands_list = res.data or []
    except Exception as e:
        print(f"[GRID CONTROL] Session verify: could not fetch brands: {e}")
        return

    for brand_row in brands_list:
        brand_id = brand_row["id"]
        brand_name = brand_row.get("name", brand_row.get("slug", ""))
        try:
            state = _db.get_session_state(brand_id) or {}
            updated = False
            for key, default in required_defaults.items():
                if key not in state:
                    state[key] = default
                    updated = True
            if updated:
                _db.upsert_session_state(brand_id, state)
            print(f"[GRID CONTROL] ✅ Session state verified for {brand_name}")
        except Exception as e:
            print(f"[GRID CONTROL] ⚠️  Session verify failed for {brand_name}: {e}")


# Run session integrity check at startup (non-blocking; log result)
try:
    _verify_session_states()
except Exception as _sv_err:
    print(f"[GRID CONTROL] Session verify error: {_sv_err}")


def _auto_refresh_intelligence() -> None:
    """
    On server startup: scan every brand folder.
    If trends_live.json is stale (>24h or never run), fire Trend Researcher in background.
    Runs once per server boot in a daemon thread — never blocks startup.
    """
    if not BRANDS_DIR.exists():
        return
    apify_key = os.getenv("APIFY_API_KEY", "").strip()
    if not apify_key:
        print("[GRID CONTROL] ℹ️  Auto-refresh skipped — APIFY_API_KEY not set")
        return

    for brand_dir in sorted(BRANDS_DIR.iterdir()):
        if not brand_dir.is_dir():
            continue
        slug = brand_dir.name
        if not _validate_brand_slug(slug):
            continue
        # Bootstrap memory if it doesn't exist yet (migration for old brands)
        mem_dir = brand_dir / "brand_memory"
        if not mem_dir.exists():
            try:
                profile_path = brand_dir / "brand_profile.json"
                profile: dict = {}
                if profile_path.exists():
                    with open(profile_path) as f:
                        profile = json.load(f)
                _bootstrap_brand_memory(brand_dir, profile)
                print(f"[GRID CONTROL] ✅ Bootstrapped memory for existing brand: {slug}")
            except Exception as e:
                print(f"[GRID CONTROL] ⚠️  Memory bootstrap failed for {slug}: {e}")

        # Fire Trend Researcher if stale
        if _intelligence_is_stale(slug, "trends_live"):
            script_path = BASE_DIR / AGENT_SCRIPTS.get("Trend Researcher", "")
            if script_path and script_path.exists():
                print(f"[GRID CONTROL] 🔄 Auto-refresh: Trend Researcher → {slug}")
                t = threading.Thread(
                    target=_run_agent_subprocess,
                    args=(str(script_path), slug, "Trend Researcher", None),
                    daemon=True,
                )
                t.start()
            else:
                print(f"[GRID CONTROL] ⚠️  Trend Researcher script not found — skipping auto-refresh for {slug}")


# Start intelligence auto-refresh on boot (non-blocking)
threading.Thread(target=_auto_refresh_intelligence, daemon=True).start()


if __name__ == "__main__":
    print("GRID CONTROL Flask API — port 5001")
    app.run(host="0.0.0.0", port=5001, debug=False)
