"""
core.py — GRID CONTROL backend foundation (extracted from dashboard_api.py, S2a).

Holds imports, constants, globals, the Flask `app`, infra hooks/errorhandlers,
and all helper functions. Routes live in dashboard_api.py (`from core import *`).
"""
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
import uuid as _uuid_mod
import shutil
import tempfile
import subprocess
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urlparse as _urlparse
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

# SG3 (Phase I uploads): hard request-body ceiling so Werkzeug rejects oversized
# bodies with 413 BEFORE the handler buffers them. 500 MB = the largest per-category
# limit (video); per-category checks in the upload handlers refine below this.
app.config["MAX_CONTENT_LENGTH"] = 500 * 1024 * 1024

# ── Rate Limiting (AgentShield) ───────────────────────────────────────────────
_rate_store: dict[str, list[float]] = {}
_RATE_STORE_MAX_KEYS = 10_000  # Prevent unbounded memory growth

def rate_limit(max_requests: int = 30, window_seconds: int = 60):
    """In-memory rate limiter per IP. Returns 429 on excess.
    Note: resets on deploy — acceptable for single-worker Railway deploy.
    Evicts stale keys when store exceeds _RATE_STORE_MAX_KEYS."""
    from functools import wraps
    def decorator(f):
        @wraps(f)
        def decorated(*args, **kwargs):
            ip = request.remote_addr or "unknown"
            now = time.time()
            key = f"{ip}:{f.__name__}"
            hits = _rate_store.get(key, [])
            hits = [t for t in hits if now - t < window_seconds]
            if len(hits) >= max_requests:
                return jsonify({"success": False, "error": "Rate limit exceeded"}), 429
            hits.append(now)
            _rate_store[key] = hits
            # Evict stale keys periodically
            if len(_rate_store) > _RATE_STORE_MAX_KEYS:
                stale = [k for k, v in _rate_store.items() if not v or now - v[-1] > window_seconds]
                for k in stale:
                    del _rate_store[k]
            return f(*args, **kwargs)
        return decorated
    return decorator

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


def _get_current_user() -> dict | None:
    """Extract and verify user from Authorization header (Bearer <JWT>).
    Returns {"id": ..., "email": ...} or None."""
    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        return None
    token = auth_header[7:]
    if not _DB_AVAILABLE:
        return None
    return _db.verify_jwt(token)


def require_auth(f):
    """Decorator — accepts Supabase JWT (Authorization: Bearer) or legacy X-Dashboard-Secret."""
    from functools import wraps
    @wraps(f)
    def decorated(*args, **kwargs):
        # Try JWT first
        user = _get_current_user()
        if user:
            request.user = user
            return f(*args, **kwargs)
        # Fall back to legacy secret
        if _DASHBOARD_SECRET:
            token = request.headers.get("X-Dashboard-Secret", "")
            if token == _DASHBOARD_SECRET:
                request.user = None
                return f(*args, **kwargs)
        return jsonify({"success": False, "error": "Unauthorized"}), 401
    return decorated


def require_brand_access(f):
    """Decorator — verifies the authenticated user has access to the requested brand.
    Must be used after require_auth. Reads brand_slug from query params.
    Deny-by-default: if user or DB is unavailable, reject the request."""
    from functools import wraps
    @wraps(f)
    def decorated(*args, **kwargs):
        user = getattr(request, "user", None)
        if not user:
            return jsonify({"success": False, "error": "Authentication required"}), 401
        if not _DB_AVAILABLE:
            return jsonify({"success": False, "error": "Database unavailable"}), 503
        brand_slug = request.args.get("brand_slug") or (request.json.get("brand_slug", "") if request.is_json else "")
        if not brand_slug:
            # No brand context — allow (some endpoints don't need brand scope)
            return f(*args, **kwargs)
        brand = _db.get_brand(brand_slug)
        if not brand:
            return jsonify({"success": False, "error": "Brand not found"}), 404
        role = _db.check_brand_access(user["id"], brand["id"])
        if not role:
            return jsonify({"success": False, "error": "No access to this brand"}), 403
        request.brand_role = role
        return f(*args, **kwargs)
    return decorated


def require_super_admin(f):
    """Decorator — only allows super_admin users. Must be used after require_auth."""
    from functools import wraps
    @wraps(f)
    def decorated(*args, **kwargs):
        user = getattr(request, "user", None)
        if not user or not _DB_AVAILABLE:
            return jsonify({"success": False, "error": "Unauthorized"}), 401
        if not _db.is_super_admin(user["id"]):
            return jsonify({"success": False, "error": "Admin access required"}), 403
        return f(*args, **kwargs)
    return decorated


def _authorize_brand(brand_slug: str):
    """Brand-scoped authorization for /api/brands/<slug>/* PATH-param routes.

    require_auth proves *authentication*; this proves *authorization* for the
    specific brand named in the URL path. The require_brand_access decorator only
    reads brand_slug from query/body, so it cannot guard path-param routes — and
    these routes query via the service-role client, which BYPASSES RLS, so this
    check is the ONLY multi-tenant boundary. Deny-by-default.

    Returns (brand_id, None) on success, or (None, (response, status)) — the
    caller does `brand_id, err = _authorize_brand(slug); if err: return err`.
    """
    if not _DB_AVAILABLE:
        return None, (jsonify(success=False, error="DB unavailable"), 503)
    brand_id = _get_brand_id(brand_slug)
    if not brand_id:
        return None, (jsonify(success=False, error="Brand not found"), 404)
    user = getattr(request, "user", None)
    if user is None:
        # require_auth already validated the legacy X-Dashboard-Secret = trusted operator
        return brand_id, None
    try:
        if _db.is_super_admin(user["id"]) or _db.check_brand_access(user["id"], brand_id):
            return brand_id, None
    except Exception:
        pass
    return None, (jsonify(success=False, error="No access to this brand"), 403)

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

# ── Phase 1 — role model, Brain guardrails, cost governance, agent config ──────
import dashboard_roles as _roles  # noqa: E402


def _grid_role_for(user, brand_slug: str) -> str:
    """Resolve the caller's grid role for a brand. Deny-by-default for unknowns."""
    if not user or not _DB_AVAILABLE:
        return _roles.MANAGED_CLIENT
    try:
        if _db.is_super_admin(user["id"]):
            return _roles.OPERATOR
        brand = _db.get_brand(brand_slug) if brand_slug else None
        brand_role = _db.check_brand_access(user["id"], brand["id"]) if brand else None
        return _roles.resolve_grid_role(False, brand_role)
    except Exception:
        return _roles.MANAGED_CLIENT


def _brain_tokens_used_today(brand_slug: str) -> int:
    """Sum brain_usage tokens for a brand for the current UTC day. 0 on any failure."""
    if not (_DB_AVAILABLE and brand_slug):
        return 0
    try:
        from datetime import datetime, timezone
        start = datetime.now(timezone.utc).strftime("%Y-%m-%dT00:00:00")
        res = (
            _db._client.table("brain_usage")
            .select("input_tokens, output_tokens")
            .eq("brand_slug", brand_slug)
            .gte("created_at", start)
            .execute()
        )
        rows = res.data or []
        return sum((r.get("input_tokens") or 0) + (r.get("output_tokens") or 0) for r in rows)
    except Exception:
        return 0

# ── SSE Event Bus — live agent activity stream ────────────────────────────────
import queue as _queue_mod

_sse_subscribers: list[_queue_mod.Queue] = []
_sse_lock = threading.Lock()


def broadcast_event(event_type: str, data: dict) -> None:
    """Push an event to all SSE subscribers. Non-blocking."""
    payload = json.dumps({"type": event_type, **data})
    with _sse_lock:
        dead = []
        for q in _sse_subscribers:
            try:
                q.put_nowait(payload)
            except _queue_mod.Full:
                dead.append(q)
        for q in dead:
            _sse_subscribers.remove(q)


# ── Audit logging middleware ──────────────────────────────────────────────────
_AUDIT_METHODS = {"POST", "PUT", "PATCH", "DELETE"}
_AUDIT_SKIP_PREFIXES = ("/api/events", "/api/health")


def _audit_async(slug, action, actor, payload):
    """Resolve brand + write audit row off the request thread (best-effort)."""
    def _w():
        try:
            brand_id = None
            if slug:
                b = _db.get_brand(slug)
                brand_id = b.get("id") if b else None
            _db.log_audit(brand_id, action, actor, payload)
        except Exception:
            pass
    threading.Thread(target=_w, daemon=True).start()


@app.after_request
def _audit_request(response):
    try:
        path = request.path or ""
        if (request.method in _AUDIT_METHODS and _DB_AVAILABLE
                and not path.startswith(_AUDIT_SKIP_PREFIXES)):
            user = getattr(request, "user", None) or {}
            actor = user.get("email") or user.get("id") or "secret"
            slug = request.args.get("brand_slug")
            if not slug and request.is_json:
                slug = (request.get_json(silent=True) or {}).get("brand_slug")
            _audit_async(slug, f"{request.method} {path}", actor,
                         {"status": response.status_code})
    except Exception:
        pass
    return response


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


# ── Per-brand secrets (brands/<slug>/.env) ─────────────────────────────────────
# Each brand's social/platform tokens live in its own .env, isolated from the
# global Grid Control .env (infra keys). Brand value wins; global is the fallback.
from dotenv import dotenv_values as _dotenv_values  # noqa: E402


def _brand_env_path(slug: str) -> Path:
    return BRANDS_DIR / slug / ".env"


def brand_env(slug: str) -> dict:
    """Load a brand's private .env as a dict ({} if none/unreadable)."""
    p = _brand_env_path(slug)
    if not slug or not p.exists():
        return {}
    try:
        return {k: (v or "") for k, v in _dotenv_values(p).items()}
    except Exception:
        return {}


def brand_token(slug: str, env_key: str) -> str:
    """Resolve a token for a brand: brand .env first, then global env fallback."""
    val = (brand_env(slug).get(env_key) or "").strip()
    return val if val else os.getenv(env_key, "").strip()


