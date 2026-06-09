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


@app.route("/api/events", methods=["GET"])
def sse_events():
    """Global SSE stream — client subscribes to get live agent activity updates.

    EventSource cannot set Authorization headers, so auth is via ?token= (Supabase
    JWT) or ?secret= (legacy dashboard secret). Deny-by-default.
    """
    token = request.args.get("token", "")
    secret = request.args.get("secret", "")
    authed = False
    if token and _DB_AVAILABLE:
        try:
            authed = bool(_db.verify_jwt(token))
        except Exception:
            authed = False
    if not authed and _DASHBOARD_SECRET and secret == _DASHBOARD_SECRET:
        authed = True
    if not authed:
        return jsonify({"success": False, "error": "Unauthorized"}), 401

    q: _queue_mod.Queue = _queue_mod.Queue(maxsize=100)
    with _sse_lock:
        _sse_subscribers.append(q)

    def generate():
        try:
            while True:
                try:
                    payload = q.get(timeout=30)
                    yield f"data: {payload}\n\n"
                except _queue_mod.Empty:
                    yield ": keepalive\n\n"
        except GeneratorExit:
            pass
        finally:
            with _sse_lock:
                if q in _sse_subscribers:
                    _sse_subscribers.remove(q)

    return Response(
        stream_with_context(generate()),
        mimetype="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


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
    {"id": 1, "name": "Strategy Agent",    "role": "90-day roadmap",   "model": "claude-opus-4-6",   "agentFile": "strategy-agent.md"},
    {"id": 2, "name": "Content Planner",   "role": "30-day calendar",  "model": "claude-sonnet-4-6", "agentFile": "content-planner.md"},
    {"id": 3, "name": "Script Writer",     "role": "Scripts/captions", "model": "claude-sonnet-4-6", "agentFile": "script-writer.md"},
    {"id": 4, "name": "Creative Director", "role": "AI video/image",   "model": "claude-opus-4-6",   "agentFile": "creative-director.md"},
    {"id": 5, "name": "Ad Strategist",     "role": "Paid ads",         "model": "claude-opus-4-6",   "agentFile": "ad-strategist.md"},
    {"id": 6, "name": "Data Analyst",      "role": "Metrics",          "model": "claude-sonnet-4-6", "agentFile": "data-analyst.md"},
    {"id": 7, "name": "Funnel Specialist", "role": "Conversion",       "model": "claude-sonnet-4-6", "agentFile": "funnel-specialist.md"},
    {"id": 8, "name": "Website Agent",     "role": "Site/Railway",     "model": "claude-sonnet-4-6", "agentFile": "website-agent.md"},
    {"id": 9, "name": "Cost Tracker",      "role": "Monthly spend",    "model": "none", "agentFile": ""},
    {"id": 10, "name": "Carousel Designer", "role": "Carousel slides + PNG render", "model": "claude-sonnet-4-6", "agentFile": ""},
]

# Phase D — single source of truth: override the display models from the gateway
# so this list can never drift from agents/model_gateway.AGENT_ROUTING.
try:
    from agents.model_gateway import model_for as _model_for
    for _a in AGENTS:
        _resolved = _model_for(_a["name"])
        _a["model"] = _resolved or "none"
except Exception as _mg_err:
    print(f"[dashboard_api] model_gateway sync skipped: {_mg_err}")

