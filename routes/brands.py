"""routes/brands.py — GRID CONTROL brands endpoints (blueprint). S2b split."""
from core import *  # noqa: F401,F403  (app, helpers, stdlib re-exports)
from flask import Blueprint

bp = Blueprint("brands", __name__)



# ── Auth ──────────────────────────────────────────────────────────────────────

@bp.route("/api/auth/me", methods=["GET"])
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


@bp.route("/api/auth/brands", methods=["GET"])
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


@bp.route("/api/auth/create-brand", methods=["POST"])
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


# ── BRAND FILE READER (used by InsightsSpace provenance audit) ───────────────

@bp.route("/api/brand/file", methods=["GET"])
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


# ── Cost Tracking ─────────────────────────────────────────────────────────────

@bp.route("/api/brands/<brand_slug>/costs", methods=["GET"])
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

    brand_id, err = _authorize_brand(brand_slug)   # W3.1 authz sweep
    if err:
        return err

    data = _db.get_brand_monthly_costs(brand_id, year, month)
    return jsonify({"success": True, "data": data})


@bp.route("/api/brands/<brand_slug>/costs/record", methods=["POST"])
@require_auth
def record_agent_cost(brand_slug: str):
    """
    Called by agent scripts at end of each run to record token counts.
    Body: { run_id, model, input_tokens, output_tokens, fal_generations, apify_runs }
    """
    if not _DB_AVAILABLE:
        return jsonify({"success": True, "data": {}}), 200  # silent no-op

    _bid, err = _authorize_brand(brand_slug)   # W3.1 authz sweep
    if err:
        return err

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


# ── Brand Memory API ──────────────────────────────────────────────────────────

@bp.route("/api/brands/<brand_slug>/memory/db", methods=["GET"])
@require_auth
def get_brand_memory_db(brand_slug: str):
    """Return all stored memory entries from Supabase for a brand (all agents or filtered by agent_slug)."""
    if not _DB_AVAILABLE:
        return jsonify({"success": True, "data": []}), 200

    brand_id, err = _authorize_brand(brand_slug)   # W3.1 authz sweep
    if err:
        return err

    agent_slug = request.args.get("agent_slug", "")
    if agent_slug:
        memories = _db.get_brand_memory(brand_id, agent_slug)
    else:
        memories = _db.get_all_brand_memory(brand_id)

    return jsonify({"success": True, "data": memories})


# ── Brands ────────────────────────────────────────────────────────────────────

@bp.route("/api/brands", methods=["GET"])
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


@bp.route("/api/brands/create", methods=["POST"])
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


@bp.route("/api/brands/<brand_slug>", methods=["DELETE"])
@require_auth
def delete_brand(brand_slug: str):
    if not _validate_brand_slug(brand_slug):
        return jsonify({"success": False, "error": "Invalid brand_slug"}), 400
    _bid, err = _authorize_brand(brand_slug)   # W3.1 authz sweep — CRITICAL (rmtree)
    if err:
        return err
    # Irreversible (rmtree): a brand member alone isn't enough — real users must be
    # super-admin. The operator-secret path (user is None) stays exempt.
    _u = getattr(request, "user", None)
    if _u is not None and _DB_AVAILABLE and not _db.is_super_admin(_u["id"]):
        return jsonify({"success": False, "error": "Only an admin can delete a brand"}), 403
    brand_dir = BRANDS_DIR / brand_slug
    if not brand_dir.exists():
        return jsonify({"success": False, "error": "Brand not found"}), 404
    remaining = [d for d in BRANDS_DIR.iterdir() if d.is_dir() and d.name != brand_slug]
    if not remaining:
        return jsonify({"success": False, "error": "Cannot delete the last brand"}), 400
    shutil.rmtree(brand_dir)
    return jsonify({"success": True, "deleted": brand_slug})


@bp.route("/api/brands/<brand_slug>/memory", methods=["GET"])
@require_auth
def get_brand_memory(brand_slug: str):
    """Return all brand_memory files for a brand."""
    if not _validate_brand_slug(brand_slug):
        return jsonify({"success": False, "error": "Invalid brand_slug"}), 400
    _bid, err = _authorize_brand(brand_slug)   # W3.1 authz sweep
    if err:
        return err
    result = {}
    for key in _MEMORY_FILES:
        result[key] = _read_memory(brand_slug, key)
    return jsonify({"success": True, "data": result})


