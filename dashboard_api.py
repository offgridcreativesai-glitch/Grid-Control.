"""
dashboard_api.py — GRID CONTROL route catalog.

Every HTTP endpoint lives here, grouped by URL prefix. Infra, helpers and the
Flask `app` come from core.py. gunicorn entrypoint is still `dashboard_api:app`.
"""
from core import *  # noqa: F401,F403  (app, helpers, constants, stdlib re-exports)



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


@app.route("/api/publish/check", methods=["GET"])
@require_auth
def publish_check():
    """Read-only IG token liveness probe — drives auto-publish vs prepare-only."""
    from publishing.instagram_publisher import token_status
    token = os.getenv("META_GRAPH_API_TOKEN", "").strip()
    return jsonify({"success": True, "data": token_status(token)})


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

    brand_id, err = _authorize_brand(brand_slug)   # W3.1 authz sweep
    if err:
        return err

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


@app.route("/api/brands/<brand_slug>/memory", methods=["GET"])
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


@app.route("/api/brands/<brand_slug>/intelligence", methods=["GET"])
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


@app.route("/api/brands/<brand_slug>/brand-book", methods=["GET"])
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


@app.route("/api/brands/<brand_slug>/brand-book/generate", methods=["POST"])
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


@app.route("/api/brands/<brand_slug>/brand-book/approve", methods=["POST"])
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


@app.route("/api/brands/<brand_slug>/brand-book/request-change", methods=["POST"])
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


@app.route("/api/brands/<brand_slug>/assets", methods=["GET"])
@require_auth
def list_assets(brand_slug: str):
    """I-a: List all brand assets from manifest."""
    _g = _guard_asset_brand(brand_slug)
    if _g:
        return _g
    entries = _read_manifest(brand_slug)
    return jsonify(success=True, data={"assets": entries, "count": len(entries)})


@app.route("/api/brands/<brand_slug>/assets/upload", methods=["POST"])
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


@app.route("/api/brands/<brand_slug>/assets/cloud-link", methods=["POST"])
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


@app.route("/api/brands/<brand_slug>/assets/<asset_id>", methods=["DELETE"])
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


@app.route("/api/brands/<brand_slug>/content-cards/<card_id>/upload", methods=["GET"])
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


@app.route("/api/brands/<brand_slug>/content-cards/<card_id>/upload", methods=["POST"])
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


@app.route("/api/brands/<brand_slug>/concierge", methods=["POST"])
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


@app.route("/api/brands/<brand_slug>/needs-you", methods=["GET"])
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


@app.route("/api/brands/<brand_slug>/notify", methods=["POST"])
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


if __name__ == "__main__":
    print("GRID CONTROL Flask API — port 5001")
    app.run(host="0.0.0.0", port=5001, debug=False)
