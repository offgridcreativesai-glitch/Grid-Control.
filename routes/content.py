"""routes/content.py — GRID CONTROL content endpoints (blueprint). S2b split."""
from core import *  # noqa: F401,F403  (app, helpers, stdlib re-exports)
from flask import Blueprint

bp = Blueprint("content", __name__)



# ── CAROUSEL DESIGNER ──────────────────────────────────────────────────────────

@bp.route("/api/carousel/generate", methods=["POST"])
@rate_limit(max_requests=3, window_seconds=60)
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


@bp.route("/api/publish/check", methods=["GET"])
@require_auth
def publish_check():
    """Read-only IG token liveness probe — drives auto-publish vs prepare-only."""
    from publishing.instagram_publisher import token_status
    token = os.getenv("META_GRAPH_API_TOKEN", "").strip()
    return jsonify({"success": True, "data": token_status(token)})


@bp.route("/api/publish/instagram", methods=["POST"])
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


@bp.route("/api/publish", methods=["POST"])
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


@bp.route("/api/pipeline/daily-run", methods=["POST"])
@rate_limit(max_requests=2, window_seconds=60)
@require_auth_or_service
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


@bp.route("/api/outputs/pending", methods=["GET"])
@require_auth
def get_pending_outputs():
    from utils.output_formatter import format_for_notion
    brand_slug = require_brand_slug()

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


@bp.route("/api/outputs/content", methods=["GET"])
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


@bp.route("/api/published", methods=["GET"])
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
    brand_slug = require_brand_slug()
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


@bp.route("/api/outputs/all", methods=["GET"])
@require_auth
def get_all_outputs():
    brand_slug = require_brand_slug()
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


@bp.route("/api/outputs/approve", methods=["POST"])
@require_auth
def approve_output():
    # DB-WIRED Step 5 + Phase 1 Step 4
    body = request.get_json()
    brand_slug = require_brand_slug()
    filepath = body.get("filepath", "")
    output_id = body.get("output_id", "")  # Supabase UUID — optional
    next_agent_slug: str | None = None
    # Must exist before the _DB_AVAILABLE block: with the DB down (or a brand not
    # registered in Supabase) the disk-path approve crashed 500 on this name.
    resolved_agent_slug: str | None = None

    # The Review UI sends just a filename — resolve it to a real filepath so the
    # move + skill-learning + Supabase match all work. (Without this, approve no-ops.)
    filename = body.get("filename", "")
    if not filepath and filename and "/" not in filename and ".." not in filename:
        found = _find_pending_output(get_brand_dir(brand_slug), filename)
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


@bp.route("/api/outputs/reject", methods=["POST"])
@require_auth
def reject_output():
    # DB-WIRED Step 5
    body = request.get_json()
    brand_slug = require_brand_slug()
    filepath = body.get("filepath", "")
    output_id = body.get("output_id", "")  # Supabase UUID — optional
    reason = body.get("reason", "")
    agent_slug_key = ""

    # Review UI sends just a filename — resolve to a real filepath (else reject no-ops).
    filename = body.get("filename", "")
    if not filepath and filename and "/" not in filename and ".." not in filename:
        found = _find_pending_output(get_brand_dir(brand_slug), filename)
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

    removed = False
    if filepath:
        src = _safe_path(BASE_DIR, filepath)
        if src and src.exists():
            src.unlink()
            removed = True

    # Honesty: if we resolved nothing and removed nothing, say so — never a false success
    # that makes the UI think a still-present card was rejected.
    if not removed and not output_id:
        return jsonify({"success": False, "error": "Could not find that item to reject."}), 404
    return jsonify({"success": True, "data": {"message": "Rejected and removed."}})


@bp.route("/api/outputs/request-changes", methods=["POST"])
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


@bp.route("/api/outputs/download/<path:filepath>", methods=["GET"])
@require_auth
def download_file(filepath):
    """Force-download any output file."""
    fpath = _resolve_output_file(filepath)
    if not fpath:
        return jsonify({"success": False, "error": "File not found"}), 404
    mime = _MIME_MAP.get(fpath.suffix.lower(), "application/octet-stream")
    return send_file(str(fpath), mimetype=mime, as_attachment=True,
                     download_name=fpath.name)


@bp.route("/api/outputs/media/<path:filepath>", methods=["GET"])
@require_auth
def serve_media(filepath):
    """Serve an output file inline (for browser preview — images, video, audio)."""
    fpath = _resolve_output_file(filepath)
    if not fpath:
        return jsonify({"success": False, "error": "File not found"}), 404
    mime = _MIME_MAP.get(fpath.suffix.lower(), "application/octet-stream")
    return send_file(str(fpath), mimetype=mime, as_attachment=False)


# ── Dashboard Output Bundle ───────────────────────────────────────────────────

@bp.route("/api/dashboard-output", methods=["GET"])
@require_auth
def get_dashboard_output():
    from utils.output_formatter import format_scripts, format_calendar, format_strategy

    brand_slug = require_brand_slug()

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