@bp.route("/api/brands/<brand_slug>/intelligence", methods=["GET"])
@require_auth
def get_brand_intelligence(brand_slug: str):
    """Return market_intelligence files + staleness info."""
    if not _validate_brand_slug(brand_slug):
        return jsonify({"success": False, "error": "Invalid brand_slug"}), 400
    _bid, err = _authorize_brand(brand_slug)   # W3.1 authz sweep
    if err:
        return err
    result = {}
    for key in _INTELLIGENCE_FILES:
        data = _read_intelligence(brand_slug, key)
        result[key] = {
            "data": data,
            "stale": _intelligence_is_stale(brand_slug, key) if key in _INTELLIGENCE_TTL else False,
        }
    return jsonify({"success": True, "data": result})


@bp.route("/api/brands/<brand_slug>/memory/approve", methods=["POST"])
@require_auth
def approve_memory_update(brand_slug: str):
    """
    Gaurav approves a change to brand_memory.
    Body: { memory_key: str, updates: dict }
    This is the ONLY way brand_memory files get updated.
    """
    if not _validate_brand_slug(brand_slug):
        return jsonify({"success": False, "error": "Invalid brand_slug"}), 400
    _bid, err = _authorize_brand(brand_slug)   # W3.1 authz sweep
    if err:
        return err
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


@bp.route("/api/brands/<brand_slug>/goals", methods=["POST"])
@require_auth
def set_brand_goal(brand_slug: str):
    """
    Gaurav sets or updates an active goal (e.g. '500 followers in 30 days').
    Immediately stored in brand_memory/goals.json.
    Triggers a task-specific scrape in background.
    """
    if not _validate_brand_slug(brand_slug):
        return jsonify({"success": False, "error": "Invalid brand_slug"}), 400
    _bid, err = _authorize_brand(brand_slug)   # W3.1 authz sweep
    if err:
        return err
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


# ── Brand profile / dashboard ─────────────────────────────────────────────────

@bp.route("/api/brand/profile", methods=["GET"])
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


@bp.route("/api/brand/profile", methods=["POST"])
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


@bp.route("/api/brand/dashboard", methods=["GET"])
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

@bp.route("/api/brand/summary", methods=["GET"])
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


@bp.route("/api/brands/<slug>/connections", methods=["GET"])
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


# ============================================================
# TEAM ROLES — Admin / Editor / Viewer per brand
# ============================================================

@bp.route("/api/team/members", methods=["GET"])
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
@bp.route("/api/team/invite", methods=["POST"])
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


@bp.route("/api/team/update-role", methods=["POST"])
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


@bp.route("/api/team/remove", methods=["POST"])
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
# ADMIN — Super Admin Endpoints (Grid Control owner only)
# ============================================================

@bp.route("/api/admin/check", methods=["GET"])
@require_auth
def admin_check():
    """Check if the current user is a super admin."""
    user = getattr(request, "user", None)
    if not user or not _DB_AVAILABLE:
        return jsonify(success=True, data={"is_admin": False})
    is_admin = _db.is_super_admin(user["id"])
    return jsonify(success=True, data={"is_admin": is_admin})


@bp.route("/api/admin/overview", methods=["GET"])
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


@bp.route("/api/admin/clients", methods=["GET"])
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


@bp.route("/api/admin/revenue", methods=["GET"])
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


@bp.route("/api/admin/system", methods=["GET"])
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

@bp.route("/api/brands/<brand_slug>/runs", methods=["GET"])
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


@bp.route("/api/brands/<brand_slug>/narrative", methods=["GET"])
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


@bp.route("/api/brands/<brand_slug>/narrative", methods=["POST"])
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


