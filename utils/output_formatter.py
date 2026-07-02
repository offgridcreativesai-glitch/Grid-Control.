"""
output_formatter.py — OffGrid Marketing OS
Converts agent JSON outputs to clean human-readable markdown/plain English.
Never writes raw JSON to Notion or dashboard cards.
"""

from typing import Any


def format_scripts(data: dict) -> list[dict]:
    """
    Convert Script Writer output to a list of clean dicts.
    Keys: platform, format, hook, body, cta, requires_human_face
    """
    scripts_raw = data.get("scripts", [])
    result = []
    for item in scripts_raw:
        s = item.get("script", item)  # handle both wrapped and flat
        body = s.get("body", "")
        if isinstance(body, dict):
            # Carousel / Story frames — flatten to readable text
            parts = []
            for frame_key, frame in body.items():
                label = frame_key.replace("_", " ").title()
                bits = []
                if frame.get("headline"):
                    bits.append(f"**{frame['headline']}**")
                if frame.get("subtext"):
                    bits.append(frame["subtext"])
                if frame.get("body_copy"):
                    bits.append(frame["body_copy"])
                if frame.get("poll_question"):
                    bits.append(f"Poll: {frame['poll_question']}")
                if frame.get("cta_line"):
                    bits.append(f"→ {frame['cta_line']}")
                parts.append(f"{label}: {' | '.join(bits)}")
            body_text = "\n".join(parts)
        else:
            body_text = str(body)

        result.append({
            "platform": s.get("platform") or item.get("platform", ""),
            "format": s.get("format") or item.get("format", ""),
            "hook": s.get("hook", ""),
            "body": body_text,
            "cta": s.get("cta", ""),
            "requires_human_face": bool(item.get("requires_human_face", False)),
        })
    return result


def format_calendar(data: dict) -> list[dict]:
    """
    Convert Content Planner output to flattened list.
    Keys: day, topic, platform, format, hook
    """
    result = []
    day_counter = 1
    for week_key in ["week_1", "week_2", "week_3", "week_4"]:
        week = data.get(week_key, {})
        posts = week.get("posts", [])
        for post in posts:
            result.append({
                "day": post.get("day", day_counter),
                "topic": post.get("topic", ""),
                "platform": post.get("platform", ""),
                "format": post.get("format", ""),
                "hook": post.get("hook", ""),
            })
            day_counter += 1
    # Also handle flat posts array
    if not result and "posts" in data:
        for post in data["posts"]:
            result.append({
                "day": post.get("day", day_counter),
                "topic": post.get("topic", ""),
                "platform": post.get("platform", ""),
                "format": post.get("format", ""),
                "hook": post.get("hook", ""),
            })
            day_counter += 1
    return result


def format_strategy(data: dict) -> list[dict]:
    """
    Convert Strategy Agent output to list of phase dicts.
    Keys: phase_name, days, goal, success_gate
    """
    result = []
    for phase_key in ["phase_1", "phase_2", "phase_3"]:
        phase = data.get(phase_key)
        if not phase:
            continue
        result.append({
            "phase_name": phase.get("name", phase_key.replace("_", " ").title()),
            "days": phase.get("days", ""),
            "goal": phase.get("goal", ""),
            "success_gate": phase.get("success_gate", ""),
        })
    # Handle phases array format
    if not result and "phases" in data:
        for phase in data["phases"]:
            result.append({
                "phase_name": phase.get("name", ""),
                "days": phase.get("days", ""),
                "goal": phase.get("goal", ""),
                "success_gate": phase.get("success_gate", ""),
            })
    return result


def format_data_analyst(data: dict) -> tuple[str, list[str]]:
    """
    Convert Data Analyst output to (executive_summary string, action_items list).
    """
    summary = data.get("executive_summary") or data.get("summary") or data.get("overview", "")
    if isinstance(summary, dict):
        summary = summary.get("text", str(summary))

    raw_actions = (
        data.get("action_items")
        or data.get("recommendations")
        or data.get("actions")
        or []
    )
    actions = []
    for item in raw_actions:
        if isinstance(item, str):
            actions.append(item)
        elif isinstance(item, dict):
            text = item.get("action") or item.get("recommendation") or item.get("text", str(item))
            actions.append(str(text))

    return str(summary), actions


