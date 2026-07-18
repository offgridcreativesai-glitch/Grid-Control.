"""routes/system.py — GRID CONTROL system endpoints (blueprint). S2b split."""
from core import *  # noqa: F401,F403  (app, helpers, stdlib re-exports)
from datetime import timedelta
from flask import Blueprint

bp = Blueprint("system", __name__)




@bp.route("/api/events", methods=["GET"])
def sse_events():
    """Global SSE stream — client subscribes to get live agent activity updates.

    EventSource cannot set Authorization headers, so auth is via ?token=
    (Supabase JWT) only. Deny-by-default. (Jul 6: dropped the legacy
    ?secret= dashboard-secret fallback — see require_auth's docstring in
    core.py for why that secret is retired everywhere.)
    """
    token = request.args.get("token", "")
    authed = False
    if token and _DB_AVAILABLE:
        try:
            authed = bool(_db.verify_jwt(token))
        except Exception:
            authed = False
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


@bp.route("/api/scheduler/trigger", methods=["POST"])
def scheduler_trigger():
    """Service-to-service: run a pipeline for a brand. Token-authed.
    Body: { brand_slug, pipeline? }. pipeline defaults to "daily"; "weekly" runs
    the proactive weekly operating program (run_weekly_program); "monthly" runs
    the monthly mix-review cadence (run_monthly_program); "quarterly" runs the
    QBR cadence (run_quarterly_program). Returns immediately; pipeline runs in
    background."""
    if not _valid_service_token():
        return jsonify({"success": False, "error": "invalid service token"}), 401
    data = request.get_json(silent=True) or {}
    brand_slug = (data.get("brand_slug") or "").strip()
    pipeline = (data.get("pipeline") or "daily").strip().lower()
    if pipeline == "ops":
        # Platform-level production-health audit — no brand, $0, no model.
        from agents.ops_auditor import run_audit
        threading.Thread(target=run_audit, daemon=True).start()
        return jsonify({"success": True, "data": {"message": "ops audit started",
                        "pipeline": "ops"}})
    if not brand_slug:
        return jsonify({"success": False, "error": "brand_slug required"}), 400
    if not re.fullmatch(r"[a-z0-9][a-z0-9_-]{0,63}", brand_slug):
        # path-traversal guard: slug becomes a directory name below
        return jsonify({"success": False, "error": "invalid brand_slug"}), 400
    if not (BRANDS_DIR / brand_slug).is_dir():
        return jsonify({"success": False, "error": f"Brand '{brand_slug}' not found"}), 404
    pipelines = {
        "daily": run_daily_pipeline,
        "weekly": run_weekly_program,
        "monthly": run_monthly_program,
        "quarterly": run_quarterly_program,
    }
    if pipeline not in pipelines:
        return jsonify({"success": False, "error": f"unknown pipeline '{pipeline}'"}), 400
    target = pipelines[pipeline]
    print(f"[scheduler-trigger] {pipeline} pipeline for {brand_slug} (service token)")
    threading.Thread(target=target, args=(brand_slug,), daemon=True).start()
    return jsonify({"success": True, "data": {
        "message": f"{pipeline} pipeline started for {brand_slug}",
        "brand_slug": brand_slug,
        "pipeline": pipeline,
        "started_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
    }})


@bp.route("/api/ops/health", methods=["GET"])
@require_auth
@require_super_admin
def ops_health():
    """Latest Production Health card (markdown) — super-admin only."""
    md = Path(BASE_DIR) / ".grid_state" / "ops_health_latest.md"
    if not md.exists():
        return jsonify({"success": True, "data": {
            "markdown": None,
            "note": "No audit has run yet — trigger the ops pipeline or run agents/ops_auditor.py.",
        }})
    return jsonify({"success": True, "data": {"markdown": md.read_text()}})


# ── n8n Webhook Receiver ───────────────────────────────────────────────────────