@bp.route("/api/brands/<brand_slug>/brand-book", methods=["GET"])
@require_auth
def get_brand_book_status(brand_slug: str):
    """Return current brand-book gate state for the brand."""
    brand_id, err = _authorize_brand(brand_slug)
    if err:
        return err
    info = _brand_book_status(brand_slug)
    # Attach a summary of the latest report if we have a path
    summary = None
    lp = info.get("latest_path")
    if lp and Path(lp).exists():
        try:
            raw = Path(lp).read_text()
            # Strip LOOP HEADER (split on first \n---\n)
            body = raw.split("\n---\n", 1)[1] if "\n---\n" in raw else raw
            report = json.loads(body)
            meta = report.get("meta", {})
            sc = report.get("parts", {}).get("part0_scorecard", {})
            summary = {
                "brand":      meta.get("brand"),
                "version":    meta.get("version"),
                "date":       meta.get("date"),
                "mode":       meta.get("mode"),
                "data_basis": meta.get("data_basis"),
                "scorecard_metrics": [
                    {"label": lbl, "value": m.get("value"), "basis": m.get("basis")}
                    for lbl, m in sc.get("metrics", [])
                ],
                "eval": report.get("eval", {}),
            }
        except Exception:
            pass
    return jsonify(success=True, data={**info, "report_summary": summary})


@bp.route("/api/brands/<brand_slug>/brand-book/generate", methods=["POST"])
@require_auth
def generate_brand_book(brand_slug: str):
    """H1: Trigger Brand-Book generation. PAID RUN — Opus + (onboarding) IG Insights.
    Body: { mode?: "cold_sellable" | "onboarding_connected" }
    Sets status → "generating" immediately; background thread sets "pending_review" on completion.
    """
    brand_id, err = _authorize_brand(brand_slug)
    if err:
        return err
    body = request.get_json(force=True) or {}
    mode = body.get("mode", "cold_sellable")
    if mode not in ("cold_sellable", "onboarding_connected"):
        return jsonify(success=False, error="mode must be cold_sellable or onboarding_connected"), 400
    current = _brand_book_status(brand_slug)
    if current.get("status") == "generating":
        return jsonify(success=False, error="Brand-Book generation already in progress"), 409
    # Guard: regenerating an already-approved book resets the sign-off gate
    # (Foundation goes back to pending_review). Require an explicit force flag.
    if current.get("status") == "approved" and not body.get("force"):
        return jsonify(success=False, error=(
            "Brand-Book is already approved and the Foundation is live. Regenerating "
            "will reset the sign-off gate to pending_review. Pass {\"force\": true} "
            "to regenerate anyway."
        )), 409
    # Set generating immediately
    _update_brand_profile_fields(brand_slug, {
        "brand_book_status": "generating",
        "brand_book_error":  None,
    })
    thread = threading.Thread(
        target=_run_brand_book_generate,
        args=(brand_slug, mode),
        daemon=True,
    )
    thread.start()
    return jsonify(success=True, data={
        "message": "Brand-Book generation started (PAID run). Poll GET /api/brands/<slug>/brand-book for status.",
        "mode": mode,
    })


@bp.route("/api/brands/<brand_slug>/brand-book/approve", methods=["POST"])
@require_auth
def approve_brand_book(brand_slug: str):
    """H2: Approve the brand-book Foundation. Writes Foundation → brand_profile.json +
    voice_profile.json + appends brand_narrative entry. Sets status → approved.
    Body: { notes?: string }
    """
    brand_id, err = _authorize_brand(brand_slug)
    if err:
        return err
    info = _brand_book_status(brand_slug)
    if info.get("status") not in ("pending_review", "change_requested"):
        return jsonify(success=False, error=(
            f"Cannot approve: status is '{info.get('status', 'none')}'. "
            "Generate the Brand-Book first."
        )), 409
    lp = info.get("latest_path")
    if not lp or not Path(lp).exists():
        return jsonify(success=False, error="Brand-Book report file not found. Re-generate."), 404
    # Parse report
    try:
        raw = Path(lp).read_text()
        body_text = raw.split("\n---\n", 1)[1] if "\n---\n" in raw else raw
        report = json.loads(body_text)
    except Exception as e:
        return jsonify(success=False, error=f"Could not parse Brand-Book report: {e}"), 500
    foundation = report.get("parts", {}).get("part1_foundation", {})
    _write_foundation(brand_slug, foundation)
    ts = datetime.utcnow().isoformat() + "Z"
    _update_brand_profile_fields(brand_slug, {
        "brand_book_status":      "approved",
        "brand_book_approved_ts": ts,
    })
    # Append narrative entry (Phase A)
    ps = (foundation or {}).get("positioning_statement", "")
    summary_text = f"Brand Foundation approved (brand-book v6). Positioning: {ps[:120]}"
    if _DB_AVAILABLE and brand_id:
        try:
            _db.append_narrative(brand_id, "brand-book", "decision", summary_text, refs={"path": lp})
        except Exception:
            pass
    # Also append to local brand_narrative.json for offline use
    narr_path = BRANDS_DIR / brand_slug / "brand_narrative.json"
    try:
        narr = []
        if narr_path.exists():
            narr = json.loads(narr_path.read_text())
        narr.append({"ts": ts, "agent": "brand-book", "entry_type": "decision", "summary": summary_text})
        narr_path.write_text(json.dumps(narr, indent=2))
    except Exception:
        pass
    return jsonify(success=True, data={
        "message": "Brand Foundation approved. brand_profile.json + voice_profile.json updated. Strategy Agent is now unlocked.",
        "approved_ts": ts,
        "foundation_written": bool(foundation and not foundation.get("_unparsed")),
    })