def _write_brand_env_token(slug: str, env_key: str, value: str) -> None:
    """Upsert key=value into brands/<slug>/.env (creates file/dir if needed)."""
    p = _brand_env_path(slug)
    p.parent.mkdir(parents=True, exist_ok=True)
    content = p.read_text(encoding="utf-8") if p.exists() else ""
    pattern = re.compile(rf"^{re.escape(env_key)}\s*=.*$", re.MULTILINE)
    new_line = f"{env_key}={value}"
    if pattern.search(content):
        new_content = pattern.sub(new_line, content)
    else:
        new_content = content.rstrip("\n") + ("\n" if content else "") + new_line + "\n"
    p.write_text(new_content, encoding="utf-8")

# Locked roster — exactly 9 agents in pipeline order
AGENTS = [
    {"id": 0, "name": "Trend Researcher",  "role": "Weekly trends",    "model": "claude-sonnet-4-6", "agentFile": "trend-researcher.md"},
    {"id": 1, "name": "Strategy Agent",    "role": "90-day roadmap",   "model": "claude-opus-4-8",   "agentFile": "strategy-agent.md"},
    {"id": 2, "name": "Content Planner",   "role": "30-day calendar",  "model": "claude-sonnet-4-6", "agentFile": "content-planner.md"},
    {"id": 3, "name": "Script Writer",     "role": "Scripts/captions", "model": "claude-sonnet-4-6", "agentFile": "script-writer.md"},
    {"id": 4, "name": "Creative Director", "role": "AI video/image",   "model": "claude-opus-4-8",   "agentFile": "creative-director.md"},
    {"id": 5, "name": "Ad Strategist",     "role": "Paid ads",         "model": "claude-opus-4-8",   "agentFile": "ad-strategist.md"},
    {"id": 6, "name": "Data Analyst",      "role": "Metrics",          "model": "claude-sonnet-4-6", "agentFile": "data-analyst.md"},
    {"id": 7, "name": "Funnel Specialist", "role": "Conversion",       "model": "claude-sonnet-4-6", "agentFile": "funnel-specialist.md"},
    {"id": 8, "name": "Website Agent",     "role": "Site/Railway",     "model": "claude-sonnet-4-6", "agentFile": "website-agent.md"},
    {"id": 9, "name": "Cost Tracker",      "role": "Monthly spend",    "model": "none", "agentFile": ""},
    {"id": 10, "name": "Carousel Designer", "role": "Carousel slides + PNG render", "model": "claude-sonnet-4-6", "agentFile": ""},
    {"id": 13, "name": "Community Manager", "role": "Replies/mentions",   "model": "claude-sonnet-4-6", "agentFile": ""},
    {"id": 14, "name": "DM Customer Hunter",    "role": "Inbound + warm DMs", "model": "claude-sonnet-4-6", "agentFile": ""},
    {"id": 12, "name": "Email Marketing Agent", "role": "Nurture sequences", "model": "claude-sonnet-4-6", "agentFile": ""},
]

# Phase D — single source of truth: override the display models from the gateway
# so this list can never drift from agents/model_gateway.AGENT_ROUTING.
try:
    from agents._lib.model_gateway import model_for as _model_for
    for _a in AGENTS:
        _resolved = _model_for(_a["name"])
        _a["model"] = _resolved or "none"
except Exception as _mg_err:
    print(f"[dashboard_api] model_gateway sync skipped: {_mg_err}")