def format_funnel(data: dict) -> list[dict]:
    """
    Convert Funnel Specialist output to list of stage dicts.
    Each stage has: stage_name, description
    """
    result = []
    stages_raw = (
        data.get("funnel_stages")
        or data.get("stages")
        or data.get("funnel")
        or []
    )
    if isinstance(stages_raw, dict):
        stages_raw = [{"stage_name": k, **v} if isinstance(v, dict) else {"stage_name": k, "description": str(v)}
                      for k, v in stages_raw.items()]
    for stage in stages_raw:
        result.append({
            "stage_name": stage.get("stage_name") or stage.get("name") or stage.get("stage", ""),
            "description": stage.get("description") or stage.get("goal") or stage.get("detail", ""),
        })
    return result


def format_website(data: dict) -> list[dict]:
    """
    Convert Website Agent output to list of pages.
    Each page has: name, purpose, key_copy
    """
    result = []
    pages_raw = data.get("pages") or data.get("site_pages") or []
    for page in pages_raw:
        result.append({
            "name": page.get("name") or page.get("page_name") or page.get("title", ""),
            "purpose": page.get("purpose") or page.get("description", ""),
            "key_copy": page.get("key_copy") or page.get("copy") or page.get("headline", ""),
        })
    return result


def format_for_notion(agent_name: str, data: Any) -> str:
    """
    Convert any agent output to a clean human-readable markdown string.
    No JSON anywhere. Used for Notion card body and dashboard.
    """
    if data is None:
        return f"No output data available for {agent_name}."

    # If it's a plain string, return as-is (strip any JSON artifacts)
    if isinstance(data, str):
        # If it looks like JSON, try to parse and format it
        if data.strip().startswith("{") or data.strip().startswith("["):
            try:
                import json
                parsed = json.loads(data)
                return format_for_notion(agent_name, parsed)
            except Exception:
                pass
        return data

    if not isinstance(data, dict):
        return str(data)

    agent_lower = agent_name.lower()
    lines: list[str] = []

    # ── Script Writer ──────────────────────────────────────────────────────────
    if "script" in agent_lower:
        scripts = format_scripts(data)
        if scripts:
            lines.append(f"## {agent_name} — {len(scripts)} Script(s)\n")
            for i, s in enumerate(scripts, 1):
                lines.append(f"### Script {i} — {s['platform']} ({s['format']})")
                if s["requires_human_face"]:
                    lines.append("⚑ **Human face required**")
                if s["hook"]:
                    lines.append(f"**Hook:** {s['hook']}")
                if s["body"]:
                    lines.append(f"**Body:**\n{s['body']}")
                if s["cta"]:
                    lines.append(f"**CTA:** {s['cta']}")
                lines.append("")
        else:
            lines.append(f"## {agent_name}\nNo scripts found in output.")

    # ── Content Planner ────────────────────────────────────────────────────────
    elif "content" in agent_lower or "planner" in agent_lower or "calendar" in agent_lower:
        posts = format_calendar(data)
        strategic_angle = data.get("strategic_angle", "")
        if strategic_angle:
            lines.append(f"## Strategic Angle\n{strategic_angle}\n")
        lines.append(f"## {agent_name} — {len(posts)} Post(s) Planned\n")
        for post in posts:
            lines.append(f"- **Day {post['day']}** | {post['platform']} · {post['format']}: {post['topic']}")
            if post["hook"]:
                lines.append(f"  *Hook:* \"{post['hook']}\"")

    # ── Strategy Agent ─────────────────────────────────────────────────────────
    elif "strategy" in agent_lower:
        phases = format_strategy(data)
        strategic_angle = data.get("strategic_angle", "")
        if strategic_angle:
            lines.append(f"## Strategic Angle\n{strategic_angle}\n")
        lines.append(f"## {agent_name} — {len(phases)} Phase(s)\n")
        for phase in phases:
            lines.append(f"### {phase['phase_name']} ({phase['days']})")
            lines.append(f"**Goal:** {phase['goal']}")
            if phase["success_gate"]:
                lines.append(f"**Success Gate:** {phase['success_gate']}")
            lines.append("")

    # ── Data Analyst ───────────────────────────────────────────────────────────
    elif "data" in agent_lower or "analyst" in agent_lower:
        summary, actions = format_data_analyst(data)
        lines.append(f"## {agent_name} — Executive Summary\n{summary}\n")
        if actions:
            lines.append("## Action Items")
            for action in actions:
                lines.append(f"- {action}")

    # ── Weekly Program (GRIDLOCK-PROGRAM-01JUL Stage 2 — review-loop digest) ────
    elif "weekly program" in agent_lower or "weekly-program" in agent_lower:
        lines.append(f"## {agent_name} — Last Week + Keep / Cut / Scale\n")
        summary = data.get("executive_summary", "")
        if summary:
            lines.append(f"**Executive summary:** {summary}\n")
        actions = data.get("action_items") or []
        if actions:
            lines.append("**Action items:**")
            for a in actions:
                lines.append(f"- {a}")
            lines.append("")
        keep = data.get("keep") or []
        lines.append(f"### Keep ({len(keep)})")
        if keep:
            for k in keep:
                lines.append(f"- **{k.get('pattern', '?')}** — {k.get('why', '')}")
        else:
            lines.append("- No winning patterns identified yet.")
        cut = data.get("cut") or []
        lines.append(f"\n### Cut ({len(cut)})")
        if cut:
            for c in cut:
                lines.append(f"- **{c.get('pattern', '?')}** — {c.get('why', '')}")
        else:
            lines.append("- Nothing flagged as dead yet.")
        scale = data.get("scale_decision", "STAY")
        lines.append(f"\n### Scale: {scale}")
        if data.get("scale_reason"):
            lines.append(data["scale_reason"])
        missing = [
            label for key, label in (
                ("has_data_analyst", "Data Analyst"),
                ("has_performance_history", "Performance Tracker"),
                ("has_pivot_decision", "Trend Sentinel"),
            ) if not data.get(key)
        ]
        if missing:
            lines.append(f"\n_No data yet from: {', '.join(missing)}._")

    # ── Funnel Specialist ──────────────────────────────────────────────────────
    elif "funnel" in agent_lower:
        stages = format_funnel(data)
        lines.append(f"## {agent_name} — Funnel ({len(stages)} stages)\n")
        for stage in stages:
            lines.append(f"### {stage['stage_name']}")
            lines.append(stage["description"])
            lines.append("")

    # ── Website Agent ──────────────────────────────────────────────────────────
    elif "website" in agent_lower:
        pages = format_website(data)
        lines.append(f"## {agent_name} — {len(pages)} Page(s)\n")
        for page in pages:
            lines.append(f"### {page['name']}")
            if page["purpose"]:
                lines.append(f"**Purpose:** {page['purpose']}")
            if page["key_copy"]:
                lines.append(f"**Key Copy:** {page['key_copy']}")
            lines.append("")

    # ── Trend Researcher ───────────────────────────────────────────────────────
    elif "trend" in agent_lower:
        lines.append(f"## {agent_name} — Trend Report\n")
        trends = data.get("trends") or data.get("top_trends") or data.get("trend_signals") or []
        if isinstance(trends, list):
            for t in trends:
                if isinstance(t, str):
                    lines.append(f"- {t}")
                elif isinstance(t, dict):
                    name = t.get("trend") or t.get("topic") or t.get("name") or t.get("title", "")
                    insight = t.get("insight") or t.get("signal") or t.get("description", "")
                    lines.append(f"- **{name}**: {insight}")
        elif isinstance(trends, dict):
            for k, v in trends.items():
                lines.append(f"- **{k}**: {v}")

        # Handle summary fields
        for key in ["summary", "key_insight", "recommendation", "action"]:
            val = data.get(key)
            if val:
                lines.append(f"\n**{key.replace('_', ' ').title()}:** {val}")

        # Fallback: dump all top-level non-nested fields
        if not trends:
            for k, v in data.items():
                if isinstance(v, str) and v:
                    lines.append(f"**{k.replace('_', ' ').title()}:** {v}")
                elif isinstance(v, list) and v and isinstance(v[0], str):
                    lines.append(f"**{k.replace('_', ' ').title()}:**")
                    for item in v:
                        lines.append(f"  - {item}")

    # ── Community Manager (Wave 2) ───────────────────────────────────────────────
    elif "community" in agent_lower:
        drafts = data.get("drafts", []) or []
        summ = data.get("summary", {}) or {}
        lines.append(f"## {agent_name} — {len(drafts)} reply draft(s)\n")
        if summ:
            cats = summ.get("categories", {})
            cat_str = ", ".join(f"{k}: {v}" for k, v in cats.items()) if isinstance(cats, dict) else ""
            lines.append(f"*Ingested {summ.get('ingested', '?')} · drafted {summ.get('replies_drafted', '?')} · "
                         f"ignored spam {summ.get('ignored_spam', 0)}*" + (f"\n*Categories:* {cat_str}" if cat_str else ""))
            lines.append("")
        for d in drafts:
            rt = d.get("responds_to", {}) or {}
            lines.append(f"### @{rt.get('author') or 'unknown'} · {rt.get('platform') or '?'} — {d.get('category', '?')}")
            if rt.get("text"):
                lines.append(f"> {rt['text']}")
            if d.get("action") == "ignore":
                lines.append("*Action: ignore (spam) — no reply.*")
            else:
                if d.get("winner"):
                    lines.append(f"**Reply:** {d['winner']}")
                if d.get("winner_reason"):
                    lines.append(f"*Why:* {d['winner_reason']}")
            lines.append("")
        lines.append("_Drafts only — never auto-posted._")

    # ── DM Customer Hunter (Wave 2) ──────────────────────────────────────────────
    elif "hunter" in agent_lower:
        drafts = data.get("drafts", []) or []
        summ = data.get("summary", {}) or {}
        lines.append(f"## {agent_name} — {len(drafts)} DM draft(s)\n")
        if summ:
            lines.append(f"*Discovered {summ.get('discovered', '?')} ({summ.get('discovery_source', '?')}) · "
                         f"qualified {summ.get('qualified_6plus', '?')} · drafted {summ.get('drafted_today', '?')} "
                         f"(cap {summ.get('daily_cap', '?')}, held {summ.get('held_over', 0)})*")
            lines.append("")
        for d in drafts:
            _tier = {"tier1_engaged": "T1·DM-ok", "tier2_hashtag": "T2·comment-first",
                     "tier3_engage_only": "T3·engage-only"}.get(d.get("tier", ""), "")
            lines.append(f"### @{d.get('handle', '?')} — ICP {d.get('icp_score', '?')}/10"
                         + (f" · {_tier}" if _tier else ""))
            if d.get("action") == "engage_only":
                lines.append("*Tier 3 — engage/comment only, no DM.*")
            if d.get("research_summary"):
                lines.append(f"*{d['research_summary']}*")
            sig = d.get("intent_signals") or []
            if sig:
                lines.append("Signals: " + ", ".join(str(s) for s in sig))
            if d.get("winner"):
                lines.append(f"**DM:** {d['winner']}")
            if d.get("winner_reason"):
                lines.append(f"*Why:* {d['winner_reason']}")
            lines.append("")
        lines.append("_Drafts only — first DM is value/question, never auto-sent._")

    # ── Email Marketing Agent (Wave 2) ───────────────────────────────────────────
    elif "email" in agent_lower:
        seqs = data.get("sequences", []) or []
        summ = data.get("summary", {}) or {}
        lines.append(f"## {agent_name} — {len(seqs)} nurture sequence(s)\n")
        if summ:
            lines.append(f"*Ingested {summ.get('ingested', '?')} · drafted {summ.get('drafted', '?')}*")
            lines.append("")
        for s in seqs:
            fs = s.get("for_subscriber", {}) or {}
            who = fs.get("name") or s.get("email") or "subscriber"
            interest = fs.get("product_interest")
            lines.append(f"### {who}" + (f" — interested in {interest}" if interest else ""))
            for em in s.get("emails", []):
                subj = em.get("subject_winner") or (em.get("subject_variants") or [""])[0]
                lines.append(f"**Day {em.get('day', '?')} — {subj}**")
                if em.get("body"):
                    lines.append(em["body"])
                lines.append("")
        lines.append("_Drafts only — never auto-sent; send via Gmail after approval._")

    # ── Generic fallback ───────────────────────────────────────────────────────
    else:
        lines.append(f"## {agent_name} Output\n")
        _flatten_to_markdown(data, lines, depth=0)

    return "\n".join(lines).strip()


def _flatten_to_markdown(obj: Any, lines: list, depth: int = 0, max_depth: int = 4) -> None:
    """Recursively convert a dict/list to readable markdown lines."""
    if depth > max_depth:
        return
    indent = "  " * depth
    if isinstance(obj, dict):
        for key, val in obj.items():
            label = str(key).replace("_", " ").title()
            if isinstance(val, (dict, list)):
                lines.append(f"{indent}**{label}:**")
                _flatten_to_markdown(val, lines, depth + 1, max_depth)
            elif val not in (None, "", [], {}):
                lines.append(f"{indent}**{label}:** {val}")
    elif isinstance(obj, list):
        for item in obj:
            if isinstance(item, (dict, list)):
                _flatten_to_markdown(item, lines, depth, max_depth)
                lines.append("")
            elif item not in (None, "", [], {}):
                lines.append(f"{indent}- {item}")