@bp.route("/api/brands/<brand_slug>/brand-book/request-change", methods=["POST"])
@require_auth
def request_brand_book_change(brand_slug: str):
    """K3: Record a change request against the brand-book. Increments revision counter.
    At cap (3) the flag is set — further changes are scope-creep, not revisions.
    Body: { notes: string }
    """
    brand_id, err = _authorize_brand(brand_slug)
    if err:
        return err
    body = request.get_json(force=True) or {}
    notes = (body.get("notes") or "").strip()
    if not notes:
        return jsonify(success=False, error="notes required — describe the change requested"), 400
    info = _brand_book_status(brand_slug)
    if info.get("status") not in ("pending_review", "change_requested"):
        return jsonify(success=False, error=(
            f"Cannot request change: status is '{info.get('status', 'none')}'. "
            "Brand-Book must be in pending_review."
        )), 409
    rev = info.get("revision_count", 0) + 1
    scope_flag = rev > BRAND_BOOK_REVISION_CAP
    _update_brand_profile_fields(brand_slug, {
        "brand_book_status":         "change_requested",
        "brand_book_revision_count": rev,
        "brand_book_scope_flag":     scope_flag,
    })
    # Append to narrative
    ts = datetime.utcnow().isoformat() + "Z"
    summary_text = f"Brand-Book change request #{rev}: {notes[:200]}"
    if _DB_AVAILABLE and brand_id:
        try:
            _db.append_narrative(brand_id, "brand-book", "action", summary_text)
        except Exception:
            pass
    if scope_flag:
        return jsonify(success=True, data={
            "message": (
                f"Revision {rev} recorded. Revision cap ({BRAND_BOOK_REVISION_CAP}) exceeded — "
                "this is now a scope-change, not a revision. Treat as a new brief or Phase-2 work."
            ),
            "revision_count": rev,
            "scope_flag": True,
            "status": "change_requested",
        })
    return jsonify(success=True, data={
        "message": f"Change request #{rev} recorded. Re-generate the Brand-Book to address the feedback.",
        "revision_count": rev,
        "scope_flag": False,
        "revisions_remaining": BRAND_BOOK_REVISION_CAP - rev,
        "status": "change_requested",
    })


@bp.route("/api/brands/<brand_slug>/assets", methods=["GET"])
@require_auth
def list_assets(brand_slug: str):
    """I-a: List all brand assets from manifest."""
    _g = _guard_asset_brand(brand_slug)
    if _g:
        return _g
    entries = _read_manifest(brand_slug)
    return jsonify(success=True, data={"assets": entries, "count": len(entries)})


