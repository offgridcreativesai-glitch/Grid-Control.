"""routes/agents.py — GRID CONTROL agents endpoints (blueprint). S2b split."""
from core import *  # noqa: F401,F403  (app, helpers, stdlib re-exports)
from flask import Blueprint

bp = Blueprint("agents", __name__)



# ── Agents ────────────────────────────────────────────────────────────────────

@bp.route("/api/agents/status", methods=["GET"])
@require_auth
def get_agents_status():
    # DB-WIRED Step 5
    brand_slug = require_brand_slug()
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


@bp.route("/api/agents/list", methods=["GET"])
@require_auth
def get_agents_list():
    return jsonify({"success": True, "data": AGENTS_ENRICHED})


@bp.route("/api/agents/run", methods=["POST"])
@rate_limit(max_requests=5, window_seconds=60)
@require_auth
def run_agent():
    body = request.get_json() or {}
    agent_name = body.get("agentName", "").strip()
    brand_slug = require_brand_slug()
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

    # Phase H — Brand-Book Foundation gate (hard gate per dependency-chain rule)
    # Strategy Agent and Content Planner require an approved Brand Foundation before they run.
    _gate_slug = _agent_name_to_slug(agent_name)
    if _gate_slug in ("strategy-agent", "content-planner"):
        _bb = _brand_book_status(brand_slug)
        if _bb.get("status") != "approved":
            return jsonify({
                "success": False,
                "error": (
                    "Brand Foundation not approved. "
                    "Complete the Brand-Book sign-off (Step 3.5) before running "
                    "Strategy Agent or Content Planner. "
                    f"Current status: {_bb.get('status', 'none')}."
                ),
                "gate": "brand_book_foundation",
                "brand_book_status": _bb.get("status", "none"),
            }), 403

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


@bp.route("/api/agents/run/status", methods=["GET"])
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


# ── BUILD C — PERFORMANCE FEEDBACK LOOP ──────────────────────────────────────

@bp.route("/api/performance/log-post", methods=["POST"])
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


@bp.route("/api/performance/history", methods=["GET"])
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


@bp.route("/api/analysis/latest", methods=["GET"])
@require_auth
def analysis_latest():
    """The Data Analyst's latest CONCLUSION (not just raw metrics) for the cockpit.
    Reads the newest Data Analyst weekly report (approved first, else pending), strips the
    LOOP header, and returns the winning analysis: the lead insight, confidence, ranked
    next actions, and any anomalies. Honest-empty when no analysis has run yet."""
    brand_slug = request.args.get("brand_slug", "").strip()
    if not brand_slug or not _validate_brand_slug(brand_slug):
        return jsonify({"success": False, "error": "Valid brand_slug required"}), 400

    brand_dir = BRANDS_DIR / brand_slug
    candidates = []
    for sub in ("outputs/approved", "outputs/pending_approval/Data Analyst",
                "outputs/pending_approval/data-analyst"):
        d = brand_dir / sub
        if d.exists():
            candidates += [p for p in d.rglob("*weekly_report.json") if p.is_file()]
    if not candidates:
        return jsonify({"success": True, "data": {"exists": False}})

    latest = max(candidates, key=lambda p: p.stat().st_mtime)
    try:
        raw = latest.read_text(errors="replace")
        body = raw.split("\n---\n", 1)[1].strip() if "\n---\n" in raw else raw
        report = json.loads(body)
    except Exception as e:
        return jsonify({"success": False, "error": f"could not parse analysis: {e}"}), 500

    win = report.get("winning_analysis") or {}
    actions = win.get("next_actions") or []
    actions = sorted(
        [a for a in actions if isinstance(a, dict) and a.get("action")],
        key=lambda a: a.get("priority", 99),
    )
    return jsonify({"success": True, "data": {
        "exists": True,
        "report_week": report.get("report_week", ""),
        "generated_at": report.get("generated_at", ""),
        "lead_insight": win.get("lead_insight", ""),
        "confidence": (win.get("confidence") or "").lower(),
        "next_actions": actions,
        "anomalies": win.get("anomalies_detected") or [],
        "repurposing": win.get("repurposing_candidates") or [],
        "data_quality_note": report.get("data_quality_note", ""),
    }})