# Locked slug set — any agent not in this list is filtered before response
_ACTIVE_SLUGS = {
    "trend-researcher", "strategy-agent", "content-planner", "script-writer",
    "creative-director", "ad-strategist", "data-analyst", "funnel-specialist", "website-agent",
    "cost-tracker", "carousel-designer", "community-manager", "dm-customer-hunter",
    "email-marketing-agent",
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
    "Brand Guardian":      "agents/brand_guardian.py",
    "Funnel Specialist":   "agents/funnel_specialist.py",
    "Website Agent":       "agents/website_agent.py",
    "Cost Tracker":        "agents/cost_tracker.py",
    "Carousel Designer":   "agents/carousel_designer.py",
    "Community Manager":   "agents/community_manager.py",
    "DM Customer Hunter":      "agents/dm_customer_hunter.py",
    "Email Marketing Agent":   "agents/email_marketing_agent.py",
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
    "Brand Guardian":      "brand-guardian",
    "Funnel Specialist":   "funnel-specialist",
    "Website Agent":       "website-agent",
    "Cost Tracker":        "cost-tracker",
    "Carousel Designer":   "carousel-designer",
    "Community Manager":   "community-manager",
    "DM Customer Hunter":      "dm-customer-hunter",
    "Email Marketing Agent":   "email-marketing-agent",
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

        # SSE broadcast — clients see live updates
        broadcast_event("agent_status", {
            "brand": brand_slug,
            "agent": agent_name,
            "status": status,
            "timestamp": datetime.now().isoformat(),
        })
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

    # ── Cost circuit-breaker (paid_ops) ──────────────────────────────────────────
    # Refuse to LAUNCH a paid agent when the kill-switch is off or the daily cap is
    # hit. Pure-math agents ($0, no LLM) are exempt. Fail-CLOSED: if the breaker
    # itself can't be evaluated, block (money safety > convenience).
    try:
        from agents._lib import paid_ops
        from agents._lib.model_gateway import is_pure_math
        _is_free = is_pure_math(agent_slug_key)
    except Exception as _po_imp:
        _is_free, paid_ops = False, None
        print(f"[GRID CONTROL] ⛔ paid-ops unavailable ({_po_imp}) — blocking paid launch (fail-closed)")
    if not _is_free:
        _ok, _reason = (paid_ops.check(f"agent:{agent_slug_key}") if paid_ops else (False, "paid_ops import failed"))
        if not _ok:
            print(f"[GRID CONTROL] ⛔ paid-ops: {agent_name} NOT launched — {_reason}")
            _update_session_agent_status(brand_slug, agent_name, "blocked", f"paid-ops: {_reason}")
            if _DB_AVAILABLE and db_run_id:
                try:
                    _db.update_agent_run_status(db_run_id, "blocked")
                except Exception:
                    pass
            return

    try:
        # Pass run context to agent via env so it can record costs + use memory
        agent_env = os.environ.copy()
        agent_env["GRID_RUN_ID"]     = db_run_id or ""
        agent_env["GRID_BRAND_SLUG"] = brand_slug
        # Phase B: cost_reporter writes usage_logs.agent_slug from this so the
        # billing/admin cost breakdown attributes spend to the right agent.
        agent_env["GRID_AGENT_SLUG"] = agent_slug_key
        # ACTIVE_BRAND is the env var all agent scripts read — must match GRID_BRAND_SLUG
        agent_env["ACTIVE_BRAND"]    = brand_slug
        # Overlay this brand's private secrets (platform tokens) on top of global env
        agent_env.update({k: v for k, v in brand_env(brand_slug).items() if v})
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
        # Phase L — fire approval-needed notification (best-effort, never blocks)
        try:
            _maybe_notify_pending(brand_slug)
        except Exception:
            pass
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


# ── DAILY PIPELINE RUN ─────────────────────────────────────────────────────────

def run_daily_pipeline(brand_slug: str) -> None:
    """Trend Researcher + Data Analyst (parallel) → Trend Sentinel → contradiction
    detector. Stamps session_state.last_pipeline_run on completion. Module-level so
    both the HTTP endpoint and the background scheduler reuse it."""
    def _run_one(agent_name: str, script_rel: str) -> None:
        if not script_rel:
            print(f"[daily-run] Skipping {agent_name} — no script path configured")
            return
        script_path = BASE_DIR / script_rel
        if not script_path.exists():
            print(f"[daily-run] Skipping {agent_name} — script not found: {script_path}")
            return
        print(f"[daily-run] Starting: {agent_name} for {brand_slug}")
        _run_agent_subprocess(str(script_path), brand_slug, agent_name, None)
        print(f"[daily-run] Completed: {agent_name}")

    # Phase 1: Trend Researcher + Data Analyst in parallel (independent inputs).
    t_trend = threading.Thread(target=_run_one,
                               args=("Trend Researcher", AGENT_SCRIPTS.get("Trend Researcher")), daemon=True)
    t_data = threading.Thread(target=_run_one,
                              args=("Data Analyst", AGENT_SCRIPTS.get("Data Analyst")), daemon=True)
    t_trend.start(); t_data.start(); t_trend.join(); t_data.join()
    print("[daily-run] Phase 1 complete (Trend + Data parallel)")

    # Phase 2: Trend Sentinel — needs trends_live.json from Phase 1.
    _run_one("Trend Sentinel", AGENT_SCRIPTS.get("Trend Sentinel"))

    # Auto-run contradiction detector at end of pipeline.
    try:
        sys.path.insert(0, str(BASE_DIR / "ceo_brain"))
        from contradiction_detector import detect_contradictions, save_contradictions_report
        print(f"[daily-run] Running contradiction detector for {brand_slug}...")
        report = detect_contradictions(brand_slug, project_root=BASE_DIR)
        save_contradictions_report(brand_slug, report, project_root=BASE_DIR)
        print(f"[daily-run] Contradictions: {report.get('counts', {})} | blocking: {report.get('blocking', False)}")
    except Exception as e:
        print(f"[daily-run] Contradiction check failed: {e}")

    # Stamp last_pipeline_run so the Digest can show freshness.
    try:
        ss_path = BRANDS_DIR / brand_slug / "session_state.json"
        ss = json.loads(ss_path.read_text()) if ss_path.exists() else {}
        ss["last_pipeline_run"] = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        ss_path.parent.mkdir(parents=True, exist_ok=True)
        ss_path.write_text(json.dumps(ss, indent=2))
    except Exception as e:
        print(f"[daily-run] Failed to stamp last_pipeline_run: {e}")


def _daily_scheduler_loop() -> None:
    """Opt-in (ENABLE_DAILY_SCHEDULER=1). Runs the daily pipeline once per UTC day for
    every brand with a directory. Checks hourly; skips brands already run today."""
    last_run_day: dict[str, str] = {}
    while True:
        try:
            today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
            if BRANDS_DIR.exists():
                for bdir in BRANDS_DIR.iterdir():
                    if not bdir.is_dir():
                        continue
                    slug = bdir.name
                    if last_run_day.get(slug) == today:
                        continue
                    print(f"[scheduler] Daily pipeline for {slug} ({today})")
                    try:
                        run_daily_pipeline(slug)
                    except Exception as e:
                        print(f"[scheduler] pipeline failed for {slug}: {e}")
                    last_run_day[slug] = today
        except Exception as e:
            print(f"[scheduler] loop error: {e}")
        time.sleep(3600)  # re-check hourly


if os.getenv("ENABLE_DAILY_SCHEDULER", "").strip() in ("1", "true", "True"):
    threading.Thread(target=_daily_scheduler_loop, daemon=True).start()
    print("[GRID CONTROL] ✅ Daily pipeline scheduler enabled (in-process — legacy)")


# ── Phase E1 — server-side scheduler trigger (called by the Railway worker) ────
# The dedicated APScheduler worker service (scheduler/worker.py) POSTs here on a
# cadence instead of running inside gunicorn (which would double-fire under
# --workers 2 and needs the Mac awake). Authed by a shared service token, NOT a
# user JWT.

def _valid_service_token() -> bool:
    expected = os.getenv("GRID_SCHEDULER_TOKEN", "").strip()
    if not expected:
        return False  # fail closed — no token configured = no service access
    provided = request.headers.get("X-Grid-Service-Token", "").strip()
    return bool(provided) and provided == expected


# ── Instagram publishing (the "agents post it" step) ──────────────────────────

def _read_output_json(path: Path) -> dict:
    """Read a brand output file, stripping the LOOP HEADER prefix (split on first
    '\\n---\\n') before parsing. Never returns raw JSON to the client — callers map it."""
    raw = path.read_text()
    body = raw.split("\n---\n", 1)[1] if "\n---\n" in raw else raw
    return json.loads(body)


def _find_carousel_output(brand_dir: Path, filename: str) -> Path | None:
    """Locate a carousel output in outputs/approved/ ONLY.
    K1 (Phase K): pending_approval files must NOT be publishable — approval gate
    is the only path to publication. Callers get 404 for unapproved files.
    """
    candidate = brand_dir / "outputs" / "approved" / filename
    return candidate if candidate.exists() else None


def _publish_instagram_impl(brand_slug: str, filename: str):
    """
    Core Instagram carousel publish, shared by /api/publish/instagram and the generic
    /api/publish router. Hosts slides publicly first (IG fetches images from a URL).
    Token is read from the brand's private .env (brand_token), not global env. If the
    token is live → publishes for real + returns the permalink; if absent/blocked →
    returns a 'prepared' package for manual posting. Real data only — no fake post IDs.

    Returns a (json_response, status_code) tuple.
    """
    from publishing.instagram_publisher import (
        upload_slides_to_storage, publish_carousel, token_status,
    )
    if not filename or "/" in filename or ".." in filename:
        return jsonify({"success": False, "error": "Valid carousel filename required"}), 400

    brand_dir = BRANDS_DIR / brand_slug
    src = _find_carousel_output(brand_dir, filename)
    if not src:
        return jsonify({"success": False, "error": f"Carousel '{filename}' not found in outputs/approved/. Approve it first before publishing."}), 404

    try:
        data = _read_output_json(src)
    except Exception as e:
        return jsonify({"success": False, "error": f"Could not parse carousel output: {e}"}), 500

    slide_paths = data.get("slide_image_paths") or []
    caption = data.get("post_caption") or data.get("caption") or ""
    post_id = data.get("post_id") or src.stem
    if not slide_paths:
        return jsonify({"success": False, "error": "Carousel has no slide_image_paths to publish"}), 400

    # 1. Host slides publicly (required for IG fetch — and for the manual fallback).
    try:
        slide_urls = upload_slides_to_storage(brand_slug, slide_paths, post_id)
    except Exception as e:
        return jsonify({"success": False, "error": f"Slide hosting failed: {e}"}), 502

    # 2. Decide: auto-publish vs prepare-only based on real token liveness.
    token = brand_token(brand_slug, "META_GRAPH_API_TOKEN")
    status = token_status(token)
    if not status.get("live"):
        return jsonify({"success": True, "data": {
            "platform": "instagram",
            "mode": "prepared",
            "reason": status.get("reason", "token not live"),
            "slide_urls": slide_urls,
            "caption": caption,
            "post_id": post_id,
            "note": "IG token isn't live yet — slides hosted + caption ready. Post manually, or this auto-publishes once the token works.",
        }}), 200

    # 3. Publish for real.
    result = publish_carousel(slide_urls, caption, token)
    if not result.get("published"):
        return jsonify({"success": False, "error": "Publish failed", "data": result}), 502

    # 4. Record the published post (best-effort, never blocks the response).
    try:
        published_log = brand_dir / "published_posts.json"
        log = json.loads(published_log.read_text()) if published_log.exists() else []
        log.append({
            "post_id": post_id, "platform": "instagram",
            "media_id": result.get("media_id"), "permalink": result.get("permalink"),
            "caption": caption, "slide_urls": slide_urls,
            "published_at": datetime.now().isoformat(),
        })
        published_log.write_text(json.dumps(log, indent=2))
    except Exception:
        pass

    return jsonify({"success": True, "data": {
        "platform": "instagram",
        "mode": "published",
        "media_id": result.get("media_id"),
        "permalink": result.get("permalink"),
        "post_id": post_id,
    }}), 200


# ── Generic (non-carousel) output loading + per-platform publish impls ─────────

def _find_output(brand_dir: Path, filename: str) -> Path | None:
    """Locate an output file in outputs/approved/ ONLY (direct match or rglob).
    K1 (Phase K): pending_approval files must NOT reach publishers — the approval
    gate is the ONLY path from agent output to publication. Returns None for any
    file that has not been explicitly approved.
    """
    base = brand_dir / "outputs" / "approved"
    if not base.exists():
        return None
    direct = base / filename
    if direct.exists():
        return direct
    for hit in base.rglob(filename):
        if hit.is_file():
            return hit
    return None


def _load_post_fields(src: Path) -> dict:
    """Parse an output file into the fields a publisher needs. Strips the LOOP HEADER."""
    data = _read_output_json(src)
    if not isinstance(data, dict):
        data = {}
    caption = data.get("post_caption") or data.get("caption") or ""
    body = data.get("body_text") or data.get("post_body") or data.get("script") or ""
    hashtags = data.get("hashtags") or []
    return {
        "caption": caption,
        "body": body,
        "title": data.get("title") or data.get("video_title") or "",
        "description": data.get("description") or data.get("video_description") or body or caption,
        "hashtags": hashtags,
        "video_path": data.get("video_path") or data.get("video_file") or "",
        "post_id": data.get("post_id") or src.stem,
    }


def _compose_social_text(fields: dict, prefer: str = "body") -> str:
    """Build the post text: prefer body_text (long form) or caption, then append hashtags."""
    primary = (fields.get(prefer) or fields.get("caption") or fields.get("body") or "").strip()
    tags = fields.get("hashtags") or []
    if tags:
        tag_line = " ".join(t if t.startswith("#") else f"#{t}" for t in tags)
        primary = f"{primary}\n\n{tag_line}".strip()
    return primary


def _record_published(brand_dir: Path, entry: dict) -> None:
    """Append to brands/<slug>/published_posts.json. Best-effort, never raises."""
    try:
        log_path = brand_dir / "published_posts.json"
        log = json.loads(log_path.read_text()) if log_path.exists() else []
        entry.setdefault("published_at", datetime.now().isoformat())
        log.append(entry)
        log_path.write_text(json.dumps(log, indent=2))
    except Exception:
        pass


def _publish_linkedin_impl(brand_slug: str, filename: str):
    """Publish an approved text post to LinkedIn as the member (w_member_social)."""
    from publishing.linkedin_publisher import token_status, publish_text
    brand_dir = BRANDS_DIR / brand_slug
    src = _find_output(brand_dir, filename)
    if not src:
        return jsonify({"success": False, "error": f"Output '{filename}' not found"}), 404
    fields = _load_post_fields(src)
    text = _compose_social_text(fields, prefer="body")
    if not text:
        return jsonify({"success": False, "error": "No text to post (empty body and caption)"}), 400

    token = brand_token(brand_slug, "LINKEDIN_ACCESS_TOKEN")
    urn = brand_token(brand_slug, "LINKEDIN_URN")
    status = token_status(token, urn)
    if not status.get("live"):
        return jsonify({"success": True, "data": {
            "platform": "linkedin", "mode": "prepared", "reason": status.get("reason", "token not live"),
            "text": text, "post_id": fields["post_id"],
            "note": "LinkedIn token isn't live — text ready. Post manually, or this auto-publishes once the token works.",
        }}), 200

    result = publish_text(token, urn, text)
    if not result.get("published"):
        return jsonify({"success": False, "error": "Publish failed", "data": result}), 502
    _record_published(brand_dir, {
        "post_id": fields["post_id"], "platform": "linkedin",
        "post_urn": result.get("post_urn"), "permalink": result.get("permalink"), "text": text,
    })
    return jsonify({"success": True, "data": {
        "platform": "linkedin", "mode": "published",
        "permalink": result.get("permalink"), "post_id": fields["post_id"],
    }}), 200


def _publish_twitter_impl(brand_slug: str, filename: str):
    """Publish an approved text post to X via OAuth 1.0a (4 keys from brand .env)."""
    from publishing.twitter_publisher import token_status, publish_text
    brand_dir = BRANDS_DIR / brand_slug
    src = _find_output(brand_dir, filename)
    if not src:
        return jsonify({"success": False, "error": f"Output '{filename}' not found"}), 404
    fields = _load_post_fields(src)
    text = _compose_social_text(fields, prefer="caption")
    if not text:
        return jsonify({"success": False, "error": "No text to post (empty caption and body)"}), 400

    keys = (
        brand_token(brand_slug, "TWITTER_API_KEY"),
        brand_token(brand_slug, "TWITTER_API_SECRET"),
        brand_token(brand_slug, "TWITTER_ACCESS_TOKEN"),
        brand_token(brand_slug, "TWITTER_ACCESS_SECRET"),
    )
    status = token_status(*keys)
    if not status.get("live"):
        return jsonify({"success": True, "data": {
            "platform": "twitter", "mode": "prepared", "reason": status.get("reason", "keys not live"),
            "text": text, "post_id": fields["post_id"],
            "note": "X keys aren't live — text ready. Post manually, or this auto-publishes once the keys work.",
        }}), 200
    if not status.get("write", True):
        return jsonify({"success": True, "data": {
            "platform": "twitter", "mode": "prepared", "reason": "read_only_app",
            "text": text, "post_id": fields["post_id"],
            "note": "X app is read-only — enable Read+Write and regenerate the access token to post.",
        }}), 200

    result = publish_text(*keys, text)
    if not result.get("published"):
        return jsonify({"success": False, "error": "Publish failed", "data": result}), 502
    _record_published(brand_dir, {
        "post_id": fields["post_id"], "platform": "twitter",
        "tweet_id": result.get("tweet_id"), "permalink": result.get("permalink"), "text": text,
    })
    return jsonify({"success": True, "data": {
        "platform": "twitter", "mode": "published",
        "permalink": result.get("permalink"), "post_id": fields["post_id"],
    }}), 200


def _publish_youtube_impl(brand_slug: str, filename: str):
    """Upload an approved video to YouTube via OAuth refresh token. Requires a REAL
    video file — returns 'needs_video' if none, never fabricates an upload."""
    from publishing.youtube_publisher import token_status, upload_video
    brand_dir = BRANDS_DIR / brand_slug
    src = _find_output(brand_dir, filename)
    if not src:
        return jsonify({"success": False, "error": f"Output '{filename}' not found"}), 404
    fields = _load_post_fields(src)

    client_id = brand_token(brand_slug, "YOUTUBE_CLIENT_ID")
    client_secret = brand_token(brand_slug, "YOUTUBE_CLIENT_SECRET")
    refresh_token = brand_token(brand_slug, "YOUTUBE_REFRESH_TOKEN")
    status = token_status(client_id, client_secret, refresh_token)

    # Resolve video path (relative to project root if not absolute).
    video_path = fields["video_path"]
    if video_path and not os.path.isabs(video_path):
        video_path = str((BASE_DIR / video_path).resolve())

    if not status.get("live"):
        return jsonify({"success": True, "data": {
            "platform": "youtube", "mode": "prepared", "reason": status.get("reason", "oauth not live"),
            "title": fields["title"], "post_id": fields["post_id"],
            "note": "YouTube OAuth isn't live — re-run publishing/youtube_oauth.py. Nothing uploaded.",
        }}), 200

    result = upload_video(
        client_id, client_secret, refresh_token,
        video_path, fields["title"], fields["description"], fields["hashtags"],
    )
    if result.get("mode") == "needs_video":
        return jsonify({"success": True, "data": {
            "platform": "youtube", "mode": "needs_video",
            "title": fields["title"], "post_id": fields["post_id"],
            "note": result.get("note"), "error": result.get("error"),
        }}), 200
    if not result.get("published"):
        return jsonify({"success": False, "error": "Upload failed", "data": result}), 502
    _record_published(brand_dir, {
        "post_id": fields["post_id"], "platform": "youtube",
        "video_id": result.get("video_id"), "permalink": result.get("permalink"), "title": fields["title"],
    })
    return jsonify({"success": True, "data": {
        "platform": "youtube", "mode": "published",
        "permalink": result.get("permalink"), "post_id": fields["post_id"],
    }}), 200


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


# ── Outputs ───────────────────────────────────────────────────────────────────

def _strip_markdown(text: str) -> str:
    """Remove markdown syntax for clean plain-English display in the UI.
    Strips: # headers, **bold**, *italic*, `code`, [link](url)→link.
    """
    import re as _re
    if not text:
        return ""
    # Remove leading hashes (## headers)
    text = _re.sub(r"^#{1,6}\s+", "", text, flags=_re.MULTILINE)
    # Remove bold/italic markers
    text = _re.sub(r"\*\*([^*]+)\*\*", r"\1", text)
    text = _re.sub(r"\*([^*]+)\*", r"\1", text)
    text = _re.sub(r"__([^_]+)__", r"\1", text)
    text = _re.sub(r"_([^_]+)_", r"\1", text)
    # Inline code
    text = _re.sub(r"`([^`]+)`", r"\1", text)
    # Links: [label](url) → label
    text = _re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", text)
    return text.strip()


def _extract_output_meta(agent_slug: str, data: dict) -> dict:
    """Pull human-readable meta + media paths from an agent JSON output.

    Returns dict with keys: title, platform, caption, body_text, slide_images,
    hashtags, scheduled_for. All optional (None/empty if missing).
    """
    if not isinstance(data, dict):
        return {}

    out: dict = {
        "title": None,
        "platform": None,
        "caption": None,
        "body_text": None,
        "slide_images": [],
        "hashtags": [],
        "scheduled_for": None,
    }

    # Carousel Designer
    if "carousel" in agent_slug:
        out["title"] = data.get("topic") or data.get("post_id")
        out["platform"] = data.get("platform")
        out["caption"] = data.get("post_caption")
        out["slide_images"] = data.get("slide_image_paths", []) or []
        out["scheduled_for"] = data.get("scheduled_for")

    # Script Writer
    elif "script" in agent_slug:
        scripts = data.get("scripts") or []
        if scripts:
            first = scripts[0] if isinstance(scripts[0], dict) else {}
            inner = first.get("script", first)
            out["title"] = inner.get("title") or inner.get("hook") or inner.get("topic") or "Script"
            out["platform"] = inner.get("platform") or first.get("platform")
            # Compose body from beats / body / hook+body+cta
            parts = []
            for k in ("hook", "beat_1", "beat_2", "beat_3", "body", "cta"):
                v = inner.get(k)
                if isinstance(v, str) and v:
                    parts.append(v)
                elif isinstance(v, dict) and v.get("text"):
                    parts.append(v["text"])
            out["body_text"] = "\n\n".join(parts) if parts else None
            out["caption"] = inner.get("caption")

    # Content Planner / Strategy / Trend / etc — surface a usable title + summary
    else:
        out["title"] = (
            data.get("topic")
            or data.get("title")
            or data.get("hook")
            or data.get("summary", "")[:80]
            or None
        )
        out["caption"] = data.get("summary") or data.get("description") or data.get("overall_decision")
        out["platform"] = data.get("platform")

    # Hashtags (any agent)
    h = data.get("hashtags")
    if isinstance(h, list):
        out["hashtags"] = h
    elif isinstance(h, str):
        out["hashtags"] = [t for t in h.split() if t.startswith("#")]

    return out


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
    "community-manager": "Community Manager",
    "dm-customer-hunter": "DM Customer Hunter",
    "email-marketing-agent": "Email Marketing Agent",
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


# ── Skill learning hooks ─────────────────────────────────────────────────────

_SLUG_TO_AGENT_NAME = {v: k for k, v in _FOLDER_TO_SLUG.items()}

def _skill_on_approve(brand_slug: str, agent_slug: str, filepath: str):
    """Extract approved output as a learned skill (fire-and-forget)."""
    try:
        from agents._lib.base_agent import BaseAgent
        agent_name = _SLUG_TO_AGENT_NAME.get(agent_slug, agent_slug)
        agent = BaseAgent(agent_name)
        src = Path(filepath)
        if not src.exists():
            return
        content = src.read_text(encoding="utf-8")[:2000]
        filename = src.stem
        agent.extract_skill_on_approval(
            brand_slug=brand_slug,
            skill_name=f"approved-{filename}",
            pattern=f"Approved output ({filename}):\n{content}",
            tags=["auto-extracted", "approved"],
        )
    except Exception as e:
        print(f"[skill-learn] approve extraction failed: {e}")

def _skill_on_reject(brand_slug: str, agent_slug: str, reason: str):
    """Patch agent skill with rejection lesson (fire-and-forget)."""
    try:
        from agents._lib.base_agent import BaseAgent
        agent_name = _SLUG_TO_AGENT_NAME.get(agent_slug, agent_slug)
        agent = BaseAgent(agent_name)
        skills_dir = agent._skills_dir(brand_slug)
        if not skills_dir.exists() or not list(skills_dir.glob("*.md")):
            agent.save_skill(
                brand_slug=brand_slug,
                skill_name="rejection-lessons",
                content=f"### Rejection ({datetime.now().strftime('%Y-%m-%d')})\n{reason}",
                tags=["rejection", "lesson"],
            )
        else:
            latest = sorted(skills_dir.glob("*.md"))[-1]
            agent.patch_skill(brand_slug, latest.stem, reason)
    except Exception as e:
        print(f"[skill-learn] rejection patch failed: {e}")


def _resolve_output_file(filepath_param: str) -> Path | None:
    """
    Resolve a filepath parameter to an absolute path, searching both
    BASE_DIR/outputs/ (legacy) and BASE_DIR/brands/*/outputs/ (current).
    Returns None if the path escapes the project root or doesn't exist.
    """
    import urllib.parse
    decoded = urllib.parse.unquote(filepath_param)
    # SECURITY: confine to output/visual directories ONLY. A bare startswith(BASE_DIR)
    # check is insufficient — .env, .git, and source files live under BASE_DIR too and
    # were downloadable via path params. Build the allowed-roots whitelist explicitly.
    allowed_roots = [(BASE_DIR / "outputs").resolve()]
    if BRANDS_DIR.exists():
        for _bdir in BRANDS_DIR.iterdir():
            if _bdir.is_dir():
                allowed_roots.append((_bdir / "outputs").resolve())
                allowed_roots.append((_bdir / "visuals").resolve())
    # Reject dotfiles / secrets outright regardless of location
    if Path(decoded).name.lower().startswith(".env") or ".git" in Path(decoded).parts:
        return None
    # Try as relative to BASE_DIR first (filepath may already include brands/...)
    candidate = (BASE_DIR / decoded).resolve()
    if candidate.is_file() and any(
        str(candidate).startswith(str(root)) for root in allowed_roots
    ):
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


# ── The Brain (Claude chat embedded in GRID CONTROL) ─────────────────────────

# In-memory rate limiting for client Brain chat (resets on server restart)
_brain_rate_counts: dict = {}

# Tool definitions for Claude — read tools auto-execute, write tools require approval.
BRAIN_TOOLS_DEF = [
    {
        "name": "read_file",
        "description": "Read a text file inside the project (auto-executes, no approval needed). Path must be relative to project root and stay within brands/, agents/, or top-level config files. Returns first 8KB.",
        "input_schema": {
            "type": "object",
            "properties": {"path": {"type": "string", "description": "Relative file path"}},
            "required": ["path"],
        },
    },
    {
        "name": "list_dir",
        "description": "List files in a project directory (auto-executes, no approval needed).",
        "input_schema": {
            "type": "object",
            "properties": {"path": {"type": "string", "description": "Relative directory path"}},
            "required": ["path"],
        },
    },
    {
        "name": "propose_edit",
        "description": "Propose a file edit. Returned to user for approval — does NOT execute. User clicks Approve in the UI to apply.",
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "Relative file path"},
                "old_string": {"type": "string", "description": "Exact text to find"},
                "new_string": {"type": "string", "description": "Replacement text"},
                "rationale": {"type": "string", "description": "Why this change"},
            },
            "required": ["path", "old_string", "new_string", "rationale"],
        },
    },
    {
        "name": "propose_bash",
        "description": "Propose a shell command. Returned to user for approval — does NOT execute. User clicks Approve to run.",
        "input_schema": {
            "type": "object",
            "properties": {
                "command": {"type": "string", "description": "Shell command"},
                "rationale": {"type": "string", "description": "Why this command"},
            },
            "required": ["command", "rationale"],
        },
    },
]