@bp.route("/api/brands/<brand_slug>/assets/upload", methods=["POST"])
@require_auth
def upload_asset(brand_slug: str):
    """I-a: Accept a direct file upload into brands/{slug}/assets/{category}/."""
    _g = _guard_asset_brand(brand_slug)
    if _g:
        return _g
    f = request.files.get("file")
    if not f or not f.filename:
        return jsonify(success=False, error="No file provided."), 400

    suffix = Path(f.filename).suffix
    try:
        category = _classify_ext(suffix)
    except ValueError as e:
        return jsonify(success=False, error=str(e)), 415

    limit = _ASSET_MAX_BYTES[category]
    # Early reject by declared body size (file + multipart overhead) before reading.
    if request.content_length and request.content_length > limit + 1024 * 1024:
        return jsonify(
            success=False,
            error=f"File too large. Limit for {category}: {limit // (1024*1024)} MB."
        ), 413
    data = f.read()
    size = len(data)
    if size > limit:
        return jsonify(
            success=False,
            error=f"File too large. Limit for {category}: {limit // (1024*1024)} MB."
        ), 413

    uid = _uuid_mod.uuid4().hex[:12]
    safe = _safe_fname(f.filename)
    dest = _asset_dir(brand_slug, category) / f"{uid}_{safe}"
    dest.write_bytes(data)

    entry = {
        "id":          uid,
        "filename":    safe,
        "category":    category,
        "size_bytes":  size,
        "path":        str(dest),
        "source":      "direct_upload",
        "uploaded_at": datetime.now(timezone.utc).isoformat(),
    }
    entries = _read_manifest(brand_slug)
    entries.append(entry)
    _write_manifest(brand_slug, entries)
    return jsonify(success=True, data={"asset": entry}), 201


@bp.route("/api/brands/<brand_slug>/assets/cloud-link", methods=["POST"])
@require_auth
def add_cloud_link(brand_slug: str):
    """I-a: Store a cloud-link reference (Drive / Dropbox / OneDrive).
    No HTTP fetch here — SG3 audits any future fetch path. SSRF guard rejects
    everything outside _ASSET_CLOUD_DOMAINS.
    """
    _g = _guard_asset_brand(brand_slug)
    if _g:
        return _g
    body = request.get_json(silent=True) or {}
    url = (body.get("url") or "").strip()
    if not url:
        return jsonify(success=False, error="'url' is required."), 400
    if not _ssrf_check(url):
        return jsonify(
            success=False,
            error="Only Google Drive, Dropbox, and OneDrive links are accepted."
        ), 422

    category = (body.get("category") or "document")
    if category not in _ASSET_MAX_BYTES:
        category = "document"
    label = (body.get("label") or Path(url).name or "cloud asset")[:200]

    uid = _uuid_mod.uuid4().hex[:12]
    entry = {
        "id":        uid,
        "label":     label,
        "url":       url,
        "category":  category,
        "source":    "cloud_link",
        "linked_at": datetime.now(timezone.utc).isoformat(),
    }
    entries = _read_manifest(brand_slug)
    entries.append(entry)
    _write_manifest(brand_slug, entries)
    return jsonify(success=True, data={"asset": entry}), 201


@bp.route("/api/brands/<brand_slug>/assets/<asset_id>", methods=["DELETE"])
@require_auth
def delete_asset(brand_slug: str, asset_id: str):
    """I-a: Remove an asset from the manifest. Deletes the file from disk
    if it was a direct upload.
    """
    _g = _guard_asset_brand(brand_slug)
    if _g:
        return _g
    entries = _read_manifest(brand_slug)
    target = next((e for e in entries if e.get("id") == asset_id), None)
    if not target:
        return jsonify(success=False, error="Asset not found."), 404
    fpath = target.get("path")
    if fpath:
        try:
            Path(fpath).unlink(missing_ok=True)
        except Exception:
            pass
    _write_manifest(brand_slug, [e for e in entries if e.get("id") != asset_id])
    return jsonify(success=True, data={"deleted": asset_id})


@bp.route("/api/brands/<brand_slug>/content-cards/<card_id>/upload", methods=["GET"])
@require_auth
def get_card_upload(brand_slug: str, card_id: str):
    """I-b: Get the upload status for a content card."""
    _g = _guard_asset_brand(brand_slug)
    if _g:
        return _g
    card = _get_card(brand_slug, card_id)
    if card is None:
        return jsonify(success=False, error="Card not found."), 404
    return jsonify(success=True, data={
        "card_id":         card_id,
        "requires_upload": card.get("requires_upload", False),
        "upload_status":   card.get("upload_status", "none"),
        "upload_path":     card.get("upload_path"),
        "upload_url":      card.get("upload_url"),
        "upload_label":    card.get("upload_label"),
        "upload_ts":       card.get("upload_ts"),
    })