@bp.route("/api/webhooks/n8n", methods=["POST"])
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

    # In-flight lock (reusable — also guards run_weekly_program's own dispatch)
    agent_slug_key = _agent_name_to_slug(agent_name)
    if _agent_already_running(brand_slug, agent_slug_key):
        return jsonify({"success": False, "error": "Agent already running"}), 409

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


# ── Week view (client operating rhythm) ──────────────────────────────────────

@bp.route("/api/week", methods=["GET"])
@require_auth
def week_view():
    """The client's operating rhythm in one call — what RAN this week, what is
    WAITING on them, what is COMING UP. Feeds the Command Center "Your week"
    panel so a non-technical owner can feel the agency cycle working.

    Returns: { ran: [{agent_slug, status, started_at, completed_at}],
               waiting: {count, by_agent},
               next: [{pipeline, day_of_week, hour, minute, enabled}] }
    """
    brand_slug = (request.args.get("brand_slug") or "").strip()
    if not brand_slug or not re.fullmatch(r"[a-z0-9][a-z0-9_-]{0,63}", brand_slug):
        return jsonify({"success": False, "error": "brand_slug required"}), 400

    ran: list = []
    waiting = {"count": 0, "by_agent": {}}

    if _DB_AVAILABLE:
        brand_id = _resolve_brand_id(brand_slug)
        if brand_id:
            since = (datetime.now(timezone.utc) - timedelta(days=7)).strftime("%Y-%m-%dT%H:%M:%SZ")
            try:
                ran = _db.get_brand_agent_runs(brand_id, since_iso=since, limit=50)
            except Exception:
                ran = []
            try:
                rows = (_db._client.table("agent_outputs")
                        .select("agent_slug")
                        .eq("brand_id", brand_id)
                        .eq("approval_status", "pending").execute())
                waiting["count"] = len(rows.data)
                for r in rows.data:
                    slug = r.get("agent_slug", "unknown")
                    waiting["by_agent"][slug] = waiting["by_agent"].get(slug, 0) + 1
            except Exception:
                pass

    # Disk fallback for pending count (file-based approval queue)
    if waiting["count"] == 0:
        pending_dir = BRANDS_DIR / brand_slug / "outputs" / "pending_approval"
        if pending_dir.is_dir():
            for agent_dir in pending_dir.iterdir():
                if agent_dir.is_dir():
                    n = len([f for f in agent_dir.iterdir() if f.is_file()])
                    if n:
                        waiting["by_agent"][agent_dir.name] = n
                        waiting["count"] += n

    # Upcoming scheduled pipelines for this brand from scheduler config
    upcoming: list = []
    try:
        cfg_path = BASE_DIR / "scheduler" / "schedule_config.json"
        if cfg_path.exists():
            cfg = json.loads(cfg_path.read_text())
            for job in cfg.get("jobs", []):
                if job.get("brand_slug") != brand_slug or job.get("enabled") is False:
                    continue
                upcoming.append({
                    "pipeline": job.get("pipeline", "daily"),
                    "day_of_week": job.get("cron", {}).get("day_of_week"),
                    "hour": job.get("cron", {}).get("hour"),
                    "minute": job.get("cron", {}).get("minute"),
                })
    except Exception as e:
        print(f"[week] schedule_config read failed: {e}")

    return jsonify({"success": True, "data": {
        "ran": ran, "waiting": waiting, "next": upcoming,
    }})


# ── Health + Config ───────────────────────────────────────────────────────────

@bp.route("/api/health", methods=["GET"])
def health():
    return jsonify({"success": True, "data": {"status": "GRID CONTROL API running", "port": 5001}})


@bp.route("/api/config/keys", methods=["GET"])
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


# ============================================================
# EMAIL NOTIFICATIONS — Approval alerts
# ============================================================

@bp.route("/api/notifications/pending-summary", methods=["GET"])
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


@bp.route("/api/notifications/send-digest", methods=["POST"])
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