def _brain_safe_path(rel_path: str) -> Path | None:
    """Resolve a relative path safely under BASE_DIR. Returns None if outside or hidden."""
    try:
        p = (BASE_DIR / rel_path).resolve()
        if BASE_DIR.resolve() not in p.parents and p != BASE_DIR.resolve():
            return None
        # Block .git, .env, secrets
        parts = {part.lower() for part in p.parts}
        if ".git" in parts or ".env" in [p.name.lower()] or "secrets" in parts:
            return None
        return p
    except Exception:
        return None


def _brain_execute_read_tool(name: str, args: dict) -> dict:
    """Execute auto-approved read-only tools. Returns dict with 'output' or 'error'."""
    if name == "read_file":
        path = args.get("path", "")
        p = _brain_safe_path(path)
        if not p or not p.exists() or not p.is_file():
            return {"error": f"Path not accessible: {path}"}
        try:
            return {"output": p.read_text(errors="replace")[:8000]}
        except Exception as e:
            return {"error": str(e)}
    if name == "list_dir":
        path = args.get("path", "")
        p = _brain_safe_path(path)
        if not p or not p.exists() or not p.is_dir():
            return {"error": f"Directory not accessible: {path}"}
        try:
            entries = sorted(
                f"{x.name}/" if x.is_dir() else x.name
                for x in p.iterdir()
                if not x.name.startswith(".")
            )[:100]
            return {"output": "\n".join(entries)}
        except Exception as e:
            return {"error": str(e)}
    return {"error": f"Unknown read tool: {name}"}