@bp.route("/api/brands/<brand_slug>/content-cards/<card_id>/upload", methods=["POST"])
@require_auth
def post_card_upload(brand_slug: str, card_id: str):
    """I-b: Attach a production file or cloud link to a content card.
    Sets upload_status='pending_edit' and writes a routing stub to
    pending_approval/creative-director/ so it surfaces in the approval dashboard.
    """
    _g = _guard_asset_brand(brand_slug)
    if _g:
        return _g
    if not _safe_card_id(card_id):
        return jsonify(success=False, error="Invalid card id."), 400
    card = _get_card(brand_slug, card_id)
    if card is None:
        return jsonify(success=False, error="Card not found."), 404

    updates: dict = {}
    f = request.files.get("file")

    if f and f.filename:
        # ── file upload path ──────────────────────────────────────────────────
        suffix = Path(f.filename).suffix
        try:
            category = _classify_ext(suffix)
        except ValueError as e:
            return jsonify(success=False, error=str(e)), 415

        limit = _ASSET_MAX_BYTES[category]
        if request.content_length and request.content_length > limit + 1024 * 1024:
            return jsonify(
                success=False,
                error=f"File too large. Limit for {category}: {limit // (1024*1024)} MB."
            ), 413
        data = f.read()
        size = len(data)
        if size > limit:
            return jsonify(
                success=False,
                error=f"File too large. Limit for {category}: {limit // (1024*1024)} MB."
            ), 413

        uid = _uuid_mod.uuid4().hex[:12]
        safe = _safe_fname(f.filename)
        dest = _asset_dir(brand_slug, f"production/{card_id}") / f"{uid}_{safe}"
        dest.write_bytes(data)
        updates = {
            "upload_path":   str(dest),
            "upload_label":  safe,
            "upload_status": "pending_edit",
            "upload_ts":     datetime.now(timezone.utc).isoformat(),
        }
    else:
        # ── cloud-link path ───────────────────────────────────────────────────
        body = request.get_json(silent=True) or {}
        url = (body.get("url") or "").strip()
        if not url:
            return jsonify(
                success=False,
                error="Provide 'file' (multipart) or 'url' (JSON body)."
            ), 400
        if not _ssrf_check(url):
            return jsonify(
                success=False,
                error="Only Google Drive, Dropbox, and OneDrive links are accepted."
            ), 422
        label = (body.get("label") or url)[:200]
        updates = {
            "upload_url":    url,
            "upload_label":  label,
            "upload_status": "pending_edit",
            "upload_ts":     datetime.now(timezone.utc).isoformat(),
        }

    if not _update_card(brand_slug, card_id, updates):
        return jsonify(
            success=False,
            error="Failed to update card. Verify content_calendar.json exists."
        ), 500

    # Write routing stub so the approval dashboard surfaces this card
    try:
        cd_dir = (BRANDS_DIR / brand_slug / "outputs"
                  / "pending_approval" / "creative-director")
        cd_dir.mkdir(parents=True, exist_ok=True)
        ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        stub = {
            "type":        "production_upload",
            "card_id":     card_id,
            "card_title":  card.get("title") or card.get("post_type") or card_id,
            "upload":      updates,
            "instruction": (
                "Founder has uploaded raw footage/file for this content card. "
                "Edit and return to the approval queue."
            ),
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        loop_header = (
            f"LOOP: creative-director — production_upload / "
            f"edit uploaded asset for card {card_id} / approval / VARIANTS=1 / WINNER=pending\n---\n"
        )
        (cd_dir / f"{ts}_card_{card_id}_upload.json").write_text(
            loop_header + json.dumps(stub, indent=2)
        )
    except Exception:
        pass  # routing stub is best-effort; the upload is already persisted

    return jsonify(success=True, data={
        "card_id": card_id,
        "updates": updates,
        "message": "Upload saved. Routed to Creative Director queue for editing.",
    }), 201


@bp.route("/api/brands/<brand_slug>/concierge", methods=["POST"])
@require_auth
@rate_limit(max_requests=20, window_seconds=60)
def concierge_chat(brand_slug: str):
    """J: Chief of Staff router.

    Trivial/deterministic (pause, reschedule, caption edit, slide swap) →
    execute instantly, no LLM.  Substantive (re-plan, new angle, inject trend,
    strategy) → dispatch specialist → result in approval dashboard.

    Body:
      { message: str,
        context?: { card_id?, new_date?, new_caption?, new_slides? } }

    Returns:
      { tier: "trivial" | "dispatch" | "unrecognized",
        action?, agent?, result?, message, ... }
    """
    _g = _guard_asset_brand(brand_slug)
    if _g:
        return _g

    body = request.get_json(silent=True) or {}
    message = (body.get("message") or "").strip()
    if not message:
        return jsonify(success=False, error="'message' is required."), 400
    if len(message) > MAX_CONCIERGE_MSG:
        return jsonify(
            success=False,
            error=f"Message too long (max {MAX_CONCIERGE_MSG} characters)."
        ), 413

    context = body.get("context") or {}
    if not isinstance(context, dict):
        context = {}

    tier, action_key = _concierge_classify(message)

    if tier == "trivial":
        result = _concierge_trivial(brand_slug, action_key, message, context)
        return jsonify(success=True, data={"tier": "trivial", **result})

    if tier == "dispatch":
        # SG4: throttle the paid path (each dispatch spawns a real agent run).
        ok, reason = _concierge_dispatch_allowed(brand_slug, action_key)
        if not ok:
            return jsonify(success=True, data={
                "tier": "dispatch", "throttled": True, "message": reason,
            })
        dispatch = _concierge_dispatch(brand_slug, action_key, message)
        _concierge_dispatch_record(brand_slug, action_key)
        return jsonify(success=True, data={"tier": "dispatch", **dispatch})

    return jsonify(success=True, data={
        "tier":    "unrecognized",
        "message": (
            "I can handle: pause / resume / reschedule a post, edit a caption, "
            "swap slides, re-plan the calendar, inject a trend, rewrite a script, "
            "or change strategy. What would you like to do?"
        ),
    })


@bp.route("/api/brands/<brand_slug>/needs-you", methods=["GET"])
@require_auth
def needs_you(brand_slug: str):
    """L: 'Needs you' queue — pending approval items for a brand.
    Returns count, item list, and email configuration status.
    """
    _g = _guard_asset_brand(brand_slug)
    if _g:
        return _g

    items = _needs_you_items(brand_slug)
    email_to = os.getenv("NOTIFICATION_EMAIL_TO", "")
    # Mask email for display: gaurav.khanna110@gmail.com → g***@gmail.com
    if email_to and "@" in email_to:
        local, domain = email_to.split("@", 1)
        masked = local[0] + "***@" + domain
    else:
        masked = ""
    return jsonify(success=True, data={
        "count":              len(items),
        "items":              items,
        "email_configured":   _notification_configured(),
        "notification_email": masked,
    })


@bp.route("/api/brands/<brand_slug>/notify", methods=["POST"])
@require_auth
def send_notify(brand_slug: str):
    """L: Manually trigger an approval-needed notification email.
    Body: {} (empty) — sends current pending queue for the brand.
    No-ops gracefully if email is not configured.
    """
    _g = _guard_asset_brand(brand_slug)
    if _g:
        return _g

    if not _notification_configured():
        return jsonify(success=True, data={
            "sent": False,
            "message": (
                "Notifications not configured. Set NOTIFICATION_WEBHOOK_URL "
                "(Make.com webhook) in .env / Railway."
            ),
        })

    items = _needs_you_items(brand_slug)
    if not items:
        return jsonify(success=True, data={
            "sent": False,
            "message": "Nothing pending for this brand — no notification sent.",
            "count": 0,
        })

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

    ok = _send_notification(subject, "\n".join(lines), count=n)
    return jsonify(success=True, data={
        "sent":    ok,
        "count":   n,
        "message": f"Notification sent for {n} item(s)." if ok else "Webhook send failed — check NOTIFICATION_WEBHOOK_URL / Make.com scenario.",
    })