@bp.route("/api/listening", methods=["GET"])
@require_auth
def listening_get():
    """Cached social-listening result for the brand (what the internet is saying)."""
    brand_slug = request.args.get("brand_slug", "").strip()
    if not brand_slug or not _validate_brand_slug(brand_slug):
        return jsonify({"success": False, "error": "Valid brand_slug required"}), 400
    p = BRANDS_DIR / brand_slug / "social_listening.json"
    if not p.exists():
        return jsonify({"success": True, "data": {"status": "none"}})
    try:
        return jsonify({"success": True, "data": json.loads(p.read_text())})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@bp.route("/api/listening/run", methods=["POST"])
@require_auth
@require_brand_access
def listening_run():
    """Run social listening now (real Bright Data SERP search). Cost-gated by GRID_PAID_OPS
    inside the module — returns a 'blocked' status if paid ops are off. Runs as a subprocess
    (never imports agents into the API process)."""
    body = request.get_json(silent=True) or {}
    brand_slug = (body.get("brand_slug") or "").strip()
    if not brand_slug or not _validate_brand_slug(brand_slug):
        return jsonify({"success": False, "error": "Valid brand_slug required"}), 400
    script = BASE_DIR / "agents" / "intel" / "social_listening.py"
    env = os.environ.copy()
    env["ACTIVE_BRAND"] = brand_slug
    env.update({k: v for k, v in brand_env(brand_slug).items() if v})
    try:
        res = subprocess.run([sys.executable, str(script), brand_slug], env=env,
                             capture_output=True, text=True, timeout=120, cwd=str(BASE_DIR))
    except subprocess.TimeoutExpired:
        return jsonify({"success": False, "error": "listening run timed out (>2min)"}), 504
    p = BRANDS_DIR / brand_slug / "social_listening.json"
    if p.exists():
        try:
            return jsonify({"success": True, "data": json.loads(p.read_text())})
        except Exception:
            pass
    # No file written → surface the module's honest status (blocked / no_provider / no identity).
    return jsonify({"success": True, "data": {
        "status": "not_run",
        "note": (res.stdout or res.stderr or "").strip()[-300:],
    }})


@bp.route("/api/reputation", methods=["GET"])
@require_auth
def reputation_get():
    """Cached reputation result (star rating + per-platform reviews + what needs a response)."""
    brand_slug = request.args.get("brand_slug", "").strip()
    if not brand_slug or not _validate_brand_slug(brand_slug):
        return jsonify({"success": False, "error": "Valid brand_slug required"}), 400
    p = BRANDS_DIR / brand_slug / "reputation.json"
    if not p.exists():
        return jsonify({"success": True, "data": {"status": "none"}})
    try:
        return jsonify({"success": True, "data": json.loads(p.read_text())})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@bp.route("/api/reputation/run", methods=["POST"])
@require_auth
@require_brand_access
def reputation_run():
    """Run the reputation engine now (real Bright Data SERP over review sites). Cost-gated by
    GRID_PAID_OPS inside the module. Subprocess, same pattern as listening."""
    body = request.get_json(silent=True) or {}
    brand_slug = (body.get("brand_slug") or "").strip()
    if not brand_slug or not _validate_brand_slug(brand_slug):
        return jsonify({"success": False, "error": "Valid brand_slug required"}), 400
    script = BASE_DIR / "agents" / "intel" / "reputation.py"
    env = os.environ.copy()
    env["ACTIVE_BRAND"] = brand_slug
    env.update({k: v for k, v in brand_env(brand_slug).items() if v})
    try:
        res = subprocess.run([sys.executable, str(script), brand_slug], env=env,
                             capture_output=True, text=True, timeout=120, cwd=str(BASE_DIR))
    except subprocess.TimeoutExpired:
        return jsonify({"success": False, "error": "reputation run timed out (>2min)"}), 504
    p = BRANDS_DIR / brand_slug / "reputation.json"
    if p.exists():
        try:
            return jsonify({"success": True, "data": json.loads(p.read_text())})
        except Exception:
            pass
    return jsonify({"success": True, "data": {
        "status": "not_run",
        "note": (res.stdout or res.stderr or "").strip()[-300:],
    }})