def _build_brain_agent_summary(brand_slug: str, agent_slug: str) -> str:
    """Agent-scoped context: role, recent outputs, last run.

    Used when The Brain is in per-agent scope (clicking Chat on an agent card).
    """
    if not brand_slug or not agent_slug:
        return ""

    # Find agent role from registry
    agent_name = ""
    agent_role = ""
    for a in AGENTS:  # type: ignore[name-defined]
        if a.get("name", "").lower().replace(" ", "-").replace("+", "-") == agent_slug:
            agent_name = a.get("name", agent_slug)
            agent_role = a.get("role", "")
            break

    parts: list[str] = [
        f"AGENT SCOPE: {agent_name or agent_slug}",
        f"ROLE: {agent_role}" if agent_role else "",
    ]

    # Last 3 output filenames + first 200 chars of latest output
    out_dir = BASE_DIR / "brands" / brand_slug / "outputs" / "pending_approval" / agent_slug
    if out_dir.exists():
        files = sorted([f for f in out_dir.iterdir() if f.is_file()], key=lambda p: p.stat().st_mtime, reverse=True)
        if files:
            recent = files[:3]
            parts.append("RECENT OUTPUTS (pending):")
            for f in recent:
                parts.append(f"  · {f.name}")
            try:
                latest_preview = recent[0].read_text(errors="replace")[:600]
                parts.append(f"\nLATEST OUTPUT PREVIEW ({recent[0].name}):\n{latest_preview}")
            except Exception:
                pass

    # Pull persisted learnings for this agent on this brand
    try:
        import sys as _sys
        agents_dir = str(BASE_DIR / "agents")
        if agents_dir not in _sys.path:
            _sys.path.insert(0, agents_dir)
        from agents._lib._learnings import render_recent_for_prompt  # type: ignore
        learnings_block = render_recent_for_prompt(brand_slug, n=8, agent_filter=agent_slug)
        if learnings_block:
            parts.append(learnings_block)
    except Exception:
        pass

    parts.append(
        "Brain rules in this scope: answer specifically about THIS agent. "
        "Use propose_bash to run the agent (e.g., python3 agents/<file>.py). "
        "Use propose_edit to modify its outputs."
    )
    return "\n".join([p for p in parts if p])


def _build_brain_brand_summary(brand_slug: str) -> str:
    """Slim brand context for The Brain — uses agents._lib._state compact summary.

    Brain has read_file tool, so full files are accessible on demand.
    """
    if not brand_slug:
        return "(no brand selected)"

    try:
        # Use the same compact state the agents read — no duplicate logic.
        import sys
        agents_dir = str(BASE_DIR / "agents")
        if agents_dir not in sys.path:
            sys.path.insert(0, agents_dir)
        from agents._lib._state import load_brand_state  # type: ignore
        state = load_brand_state(brand_slug)
        # Render as readable JSON-ish block (already only ~4KB).
        return json.dumps(state, ensure_ascii=False, indent=2)[:6000]
    except Exception as e:
        return f"(failed to load state for {brand_slug}: {e})"


# ── Connections — Save Token ───────────────────────────────────────────────────

# Mapping from platform name → .env variable name
_PLATFORM_ENV_MAP: dict[str, str] = {
    "instagram": "META_GRAPH_API_TOKEN",
    "meta":      "META_GRAPH_API_TOKEN",
    "linkedin":  "LINKEDIN_ACCESS_TOKEN",
    "youtube":   "YOUTUBE_API_KEY",
    "twitter":   "TWITTER_BEARER_TOKEN",
    "x":         "TWITTER_BEARER_TOKEN",
    "tiktok":    "TIKTOK_ACCESS_TOKEN",
    "whatsapp":  "WHATSAPP_ACCESS_TOKEN",
}

# Social platforms surfaced on the per-brand Connections page (in display order).
_SOCIAL_PLATFORMS = ["instagram", "linkedin", "youtube", "twitter", "tiktok"]


def _verify_social(platform: str, token: str) -> dict:
    """Live-verify one social platform token. Returns {connected, account}.
    Never raises; never returns the token."""
    import requests as _req
    if not token:
        return {"connected": False, "account": "Not connected"}
    try:
        if platform in ("instagram", "meta"):
            # Instagram Login (IGAA…) tokens validate on graph.instagram.com; classic
            # Graph tokens on graph.facebook.com. Try both.
            r = _req.get(f"https://graph.instagram.com/me?fields=username&access_token={token}", timeout=5)
            if r.status_code == 200:
                return {"connected": True, "account": "@" + (r.json().get("username") or "")}
            r = _req.get(f"https://graph.facebook.com/me?fields=name&access_token={token}", timeout=5)
            if r.status_code == 200:
                return {"connected": True, "account": r.json().get("name") or "Connected"}
            return {"connected": False, "account": f"Token invalid ({r.status_code})"}
        if platform == "linkedin":
            # OpenID Connect token (openid/profile scopes) → /v2/userinfo
            r = _req.get("https://api.linkedin.com/v2/userinfo",
                         headers={"Authorization": f"Bearer {token}"}, timeout=5)
            if r.status_code == 200:
                d = r.json()
                return {"connected": True, "account": d.get("name") or d.get("email") or "Connected"}
            # Fallback for older r_liteprofile tokens
            r2 = _req.get("https://api.linkedin.com/v2/me",
                          headers={"Authorization": f"Bearer {token}"}, timeout=5)
            if r2.status_code == 200:
                d = r2.json()
                name = f"{d.get('localizedFirstName','')} {d.get('localizedLastName','')}".strip()
                return {"connected": True, "account": name or "Connected"}
            return {"connected": False, "account": f"Token invalid ({r.status_code})"}
        if platform == "youtube":
            r = _req.get(f"https://www.googleapis.com/youtube/v3/channels?part=snippet&mine=true&access_token={token}", timeout=5)
            if r.status_code == 200:
                items = r.json().get("items", [])
                title = items[0]["snippet"]["title"] if items else "Key valid"
                return {"connected": True, "account": title}
            # Fall back to API-key validity probe
            r2 = _req.get(f"https://www.googleapis.com/youtube/v3/channels?part=id&forHandle=AskGauravAI&key={token}", timeout=5)
            if r2.status_code == 200:
                return {"connected": True, "account": "API key valid"}
            return {"connected": False, "account": f"Invalid ({r.status_code})"}
        if platform in ("twitter", "x"):
            r = _req.get("https://api.twitter.com/2/users/me",
                         headers={"Authorization": f"Bearer {token}"}, timeout=5)
            if r.status_code == 200:
                d = r.json().get("data", {})
                return {"connected": True, "account": "@" + (d.get("username") or d.get("name") or "")}
            if r.status_code in (403, 429):
                return {"connected": True, "account": "Token set (Free tier)"}
            return {"connected": False, "account": f"Token invalid ({r.status_code})"}
        if platform == "tiktok":
            r = _req.get("https://open.tiktokapis.com/v2/user/info/?fields=display_name",
                         headers={"Authorization": f"Bearer {token}"}, timeout=5)
            if r.status_code == 200:
                d = r.json().get("data", {}).get("user", {})
                return {"connected": True, "account": d.get("display_name") or "Connected"}
            return {"connected": False, "account": f"Token invalid ({r.status_code})"}
    except Exception as e:
        return {"connected": False, "account": f"Error: {type(e).__name__}"}
    return {"connected": bool(token), "account": "Token set"}


