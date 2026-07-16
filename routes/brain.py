"""routes/brain.py — GRID CONTROL brain endpoints (blueprint). S2b split."""
from core import *  # noqa: F401,F403  (app, helpers, stdlib re-exports)
from flask import Blueprint

bp = Blueprint("brain", __name__)



# ── JARVIS QUERY ───────────────────────────────────────────────────────────────

@bp.route("/api/jarvis/query", methods=["POST"])
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


# ── Agent Log ─────────────────────────────────────────────────────────────────

@bp.route("/api/ceo/next-agent", methods=["GET"])
@require_auth
def ceo_next_agent():
    """
    Return CEO Brain's recommended next agent and reason.
    Phase 1 Step 2.
    """
    brand_slug = require_brand_slug()
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


@bp.route("/api/brain/execute", methods=["POST"])
@rate_limit(max_requests=5, window_seconds=60)
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
        # Jul 6 security fix: shell=True + a substring blocklist was RCE one
        # leaked secret away — the blocklist is trivially bypassed (e.g.
        # "rm${IFS}-rf${IFS}/" or chaining "; anything" past it), and shell=True
        # is what makes chaining/substitution/redirection possible at all.
        # Parse into argv and run WITHOUT a shell — this removes the entire
        # class of shell-metacharacter injection. Trade-off: pipes/&&/;
        # chains no longer work through this endpoint; a single command with
        # args still does (this is the operator-mode tool, not a public one —
        # gated by super-admin + explicit operator-mode toggle above).
        import shlex
        try:
            argv = shlex.split(command)
        except ValueError as e:
            return jsonify({"success": False, "error": f"Could not parse command: {e}"}), 400
        if not argv:
            return jsonify({"success": False, "error": "Empty command"}), 400
        blocked_bins = {"sudo", "curl", "wget", "rm", "reboot", "shutdown", "mkfs", "dd"}
        if argv[0] in blocked_bins:
            return jsonify({"success": False, "error": f"'{argv[0]}' is blocked by the safety filter"}), 403
        try:
            import subprocess as _sp
            result = _sp.run(
                argv,
                shell=False,
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
        except FileNotFoundError:
            return jsonify({"success": False, "error": f"Command not found: {argv[0]}"}), 400
        except Exception as e:
            return jsonify({"success": False, "error": str(e)}), 500

    return jsonify({"success": False, "error": f"Unknown kind: {kind}"}), 400


# ── CONCIERGE (Chief of Staff) — tiered router ────────────────────────────────
# Phase J: the client talks to ONE agent. Trivial/deterministic asks are answered
# here with NO LLM spin-up; substantive asks are forwarded to the Brain LLM, which
# dispatches the right specialist → result lands in the approval dashboard.
@bp.route("/api/concierge", methods=["POST"])
@require_auth
@rate_limit(max_requests=20, window_seconds=60)
def concierge():
    from agents._lib.concierge_router import classify

    body = request.get_json(silent=True) or {}
    message = (body.get("message") or "").strip()
    brand_slug = (body.get("brand_slug") or "").strip()
    if not message:
        return jsonify({"success": False, "error": "message required"}), 400

    route = classify(message)
    tier = route["tier"]
    intent = route["intent"]

    # ── Trivial tier — no LLM, no token cost ──────────────────────────────────
    if tier == "trivial":
        # READ-ONLY: safe to answer / point at a data source with zero side effects.
        if route["safe_execute"]:
            if intent == "list_pending":
                items = _needs_you_items(brand_slug) if brand_slug else []
                n = len(items)
                if n == 0:
                    answer = "Nothing's waiting on you — the queue is clear."
                else:
                    head = "\n".join(
                        f"  • [{it['agent']}] {it['filename']} ({(it.get('created_at') or '')[:10]})"
                        for it in items[:10]
                    )
                    more = f"\n  … and {n - 10} more" if n > 10 else ""
                    answer = f"{n} item{'s' if n != 1 else ''} need your approval:\n{head}{more}"
                return jsonify({"success": True, "data": {
                    "tier": "trivial", "intent": intent, "llm_used": False,
                    "answer": answer, "items": items,
                }})
            # team_status / cost_status: hand back the live data source to GET.
            return jsonify({"success": True, "data": {
                "tier": "trivial", "intent": intent, "llm_used": False,
                "data_endpoint": route["endpoint"],
                "answer": f"Pull live {intent.replace('_', ' ')} from {route['endpoint']}"
                          + (f"?brand_slug={brand_slug}" if brand_slug else ""),
            }})

        # STATE-CHANGING: recognised but never executed here (approval law, K1).
        # Route the user to the dedicated, already-gated endpoint.
        return jsonify({"success": True, "data": {
            "tier": "trivial", "intent": intent, "llm_used": False,
            "action_required": True, "endpoint": route["endpoint"],
            "answer": f"That's a `{intent}` action — confirm it on the work card "
                      f"(POST {route['endpoint']}). I won't run it without your explicit approval.",
        }})

    # ── Substantive tier — needs reasoning → the Brain LLM + a specialist ──────
    return jsonify({"success": True, "data": {
        "tier": "substantive", "intent": None, "llm_used": False,
        "forward_to": "/api/brain/chat",
        "answer": "This needs the team to think — sending it to the Brain to plan + "
                  "dispatch the right specialist. The result will land in your approval queue.",
    }})


@bp.route("/api/brain/chat", methods=["POST"])
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
        _agent_list = ", ".join(DISPATCHABLE_AGENTS)
        system_static = (
            "You are Atlas, chief of staff inside Grid Control — the ORCHESTRATOR of a real marketing "
            "team. You do NOT do the specialists' work yourself. You dispatch them.\n\n"
            "YOUR TOOL:\n"
            "• run_agent(agent_name, rationale) — dispatches a real specialist that scrapes/computes REAL "
            "data and routes its output to the approval queue. It is gated: the user approves before it runs.\n\n"
            f"SPECIALISTS you can dispatch (use the exact agent_name): {_agent_list}.\n\n"
            "HARD RULES:\n"
            "1. When the user wants marketing WORK done — research trends, plan content, write scripts, "
            "design creative, analyze performance, audit SEO, plan ads — you MUST call run_agent to put the "
            "right specialist on it. Then tell the user which specialist you dispatched, in plain language.\n"
            "2. NEVER do that work from your own memory. NEVER invent or 'based on my training' trends, "
            "numbers, competitor data, or performance figures. You have no live data yourself — the "
            "specialists fetch it. Fabricating it is the single worst thing you can do here.\n"
            "3. If you're unsure which specialist fits, ask one short clarifying question — don't guess-answer.\n"
            "4. Pure questions about THIS brand's existing strategy/context you may answer directly and "
            "briefly. Anything needing fresh data or an artifact = run_agent.\n"
            "5. Stay on this brand's marketing. Refuse off-topic (code, trivia, homework) politely.\n"
            "6. Never expose file paths, system names, API keys, or internal architecture. Refer to "
            "specialists by what they do, not by any code name.\n"
            "7. Terse, founder-grade, no fluff, no hype, no emojis."
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

        # Client: dispatch-only tool (run_agent), few loops so it can task + reply.
        # Admin: full tools, multi-turn loop.
        max_loops = 6 if is_admin else 3
        max_tokens = 2000 if is_admin else 1000
        tools_arg = BRAIN_TOOLS_DEF if is_admin else BRAIN_CLIENT_TOOLS_DEF

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
                    elif tu_name == "run_agent":
                        proposals.append({
                            "kind": "agent",
                            "tool_use_id": tu_id,
                            "payload": tu_input,   # {agent_name, rationale}
                        })
                        tool_results.append({
                            "type": "tool_result",
                            "tool_use_id": tu_id,
                            "content": (f"Dispatch of '{(tu_input or {}).get('agent_name','?')}' queued — "
                                        "awaiting the user's approval. Tell them which specialist you put on it."),
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
@bp.route("/api/operator-mode", methods=["GET", "POST"])
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
@bp.route("/api/digest", methods=["GET"])
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


# ── Team Standup ──────────────────────────────────────────────────────────────

@bp.route("/api/standup", methods=["POST"])
@require_auth
def team_standup():
    """Generate a brief team standup summary from session state + recent agent activity."""
    import anthropic as _anthropic

    body = request.get_json() or {}
    brand_slug = require_brand_slug()

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