# ── BUILD D — CROSS-AGENT CONTRADICTION DETECTOR ─────────────────────────────

@bp.route("/api/contradictions/check", methods=["POST", "GET"])
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


@bp.route("/api/contradictions/latest", methods=["GET"])
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


@bp.route("/api/performance/inbox", methods=["GET"])
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


@bp.route("/api/agents/conversation", methods=["GET"])
@require_auth
def get_conversation():
    """Return persisted conversation history for a brand+agent pair."""
    brand_slug = require_brand_slug()
    agent_slug = request.args.get("agent_slug", "")
    if not agent_slug:
        return jsonify({"success": False, "error": "agent_slug required"}), 400
    history = _load_conversation(brand_slug, agent_slug)
    return jsonify({"success": True, "data": history})


@bp.route("/api/agents/chat", methods=["POST"])
@require_auth
def agent_chat():
    import anthropic as _anthropic

    body = request.get_json() or {}
    agent_name  = body.get("agentName", "").strip()
    user_msg    = body.get("message", "").strip()
    brand_slug  = require_brand_slug()
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


@bp.route("/api/agents/group-chat", methods=["POST"])
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
    brand_slug = require_brand_slug()
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


@bp.route("/api/agents/request-changes", methods=["POST"])
@require_auth
def agent_request_changes():
    """Save feedback for an agent, reset its status to idle so it can be re-run."""
    body = request.get_json() or {}
    brand_slug = require_brand_slug()
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


@bp.route("/api/agents/train", methods=["POST"])
@require_auth
def agent_train():
    body = request.get_json() or {}
    agent_name  = body.get("agentName", "unknown").strip()
    note        = body.get("note", "").strip()
    brand_slug  = require_brand_slug()

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


@bp.route("/api/agents/output/history", methods=["GET"])
@require_auth
def get_agent_output_history():
    """Return version history for an agent's outputs. Phase 1 Step 3."""
    brand_slug = require_brand_slug()
    agent_slug = request.args.get("agent_slug", "")
    if not agent_slug:
        return jsonify({"success": False, "error": "agent_slug required"}), 400

    if _DB_AVAILABLE:
        brand_id = _get_brand_id(brand_slug)
        if brand_id:
            rows = _db.get_output_history(brand_id, agent_slug)
            return jsonify({"success": True, "data": rows})

    return jsonify({"success": True, "data": []})


@bp.route("/api/agents/output", methods=["GET"])
@require_auth
def get_agent_output():
    # DB-WIRED Step 5 + Phase 1 Step 3
    from utils.output_formatter import format_for_notion, format_scripts, format_calendar, format_strategy
    brand_slug = require_brand_slug()
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


@bp.route("/api/agents/log", methods=["GET"])
@require_auth
def get_agent_log():
    brand_slug = require_brand_slug()
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


# ── Per-brand agent config (which of the 18 agents are on + tuning) ────────────
@bp.route("/api/agent-config", methods=["GET", "PUT"])
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


# ============================================================
# CONTINUOUS LEARNING — Auto-capture agent patterns per brand
# ============================================================

@bp.route("/api/learning/capture", methods=["POST"])
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


@bp.route("/api/learning/list", methods=["GET"])
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


@bp.route("/api/learning/stats", methods=["GET"])
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