def _verify_twitter_oauth(benv: dict) -> dict:
    """Verify X OAuth 1.0a user credentials (post-capable). Returns {connected,
    account} with a write/read-only note from the x-access-level header."""
    keys = ["TWITTER_API_KEY", "TWITTER_API_SECRET", "TWITTER_ACCESS_TOKEN", "TWITTER_ACCESS_SECRET"]
    vals = [(benv.get(k) or "").strip() for k in keys]
    if not all(vals):
        return {"connected": False, "account": "OAuth keys incomplete"}
    try:
        from requests_oauthlib import OAuth1Session
        auth = OAuth1Session(*vals)
        r = auth.get("https://api.twitter.com/1.1/account/verify_credentials.json", timeout=6)
        if r.status_code == 200:
            handle = r.json().get("screen_name", "")
            level = r.headers.get("x-access-level", "")
            tag = " · write" if "write" in level else " · read-only"
            return {"connected": True, "account": f"@{handle}{tag}"}
        return {"connected": False, "account": f"Invalid ({r.status_code})"}
    except Exception as e:
        return {"connected": False, "account": f"Error: {type(e).__name__}"}


def _verify_youtube_oauth(benv: dict) -> dict:
    """Verify a YouTube OAuth connection: mint an access token from the refresh
    token and fetch the channel title. Returns {connected, account}."""
    import requests as _req
    refresh = (benv.get("YOUTUBE_REFRESH_TOKEN") or "").strip()
    cid     = (benv.get("YOUTUBE_CLIENT_ID") or "").strip()
    secret  = (benv.get("YOUTUBE_CLIENT_SECRET") or "").strip()
    if not (refresh and cid and secret):
        return {"connected": False, "account": "OAuth incomplete"}
    try:
        tok = _req.post("https://oauth2.googleapis.com/token", data={
            "client_id": cid, "client_secret": secret,
            "refresh_token": refresh, "grant_type": "refresh_token",
        }, timeout=6)
        if tok.status_code != 200:
            return {"connected": False, "account": f"Refresh failed ({tok.status_code})"}
        access = tok.json().get("access_token", "")
        ch = _req.get(
            "https://www.googleapis.com/youtube/v3/channels?part=snippet&mine=true",
            headers={"Authorization": f"Bearer {access}"}, timeout=6)
        if ch.status_code == 200:
            items = ch.json().get("items", [])
            title = items[0]["snippet"]["title"] if items else "Connected (no channel)"
            return {"connected": True, "account": title}
        return {"connected": False, "account": f"Channel lookup failed ({ch.status_code})"}
    except Exception as e:
        return {"connected": False, "account": f"Error: {type(e).__name__}"}

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


# Intelligence auto-refresh — OPT-IN ONLY (default OFF).
# WHY: this used to fire on every module import. Because boot-checks, tooling, and
# every Railway redeploy `import dashboard_api`, each import spawned Trend Researcher
# for ALL brands → paid apify/instagram-scraper runs + Claude analysis. With no
# in-flight lock and a ~2-min run, rapid imports stacked and burned Apify + Claude
# credits (diagnosed Jun 15 2026). Periodic refresh now belongs to the scheduler
# (Phase E), which respects a real schedule. Set GRID_AUTO_REFRESH=1 to re-enable
# boot-time refresh deliberately (e.g. on the prod web service only).
if os.getenv("GRID_AUTO_REFRESH", "").strip() == "1":
    threading.Thread(target=_auto_refresh_intelligence, daemon=True).start()
else:
    print("[GRID CONTROL] ℹ️  Boot auto-refresh OFF (set GRID_AUTO_REFRESH=1 to enable; scheduler handles periodic refresh)")


# ============================================================
# BILLING — Razorpay Subscriptions
# ============================================================
sys.path.insert(0, str(Path(__file__).parent / "billing"))
try:
    from billing import razorpay_client as _rz
    _razorpay_ok = _rz.is_configured()
except Exception:
    _razorpay_ok = False


def _resolve_brand_id(slug_or_id: str) -> str | None:
    """Resolve a brand_slug to its UUID brand_id. Pass-through if already a UUID."""
    if not slug_or_id:
        return None
    # If it looks like a UUID, return as-is
    if len(slug_or_id) == 36 and "-" in slug_or_id:
        return slug_or_id
    try:
        rows = _db._client.table("brands").select("id").eq("slug", slug_or_id).limit(1).execute()
        return rows.data[0]["id"] if rows.data else None
    except Exception:
        return None


# ── Phase H — Brand-Book sign-off gate ───────────────────────────────────────
# H1: generate → pending_review → approve / request-change (K3 revision cap)
# H2: approve writes Foundation → brand_profile.json + voice_profile.json + narrative

BRAND_BOOK_REVISION_CAP = 3  # K3: after this many change requests, flag as scope-creep


def _brand_book_status(brand_slug: str) -> dict:
    """Read brand-book gate fields from brand_profile.json. Safe: returns defaults if missing."""
    profile_path = BRANDS_DIR / brand_slug / "brand_profile.json"
    if not profile_path.exists():
        return {"status": "none", "revision_count": 0, "scope_flag": False, "latest_path": None}
    try:
        with open(profile_path) as f:
            bp = json.load(f)
        return {
            "status":         bp.get("brand_book_status", "none"),
            "revision_count": bp.get("brand_book_revision_count", 0),
            "scope_flag":     bp.get("brand_book_scope_flag", False),
            "latest_path":    bp.get("brand_book_latest_path"),
            "approved_ts":    bp.get("brand_book_approved_ts"),
        }
    except Exception:
        return {"status": "none", "revision_count": 0, "scope_flag": False, "latest_path": None}


def _update_brand_profile_fields(brand_slug: str, updates: dict) -> None:
    """Merge `updates` into brand_profile.json (last-write wins per field)."""
    profile_path = BRANDS_DIR / brand_slug / "brand_profile.json"
    bp = {}
    if profile_path.exists():
        try:
            with open(profile_path) as f:
                bp = json.load(f)
        except Exception:
            pass
    bp.update(updates)
    with open(profile_path, "w") as f:
        json.dump(bp, f, indent=2)


def _write_foundation(brand_slug: str, foundation: dict) -> None:
    """H2: merge approved Foundation block into brand_profile.json + write voice_profile.json."""
    if not foundation or foundation.get("_unparsed"):
        return
    # brand_profile fields
    bp_updates = {}
    if foundation.get("positioning_statement"):
        bp_updates["positioning_statement"] = foundation["positioning_statement"]
    if foundation.get("value_prop"):
        bp_updates["value_prop"] = foundation["value_prop"]
    if foundation.get("pillars"):
        bp_updates["messaging_pillars"] = foundation["pillars"]
    if foundation.get("icp"):
        bp_updates["icp"] = foundation["icp"]
    if foundation.get("north_star"):
        bp_updates["north_star_90d"] = foundation["north_star"]
    if bp_updates:
        _update_brand_profile_fields(brand_slug, bp_updates)
    # voice_profile.json
    voice = foundation.get("voice") or {}
    if voice:
        vp_path = BRANDS_DIR / brand_slug / "voice_profile.json"
        existing_vp = {}
        if vp_path.exists():
            try:
                with open(vp_path) as f:
                    existing_vp = json.load(f)
            except Exception:
                pass
        existing_vp.update({
            "personality": voice.get("personality", existing_vp.get("personality", "")),
            "do":          voice.get("do", existing_vp.get("do", [])),
            "dont":        voice.get("dont", existing_vp.get("dont", [])),
            "vocab_use":   voice.get("vocab_use", existing_vp.get("vocab_use", [])),
            "vocab_avoid": voice.get("vocab_avoid", existing_vp.get("vocab_avoid", [])),
            "source":      "brand_book_v7_approved",
        })
        with open(vp_path, "w") as f:
            json.dump(existing_vp, f, indent=2)


def _run_brand_book_generate(brand_slug: str, mode: str = "onboarding") -> None:
    """Background thread: run brand-book v7 generate(), update brand_profile status when done.
    `mode` is kept for caller compatibility; v7 is a single brand-centered onboarding audit."""
    try:
        import sys
        if str(BASE_DIR) not in sys.path:
            sys.path.insert(0, str(BASE_DIR))
        from agents.brand_book_v7 import generate as _generate_brand_book
        result = _generate_brand_book(brand_slug, render_pdf=True)
        # generate() returns the report DICT; the written-file path is in _output_path.
        latest_path = result.get("_output_path") if isinstance(result, dict) else None
        _update_brand_profile_fields(brand_slug, {
            "brand_book_status":      "pending_review",
            "brand_book_latest_path": latest_path,
        })
    except Exception as e:
        _update_brand_profile_fields(brand_slug, {
            "brand_book_status": "error",
            "brand_book_error":  str(e),
        })
        print(f"[brand-book] generate failed for {brand_slug}: {e}")


# ─────────────────────────────────────────────────────────────────────────────
# Phase I — Upload surfaces
#   I-a: Brand-asset ingestion (direct file + cloud link reference)
#   I-b: Per-content-card production upload → routes to creative-director queue
# ─────────────────────────────────────────────────────────────────────────────

# Extension → asset category map.
# SG3: .svg deliberately EXCLUDED — it is an active-content format (can embed
# <script>) and is a stored-XSS vector if assets are ever served inline same-origin.
_ASSET_EXT_MAP: dict[str, str] = {
    **{ext: "image"    for ext in (".jpg", ".jpeg", ".png", ".gif", ".webp")},
    **{ext: "video"    for ext in (".mp4", ".mov", ".avi", ".webm", ".mkv")},
    **{ext: "document" for ext in (".pdf", ".docx", ".doc", ".txt", ".md", ".csv")},
    **{ext: "audio"    for ext in (".mp3", ".wav", ".m4a", ".aac", ".ogg")},
}
_ASSET_MAX_BYTES: dict[str, int] = {
    "image":    10  * 1024 * 1024,   # 10 MB
    "video":    500 * 1024 * 1024,   # 500 MB
    "document": 20  * 1024 * 1024,   # 20 MB
    "audio":    100 * 1024 * 1024,   # 100 MB
}
# Allowed cloud-storage domains for link ingestion (SSRF guard — deny everything else)
_ASSET_CLOUD_DOMAINS = frozenset({
    "drive.google.com", "docs.google.com",
    "dropbox.com",
    "onedrive.live.com", "1drv.ms", "sharepoint.com",
})


def _asset_dir(brand_slug: str, sub: str = "") -> Path:
    d = BRANDS_DIR / brand_slug / "assets"
    if sub:
        d = d / sub
    d.mkdir(parents=True, exist_ok=True)
    return d


def _manifest_path(brand_slug: str) -> Path:
    return BRANDS_DIR / brand_slug / "assets" / "manifest.json"