# Locked slug set — any agent not in this list is filtered before response
_ACTIVE_SLUGS = {
    "trend-researcher", "strategy-agent", "content-planner", "script-writer",
    "creative-director", "ad-strategist", "data-analyst", "funnel-specialist", "website-agent",
    "cost-tracker", "carousel-designer",
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
    try:
        # Pass run context to agent via env so it can record costs + use memory
        agent_env = os.environ.copy()
        agent_env["GRID_RUN_ID"]     = db_run_id or ""
        agent_env["GRID_BRAND_SLUG"] = brand_slug
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


# ── Auth ──────────────────────────────────────────────────────────────────────

@app.route("/api/auth/me", methods=["GET"])
def get_me():
    """Return current user profile + their brands. No auth required (returns null if not logged in)."""
    user = _get_current_user()
    if not user or not _DB_AVAILABLE:
        return jsonify({"user": None, "brands": []})
    profile = _db.get_profile(user["id"])
    brands_raw = _db.get_user_brands(user["id"])
    brands = []
    for bm in brands_raw:
        b = bm.get("brands", {})
        if b:
            brands.append({
                "id": b.get("id"),
                "slug": b.get("slug"),
                "name": b.get("name"),
                "role": bm.get("role"),
            })
    return jsonify({"user": profile, "brands": brands})


@app.route("/api/auth/brands", methods=["GET"])
@require_auth
def get_my_brands():
    """Return brands for authenticated user."""
    user = getattr(request, "user", None)
    if not user or not _DB_AVAILABLE:
        return jsonify(list_brands())
    brands_raw = _db.get_user_brands(user["id"])
    brands = []
    for bm in brands_raw:
        b = bm.get("brands", {})
        if b:
            brands.append({
                "id": b.get("id"),
                "slug": b.get("slug"),
                "name": b.get("name"),
                "role": bm.get("role"),
                "profile": b.get("profile", {}),
            })
    return jsonify(brands)


@app.route("/api/auth/create-brand", methods=["POST"])
@require_auth
def auth_create_brand():
    """Create a new brand and assign the current user as admin."""
    user = getattr(request, "user", None)
    data = request.json or {}
    slug = data.get("slug", "").strip().lower()
    name = data.get("name", "").strip()
    if not slug or not name:
        return jsonify({"success": False, "error": "slug and name required"}), 400
    if not _validate_brand_slug(slug):
        return jsonify({"success": False, "error": "Invalid slug format"}), 400
    if not _DB_AVAILABLE:
        return jsonify({"success": False, "error": "Database not available"}), 503

    profile = data.get("profile", {})
    if user:
        brand = _db.create_brand_with_owner(slug, name, profile, user["id"])
    else:
        brand = _db.upsert_brand(slug, name, profile)

    if not brand:
        return jsonify({"success": False, "error": "Failed to create brand"}), 500

    brand_dir = BRANDS_DIR / slug
    brand_dir.mkdir(parents=True, exist_ok=True)
    bp_path = brand_dir / "brand_profile.json"
    if not bp_path.exists():
        profile["name"] = name
        profile["slug"] = slug
        _atomic_write_json(bp_path, profile)

    return jsonify({"success": True, "brand": brand})


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
@require_auth
def get_agents_list():
    return jsonify({"success": True, "data": AGENTS_ENRICHED})


@rate_limit(max_requests=5, window_seconds=60)
@app.route("/api/agents/run", methods=["POST"])
@require_auth
def run_agent():
    body = request.get_json() or {}
    agent_name = body.get("agentName", "").strip()
    brand_slug = body.get("brand_slug", "offgrid-creatives-ai")
    # Accept agent_slug too — the cockpit UI and Brain send kebab slugs
    # (e.g. "script-writer"), not the human name. Resolve slug → name.
    if not agent_name:
        slug_in = (body.get("agent_slug") or "").strip().lower()
        if slug_in:
            agent_name = next(
                (n for n in AGENT_SCRIPTS if _agent_name_to_slug(n) == slug_in), ""
            )
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
@require_auth
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


# ── CAROUSEL DESIGNER ──────────────────────────────────────────────────────────

@rate_limit(max_requests=3, window_seconds=60)
@app.route("/api/carousel/generate", methods=["POST"])
@require_auth
def carousel_generate():
    """
    Generate a carousel (slides JSON + PNG render + pending_approval push).

    Body:
      brand_slug: required
      post_id:    optional — pulls hook/body/cta from content_calendar.json or
                  script-writer outputs. If absent, requires `topic`.
      topic:     optional — freeform topic if no post_id present.
      slides:    int, default 7
      platform:  "instagram" | "linkedin" | "square", default "instagram"
      hook:      optional override
      body:      optional override
      cta:       optional override

    Runs synchronously (~30-60s). Returns paths + spec preview.
    """
    if not _ANTHROPIC_KEY:
        return jsonify({"success": False, "error": "ANTHROPIC_API_KEY not configured"}), 400

    body = request.get_json() or {}
    brand_slug = (body.get("brand_slug") or "").strip()
    if not brand_slug or not _validate_brand_slug(brand_slug):
        return jsonify({"success": False, "error": "Valid brand_slug required"}), 400

    post_id = (body.get("post_id") or "").strip() or None
    topic = (body.get("topic") or "").strip() or None
    if not post_id and not topic:
        return jsonify({"success": False, "error": "Either post_id or topic required"}), 400

    slides = int(body.get("slides") or 7)
    if slides < 3 or slides > 12:
        return jsonify({"success": False, "error": "slides must be between 3 and 12"}), 400

    platform = (body.get("platform") or "instagram").strip()

    script_path = BASE_DIR / AGENT_SCRIPTS["Carousel Designer"]
    if not script_path.exists():
        return jsonify({"success": False, "error": "Carousel Designer script missing"}), 500

    cmd = [
        sys.executable, str(script_path),
        "--brand-slug", brand_slug,
        "--slides", str(slides),
        "--platform", platform,
    ]
    if post_id:
        cmd.extend(["--post-id", post_id])
    if topic:
        cmd.extend(["--topic", topic])
    for opt_key, flag in (("hook", "--hook"), ("body", "--body"), ("cta", "--cta")):
        v = (body.get(opt_key) or "").strip()
        if v:
            cmd.extend([flag, v])

    env = os.environ.copy()
    env["ACTIVE_BRAND"] = brand_slug
    env["GRID_BRAND_SLUG"] = brand_slug
    # Overlay this brand's private secrets (platform tokens) on top of global env
    env.update({k: v for k, v in brand_env(brand_slug).items() if v})

    try:
        result = subprocess.run(
            cmd, env=env, capture_output=True, text=True, timeout=300, cwd=str(BASE_DIR)
        )
    except subprocess.TimeoutExpired:
        return jsonify({"success": False, "error": "Carousel generation timed out (>5min)"}), 504

    if result.returncode != 0:
        return jsonify({
            "success": False,
            "error": "Carousel Designer subprocess failed",
            "stderr": result.stderr[-2000:],
            "stdout": result.stdout[-1000:],
        }), 500

    # Parse the JSON tail of stdout (designer prints {ok, spec_path, slide_paths})
    parsed = None
    for line in reversed(result.stdout.splitlines()):
        if line.strip().startswith("{"):
            try:
                parsed = json.loads(line)
                break
            except Exception:
                continue
    if parsed is None:
        # try entire stdout
        try:
            parsed = json.loads(result.stdout)
        except Exception:
            parsed = {"raw_stdout": result.stdout[-1500:]}

    return jsonify({"success": True, "data": parsed})


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


@app.route("/api/scheduler/trigger", methods=["POST"])
def scheduler_trigger():
    """Service-to-service: run the daily pipeline for a brand. Token-authed.
    Body: { brand_slug }. Returns immediately; pipeline runs in background."""
    if not _valid_service_token():
        return jsonify({"success": False, "error": "invalid service token"}), 401
    data = request.get_json(silent=True) or {}
    brand_slug = (data.get("brand_slug") or "").strip()
    if not brand_slug:
        return jsonify({"success": False, "error": "brand_slug required"}), 400
    if not re.fullmatch(r"[a-z0-9][a-z0-9_-]{0,63}", brand_slug):
        # path-traversal guard: slug becomes a directory name below
        return jsonify({"success": False, "error": "invalid brand_slug"}), 400
    if not (BRANDS_DIR / brand_slug).is_dir():
        return jsonify({"success": False, "error": f"Brand '{brand_slug}' not found"}), 404
    print(f"[scheduler-trigger] daily pipeline for {brand_slug} (service token)")
    threading.Thread(target=run_daily_pipeline, args=(brand_slug,), daemon=True).start()
    return jsonify({"success": True, "data": {
        "message": f"daily pipeline started for {brand_slug}",
        "brand_slug": brand_slug,
        "started_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
    }})


# ── Instagram publishing (the "agents post it" step) ──────────────────────────

def _read_output_json(path: Path) -> dict:
    """Read a brand output file, stripping the LOOP HEADER prefix (split on first
    '\\n---\\n') before parsing. Never returns raw JSON to the client — callers map it."""
    raw = path.read_text()
    body = raw.split("\n---\n", 1)[1] if "\n---\n" in raw else raw
    return json.loads(body)


def _find_carousel_output(brand_dir: Path, filename: str) -> Path | None:
    """Locate an approved (preferred) or still-pending carousel output by filename."""
    candidates = [
        brand_dir / "outputs" / "approved" / filename,
        brand_dir / "outputs" / "pending_approval" / "carousel-designer" / filename,
    ]
    for c in candidates:
        if c.exists():
            return c
    return None


@app.route("/api/publish/check", methods=["GET"])
@require_auth
def publish_check():
    """Read-only IG token liveness probe — drives auto-publish vs prepare-only."""
    from publishing.instagram_publisher import token_status
    token = os.getenv("META_GRAPH_API_TOKEN", "").strip()
    return jsonify({"success": True, "data": token_status(token)})


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
        return jsonify({"success": False, "error": f"Carousel '{filename}' not found in approved or pending"}), 404

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
    """Locate an approved (preferred) or still-pending output by filename, across any
    agent subfolder."""
    for base in (brand_dir / "outputs" / "approved", brand_dir / "outputs" / "pending_approval"):
        if not base.exists():
            continue
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


@app.route("/api/publish/instagram", methods=["POST"])
@require_auth
@require_brand_access
def publish_instagram():
    """Publish an approved carousel to Instagram (thin wrapper over the shared impl)."""
    body = request.get_json(silent=True) or {}
    brand_slug = (body.get("brand_slug") or "").strip()
    filename = (body.get("filename") or "").strip()
    if not brand_slug or not _validate_brand_slug(brand_slug):
        return jsonify({"success": False, "error": "Valid brand_slug required"}), 400
    return _publish_instagram_impl(brand_slug, filename)


@app.route("/api/publish", methods=["POST"])
@require_auth
@require_brand_access
def publish_generic():
    """
    Platform-agnostic publish router — the spine of the create → approve → publish pipeline.
    Routes by `platform` through the publisher registry (publishing/base.py):
      - instagram  → real carousel publish.
      - linkedin / youtube / twitter → honest "publisher not built yet" (nothing sent).
    Never fabricates a success for an unbuilt platform.
    """
    from publishing.base import is_built, unbuilt_result
    body = request.get_json(silent=True) or {}
    brand_slug = (body.get("brand_slug") or "").strip()
    platform = (body.get("platform") or "").strip().lower()
    filename = (body.get("filename") or "").strip()
    if not brand_slug or not _validate_brand_slug(brand_slug):
        return jsonify({"success": False, "error": "Valid brand_slug required"}), 400
    if not platform:
        return jsonify({"success": False, "error": "platform required"}), 400

    routes = {
        "instagram": _publish_instagram_impl,
        "linkedin": _publish_linkedin_impl,
        "twitter": _publish_twitter_impl,
        "youtube": _publish_youtube_impl,
    }
    if platform in routes:
        return routes[platform](brand_slug, filename)

    if not is_built(platform):
        return jsonify({"success": True, "data": unbuilt_result(platform)}), 200

    # A platform marked built but with no route here is a wiring bug, not a runtime path.
    return jsonify({"success": False, "error": f"No publish route wired for '{platform}'"}), 501


@rate_limit(max_requests=2, window_seconds=60)
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

    t = threading.Thread(target=run_daily_pipeline, args=(brand_slug,), daemon=True)
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
@require_auth
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
@require_auth
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


# ── BRAND FILE READER (used by InsightsSpace provenance audit) ───────────────

@app.route("/api/brand/file", methods=["GET"])
@require_auth
def brand_file():
    """
    Read a single JSON file from a brand's directory (whitelisted set only).
    Used by InsightsSpace to render data_provenance + provenance_validation blocks.
    """
    brand_slug = request.args.get("brand_slug", "").strip()
    file_arg   = request.args.get("file", "").strip()
    if not brand_slug:
        return jsonify({"success": False, "error": "brand_slug required"}), 400
    if not _validate_brand_slug(brand_slug):
        return jsonify({"success": False, "error": "Invalid brand_slug"}), 400

    # Whitelist — only specific brand-output JSON files allowed
    ALLOWED = {
        "strategy_90day.json", "content_calendar.json", "trends_live.json",
        "performance_history.json", "performance_inbox.json",
        "contradictions.json", "pivot_decision.json", "pivot_impact.json",
        "brand_consistency_report.json", "trend_sentinel_watchlist.json",
        "voice_profile.json", "competitors_db.json",
    }
    if file_arg not in ALLOWED:
        return jsonify({"success": False, "error": f"File '{file_arg}' not in whitelist"}), 400

    fpath = BRANDS_DIR / brand_slug / file_arg
    if not fpath.exists():
        return jsonify({"success": True, "data": None})
    try:
        with open(fpath) as f:
            return jsonify({"success": True, "data": json.load(f)})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


# ── BUILD D — CROSS-AGENT CONTRADICTION DETECTOR ─────────────────────────────

@app.route("/api/contradictions/check", methods=["POST", "GET"])
@require_auth
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
@require_auth
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
@require_auth
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
@require_auth
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
            model="claude-opus-4-8",
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
@require_auth
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
@require_auth
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
@require_auth
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
@require_auth
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
@require_auth
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
@require_auth
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
@require_auth
@require_auth
def get_brands():
    """Return brands the current user has access to.
    Super admins see all brands. Regular users see only their brand_members brands."""
    user = getattr(request, "user", None)
    is_super = _DB_AVAILABLE and user and _db.is_super_admin(user["id"])

    if _DB_AVAILABLE:
        try:
            if is_super:
                # Super admin sees everything
                res = _db._client.table("brands").select("slug, name").order("created_at").execute()
            else:
                # Regular user: only brands they're a member of
                user_id = user["id"] if user else None
                if not user_id:
                    return jsonify({"brands": []})
                mem = _db._client.table("brand_members").select("brand_id").eq("user_id", user_id).execute()
                brand_ids = [m["brand_id"] for m in (mem.data or [])]
                if not brand_ids:
                    return jsonify({"brands": []})
                res = _db._client.table("brands").select("slug, name").in_("id", brand_ids).order("created_at").execute()
            if res.data:
                return jsonify({"brands": res.data})
        except Exception as e:
            print(f"[dashboard_api] Supabase brands list failed: {e}")
    return jsonify({"brands": list_brands()})


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


@app.route("/api/outputs/pending", methods=["GET"])
@require_auth
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
            # Skip dotfiles (.DS_Store, .gitkeep)
            if filepath.name.startswith("."):
                continue
            agent_name = filepath.parent.name if filepath.parent != pending_dir else "unknown"
            preview = ""
            # Files written by orchestrator have a LOOP HEADER at the top, then
            # `---`, then the JSON body. Strip the header before parsing.
            try:
                raw_text = filepath.read_text(errors="replace")
            except Exception:
                raw_text = ""

            meta = {}
            if filepath.suffix == ".json":
                # Try direct parse first
                json_body = raw_text
                if "---" in raw_text:
                    # Likely has loop header — JSON starts after the first '---' line
                    parts = raw_text.split("\n---\n", 1)
                    if len(parts) == 2:
                        json_body = parts[1].strip()
                try:
                    raw = json.loads(json_body)
                    # Format as PLAIN ENGLISH for the dashboard. NEVER raw JSON.
                    formatted = format_for_notion(agent_name, raw)
                    preview = _strip_markdown(formatted[:1500]) if formatted else json_body[:500]
                    meta = _extract_output_meta(agent_name, raw)
                except Exception:
                    # Last resort — show plain text excerpt without the loop header
                    if "---" in raw_text:
                        preview = raw_text.split("\n---\n", 1)[-1][:500]
                    else:
                        preview = raw_text[:500]
            elif filepath.suffix in (".txt", ".md"):
                preview = raw_text[:1500]
            items.append({
                "output_id": None,
                "filename": filepath.name,
                "filepath": str(filepath.relative_to(BASE_DIR)),
                "agentName": agent_name,
                "contentType": filepath.suffix.lstrip(".").upper() or "FILE",
                "preview": preview,
                "timestamp": datetime.fromtimestamp(stat.st_mtime).isoformat(),
                # Enriched human-readable fields (no markdown, ready for UI)
                "title": meta.get("title"),
                "platform": meta.get("platform"),
                "caption": meta.get("caption"),
                "body_text": meta.get("body_text"),
                "slide_images": meta.get("slide_images", []),
                "hashtags": meta.get("hashtags", []),
                "scheduled_for": meta.get("scheduled_for"),
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
@require_auth
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
@require_auth
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


@app.route("/api/published", methods=["GET"])
@require_auth
def get_published():
    """Approved + scheduled + published posts across all platforms.

    Reads:
      - brands/{slug}/outputs/approved/*/*.json (each = one approved post)
      - brands/{slug}/performance_inbox.json (queued metric entries — joined by post_id)
      - brands/{slug}/performance_history.json (computed metrics — joined by post_id)

    Returns each post as a row with: platform, title, caption, slide_images,
    scheduled_for, posted_at, status (scheduled|published), and engagement
    (likes/comments/shares/impressions/saves) once posted.
    """
    brand_slug = request.args.get("brand_slug", "askgauravai")
    brand_dir = get_brand_dir(brand_slug)
    approved_dir = brand_dir / "outputs" / "approved"

    # Build engagement lookup keyed by post_id (and by filename as fallback)
    engagement_by_id: dict[str, dict] = {}
    posted_by_id: dict[str, str] = {}
    for fp in (brand_dir / "performance_history.json", brand_dir / "performance_inbox.json"):
        if not fp.exists():
            continue
        try:
            data = json.loads(fp.read_text())
        except Exception:
            continue
        # Both files have a 'posts' / 'queue' / similar list of entries with metrics
        candidate_lists = []
        for k in ("posts", "queue", "entries", "items"):
            if isinstance(data.get(k), list):
                candidate_lists.append(data[k])
        for lst in candidate_lists:
            for entry in lst:
                if not isinstance(entry, dict):
                    continue
                pid = entry.get("post_id") or entry.get("id") or entry.get("filename")
                if not pid:
                    continue
                metrics = entry.get("metrics") or entry
                engagement_by_id[str(pid)] = {
                    "likes":       metrics.get("likes") or metrics.get("like_count") or 0,
                    "comments":    metrics.get("comments") or metrics.get("comment_count") or 0,
                    "shares":      metrics.get("shares") or metrics.get("share_count") or 0,
                    "impressions": metrics.get("impressions") or metrics.get("reach") or 0,
                    "saves":       metrics.get("saves") or 0,
                }
                if entry.get("posted_at"):
                    posted_by_id[str(pid)] = entry["posted_at"]

    items: list[dict] = []
    if approved_dir.exists():
        for filepath in approved_dir.rglob("*.json"):
            if filepath.name.startswith("."):
                continue
            try:
                raw_text = filepath.read_text(errors="replace")
                json_body = raw_text.split("\n---\n", 1)[1].strip() if "\n---\n" in raw_text else raw_text
                raw = json.loads(json_body)
            except Exception:
                continue
            agent_slug = filepath.parent.name
            meta = _extract_output_meta(agent_slug, raw)
            post_id = (raw.get("post_id") or filepath.stem) if isinstance(raw, dict) else filepath.stem
            stat = filepath.stat()
            engagement = engagement_by_id.get(str(post_id))
            posted_at = posted_by_id.get(str(post_id))
            items.append({
                "id":             filepath.name,
                "post_id":        post_id,
                "platform":       meta.get("platform"),
                "title":          meta.get("title"),
                "caption":        meta.get("caption"),
                "body_text":      meta.get("body_text"),
                "slide_images":   meta.get("slide_images", []),
                "hashtags":       meta.get("hashtags", []),
                "scheduled_for":  meta.get("scheduled_for"),
                "approved_at":    datetime.fromtimestamp(stat.st_mtime).isoformat(),
                "posted_at":      posted_at,
                "status":         "published" if posted_at or engagement else "scheduled",
                "engagement":     engagement,
                "agent_slug":     agent_slug,
                "filepath":       str(filepath.relative_to(BASE_DIR)),
            })
    # Newest first by approved_at
    items.sort(key=lambda x: x.get("approved_at") or "", reverse=True)
    return jsonify({"success": True, "data": items})


@app.route("/api/outputs/all", methods=["GET"])
@require_auth
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


# ── Skill learning hooks ─────────────────────────────────────────────────────

_SLUG_TO_AGENT_NAME = {v: k for k, v in _FOLDER_TO_SLUG.items()}

def _skill_on_approve(brand_slug: str, agent_slug: str, filepath: str):
    """Extract approved output as a learned skill (fire-and-forget)."""
    try:
        from agents.base_agent import BaseAgent
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
        from agents.base_agent import BaseAgent
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


@app.route("/api/outputs/approve", methods=["POST"])
@require_auth
def approve_output():
    # DB-WIRED Step 5 + Phase 1 Step 4
    body = request.get_json()
    brand_slug = body.get("brand_slug", "offgrid-creatives-ai")
    filepath = body.get("filepath", "")
    output_id = body.get("output_id", "")  # Supabase UUID — optional
    next_agent_slug: str | None = None

    # The Review UI sends just a filename — resolve it to a real filepath so the
    # move + skill-learning + Supabase match all work. (Without this, approve no-ops.)
    filename = body.get("filename", "")
    if not filepath and filename and "/" not in filename and ".." not in filename:
        found = _find_output(get_brand_dir(brand_slug), filename)
        if found:
            filepath = str(found.relative_to(BASE_DIR))

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

    # Resolve agent slug from filepath if not already resolved
    if not next_agent_slug and filepath:
        parts = Path(filepath).parts
        folder_nm = parts[-2] if len(parts) >= 2 else ""
        resolved_agent_slug = resolved_agent_slug or _FOLDER_TO_SLUG.get(folder_nm, "")

    # Skill learning — extract approved pattern
    if filepath and resolved_agent_slug:
        src_for_skill = _safe_path(BASE_DIR, filepath)
        if src_for_skill and src_for_skill.exists():
            _skill_on_approve(brand_slug, resolved_agent_slug, str(src_for_skill))

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
    reason = body.get("reason", "")
    agent_slug_key = ""

    # Review UI sends just a filename — resolve to a real filepath (else reject no-ops).
    filename = body.get("filename", "")
    if not filepath and filename and "/" not in filename and ".." not in filename:
        found = _find_output(get_brand_dir(brand_slug), filename)
        if found:
            filepath = str(found.relative_to(BASE_DIR))

    if _DB_AVAILABLE:
        brand_id = _get_brand_id(brand_slug)
        if brand_id:
            if output_id:
                _db.reject_output(output_id)
                _db.log_audit(brand_id, "output_rejected", "user", {"output_id": output_id})
                try:
                    res = _db._client.table("agent_outputs").select("agent_slug").eq("id", output_id).single().execute()
                    agent_slug_key = res.data.get("agent_slug", "") if res.data else ""
                except Exception:
                    pass
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

    # Skill learning — patch with rejection lesson
    if reason and agent_slug_key:
        _skill_on_reject(brand_slug, agent_slug_key, reason)

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


@app.route("/api/outputs/download/<path:filepath>", methods=["GET"])
@require_auth
def download_file(filepath):
    """Force-download any output file."""
    fpath = _resolve_output_file(filepath)
    if not fpath:
        return jsonify({"success": False, "error": "File not found"}), 404
    mime = _MIME_MAP.get(fpath.suffix.lower(), "application/octet-stream")
    return send_file(str(fpath), mimetype=mime, as_attachment=True,
                     download_name=fpath.name)


@app.route("/api/outputs/media/<path:filepath>", methods=["GET"])
@require_auth
def serve_media(filepath):
    """Serve an output file inline (for browser preview — images, video, audio)."""
    fpath = _resolve_output_file(filepath)
    if not fpath:
        return jsonify({"success": False, "error": "File not found"}), 404
    mime = _MIME_MAP.get(fpath.suffix.lower(), "application/octet-stream")
    return send_file(str(fpath), mimetype=mime, as_attachment=False)


# ── Brand profile / dashboard ─────────────────────────────────────────────────

@app.route("/api/brand/profile", methods=["GET"])
@require_auth
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
@require_auth
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
@require_auth
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
@require_auth
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
@require_auth
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
@require_auth
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
@require_auth
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
@require_auth
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
@require_auth
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
@require_auth
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
@require_auth
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


@require_auth
@rate_limit(max_requests=5, window_seconds=60)
@app.route("/api/brain/execute", methods=["POST"])
@require_auth
def brain_execute_proposal():
    """
    Execute a proposed action AFTER user approval in the UI.
    Body: { kind: 'edit' | 'bash', payload: {...} }
    """
    # ── Layer-1 hard wall — only an operator with operator-mode ON may execute ───
    _u = getattr(request, "user", None)
    _is_super = bool(_DB_AVAILABLE and _u and _db.is_super_admin(_u["id"]))
    if not _roles.brain_full_tools_allowed(_is_super, _u["id"] if _u else None):
        return jsonify({
            "success": False,
            "error": "Operator mode required. Enable operator mode to run edits/commands."
        }), 403

    body = request.get_json(silent=True) or {}
    kind = body.get("kind")
    payload = body.get("payload") or {}

    if kind == "edit":
        path = payload.get("path", "")
        old = payload.get("old_string", "")
        new = payload.get("new_string", "")
        p = _brain_safe_path(path)
        if not p or not p.exists() or not p.is_file():
            return jsonify({"success": False, "error": f"Path not accessible: {path}"}), 400
        try:
            content = p.read_text()
            if old not in content:
                return jsonify({"success": False, "error": "old_string not found in file"}), 400
            count = content.count(old)
            if count > 1:
                return jsonify({"success": False, "error": f"old_string matches {count} times — needs more context"}), 400
            new_content = content.replace(old, new, 1)
            p.write_text(new_content)
            return jsonify({"success": True, "result": f"Edited {path}"})
        except Exception as e:
            return jsonify({"success": False, "error": str(e)}), 500

    if kind == "bash":
        command = payload.get("command", "")
        if not command:
            return jsonify({"success": False, "error": "Empty command"}), 400
        # Block obviously destructive commands
        blocked = ["rm -rf /", "sudo ", "curl ", "wget ", " > /etc/", " > ~/.ssh/"]
        if any(b in command for b in blocked):
            return jsonify({"success": False, "error": "Command blocked by safety filter"}), 403
        try:
            import subprocess as _sp
            result = _sp.run(
                command,
                shell=True,
                cwd=str(BASE_DIR),
                capture_output=True,
                text=True,
                timeout=60,
            )
            return jsonify({
                "success": True,
                "result": (result.stdout + result.stderr)[:8000],
                "return_code": result.returncode,
            })
        except Exception as e:
            return jsonify({"success": False, "error": str(e)}), 500

    return jsonify({"success": False, "error": f"Unknown kind: {kind}"}), 400


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
        from _learnings import render_recent_for_prompt  # type: ignore
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
    """Slim brand context for The Brain — uses agents._state compact summary.

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
        from _state import load_brand_state  # type: ignore
        state = load_brand_state(brand_slug)
        # Render as readable JSON-ish block (already only ~4KB).
        return json.dumps(state, ensure_ascii=False, indent=2)[:6000]
    except Exception as e:
        return f"(failed to load state for {brand_slug}: {e})"


@app.route("/api/brain/chat", methods=["POST"])
@require_auth
@rate_limit(max_requests=10, window_seconds=60)
def brain_chat():
    """
    Embedded Claude chat for The Brain right-rail panel.

    Body: { messages: [{role: 'user'|'assistant', content: str}], brand_slug: str }
    Returns: { response: str }

    Admin: full tools (read_file, propose_edit, propose_bash).
    Client: brand-only Q&A — no tools, no coding, no off-topic.
    """
    body = request.get_json(silent=True) or {}
    messages = body.get("messages") or []
    brand_slug = (body.get("brand_slug") or "").strip()

    if not isinstance(messages, list) or not messages:
        return jsonify({"success": False, "error": "messages array required"}), 400

    api_key = os.getenv("ANTHROPIC_API_KEY", "").strip()
    if not api_key:
        return jsonify({"success": False, "error": "ANTHROPIC_API_KEY not set"}), 400

    # ── Role detection (Phase 1) ──────────────────────────────────────────────
    # is_super  = super-admin (Gaurav).  operator_active = super-admin WITH operator
    # mode toggled ON → only then are edit/bash tools + off-topic unlocked (D8).
    user = getattr(request, "user", None)
    is_super = bool(_DB_AVAILABLE and user and _db.is_super_admin(user["id"]))
    operator_active = _roles.brain_full_tools_allowed(is_super, user["id"] if user else None)
    grid_role = _grid_role_for(user, brand_slug)
    is_admin = operator_active  # capability gate downstream (tools/opus/proposals)

    # ── Layer-2 topical guardrail (cheap pre-check, before the paid model) ─────
    # Operators in operator mode are exempt; everyone else is held to marketing topics.
    if not operator_active:
        last = messages[-1] if messages else {}
        last_content = last.get("content") if isinstance(last, dict) else None
        last_text = ""
        if isinstance(last_content, str):
            last_text = last_content
        elif isinstance(last_content, list):
            last_text = " ".join(
                b.get("text", "") for b in last_content if isinstance(b, dict) and b.get("type") == "text"
            )
        if _roles.is_offtopic(last_text):
            brand_name = ""
            try:
                bp = get_brand_dir(brand_slug) / "brand_profile.json"
                if bp.exists():
                    brand_name = json.loads(bp.read_text()).get("brand_name", "")
            except Exception:
                pass
            return jsonify({
                "success": True,
                "response": _roles.offtopic_refusal(brand_name),
                "proposals": [],
                "refused": True,
            })

        # ── Cost governance — per-role daily token budget ─────────────────────
        if brand_slug and _roles.over_token_budget(grid_role, _brain_tokens_used_today(brand_slug)):
            return jsonify({
                "success": False,
                "error": "Daily AI usage limit reached for this brand. Resets at 00:00 UTC."
            }), 429

    # ── Rate limiting for clients (30 messages/hour per brand) ────────────────
    if not is_super and brand_slug:
        cache_key = f"brain_rate:{brand_slug}:{user['id'] if user else 'anon'}"
        count = _brain_rate_counts.get(cache_key, {"count": 0, "reset": time.time() + 3600})
        if time.time() > count["reset"]:
            count = {"count": 0, "reset": time.time() + 3600}
        count["count"] += 1
        _brain_rate_counts[cache_key] = count
        if count["count"] > 30:
            return jsonify({
                "success": False,
                "error": "Message limit reached (30/hour). Try again later."
            }), 429

    # Token optimization: load a SLIM brand summary instead of dumping full JSONs.
    # Brain can `read_file` to get full detail when actually needed.
    use_opus = bool(body.get("use_opus", False)) and is_admin  # clients never get Opus
    agent_scope = (body.get("agent_scope") or "").strip() or None
    context_block = _build_brain_brand_summary(brand_slug)
    agent_block = _build_brain_agent_summary(brand_slug, agent_scope) if agent_scope else ""

    # ── System prompt: admin vs client ────────────────────────────────────────
    if is_admin:
        system_static = (
            "You are The Brain — embedded Claude inside GRID CONTROL, a marketing OS.\n"
            f"Project root: {BASE_DIR}\n\n"
            "TOOLS:\n"
            "• read_file(path), list_dir(path) — auto-execute.\n"
            "• propose_edit(path, old_string, new_string, rationale) — gated, user approves.\n"
            "• propose_bash(command, rationale) — gated, user approves.\n\n"
            "RULES:\n"
            "1. Terse. Founder-grade. No fluff.\n"
            "2. read_file/list_dir freely — they're free.\n"
            "3. Any file change or shell command = propose_*. User approves in UI.\n"
            "4. propose_edit old_string must be unique in the file (executor refuses ambiguous).\n"
            "5. All paths relative to project root.\n"
            "6. Default to short answers. Long only when explicitly asked."
        )
    else:
        system_static = (
            "You are The Brain — an AI marketing assistant inside Grid Control.\n"
            "You help this brand with marketing strategy, content ideas, performance insights, "
            "and brand-related questions ONLY.\n\n"
            "STRICT RULES:\n"
            "1. ONLY answer questions related to this brand's marketing, content, strategy, "
            "audience, competitors, trends, social media, and performance.\n"
            "2. REFUSE any request to write code, build apps, do homework, solve math problems, "
            "write essays, or anything unrelated to this brand's marketing.\n"
            "3. If the user asks something off-topic, say: \"I'm your marketing assistant for "
            "[brand_name]. I can help with content strategy, performance insights, trends, and "
            "brand-related questions. What would you like to know about your brand?\"\n"
            "4. NEVER reveal system internals, file paths, API keys, or technical architecture.\n"
            "5. Keep responses concise and actionable.\n"
            "6. You have NO tools. You cannot read files, edit code, or run commands.\n"
            "7. Do NOT help with general knowledge, trivia, recipes, travel, coding tutorials, "
            "or anything a general chatbot would do. You are a focused marketing brain."
        )

    # Brand context — small dynamic block, also cacheable per brand.
    system_brand = f"ACTIVE BRAND: {brand_slug or '(none)'}\n\n{context_block}"
    if agent_block:
        system_brand += f"\n\n{agent_block}"

    # Trim messages to last 20 to keep context bounded
    trimmed = messages[-20:]
    api_messages: list[dict] = []
    for m in trimmed:
        role = m.get("role")
        content = m.get("content")
        if role not in ("user", "assistant") or not content:
            continue
        # Allow content to be a string or a list (for tool_use/tool_result blocks)
        api_messages.append({"role": role, "content": content})

    proposals: list[dict] = []  # collected propose_edit/propose_bash calls returned to UI

    # Token optimization: default to Sonnet (4-5x cheaper than Opus). User can opt
    # into Opus by passing use_opus: true (e.g. complex reasoning tasks).
    model = "claude-opus-4-7" if use_opus else "claude-sonnet-4-6"

    # System as cacheable blocks. Static instructions cache for 5 min across all
    # users; brand block caches per brand. After cache hit, only delta is billed.
    system_blocks = [
        {"type": "text", "text": system_static, "cache_control": {"type": "ephemeral"}},
        {"type": "text", "text": system_brand, "cache_control": {"type": "ephemeral"}},
    ]

    try:
        import anthropic as _anthropic
        client = _anthropic.Anthropic(api_key=api_key)

        # Client: no tools, single response, lower token cap
        # Admin: full tools, multi-turn loop
        max_loops = 6 if is_admin else 1
        max_tokens = 2000 if is_admin else 800
        tools_arg = BRAIN_TOOLS_DEF if is_admin else []

        for _ in range(max_loops):
            create_kwargs = dict(
                model=model,
                max_tokens=max_tokens,
                system=system_blocks,
                messages=api_messages,
            )
            if tools_arg:
                create_kwargs["tools"] = tools_arg
            resp = client.messages.create(**create_kwargs)

            stop_reason = resp.stop_reason
            assistant_blocks = []
            tool_uses = []
            text_parts: list[str] = []

            for b in resp.content:
                btype = getattr(b, "type", None)
                if btype == "text":
                    text_parts.append(b.text)
                    assistant_blocks.append({"type": "text", "text": b.text})
                elif btype == "tool_use":
                    tu = {"type": "tool_use", "id": b.id, "name": b.name, "input": b.input}
                    assistant_blocks.append(tu)
                    tool_uses.append((b.id, b.name, b.input))

            # Append assistant turn
            api_messages.append({"role": "assistant", "content": assistant_blocks})

            if stop_reason == "tool_use" and tool_uses:
                tool_results = []
                for tu_id, tu_name, tu_input in tool_uses:
                    if tu_name in ("read_file", "list_dir"):
                        result = _brain_execute_read_tool(tu_name, tu_input or {})
                        tool_results.append({
                            "type": "tool_result",
                            "tool_use_id": tu_id,
                            "content": result.get("output") or f"Error: {result.get('error')}",
                            "is_error": "error" in result,
                        })
                    elif tu_name == "propose_edit":
                        proposals.append({
                            "kind": "edit",
                            "tool_use_id": tu_id,
                            "payload": tu_input,
                        })
                        tool_results.append({
                            "type": "tool_result",
                            "tool_use_id": tu_id,
                            "content": "Proposal queued. Awaiting user approval in the UI.",
                        })
                    elif tu_name == "propose_bash":
                        proposals.append({
                            "kind": "bash",
                            "tool_use_id": tu_id,
                            "payload": tu_input,
                        })
                        tool_results.append({
                            "type": "tool_result",
                            "tool_use_id": tu_id,
                            "content": "Proposal queued. Awaiting user approval in the UI.",
                        })
                    else:
                        tool_results.append({
                            "type": "tool_result",
                            "tool_use_id": tu_id,
                            "content": f"Unknown tool: {tu_name}",
                            "is_error": True,
                        })
                api_messages.append({"role": "user", "content": tool_results})
                # Loop continues — Claude will respond to tool results
                continue

            # Done — Claude returned end_turn or max_tokens
            text = "\n".join(text_parts).strip() or "(no response)"
            usage = getattr(resp, "usage", None)
            usage_dict: dict = {}
            if usage:
                in_tok = getattr(usage, "input_tokens", 0)
                out_tok = getattr(usage, "output_tokens", 0)
                usage_dict = {
                    "input_tokens": in_tok,
                    "output_tokens": out_tok,
                    "cache_creation_input_tokens": getattr(usage, "cache_creation_input_tokens", 0),
                    "cache_read_input_tokens": getattr(usage, "cache_read_input_tokens", 0),
                }
                # ── Track cost per brand ──────────────────────────────────
                if _DB_AVAILABLE and brand_slug:
                    try:
                        # Sonnet: $3/M in, $15/M out. Opus: $15/M in, $75/M out.
                        if "opus" in model:
                            cost = (in_tok * 15 + out_tok * 75) / 1_000_000
                        else:
                            cost = (in_tok * 3 + out_tok * 15) / 1_000_000
                        _db._client.table("brain_usage").insert({
                            "brand_slug": brand_slug,
                            "user_id": user["id"] if user else None,
                            "model": model,
                            "input_tokens": in_tok,
                            "output_tokens": out_tok,
                            "cost_usd": round(cost, 6),
                            "is_admin": is_admin,
                        }).execute()
                    except Exception as e:
                        print(f"[brain] cost tracking failed: {e}")

            return jsonify({
                "success": True,
                "response": text,
                "proposals": proposals if is_admin else [],  # clients don't see proposals
                "model": model,
                "usage": usage_dict if is_admin else {},  # clients don't see token counts
            })

        # Loop cap hit
        return jsonify({
            "success": True,
            "response": "(tool-use loop cap reached)",
            "proposals": proposals,
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


# ── Operator mode toggle (D8 — locked by default, every flip audit-logged) ────
@app.route("/api/operator-mode", methods=["GET", "POST"])
@require_auth
def operator_mode_endpoint():
    user = getattr(request, "user", None)
    is_super = bool(_DB_AVAILABLE and user and _db.is_super_admin(user["id"]))
    if not is_super:
        return jsonify({"success": False, "error": "Operator mode is available to operators only."}), 403
    uid = user["id"]

    if request.method == "GET":
        return jsonify({"success": True, "data": {
            "on": _roles.operator_mode_on(uid), "user_id": uid,
        }})

    body = request.get_json(silent=True) or {}
    on = bool(body.get("on", False))
    state = _roles.set_operator_mode(uid, on)
    # Audit every flip (security + trust).
    if _DB_AVAILABLE:
        try:
            _db.log_audit(None, f"operator_mode_{'on' if on else 'off'}", actor=uid,
                          payload={"on": on})
        except Exception:
            pass
    return jsonify({"success": True, "data": {"on": state["on"]}})


# ── Daily Intelligence Digest (cockpit hero) ──────────────────────────────────
@app.route("/api/digest", methods=["GET"])
@require_auth
@require_brand_access
def get_digest():
    """Aggregates Trend Sentinel watchlist + new trends + contradictions + last-run
    timestamps for the command-center hero. Real data only — empty states, never fakes."""
    brand_slug = request.args.get("brand_slug", "").strip()
    if not brand_slug or not _validate_brand_slug(brand_slug):
        return jsonify({"success": False, "error": "Valid brand_slug required"}), 400
    bdir = BRANDS_DIR / brand_slug

    def _load(name):
        p = bdir / name
        if p.exists():
            try:
                return json.loads(p.read_text())
            except Exception:
                return None
        return None

    # Sentinel watchlist → tracked signals (label, day_count, reason).
    sentinel = _load("trend_sentinel_watchlist.json") or {}
    sig_map = sentinel.get("signals") or {}
    signals = []
    for key, v in sig_map.items() if isinstance(sig_map, dict) else []:
        if isinstance(v, dict):
            signals.append({
                "label": v.get("label") or key,
                "day_count": v.get("day_count", 0),
                "reason": v.get("reason", ""),
                "last_seen": v.get("last_seen", ""),
            })
    signals.sort(key=lambda s: s.get("day_count", 0), reverse=True)

    # New trends from trends_live.json.
    trends_live = _load("trends_live.json") or {}
    raw_trends = trends_live.get("trends") or trends_live.get("signals") or []
    trends = []
    if isinstance(raw_trends, list):
        for t in raw_trends[:8]:
            if isinstance(t, dict):
                trends.append({
                    "title": t.get("title") or t.get("trend") or t.get("label") or "",
                    "relevance": t.get("relevance_score") or t.get("relevance") or t.get("score"),
                    "classification": t.get("classification") or t.get("type") or "",
                })

    # Contradictions (counts + findings).
    contra = _load("contradictions.json") or {}
    contra_counts = contra.get("counts") or {"CRITICAL": 0, "WARNING": 0, "INFO": 0}
    contra_findings = (contra.get("findings") or [])[:5]

    # Trend Sentinel verdict (PIVOT / TRACK / STAY) — real decision only, never fabricated.
    decision = _load("pivot_decision.json") or {}
    verdict = decision.get("overall_decision")
    if verdict not in ("PIVOT", "TRACK", "STAY"):
        verdict = None
    verdict_reason = ""
    if verdict:
        per_signal = decision.get("per_signal") or []
        verdict_reason = (decision.get("reason")
                          or (decision.get("loop_header") or {}).get("winner")
                          or (per_signal[0].get("reason") if per_signal and isinstance(per_signal[0], dict) else "")
                          or "")
    verdict_at = decision.get("decided_at") or decision.get("run_at") or ""

    # Last pipeline / update timestamps.
    session = _load("session_state.json") or {}
    last_run = (session.get("last_pipeline_run")
                or trends_live.get("last_updated")
                or trends_live.get("generated_at")
                or sentinel.get("last_updated") or "")

    return jsonify({"success": True, "data": {
        "brand_slug": brand_slug,
        "verdict": verdict,
        "verdict_reason": verdict_reason,
        "verdict_at": verdict_at,
        "sentinel": {"signals": signals[:10], "tracked_count": len(signals)},
        "trends": trends,
        "contradictions": {"counts": contra_counts, "findings": contra_findings,
                            "blocking": bool(contra.get("blocking"))},
        "last_pipeline_run": last_run,
        "has_data": bool(signals or trends or contra_findings),
    }})


# ── Per-brand agent config (which of the 18 agents are on + tuning) ────────────
@app.route("/api/agent-config", methods=["GET", "PUT"])
@require_auth
@require_brand_access
def agent_config_endpoint():
    brand_slug = request.args.get("brand_slug", "").strip()
    if not brand_slug or not _validate_brand_slug(brand_slug):
        return jsonify({"success": False, "error": "Valid brand_slug required"}), 400

    if request.method == "GET":
        return jsonify({"success": True, "data": _roles.load_agent_config(BASE_DIR, brand_slug)})

    # PUT — only operator or subscriber may change agent config; managed-client cannot.
    role = getattr(request, "brand_role", None)
    user = getattr(request, "user", None)
    is_super = bool(_DB_AVAILABLE and user and _db.is_super_admin(user["id"]))
    grid_role = _roles.OPERATOR if is_super else _roles.resolve_grid_role(False, role)
    if grid_role == _roles.MANAGED_CLIENT:
        return jsonify({"success": False, "error": "Managed clients cannot change agent config."}), 403

    body = request.get_json(silent=True) or {}
    agents = body.get("agents")
    if not isinstance(agents, dict):
        return jsonify({"success": False, "error": "Body must include an 'agents' object."}), 400
    cfg = _roles.save_agent_config(BASE_DIR, brand_slug, agents)
    return jsonify({"success": True, "data": cfg})


# ── Health + Config ───────────────────────────────────────────────────────────

@app.route("/api/health", methods=["GET"])
def health():
    return jsonify({"success": True, "data": {"status": "GRID CONTROL API running", "port": 5001}})


@app.route("/api/config/keys", methods=["GET"])
@require_auth
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
@require_auth
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


@app.route("/api/brands/<slug>/connections", methods=["GET"])
@require_auth
def brand_connections(slug: str):
    """Per-brand social connection status. Reads brand .env tokens and live-verifies
    each. Never returns raw tokens."""
    profile = {}
    pf = BRANDS_DIR / slug / "brand_profile.json"
    if pf.exists():
        try:
            profile = json.loads(pf.read_text())
        except Exception:
            profile = {}
    socials = profile.get("social_handles", {}) or {}

    benv = brand_env(slug)
    out = []
    for platform in _SOCIAL_PLATFORMS:
        env_key = _PLATFORM_ENV_MAP[platform]
        # Brand-authoritative: only this brand's own .env counts here (no global
        # fallback) so the page reflects what THIS brand has actually connected.
        token = (benv.get(env_key) or "").strip()

        # YouTube: OAuth (refresh token) supersedes the read-only API key.
        if platform == "youtube":
            yt_refresh = (benv.get("YOUTUBE_REFRESH_TOKEN") or "").strip()
            if yt_refresh:
                token = yt_refresh  # marks has_token true
                status = _verify_youtube_oauth(benv)
            elif token:
                status = _verify_social("youtube", token)
            else:
                status = {"connected": False, "account": "Not connected"}
            out.append({
                "platform": platform, "handle": socials.get("youtube", "") or "",
                "env_key": env_key, "has_token": bool(token),
                "connected": status["connected"], "account": status["account"],
            })
            continue

        # X/Twitter: OAuth 1.0a (post-capable) supersedes the read-only Bearer.
        if platform == "twitter":
            oauth_keys = all((benv.get(k) or "").strip() for k in
                             ("TWITTER_API_KEY", "TWITTER_API_SECRET",
                              "TWITTER_ACCESS_TOKEN", "TWITTER_ACCESS_SECRET"))
            if oauth_keys:
                token = "oauth1"  # marks has_token true
                status = _verify_twitter_oauth(benv)
            elif token:
                status = _verify_social("twitter", token)
            else:
                status = {"connected": False, "account": "Not connected"}
            out.append({
                "platform": platform, "handle": socials.get("x", "") or socials.get("twitter", "") or "",
                "env_key": env_key, "has_token": bool(token),
                "connected": status["connected"], "account": status["account"],
            })
            continue

        status = _verify_social(platform, token) if token else {"connected": False, "account": "Not connected"}

        # LinkedIn: once connected, capture the member URN from the token (server-side
        # only, never exposed) so member posting works later without manual lookup.
        if platform == "linkedin" and status.get("connected") and not (benv.get("LINKEDIN_URN") or "").strip():
            try:
                import requests as _rq
                ui = _rq.get("https://api.linkedin.com/v2/userinfo",
                             headers={"Authorization": f"Bearer {token}"}, timeout=5)
                sub = ui.json().get("sub", "") if ui.status_code == 200 else ""
                if sub:
                    urn = sub if sub.startswith("urn:li:") else f"urn:li:person:{sub}"
                    _write_brand_env_token(slug, "LINKEDIN_URN", urn)
            except Exception:
                pass
        handle = socials.get("instagram" if platform == "instagram" else platform, "") or ""
        out.append({
            "platform":  platform,
            "handle":    handle,
            "env_key":   env_key,
            "has_token": bool(token),
            "connected": status["connected"],
            "account":   status["account"],
        })
    return jsonify({"success": True, "data": out})

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
    Persist a platform API token to a brand's private .env (brands/<slug>/.env).
    Body: { "brand_slug": "<slug>",
            "platform": "instagram"|"linkedin"|"youtube"|"twitter"|"tiktok"|"whatsapp",
            "token": "<token value>",
            "extra": { "IG_USER_ID": "...", "LINKEDIN_URN": "..." }  # optional secondary keys
    }
    Falls back to global .env when no brand_slug is given (back-compat).
    """
    body       = request.get_json() or {}
    brand_slug = (body.get("brand_slug") or "").strip()
    platform   = (body.get("platform") or "").strip().lower()
    token      = (body.get("token")    or "").strip()
    extra      = body.get("extra") or {}

    if not platform:
        return jsonify({"success": False, "error": "platform is required"}), 400
    if platform not in _PLATFORM_ENV_MAP:
        return jsonify({"success": False, "error": f"Unknown platform '{platform}'"}), 400
    if not token:
        return jsonify({"success": False, "error": "token is required"}), 400

    env_key = _PLATFORM_ENV_MAP[platform]
    try:
        if brand_slug:
            _write_brand_env_token(brand_slug, env_key, token)
            for k, v in extra.items():
                if isinstance(v, str) and v.strip():
                    _write_brand_env_token(brand_slug, str(k).strip(), v.strip())
            target = f"brands/{brand_slug}/.env"
        else:
            _write_env_token(env_key, token)
            target = ".env"
    except Exception as exc:
        return jsonify({"success": False, "error": f"Failed to write {env_key}: {exc}"}), 500

    # Live-verify what we just stored (never echo the token back)
    status = _verify_social(platform, token)
    return jsonify({
        "success": True,
        "data": {
            "platform":  platform,
            "env_key":   env_key,
            "target":    target,
            "connected": status["connected"],
            "account":   status["account"],
            "message":   f"{env_key} saved to {target}",
        },
    })


# ── Team Standup ──────────────────────────────────────────────────────────────

@app.route("/api/standup", methods=["POST"])
@require_auth
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


@app.route("/api/billing/plans", methods=["GET"])
def billing_plans():
    """List available billing plans from Supabase."""
    try:
        rows = _db._client.table("billing_plans").select("*").eq("is_active", True).order("amount_paise").execute()
        return jsonify(success=True, data=rows.data)
    except Exception as e:
        return jsonify(success=False, error=str(e)), 500


@app.route("/api/billing/subscription", methods=["GET"])
@require_auth
def billing_get_subscription():
    """Get the active subscription for a brand."""
    brand_id = _resolve_brand_id(request.args.get("brand_slug") or request.args.get("brand_id", ""))
    if not brand_id:
        return jsonify(success=False, error="brand_slug required"), 400
    try:
        rows = _db._client.table("subscriptions").select("*, billing_plans(*)").eq("brand_id", brand_id).execute()
        sub = rows.data[0] if rows.data else None
        return jsonify(success=True, data=sub)
    except Exception as e:
        return jsonify(success=False, error=str(e)), 500


@require_auth
@rate_limit(max_requests=3, window_seconds=60)
@app.route("/api/billing/subscribe", methods=["POST"])
@require_auth
def billing_subscribe():
    """Create a Razorpay subscription for a brand."""
    if not _razorpay_ok:
        return jsonify(success=False, error="Razorpay not configured"), 503
    body = request.get_json(force=True)
    brand_id = _resolve_brand_id(body.get("brand_slug") or body.get("brand_id", ""))
    plan_slug = body.get("plan_slug")
    customer_email = body.get("email", "")
    customer_name = body.get("name", "")

    if not brand_id or not plan_slug:
        return jsonify(success=False, error="brand_slug and plan_slug required"), 400

    try:
        # Fetch plan from Supabase
        plan_rows = _db._client.table("billing_plans").select("*").eq("slug", plan_slug).eq("is_active", True).execute()
        if not plan_rows.data:
            return jsonify(success=False, error=f"Plan '{plan_slug}' not found"), 404
        plan = plan_rows.data[0]

        # Create Razorpay plan if not yet synced
        rz_plan_id = plan.get("razorpay_plan_id")
        if not rz_plan_id:
            rz_plan = _rz.create_plan(
                name=plan["name"],
                amount_paise=plan["amount_paise"],
                interval=plan["interval"],
                description=plan.get("description", ""),
            )
            rz_plan_id = rz_plan["id"]
            _db._client.table("billing_plans").update({"razorpay_plan_id": rz_plan_id}).eq("id", plan["id"]).execute()

        # Create Razorpay customer
        rz_customer = _rz.create_customer(
            name=customer_name or "Grid Control User",
            email=customer_email or "user@gridcontrol.ai",
        )

        # Create Razorpay subscription
        rz_sub = _rz.create_subscription(
            plan_id=rz_plan_id,
            customer_id=rz_customer["id"],
            total_count=12,
            notes={"brand_id": brand_id, "plan_slug": plan_slug},
        )

        # Store in Supabase
        _db._client.table("subscriptions").upsert({
            "brand_id": brand_id,
            "plan_id": plan["id"],
            "razorpay_subscription_id": rz_sub["id"],
            "razorpay_customer_id": rz_customer["id"],
            "status": rz_sub.get("status", "created"),
            "metadata": {"razorpay_short_url": rz_sub.get("short_url", "")},
        }, on_conflict="brand_id").execute()

        return jsonify(success=True, data={
            "subscription_id": rz_sub["id"],
            "short_url": rz_sub.get("short_url", ""),
            "status": rz_sub.get("status", "created"),
        })
    except Exception as e:
        return jsonify(success=False, error=str(e)), 500


@app.route("/api/billing/verify", methods=["POST"])
@require_auth
def billing_verify():
    """Verify subscription payment after Razorpay checkout."""
    if not _razorpay_ok:
        return jsonify(success=False, error="Razorpay not configured"), 503
    body = request.get_json(force=True)
    sub_id = body.get("razorpay_subscription_id")
    payment_id = body.get("razorpay_payment_id")
    signature = body.get("razorpay_signature")

    if not all([sub_id, payment_id, signature]):
        return jsonify(success=False, error="Missing verification fields"), 400

    try:
        valid = _rz.verify_subscription_signature(sub_id, payment_id, signature)
        if not valid:
            return jsonify(success=False, error="Invalid signature"), 403

        # Update subscription status
        rz_sub = _rz.fetch_subscription(sub_id)
        _db._client.table("subscriptions").update({
            "status": rz_sub.get("status", "active"),
            "current_period_start": rz_sub.get("current_start"),
            "current_period_end": rz_sub.get("current_end"),
        }).eq("razorpay_subscription_id", sub_id).execute()

        # Record payment
        rz_pay = _rz.fetch_payment(payment_id)
        sub_rows = _db._client.table("subscriptions").select("id, brand_id").eq("razorpay_subscription_id", sub_id).execute()
        if sub_rows.data:
            _db._client.table("payments").insert({
                "brand_id": sub_rows.data[0]["brand_id"],
                "subscription_id": sub_rows.data[0]["id"],
                "razorpay_payment_id": payment_id,
                "amount_paise": rz_pay.get("amount", 0),
                "currency": rz_pay.get("currency", "INR"),
                "status": rz_pay.get("status", "captured"),
                "method": rz_pay.get("method", ""),
            }).execute()

        return jsonify(success=True, data={"status": "active"})
    except Exception as e:
        return jsonify(success=False, error=str(e)), 500


@app.route("/api/billing/cancel", methods=["POST"])
@require_auth
def billing_cancel():
    """Cancel a subscription (at end of billing cycle)."""
    if not _razorpay_ok:
        return jsonify(success=False, error="Razorpay not configured"), 503
    body = request.get_json(force=True)
    brand_id = _resolve_brand_id(body.get("brand_slug") or body.get("brand_id", ""))
    if not brand_id:
        return jsonify(success=False, error="brand_slug required"), 400

    try:
        sub_rows = _db._client.table("subscriptions").select("razorpay_subscription_id").eq("brand_id", brand_id).execute()
        if not sub_rows.data or not sub_rows.data[0].get("razorpay_subscription_id"):
            return jsonify(success=False, error="No active subscription"), 404

        rz_sub_id = sub_rows.data[0]["razorpay_subscription_id"]
        _rz.cancel_subscription(rz_sub_id, cancel_at_cycle_end=True)
        _db._client.table("subscriptions").update({
            "status": "cancelled",
            "cancelled_at": "now()",
        }).eq("brand_id", brand_id).execute()

        return jsonify(success=True, data={"status": "cancelled"})
    except Exception as e:
        return jsonify(success=False, error=str(e)), 500


@app.route("/api/billing/usage", methods=["GET"])
@require_auth
def billing_usage():
    """Get usage stats for a brand (current month)."""
    brand_id = _resolve_brand_id(request.args.get("brand_slug") or request.args.get("brand_id", ""))
    if not brand_id:
        return jsonify(success=False, error="brand_slug required"), 400
    try:
        # Count agent runs this month
        from datetime import datetime
        month_start = datetime.now().replace(day=1, hour=0, minute=0, second=0).isoformat()
        rows = _db._client.table("usage_logs").select("agent_slug, model_used, estimated_cost_usd, input_tokens, output_tokens").eq("brand_id", brand_id).gte("created_at", month_start).execute()

        total_runs = len(rows.data)
        total_cost = sum(float(r.get("estimated_cost_usd", 0)) for r in rows.data)
        total_input = sum(r.get("input_tokens", 0) for r in rows.data)
        total_output = sum(r.get("output_tokens", 0) for r in rows.data)

        # Group by agent
        by_agent = {}
        for r in rows.data:
            slug = r.get("agent_slug", "unknown")
            if slug not in by_agent:
                by_agent[slug] = {"runs": 0, "cost_usd": 0}
            by_agent[slug]["runs"] += 1
            by_agent[slug]["cost_usd"] += float(r.get("estimated_cost_usd", 0))

        return jsonify(success=True, data={
            "total_runs": total_runs,
            "total_cost_usd": round(total_cost, 4),
            "total_input_tokens": total_input,
            "total_output_tokens": total_output,
            "by_agent": by_agent,
            "period_start": month_start,
        })
    except Exception as e:
        return jsonify(success=False, error=str(e)), 500


@app.route("/api/billing/payments", methods=["GET"])
@require_auth
def billing_payments():
    """Get payment history for a brand."""
    brand_id = _resolve_brand_id(request.args.get("brand_slug") or request.args.get("brand_id", ""))
    if not brand_id:
        return jsonify(success=False, error="brand_slug required"), 400
    try:
        rows = _db._client.table("payments").select("*").eq("brand_id", brand_id).order("created_at", desc=True).limit(20).execute()
        return jsonify(success=True, data=rows.data)
    except Exception as e:
        return jsonify(success=False, error=str(e)), 500


@app.route("/api/billing/webhook", methods=["POST"])
def billing_webhook():
    """Razorpay webhook handler. Updates subscription/payment status."""
    sig = request.headers.get("X-Razorpay-Signature", "")
    body_raw = request.get_data(as_text=True)

    if not _razorpay_ok:
        return jsonify(success=False), 503

    # Verify signature
    if sig and not _rz.verify_webhook_signature(body_raw, sig):
        return jsonify(success=False, error="Invalid signature"), 403

    payload = request.get_json(force=True)
    event = payload.get("event", "")
    entity = payload.get("payload", {})

    try:
        if event == "subscription.authenticated":
            sub = entity.get("subscription", {}).get("entity", {})
            _db._client.table("subscriptions").update({
                "status": "authenticated",
            }).eq("razorpay_subscription_id", sub.get("id")).execute()

        elif event == "subscription.activated":
            sub = entity.get("subscription", {}).get("entity", {})
            _db._client.table("subscriptions").update({
                "status": "active",
                "current_period_start": sub.get("current_start"),
                "current_period_end": sub.get("current_end"),
            }).eq("razorpay_subscription_id", sub.get("id")).execute()

        elif event in ("subscription.cancelled", "subscription.expired"):
            sub = entity.get("subscription", {}).get("entity", {})
            new_status = "cancelled" if "cancelled" in event else "expired"
            _db._client.table("subscriptions").update({
                "status": new_status,
                "cancelled_at": sub.get("ended_at"),
            }).eq("razorpay_subscription_id", sub.get("id")).execute()

        elif event == "subscription.charged":
            pay = entity.get("payment", {}).get("entity", {})
            sub = entity.get("subscription", {}).get("entity", {})
            sub_rows = _db._client.table("subscriptions").select("id, brand_id").eq("razorpay_subscription_id", sub.get("id")).execute()
            if sub_rows.data:
                _db._client.table("payments").upsert({
                    "brand_id": sub_rows.data[0]["brand_id"],
                    "subscription_id": sub_rows.data[0]["id"],
                    "razorpay_payment_id": pay.get("id"),
                    "amount_paise": pay.get("amount", 0),
                    "currency": pay.get("currency", "INR"),
                    "status": pay.get("status", "captured"),
                    "method": pay.get("method", ""),
                }, on_conflict="razorpay_payment_id").execute()

        elif event == "payment.failed":
            pay = entity.get("payment", {}).get("entity", {})
            _db._client.table("payments").upsert({
                "razorpay_payment_id": pay.get("id"),
                "amount_paise": pay.get("amount", 0),
                "currency": pay.get("currency", "INR"),
                "status": "failed",
                "method": pay.get("method", ""),
                "brand_id": pay.get("notes", {}).get("brand_id", "00000000-0000-0000-0000-000000000000"),
            }, on_conflict="razorpay_payment_id").execute()

    except Exception as e:
        print(f"Webhook error: {e}")
        return jsonify(success=False), 500

    return jsonify(success=True), 200


# ============================================================
# REVISION LOOP — Client feedback → agent re-run with constraint
# ============================================================

@app.route("/api/outputs/revise", methods=["POST"])
@require_auth
def output_revise():
    """Request a revision on a rejected/approved output.
    Body: { brand_slug, output_id, feedback, agent_slug }
    Creates a revision record and queues a re-run with the feedback as constraint.
    """
    body = request.get_json(force=True)
    brand_slug = body.get("brand_slug", "")
    output_id = body.get("output_id", "")
    feedback = body.get("feedback", "")
    agent_slug = body.get("agent_slug", "")

    if not brand_slug or not feedback or not agent_slug:
        return jsonify(success=False, error="brand_slug, agent_slug, and feedback required"), 400

    brand_id = _resolve_brand_id(brand_slug)
    if not brand_id:
        return jsonify(success=False, error="Brand not found"), 404

    try:
        # Store revision request in audit_log
        _db._client.table("audit_log").insert({
            "brand_id": brand_id,
            "action": "revision_requested",
            "details": {
                "output_id": output_id,
                "agent_slug": agent_slug,
                "feedback": feedback,
                "requested_at": datetime.now(timezone.utc).isoformat(),
            },
        }).execute()

        # Queue agent re-run with feedback constraint
        _db._client.table("agent_runs").insert({
            "brand_id": brand_id,
            "agent_slug": agent_slug,
            "status": "queued",
            "config": {
                "revision": True,
                "original_output_id": output_id,
                "constraint": feedback,
            },
        }).execute()

        return jsonify(success=True, data={"status": "revision_queued", "agent_slug": agent_slug})
    except Exception as e:
        return jsonify(success=False, error=str(e)), 500


@app.route("/api/outputs/revisions", methods=["GET"])
@require_auth
def output_revisions():
    """Get revision history for a brand."""
    brand_slug = request.args.get("brand_slug", "")
    brand_id = _resolve_brand_id(brand_slug)
    if not brand_id:
        return jsonify(success=False, error="brand_slug required"), 400

    try:
        rows = _db._client.table("audit_log").select("*").eq("brand_id", brand_id).eq("action", "revision_requested").order("created_at", desc=True).limit(20).execute()
        return jsonify(success=True, data=rows.data)
    except Exception as e:
        return jsonify(success=False, error=str(e)), 500


# ============================================================
# TEAM ROLES — Admin / Editor / Viewer per brand
# ============================================================

@app.route("/api/team/members", methods=["GET"])
@require_auth
def team_members():
    """List team members for a brand."""
    brand_slug = request.args.get("brand_slug", "")
    brand_id = _resolve_brand_id(brand_slug)
    if not brand_id:
        return jsonify(success=False, error="brand_slug required"), 400

    try:
        rows = _db._client.table("brand_members").select("*, profiles(email, display_name)").eq("brand_id", brand_id).execute()
        return jsonify(success=True, data=rows.data)
    except Exception as e:
        return jsonify(success=False, error=str(e)), 500


@require_auth
@rate_limit(max_requests=10, window_seconds=60)
@app.route("/api/team/invite", methods=["POST"])
@require_auth
def team_invite():
    """Invite a user to a brand team.
    Body: { brand_slug, email, role }  role = admin | editor | viewer
    """
    body = request.get_json(force=True)
    brand_slug = body.get("brand_slug", "")
    email = body.get("email", "")
    role = body.get("role", "viewer")

    if not brand_slug or not email:
        return jsonify(success=False, error="brand_slug and email required"), 400
    if role not in ("admin", "editor", "viewer"):
        return jsonify(success=False, error="role must be admin, editor, or viewer"), 400

    brand_id = _resolve_brand_id(brand_slug)
    if not brand_id:
        return jsonify(success=False, error="Brand not found"), 404

    try:
        # Find user by email
        profile_rows = _db._client.table("profiles").select("id").eq("email", email).execute()
        if not profile_rows.data:
            return jsonify(success=False, error=f"No user found with email {email}"), 404

        user_id = profile_rows.data[0]["id"]

        # Check if already a member
        existing = _db._client.table("brand_members").select("id").eq("brand_id", brand_id).eq("user_id", user_id).execute()
        if existing.data:
            # Update role
            _db._client.table("brand_members").update({"role": role}).eq("brand_id", brand_id).eq("user_id", user_id).execute()
            return jsonify(success=True, data={"status": "role_updated", "role": role})

        # Insert new member
        _db._client.table("brand_members").insert({
            "brand_id": brand_id,
            "user_id": user_id,
            "role": role,
        }).execute()

        return jsonify(success=True, data={"status": "invited", "role": role})
    except Exception as e:
        return jsonify(success=False, error=str(e)), 500


@app.route("/api/team/update-role", methods=["POST"])
@require_auth
def team_update_role():
    """Update a team member's role.
    Body: { brand_slug, user_id, role }
    """
    body = request.get_json(force=True)
    brand_slug = body.get("brand_slug", "")
    user_id = body.get("user_id", "")
    role = body.get("role", "")

    if not brand_slug or not user_id or not role:
        return jsonify(success=False, error="brand_slug, user_id, and role required"), 400
    if role not in ("admin", "editor", "viewer"):
        return jsonify(success=False, error="role must be admin, editor, or viewer"), 400

    brand_id = _resolve_brand_id(brand_slug)
    if not brand_id:
        return jsonify(success=False, error="Brand not found"), 404

    try:
        _db._client.table("brand_members").update({"role": role}).eq("brand_id", brand_id).eq("user_id", user_id).execute()
        return jsonify(success=True, data={"status": "updated", "role": role})
    except Exception as e:
        return jsonify(success=False, error=str(e)), 500


@app.route("/api/team/remove", methods=["POST"])
@require_auth
def team_remove():
    """Remove a team member from a brand.
    Body: { brand_slug, user_id }
    """
    body = request.get_json(force=True)
    brand_slug = body.get("brand_slug", "")
    user_id = body.get("user_id", "")

    if not brand_slug or not user_id:
        return jsonify(success=False, error="brand_slug and user_id required"), 400

    brand_id = _resolve_brand_id(brand_slug)
    if not brand_id:
        return jsonify(success=False, error="Brand not found"), 404

    try:
        _db._client.table("brand_members").delete().eq("brand_id", brand_id).eq("user_id", user_id).execute()
        return jsonify(success=True, data={"status": "removed"})
    except Exception as e:
        return jsonify(success=False, error=str(e)), 500


# ============================================================
# EMAIL NOTIFICATIONS — Approval alerts
# ============================================================

@app.route("/api/notifications/pending-summary", methods=["GET"])
@require_auth
def notifications_pending_summary():
    """Get count of pending approvals per brand for email digest."""
    brand_slug = request.args.get("brand_slug", "")
    brand_id = _resolve_brand_id(brand_slug)
    if not brand_id:
        return jsonify(success=False, error="brand_slug required"), 400

    try:
        rows = _db._client.table("agent_outputs").select("id, agent_slug, created_at").eq("brand_id", brand_id).eq("approval_status", "pending").execute()
        pending_count = len(rows.data)
        by_agent = {}
        for r in rows.data:
            slug = r.get("agent_slug", "unknown")
            by_agent[slug] = by_agent.get(slug, 0) + 1

        return jsonify(success=True, data={
            "pending_count": pending_count,
            "by_agent": by_agent,
            "brand_id": brand_id,
        })
    except Exception as e:
        return jsonify(success=False, error=str(e)), 500


@app.route("/api/notifications/send-digest", methods=["POST"])
@require_auth
def notifications_send_digest():
    """Send an email digest of pending approvals.
    Body: { brand_slug, recipient_email }
    Uses Gmail MCP if available, otherwise returns the email content for manual send.
    """
    body = request.get_json(force=True)
    brand_slug = body.get("brand_slug", "")
    recipient = body.get("recipient_email", "")

    if not brand_slug:
        return jsonify(success=False, error="brand_slug required"), 400

    brand_id = _resolve_brand_id(brand_slug)
    if not brand_id:
        return jsonify(success=False, error="Brand not found"), 404

    try:
        rows = _db._client.table("agent_outputs").select("agent_slug, created_at").eq("brand_id", brand_id).eq("approval_status", "pending").execute()
        pending_count = len(rows.data)

        if pending_count == 0:
            return jsonify(success=True, data={"status": "no_pending", "message": "No pending approvals"})

        # Build email content
        by_agent = {}
        for r in rows.data:
            slug = r.get("agent_slug", "unknown")
            by_agent[slug] = by_agent.get(slug, 0) + 1

        agent_lines = "\n".join([f"  • {slug}: {count} item{'s' if count > 1 else ''}" for slug, count in by_agent.items()])
        dashboard_url = "https://v0-grid-control-dashboard.vercel.app/review"

        email_subject = f"[Grid Control] {pending_count} items awaiting your approval"
        email_body = f"""Hi,

You have {pending_count} content item{'s' if pending_count > 1 else ''} waiting for approval in Grid Control:

{agent_lines}

Review them now: {dashboard_url}

— Grid Control AI"""

        return jsonify(success=True, data={
            "status": "digest_ready",
            "pending_count": pending_count,
            "subject": email_subject,
            "body": email_body,
            "recipient": recipient,
        })
    except Exception as e:
        return jsonify(success=False, error=str(e)), 500


# ============================================================
# CONTINUOUS LEARNING — Auto-capture agent patterns per brand
# ============================================================

@app.route("/api/learning/capture", methods=["POST"])
@require_auth
def learning_capture():
    """Capture a learning/pattern from an agent run.
    Body: { brand_slug, agent_slug, learning_type, content, source_run_id }
    learning_type: winning_pattern | dead_pattern | audience_insight | voice_refinement
    """
    body = request.get_json(force=True)
    brand_slug = body.get("brand_slug", "")
    agent_slug = body.get("agent_slug", "")
    learning_type = body.get("learning_type", "")
    content = body.get("content", "")
    source_run_id = body.get("source_run_id", "")

    if not brand_slug or not agent_slug or not content:
        return jsonify(success=False, error="brand_slug, agent_slug, and content required"), 400

    brand_id = _resolve_brand_id(brand_slug)
    if not brand_id:
        return jsonify(success=False, error="Brand not found"), 404

    try:
        memory_key = f"{learning_type or 'general'}_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}"
        _db._client.table("brand_memory").insert({
            "brand_id": brand_id,
            "agent_slug": agent_slug,
            "memory_key": memory_key,
            "content": content,
        }).execute()

        # Also log to audit
        _db._client.table("audit_log").insert({
            "brand_id": brand_id,
            "action": "learning_captured",
            "details": {
                "agent_slug": agent_slug,
                "learning_type": learning_type,
                "memory_key": memory_key,
                "source_run_id": source_run_id,
            },
        }).execute()

        return jsonify(success=True, data={"status": "captured", "memory_key": memory_key})
    except Exception as e:
        return jsonify(success=False, error=str(e)), 500


@app.route("/api/learning/list", methods=["GET"])
@require_auth
def learning_list():
    """List captured learnings for a brand, optionally filtered by agent."""
    brand_slug = request.args.get("brand_slug", "")
    agent_slug = request.args.get("agent_slug", "")

    brand_id = _resolve_brand_id(brand_slug)
    if not brand_id:
        return jsonify(success=False, error="brand_slug required"), 400

    try:
        q = _db._client.table("brand_memory").select("*").eq("brand_id", brand_id)
        if agent_slug:
            q = q.eq("agent_slug", agent_slug)
        rows = q.order("created_at", desc=True).limit(50).execute()

        return jsonify(success=True, data=rows.data)
    except Exception as e:
        return jsonify(success=False, error=str(e)), 500


@app.route("/api/learning/stats", methods=["GET"])
@require_auth
def learning_stats():
    """Get learning stats for a brand — 'your agents learned X things this month'."""
    brand_slug = request.args.get("brand_slug", "")
    brand_id = _resolve_brand_id(brand_slug)
    if not brand_id:
        return jsonify(success=False, error="brand_slug required"), 400

    try:
        month_start = datetime.now(timezone.utc).replace(day=1, hour=0, minute=0, second=0).isoformat()
        rows = _db._client.table("brand_memory").select("agent_slug, created_at").eq("brand_id", brand_id).gte("created_at", month_start).execute()

        total = len(rows.data)
        by_agent = {}
        for r in rows.data:
            slug = r.get("agent_slug", "unknown")
            by_agent[slug] = by_agent.get(slug, 0) + 1

        all_time = _db._client.table("brand_memory").select("id", count="exact").eq("brand_id", brand_id).execute()

        return jsonify(success=True, data={
            "this_month": total,
            "all_time": all_time.count if hasattr(all_time, 'count') else len(all_time.data),
            "by_agent": by_agent,
        })
    except Exception as e:
        return jsonify(success=False, error=str(e)), 500


# ============================================================
# ADMIN — Super Admin Endpoints (Grid Control owner only)
# ============================================================

@app.route("/api/admin/check", methods=["GET"])
@require_auth
def admin_check():
    """Check if the current user is a super admin."""
    user = getattr(request, "user", None)
    if not user or not _DB_AVAILABLE:
        return jsonify(success=True, data={"is_admin": False})
    is_admin = _db.is_super_admin(user["id"])
    return jsonify(success=True, data={"is_admin": is_admin})


@app.route("/api/admin/overview", methods=["GET"])
@require_auth
@require_super_admin
def admin_overview():
    """Business overview — MRR, client count, costs, agent stats."""
    try:
        from datetime import datetime
        now = datetime.now()
        month_start = now.replace(day=1, hour=0, minute=0, second=0).isoformat()

        brands = _db.get_all_brands()
        subscriptions = _db.get_all_subscriptions()
        usage = _db.get_global_usage_stats(month_start)
        payments = _db.get_all_payments(limit=50)

        # MRR from active subscriptions
        active_subs = [s for s in subscriptions if s.get("status") == "active"]
        mrr_paise = sum(
            (s.get("billing_plans") or {}).get("amount_paise", 0)
            for s in active_subs
        )

        # Total API cost this month
        total_cost = sum(float(r.get("estimated_cost_usd", 0)) for r in usage)
        total_runs = len(usage)

        # Agent breakdown
        agent_breakdown = {}
        for r in usage:
            slug = r.get("agent_slug", "unknown")
            if slug not in agent_breakdown:
                agent_breakdown[slug] = {"runs": 0, "cost_usd": 0.0}
            agent_breakdown[slug]["runs"] += 1
            agent_breakdown[slug]["cost_usd"] += float(r.get("estimated_cost_usd", 0))

        # Brand breakdown
        brand_map = {b["id"]: b for b in brands}
        brand_costs = {}
        for r in usage:
            bid = r.get("brand_id", "unknown")
            bname = (brand_map.get(bid) or {}).get("name", bid[:8])
            if bname not in brand_costs:
                brand_costs[bname] = {"runs": 0, "cost_usd": 0.0}
            brand_costs[bname]["runs"] += 1
            brand_costs[bname]["cost_usd"] += float(r.get("estimated_cost_usd", 0))

        # Revenue from payments this month
        month_revenue_paise = sum(
            p.get("amount_paise", 0)
            for p in payments
            if p.get("status") == "captured" and p.get("created_at", "") >= month_start
        )

        return jsonify(success=True, data={
            "total_brands": len(brands),
            "active_subscriptions": len(active_subs),
            "mrr_paise": mrr_paise,
            "mrr_inr": round(mrr_paise / 100, 2),
            "month_revenue_paise": month_revenue_paise,
            "month_revenue_inr": round(month_revenue_paise / 100, 2),
            "total_cost_usd": round(total_cost, 4),
            "total_runs_this_month": total_runs,
            "agent_breakdown": agent_breakdown,
            "brand_costs": brand_costs,
            "profit_margin_pct": round(
                ((month_revenue_paise / 100 * 0.012) - total_cost) / max(total_cost, 0.01) * 100, 1
            ) if total_cost > 0 else 0,
        })
    except Exception as e:
        return jsonify(success=False, error=str(e)), 500


@app.route("/api/admin/clients", methods=["GET"])
@require_auth
@require_super_admin
def admin_clients():
    """All brands with owner info, plan, status, costs."""
    try:
        from datetime import datetime
        month_start = datetime.now().replace(day=1, hour=0, minute=0, second=0).isoformat()

        brands = _db.get_all_brands()
        members = _db.get_all_brand_members()
        subscriptions = _db.get_all_subscriptions()
        usage = _db.get_global_usage_stats(month_start)

        # Index subscriptions by brand_id
        sub_by_brand = {}
        for s in subscriptions:
            sub_by_brand[s.get("brand_id")] = s

        # Index members by brand_id (find admin/owner)
        owners_by_brand = {}
        for m in members:
            if m.get("role") == "admin":
                profile = m.get("profiles") or {}
                owners_by_brand[m.get("brand_id")] = {
                    "email": profile.get("email", ""),
                    "name": profile.get("full_name", ""),
                }

        # Cost by brand this month
        cost_by_brand = {}
        for r in usage:
            bid = r.get("brand_id", "")
            cost_by_brand[bid] = cost_by_brand.get(bid, 0) + float(r.get("estimated_cost_usd", 0))

        clients = []
        for b in brands:
            bid = b["id"]
            sub = sub_by_brand.get(bid) or {}
            plan = sub.get("billing_plans") or {}
            owner = owners_by_brand.get(bid) or {}
            clients.append({
                "id": bid,
                "slug": b["slug"],
                "name": b["name"],
                "created_at": b.get("created_at"),
                "owner_name": owner.get("name", "—"),
                "owner_email": owner.get("email", "—"),
                "plan": plan.get("name", "Free"),
                "plan_amount_paise": plan.get("amount_paise", 0),
                "subscription_status": sub.get("status", "none"),
                "cost_usd_this_month": round(cost_by_brand.get(bid, 0), 4),
            })

        return jsonify(success=True, data=clients)
    except Exception as e:
        return jsonify(success=False, error=str(e)), 500


@app.route("/api/admin/revenue", methods=["GET"])
@require_auth
@require_super_admin
def admin_revenue():
    """Payment history + MRR timeline."""
    try:
        payments = _db.get_all_payments(limit=100)
        subscriptions = _db.get_all_subscriptions()

        active_subs = [s for s in subscriptions if s.get("status") == "active"]
        mrr_paise = sum(
            (s.get("billing_plans") or {}).get("amount_paise", 0)
            for s in active_subs
        )

        return jsonify(success=True, data={
            "mrr_paise": mrr_paise,
            "mrr_inr": round(mrr_paise / 100, 2),
            "active_subscriptions": len(active_subs),
            "total_subscriptions": len(subscriptions),
            "recent_payments": payments,
        })
    except Exception as e:
        return jsonify(success=False, error=str(e)), 500


@app.route("/api/admin/system", methods=["GET"])
@require_auth
@require_super_admin
def admin_system():
    """System health — agent runs, error rates, cost breakdown."""
    try:
        runs = _db.get_all_agent_runs(limit=200)

        total = len(runs)
        errors = sum(1 for r in runs if r.get("status") == "error")
        successes = sum(1 for r in runs if r.get("status") == "success")
        running = sum(1 for r in runs if r.get("status") == "running")

        # Cost by model
        cost_by_model = {}
        for r in runs:
            model = r.get("model", "unknown")
            cost = float(r.get("api_cost_usd", 0) or 0)
            if model not in cost_by_model:
                cost_by_model[model] = {"runs": 0, "cost_usd": 0.0}
            cost_by_model[model]["runs"] += 1
            cost_by_model[model]["cost_usd"] += cost

        # Recent errors
        recent_errors = [
            {
                "agent": r.get("agent_slug"),
                "brand": (r.get("brands") or {}).get("name", ""),
                "error": (r.get("error_message") or "")[:200],
                "at": r.get("started_at"),
            }
            for r in runs if r.get("status") == "error"
        ][:10]

        total_api_cost = sum(float(r.get("api_cost_usd", 0) or 0) for r in runs)
        total_fal_cost = sum(float(r.get("fal_cost_usd", 0) or 0) for r in runs)
        total_apify_cost = sum(float(r.get("apify_cost_usd", 0) or 0) for r in runs)

        return jsonify(success=True, data={
            "total_runs": total,
            "successes": successes,
            "errors": errors,
            "running": running,
            "error_rate_pct": round(errors / max(total, 1) * 100, 1),
            "cost_by_model": cost_by_model,
            "total_api_cost_usd": round(total_api_cost, 4),
            "total_fal_cost_usd": round(total_fal_cost, 4),
            "total_apify_cost_usd": round(total_apify_cost, 4),
            "total_cost_usd": round(total_api_cost + total_fal_cost + total_apify_cost, 4),
            "recent_errors": recent_errors,
        })
    except Exception as e:
        return jsonify(success=False, error=str(e)), 500


# ── Phase C — real data endpoints for the future cockpit ──────────────────────

@app.route("/api/brands/<brand_slug>/runs", methods=["GET"])
@require_auth
def brand_agent_runs(brand_slug: str):
    """Return recent agent runs with cost data for this brand.
    Query params: limit (default 50), status (filter by status string).
    """
    brand_id, err = _authorize_brand(brand_slug)
    if err:
        return err
    limit = min(int(request.args.get("limit", 50)), 200)
    status_filter = request.args.get("status", "").strip()
    try:
        q = (
            _db._svc().table("agent_runs")
            .select(
                "id, agent_slug, status, model, "
                "input_tokens, output_tokens, api_cost_usd, fal_cost_usd, apify_cost_usd, "
                "fal_generations, apify_runs, started_at, completed_at, error"
            )
            .eq("brand_id", brand_id)
            .order("started_at", desc=True)
            .limit(limit)
        )
        if status_filter:
            q = q.eq("status", status_filter)
        rows = q.execute().data or []
        # Add total_cost_usd for convenience
        for r in rows:
            r["total_cost_usd"] = round(
                float(r.get("api_cost_usd") or 0)
                + float(r.get("fal_cost_usd") or 0)
                + float(r.get("apify_cost_usd") or 0),
                6,
            )
        return jsonify(success=True, data={"runs": rows, "count": len(rows)})
    except Exception as e:
        return jsonify(success=False, error=str(e)), 500


@app.route("/api/brands/<brand_slug>/narrative", methods=["GET"])
@require_auth
def brand_narrative(brand_slug: str):
    """Return the brand's story-so-far narrative (Phase A).
    Query params: n (default 20, max 100), agent (filter by agent slug).
    The narrative feeds the 'Story So Far' block in the cockpit.
    """
    brand_id, err = _authorize_brand(brand_slug)
    if err:
        return err
    n = min(int(request.args.get("n", 20)), 100)
    agent_filter = request.args.get("agent", "").strip() or None
    try:
        entries = _db.get_narrative(brand_id, n=n, agent=agent_filter)
        return jsonify(success=True, data={"entries": entries, "count": len(entries)})
    except Exception as e:
        return jsonify(success=False, error=str(e)), 500


@app.route("/api/brands/<brand_slug>/narrative", methods=["POST"])
@require_auth
def append_brand_narrative(brand_slug: str):
    """Append one entry to the brand narrative.
    Body: { agent, entry_type (decision|action|result), summary, refs? }
    """
    brand_id, err = _authorize_brand(brand_slug)
    if err:
        return err
    body = request.get_json(force=True) or {}
    agent = body.get("agent", "").strip()
    entry_type = body.get("entry_type", "action").strip()
    summary = body.get("summary", "").strip()
    if not agent or not summary:
        return jsonify(success=False, error="agent and summary required"), 400
    try:
        row = _db.append_narrative(
            brand_id, agent, entry_type, summary, refs=body.get("refs")
        )
        return jsonify(success=True, data=row)
    except Exception as e:
        return jsonify(success=False, error=str(e)), 500


if __name__ == "__main__":
    print("GRID CONTROL Flask API — port 5001")
    app.run(host="0.0.0.0", port=5001, debug=False)