# ============================================================
# REVISION LOOP — Client feedback → agent re-run with constraint
# K3 (Phase K): change discipline — revision cap + scope-creep flag.
# ============================================================

# How many auto-revisions a single output gets before a change must be
# human-confirmed (likely a Phase-2 upsell, not a tweak). Override via env.
REVISION_CAP = int(os.getenv("GRID_REVISION_CAP", "2"))

# Deterministic, no-LLM scope-creep heuristic ($0). A "change" containing any of
# these reads as NEW scope (a different deliverable), not a tweak.
_SCOPE_CREEP_SIGNALS = (
    "also add", "can you also", "instead make", "instead of", "completely different",
    "new angle", "another one", "redo from scratch", "different product",
    "different platform", "add a section", "make it about", "now do", "as well",
    "on top of that", "brand new", "whole new", "start over",
)


def _count_prior_revisions(brand_id: str, output_id: str) -> int:
    """Count revision_requested audit rows for one output (client-side filter on JSON details)."""
    if not output_id:
        return 0
    try:
        res = (_db._client.table("audit_log").select("details")
               .eq("brand_id", brand_id).eq("action", "revision_requested").execute())
        return sum(1 for r in (res.data or [])
                   if (r.get("details") or {}).get("output_id") == output_id)
    except Exception:
        return 0


def _scope_creep_suspected(feedback: str) -> bool:
    f = (feedback or "").lower()
    return any(sig in f for sig in _SCOPE_CREEP_SIGNALS)


@bp.route("/api/outputs/revise", methods=["POST"])
@require_auth
def output_revise():
    """Request a revision on a rejected/approved output.
    Body: { brand_slug, output_id, feedback, agent_slug, confirm_new_scope? }
    K3 discipline: enforces a revision cap and flags scope-creep. When the cap is
    hit OR the feedback reads as new scope, the re-run is NOT auto-queued — it's
    recorded as `revision_flagged` and returned as `needs_review` so a human
    decides (tweak vs. new-scope upsell). Pass confirm_new_scope=true to override.
    """
    body = request.get_json(force=True)
    brand_slug = body.get("brand_slug", "")
    output_id = body.get("output_id", "")
    feedback = body.get("feedback", "")
    agent_slug = body.get("agent_slug", "")
    confirm_new_scope = bool(body.get("confirm_new_scope", False))

    if not brand_slug or not feedback or not agent_slug:
        return jsonify(success=False, error="brand_slug, agent_slug, and feedback required"), 400

    brand_id = _resolve_brand_id(brand_slug)
    if not brand_id:
        return jsonify(success=False, error="Brand not found"), 404

    prior = _count_prior_revisions(brand_id, output_id)
    scope_creep = _scope_creep_suspected(feedback)
    cap_hit = prior >= REVISION_CAP

    try:
        # K3 gate: hold the re-run for human review unless explicitly overridden.
        if (cap_hit or scope_creep) and not confirm_new_scope:
            _db._client.table("audit_log").insert({
                "brand_id": brand_id,
                "action": "revision_flagged",
                "details": {
                    "output_id": output_id,
                    "agent_slug": agent_slug,
                    "feedback": feedback,
                    "prior_revisions": prior,
                    "revision_cap": REVISION_CAP,
                    "cap_hit": cap_hit,
                    "scope_creep_suspected": scope_creep,
                    "flagged_at": datetime.now(timezone.utc).isoformat(),
                },
            }).execute()
            reasons = []
            if cap_hit:
                reasons.append(f"revision cap reached ({prior}/{REVISION_CAP})")
            if scope_creep:
                reasons.append("reads as new scope (possible upsell)")
            return jsonify(success=True, data={
                "status": "needs_review",
                "flagged": True,
                "cap_hit": cap_hit,
                "scope_creep_suspected": scope_creep,
                "prior_revisions": prior,
                "revision_cap": REVISION_CAP,
                "message": "Revision not auto-queued — " + " + ".join(reasons) +
                           ". Confirm to proceed (confirm_new_scope=true) or treat as new scope.",
            })

        # Store revision request in audit_log
        _db._client.table("audit_log").insert({
            "brand_id": brand_id,
            "action": "revision_requested",
            "details": {
                "output_id": output_id,
                "agent_slug": agent_slug,
                "feedback": feedback,
                "revision_number": prior + 1,
                "scope_creep_suspected": scope_creep,
                "confirmed_new_scope": confirm_new_scope,
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
                "revision_number": prior + 1,
            },
        }).execute()

        return jsonify(success=True, data={
            "status": "revision_queued",
            "agent_slug": agent_slug,
            "revision_number": prior + 1,
            "revision_cap": REVISION_CAP,
        })
    except Exception as e:
        return jsonify(success=False, error=str(e)), 500


@bp.route("/api/outputs/revisions", methods=["GET"])
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