def _read_manifest(brand_slug: str) -> list:
    p = _manifest_path(brand_slug)
    if not p.exists():
        return []
    try:
        return json.loads(p.read_text())
    except Exception:
        return []


def _write_manifest(brand_slug: str, entries: list) -> None:
    p = _manifest_path(brand_slug)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(entries, indent=2))


def _safe_fname(name: str) -> str:
    """Strip path components and replace shell-unsafe chars."""
    name = Path(name).name
    return re.sub(r"[^\w.\-]", "_", name) or "upload"


def _safe_card_id(card_id: str) -> bool:
    """SG4: card ids are used to build asset paths (production/{card_id}/...).
    Flask's <card_id> converter already blocks '/', but enforce a strict charset
    so a bare '..' or odd token can never shape a path segment. Alphanumerics,
    dash, underscore only, max 64 chars."""
    return bool(re.match(r"^[A-Za-z0-9_-]{1,64}$", card_id or ""))


def _classify_ext(suffix: str) -> str:
    cat = _ASSET_EXT_MAP.get(suffix.lower())
    if not cat:
        raise ValueError(f"File type '{suffix}' is not allowed.")
    return cat


def _ssrf_check(url: str) -> bool:
    """True only for an http(s) link to an allowlisted cloud-storage host.

    Uses .hostname (NOT .netloc): hostname strips userinfo and port, so the
    credentials-in-URL trick `https://drive.google.com@evil.com/` resolves to
    its REAL host (evil.com) and is rejected. Allowlist + exact/sub-domain
    match only — deny by default. No fetch happens here (SG3: any future fetch
    path must re-clear this gate).
    """
    try:
        parts = _urlparse(url)
    except Exception:
        return False
    if parts.scheme not in ("http", "https"):
        return False
    host = (parts.hostname or "").lower()
    if not host:
        return False
    return any(host == d or host.endswith("." + d) for d in _ASSET_CLOUD_DOMAINS)


def _guard_asset_brand(brand_slug: str):
    """SG3 guard for Phase I upload routes: validate slug format (blocks
    ../ path-traversal in the brand_slug path param) THEN brand authz.
    Returns an (response, status) tuple to return on failure, or None to proceed.
    """
    if not _validate_brand_slug(brand_slug):
        return jsonify(success=False, error="Invalid brand slug."), 400
    _bid, err = _authorize_brand(brand_slug)
    if err:
        return err
    return None


# ── I-b helpers ───────────────────────────────────────────────────────────────

def _get_card(brand_slug: str, card_id: str) -> dict | None:
    """Return the card dict from content_calendar.json or None."""
    cal_path = BRANDS_DIR / brand_slug / "content_calendar.json"
    if not cal_path.exists():
        return None
    try:
        cal = json.loads(cal_path.read_text())
    except Exception:
        return None
    posts = cal if isinstance(cal, list) else (
        cal.get("posts") or cal.get("calendar") or []
    )
    return next((p for p in posts if str(p.get("id")) == str(card_id)), None)


def _update_card(brand_slug: str, card_id: str, updates: dict) -> bool:
    """Merge updates into the matching card in content_calendar.json."""
    cal_path = BRANDS_DIR / brand_slug / "content_calendar.json"
    if not cal_path.exists():
        return False
    try:
        cal = json.loads(cal_path.read_text())
    except Exception:
        return False

    def _patch(posts: list) -> bool:
        for i, p in enumerate(posts):
            if str(p.get("id")) == str(card_id):
                posts[i].update(updates)
                return True
        return False

    if isinstance(cal, list):
        if not _patch(cal):
            return False
        cal_path.write_text(json.dumps(cal, indent=2))
        return True
    for key in ("posts", "calendar"):
        posts = cal.get(key)
        if posts and isinstance(posts, list) and _patch(posts):
            cal_path.write_text(json.dumps(cal, indent=2))
            return True
    return False


# ─────────────────────────────────────────────────────────────────────────────
# Phase J — Concierge chat (Chief of Staff router)
#
# Tiered: trivial/deterministic (pause, reschedule, caption edit, slide swap)
# → execute instantly, zero LLM.  Substantive (re-plan, new angle, inject
# trend, strategy pivot) → dispatch right specialist → approval dashboard.
# Available pre- AND post-approval (client is never boxed in).
# ─────────────────────────────────────────────────────────────────────────────

# Trivial action patterns: (regex, action_type). All matched against lower-case
# input. Order matters — more specific patterns first.
_CONCIERGE_TRIVIAL: list[tuple[str, str]] = [
    (r"\b(pause|hold|skip|disable|stop)\b.{0,60}\bpost\b",       "pause_card"),
    (r"\bpost\b.{0,60}\b(pause|hold|skip|disable|stop)\b",       "pause_card"),
    (r"\b(resume|unpause|restore|re-enable|reactivate)\b.{0,60}\bpost\b", "unpause_card"),
    (r"\bpost\b.{0,60}\b(resume|unpause|restore)\b",             "unpause_card"),
    (r"\b(reschedule|move|push|shift|delay|bring forward)\b.{0,60}\bpost\b", "reschedule_card"),
    (r"\bpost\b.{0,60}\b(reschedule|move|push|shift|delay)\b",  "reschedule_card"),
    (r"\b(edit|change|update|fix|rewrite|tweak)\b.{0,60}\b(caption|copy|text|description)\b", "caption_edit"),
    (r"\b(swap|reorder|move)\b.{0,40}\bslides?\b",               "swap_slides"),
]

# Substantive dispatch patterns: (regex, agent_slug).
_CONCIERGE_DISPATCH: list[tuple[str, str]] = [
    (r"\b(re-?plan|redo.{0,20}(calendar|schedule)|new content plan|redo content)\b", "content-planner"),
    (r"\b(plan.{0,20}(next|more|another)|new.{0,20}(calendar|week|month))\b",        "content-planner"),
    (r"\b(new.{0,20}(angle|hook|script)|rewrite.{0,20}script|different.{0,20}(hook|angle|approach))\b", "script-writer"),
    (r"\b(inject.{0,20}trend|add.{0,20}trend|trending topic|new trend)\b",           "trend-researcher"),
    (r"\b(pivot|new.{0,20}(direction|strategy)|change.{0,20}strategy|different strategy)\b", "strategy-agent"),
    (r"\b(brand voice|brand tone|reposit|new positioning)\b",                        "strategy-agent"),
]

_CONCIERGE_AGENT_LABELS: dict[str, str] = {
    "content-planner":  "Content Planner",
    "script-writer":    "Script Writer",
    "trend-researcher": "Trend Researcher",
    "strategy-agent":   "Strategy Agent",
}

# SG4 — dispatch cost-governance. A concierge dispatch spawns a REAL paid agent
# subprocess (Opus/Sonnet). The endpoint IP rate-limit alone is not a cost gate,
# so throttle the expensive path per-brand: a same-agent cooldown (the prior run
# is likely still in flight) + an hourly cap on new specialist requests. Trivial
# calendar edits are NOT throttled — they're free.
MAX_CONCIERGE_MSG = 2000           # chars; bounds brief size + regex/prompt input
_CONCIERGE_MAX_PER_HOUR = 6        # new specialist dispatches per brand per hour
_CONCIERGE_AGENT_COOLDOWN = 90     # seconds before the same agent can be re-fired
_CONCIERGE_DISPATCH_LOG: dict[str, list[float]] = {}   # brand_slug -> [timestamps]
_CONCIERGE_AGENT_LAST: dict[str, float] = {}           # "brand:agent" -> last ts


def _concierge_dispatch_allowed(brand_slug: str, agent_slug: str) -> tuple[bool, str | None]:
    """SG4 throttle check for the paid dispatch path. Returns (ok, reason)."""
    now = time.time()
    label = _CONCIERGE_AGENT_LABELS.get(agent_slug, agent_slug)
    last = _CONCIERGE_AGENT_LAST.get(f"{brand_slug}:{agent_slug}", 0.0)
    if now - last < _CONCIERGE_AGENT_COOLDOWN:
        return False, (f"The {label} is already working on your last request — "
                       "give it a moment before sending another.")
    window = [t for t in _CONCIERGE_DISPATCH_LOG.get(brand_slug, []) if now - t < 3600]
    if len(window) >= _CONCIERGE_MAX_PER_HOUR:
        return False, (f"Hourly limit reached for new specialist requests "
                       f"({_CONCIERGE_MAX_PER_HOUR}/hr). Trivial edits — pause, "
                       "reschedule, caption — still work.")
    return True, None


def _concierge_dispatch_record(brand_slug: str, agent_slug: str) -> None:
    """Record a fired dispatch for the throttle window."""
    now = time.time()
    _CONCIERGE_AGENT_LAST[f"{brand_slug}:{agent_slug}"] = now
    window = [t for t in _CONCIERGE_DISPATCH_LOG.get(brand_slug, []) if now - t < 3600]
    window.append(now)
    _CONCIERGE_DISPATCH_LOG[brand_slug] = window


def _concierge_classify(text: str) -> tuple[str, str | None]:
    """Pure regex classifier — zero LLM cost.
    Returns ("trivial", action_type) | ("dispatch", agent_slug) | ("none", None).
    """
    t = text.lower()
    for pattern, action in _CONCIERGE_TRIVIAL:
        if re.search(pattern, t):
            return "trivial", action
    for pattern, agent in _CONCIERGE_DISPATCH:
        if re.search(pattern, t):
            return "dispatch", agent
    return "none", None


def _concierge_extract_card_id(text: str, context: dict) -> str | None:
    """Card id from explicit context or numeric mention ('post 5', 'card 3', '#2')."""
    if context.get("card_id"):
        return str(context["card_id"])
    m = re.search(r"\b(?:post|card|#)\s*(\d+)\b", text.lower())
    return m.group(1) if m else None


def _concierge_extract_date(text: str, context: dict) -> str | None:
    """Resolve a schedule date from context or simple text patterns."""
    if context.get("new_date"):
        return str(context["new_date"])
    # ISO 8601
    m = re.search(r"\b(20\d{2}-\d{2}-\d{2})\b", text)
    if m:
        return m.group(1)
    # "June 15" / "Jun 15"
    _months = {"jan":1,"feb":2,"mar":3,"apr":4,"may":5,"jun":6,
               "jul":7,"aug":8,"sep":9,"oct":10,"nov":11,"dec":12}
    m = re.search(r"\b(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)\w*\s+(\d{1,2})\b",
                  text.lower())
    if m:
        mon = _months.get(m.group(1)[:3], 0)
        day = int(m.group(2))
        if mon and 1 <= day <= 31:
            yr = datetime.now(timezone.utc).year
            return f"{yr}-{mon:02d}-{day:02d}"
    return None


def _concierge_trivial(brand_slug: str, action_type: str,
                       text: str, context: dict) -> dict:
    """Execute a trivial deterministic action directly on content_calendar.json.
    Returns {success, action, result, card_id?}.
    """
    card_id = _concierge_extract_card_id(text, context)

    if action_type == "pause_card":
        if not card_id:
            return {"success": False, "action": action_type,
                    "result": "Which post? Try: 'pause post 3'."}
        if not _update_card(brand_slug, card_id, {"status": "paused"}):
            return {"success": False, "action": action_type,
                    "result": f"Post {card_id} not found in the calendar."}
        return {"success": True, "action": action_type, "card_id": card_id,
                "result": f"Post {card_id} paused — won't be scheduled until resumed."}

    if action_type == "unpause_card":
        if not card_id:
            return {"success": False, "action": action_type,
                    "result": "Which post? Try: 'resume post 3'."}
        if not _update_card(brand_slug, card_id, {"status": "active"}):
            return {"success": False, "action": action_type,
                    "result": f"Post {card_id} not found in the calendar."}
        return {"success": True, "action": action_type, "card_id": card_id,
                "result": f"Post {card_id} is active again."}

    if action_type == "reschedule_card":
        if not card_id:
            return {"success": False, "action": action_type,
                    "result": "Which post? Try: 'reschedule post 3 to June 20'."}
        date_str = _concierge_extract_date(text, context)
        if not date_str:
            return {"success": False, "action": action_type,
                    "result": f"Which date? Try: 'reschedule post {card_id} to June 20'."}
        if not _update_card(brand_slug, card_id, {"schedule_date": date_str,
                                                   "status": "scheduled"}):
            return {"success": False, "action": action_type,
                    "result": f"Post {card_id} not found in the calendar."}
        return {"success": True, "action": action_type, "card_id": card_id,
                "new_date": date_str,
                "result": f"Post {card_id} rescheduled to {date_str}."}

    if action_type == "caption_edit":
        new_caption = (context.get("new_caption") or "").strip()
        if not new_caption:
            return {"success": False, "action": action_type,
                    "result": "Pass 'new_caption' in the context field with the replacement text."}
        if not card_id:
            return {"success": False, "action": action_type,
                    "result": "Which post? Pass 'card_id' in the context field."}
        if not _update_card(brand_slug, card_id, {"caption": new_caption}):
            return {"success": False, "action": action_type,
                    "result": f"Post {card_id} not found in the calendar."}
        return {"success": True, "action": action_type, "card_id": card_id,
                "result": f"Caption updated for post {card_id}."}

    if action_type == "swap_slides":
        new_slides = context.get("new_slides")
        if not new_slides:
            return {"success": False, "action": action_type,
                    "result": "Pass 'new_slides' (ordered slide list) in the context field."}
        if not card_id:
            return {"success": False, "action": action_type,
                    "result": "Which post? Pass 'card_id' in the context field."}
        if not _update_card(brand_slug, card_id, {"slides": new_slides}):
            return {"success": False, "action": action_type,
                    "result": f"Post {card_id} not found in the calendar."}
        return {"success": True, "action": action_type, "card_id": card_id,
                "result": f"Slide order updated for post {card_id}."}

    return {"success": False, "action": action_type,
            "result": f"Unknown trivial action: {action_type}"}


def _concierge_dispatch(brand_slug: str, agent_slug: str, brief_text: str) -> dict:
    """Dispatch a substantive request to the right specialist agent.
    Writes a concierge brief to pending_approval/{agent_slug}/ so it appears
    on the approval dashboard, then fires the agent script in a background
    thread (same pattern as run_agent). Returns dispatch metadata.
    """
    ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")

    # Write brief to pending_approval
    brief_dir = (BRANDS_DIR / brand_slug / "outputs"
                 / "pending_approval" / agent_slug)
    brief_dir.mkdir(parents=True, exist_ok=True)
    brief_data = {
        "type":         "concierge_brief",
        "agent":        agent_slug,
        # SG4: 'brief' is raw client input. Length-capped by the endpoint
        # (MAX_CONCIERGE_MSG). No agent reads this into a prompt today; ANY future
        # consumer MUST wrap it via agents/_untrusted.py before the model.
        "brief":        brief_text,
        "_untrusted":   True,
        "brand_slug":   brand_slug,
        "requested_at": datetime.now(timezone.utc).isoformat(),
        "status":       "dispatched",
    }
    loop_hdr = (
        f"LOOP: {agent_slug} — concierge_dispatch / "
        f"concierge brief / pending_review / VARIANTS=1 / WINNER=pending\n---\n"
    )
    brief_path = brief_dir / f"{ts}_concierge_brief.json"
    brief_path.write_text(loop_hdr + json.dumps(brief_data, indent=2))

    # Fire agent script in background thread
    agent_script = BASE_DIR / "agents" / f"{agent_slug.replace('-', '_')}.py"
    task_id = f"concierge_{ts}_{agent_slug}"

    if agent_script.exists():
        threading.Thread(
            target=_run_agent_subprocess,
            args=(str(agent_script), brand_slug, agent_slug, None),
            daemon=True,
        ).start()
        run_status = "running"
    else:
        run_status = "brief_only"   # agent script not present; brief queued for review

    label = _CONCIERGE_AGENT_LABELS.get(agent_slug, agent_slug)
    suffix = ("The result will appear in your approval queue."
              if run_status == "running"
              else "Your brief is queued — check the approval dashboard.")
    return {
        "task_id":     task_id,
        "agent":       agent_slug,
        "agent_label": label,
        "run_status":  run_status,
        "brief_path":  str(brief_path),
        "message":     f"Got it. I've briefed the {label} with your request. {suffix}",
    }


# ─────────────────────────────────────────────────────────────────────────────
# Phase L — Notifications (P0 minimal — email-first)
#
# Ping the brand owner when something needs approval. Drives "Needs you" queue
# + morning brief. WhatsApp = P1.
#
# Transport = Make.com webhook (NOT raw SMTP): Railway blocks outbound SMTP
# ports, so we hand the email off to the same tested Make.com pipeline the
# reporting product already uses. We POST a JSON payload; the Make scenario
# sends the actual email.
#
# Required env vars (add to .env + Railway):
#   NOTIFICATION_WEBHOOK_URL — Make.com webhook that sends the email (REQUIRED)
#   NOTIFICATION_EMAIL_TO    — recipient, passed through in the payload (optional
#                              if the Make scenario hard-codes the recipient)
#
# If NOTIFICATION_WEBHOOK_URL is unset, notifications silently no-op and the
# needs-you queue endpoint still works (no degradation to the approval flow).
# ─────────────────────────────────────────────────────────────────────────────


def _notification_configured() -> bool:
    return bool(os.getenv("NOTIFICATION_WEBHOOK_URL", "").strip())


def _send_notification(subject: str, body_text: str, *, count: int = 0) -> bool:
    """Hand an approval-needed notification to the Make.com webhook, which sends
    the email. Railway blocks outbound SMTP, so this is the tested path. POSTs a
    JSON payload; the Make scenario does the send. Never raises — log + return
    False on any error.
    """
    url = os.getenv("NOTIFICATION_WEBHOOK_URL", "").strip()
    if not url:
        return False
    payload = {
        "type":    "approval_notification",
        "to":      os.getenv("NOTIFICATION_EMAIL_TO", "").strip(),
        "subject": subject,
        "body":    body_text,
        "count":   count,
    }
    try:
        import requests as _req
        r = _req.post(url, json=payload, timeout=15)
        if 200 <= r.status_code < 300:
            return True
        print(f"[notification] webhook returned {r.status_code}")
        return False
    except Exception as exc:
        print(f"[notification] webhook post failed: {exc}")
        return False


def _needs_you_items(brand_slug: str) -> list[dict]:
    """Return list of pending-approval items for brand_slug, newest first."""
    root = BRANDS_DIR / brand_slug / "outputs" / "pending_approval"
    if not root.exists():
        return []
    items: list[dict] = []
    for agent_dir in sorted(root.iterdir()):
        if not agent_dir.is_dir():
            continue
        agent = agent_dir.name
        for f in sorted(agent_dir.iterdir(), key=lambda x: x.stat().st_mtime, reverse=True):
            if not f.is_file():
                continue
            try:
                mtime = datetime.fromtimestamp(f.stat().st_mtime, tz=timezone.utc).isoformat()
            except Exception:
                mtime = ""
            items.append({
                "agent":      agent,
                "filename":   f.name,
                "path":       str(f.relative_to(BRANDS_DIR / brand_slug)),
                "created_at": mtime,
            })
    # sort newest first overall
    items.sort(key=lambda x: x.get("created_at", ""), reverse=True)
    return items


def _maybe_notify_pending(brand_slug: str) -> None:
    """Fire an approval-needed email when pending_approval/ is non-empty and
    email is configured. Called after every successful agent run. Best-effort.
    """
    if not _notification_configured():
        return
    items = _needs_you_items(brand_slug)
    if not items:
        return
    n = len(items)
    subject = f"Grid Control: {n} item{'s' if n != 1 else ''} need your approval — {brand_slug}"
    lines = [
        f"Brand: {brand_slug}",
        f"Pending approvals: {n}",
        "",
        "Items:",
    ]
    for item in items[:10]:
        lines.append(f"  • [{item['agent']}] {item['filename']}  ({item['created_at'][:10]})")
    if n > 10:
        lines.append(f"  … and {n - 10} more")
    lines += ["", "Review at: your Grid Control dashboard → Review tab."]
    _send_notification(subject, "\n".join(lines), count=n)


# ─────────────────────────────────────────────────────────────────────────────





# Export EVERY module-level name (incl. _underscore helpers and names bound
# inside module-level try/if blocks, e.g. _db) so `from core import *` carries
# the full backend foundation into the route blueprints. Dynamic = nothing missed.
__all__ = [n for n in dir() if not n.startswith("__")]
