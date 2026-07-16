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

    # ── Brand Book (onboarding audit deliverable) ───────────────────────────────
    # The brand-book JSON is a big nested structure (meta/brand/scores/signals…).
    # NEVER dump those keys — the client sees the human `narrative` block only.
    elif ("brand" in agent_lower and "book" in agent_lower) or "onboarding" in agent_lower:
        n = data.get("narrative") or {}
        if not isinstance(n, dict) or not n:
            lines.append(f"## {agent_name}\nBrand audit generated — open the PDF for the full report.")
        else:
            if n.get("headline"):
                lines.append(f"# {n['headline']}")
            if n.get("subhead"):
                lines.append(f"_{n['subhead']}_\n")

            def _para(key: str, title: str) -> None:
                v = n.get(key)
                if isinstance(v, str) and v.strip():
                    lines.append(f"## {title}\n{v.strip()}\n")

            def _bullets(key: str, title: str) -> None:
                v = n.get(key)
                if isinstance(v, list) and v:
                    lines.append(f"## {title}")
                    lines.extend(f"- {it.strip()}" for it in v if isinstance(it, str) and it.strip())
                    lines.append("")

            _bullets("exec_summary", "Executive Summary")
            _para("where_you_stand", "Where You Stand")
            _para("white_space", "White Space")
            _bullets("your_playbook", "Your Playbook")

            rm = n.get("roadmap")
            if isinstance(rm, dict) and rm:
                lines.append("## Roadmap")
                for mk in ("month_1", "month_2", "month_3"):
                    mv = rm.get(mk)
                    if isinstance(mv, dict):
                        title = mv.get("title") or mk.replace("_", " ").title()
                        lines.append(f"**{mk.replace('_', ' ').title()} — {title}:** {mv.get('goal', '')}".rstrip())
                    elif isinstance(mv, str) and mv.strip():
                        lines.append(f"**{mk.replace('_', ' ').title()}:** {mv.strip()}")
                lines.append("")

    # ── Creative Director (winning variant + production notes) ─────────────────
    elif "creative" in agent_lower or "director" in agent_lower:
        lines.append(f"## {agent_name} — Creative Direction\n")
        if data.get("scripts_processed"):
            lines.append(f"*{data['scripts_processed']} script(s) processed*\n")
        wv = data.get("winning_variant")
        if wv:
            lines.append("### Winning creative")
            _human_block(wv, lines)
        notes = data.get("production_notes")
        if isinstance(notes, str) and notes.strip():
            lines.append(f"### Production notes\n{notes.strip()}\n")
        if not wv and not notes:
            lines.append(data.get("data_quality_note") or "No creative variants in this output.")

    # ── Ad Strategist (paid plan or dormant note) ───────────────────────────────
    elif "strategist" in agent_lower:
        lines.append(f"## {agent_name} — Paid Ads Plan\n")
        if data.get("data_quality_note"):
            lines.append(str(data["data_quality_note"]) + "\n")
        for key, title in (("competitor_read", "What competitors are running"),
                           ("ad_angles", "Ad angles"),
                           ("targeting_brief", "Targeting"),
                           ("ab_test_plan", "A/B test plan"),
                           ("budget_note", "Budget"),
                           ("ad_intel_note", "Ad intel note")):
            v = data.get(key)
            if v:
                lines.append(f"### {title}")
                _human_block(v, lines)

    # ── Brand Guardian (consistency audit) ──────────────────────────────────────
    elif "guardian" in agent_lower:
        grade = data.get("overall_grade")
        lines.append(f"## {agent_name} — Brand Consistency Audit" + (f": {grade}" if grade else "") + "\n")
        if data.get("scripts_evaluated") is not None:
            lines.append(f"*{data.get('scripts_evaluated')} script(s) evaluated across {len(data.get('agents_audited') or [])} agent(s)*\n")
        for key, title in (("voice_findings", "Voice"),
                           ("audience_findings", "Audience"),
                           ("positioning_findings", "Positioning"),
                           ("forbidden_phrase_violations", "Forbidden phrases")):
            v = data.get(key)
            if v:
                lines.append(f"### {title}")
                _human_block(v, lines)

    # ── SEO + AEO Agent (audit or no-site note) ─────────────────────────────────
    elif "seo" in agent_lower or "aeo" in agent_lower:
        lines.append(f"## {agent_name} — SEO / AEO Audit\n")
        if data.get("url"):
            lines.append(f"*Site: {data['url']}*\n")
        if data.get("data_quality_note"):
            lines.append(str(data["data_quality_note"]) + "\n")
        if data.get("technical_summary"):
            score = data.get("technical_score")
            lines.append("### Technical health" + (f" — {score}/100" if score is not None else ""))
            _human_block(data["technical_summary"], lines)
        if data.get("aeo"):
            lines.append("### Answer-engine readiness")
            _human_block(data["aeo"], lines)

    # ── Carousel Designer (approval payload) ────────────────────────────────────
    elif "carousel" in agent_lower:
        topic = data.get("topic") or ""
        lines.append(f"## {agent_name}" + (f" — {topic}" if topic else "") + "\n")
        bits = []
        if data.get("platform"):
            bits.append(str(data["platform"]))
        if data.get("slide_count"):
            bits.append(f"{data['slide_count']} slides")
        if bits:
            lines.append(f"*{' · '.join(bits)}*\n")
        if data.get("post_caption"):
            lines.append(f"### Caption\n{data['post_caption']}\n")
        if data.get("save_prompt"):
            lines.append(f"### Save prompt\n{data['save_prompt']}\n")

    # ── Performance Tracker (winning/dead patterns) ─────────────────────────────
    elif "performance" in agent_lower or "tracker" in agent_lower:
        lines.append(f"## {agent_name} — Winning & Dead Patterns\n")
        if data.get("posts_total") is not None:
            lines.append(f"*Based on {data['posts_total']} tracked post(s)*\n")
        for key, title in (("winning_patterns", "Keep doing (winning)"),
                           ("dead_patterns", "Stop doing (dead)")):
            v = data.get(key)
            lines.append(f"### {title}")
            if v:
                _human_block(v, lines)
            else:
                lines.append("_No patterns yet — needs more posts._\n")

    # ── Monthly Program (mix review) ────────────────────────────────────────────
    elif ("monthly" in agent_lower and "program" in agent_lower) or "monthly-mix" in agent_lower:
        lines.append(f"## {agent_name} — Month in Review\n")
        if data.get("window"):
            lines.append(f"*{data['window']}*\n")
        for key, title in (("scale_next_month", "Scale next month"),
                           ("keep", "Keep"),
                           ("cut", "Cut")):
            v = data.get(key)
            if v:
                lines.append(f"### {title}")
                _human_block(v, lines)
        if data.get("budget_split_reason"):
            lines.append(f"### Budget\n{data['budget_split_reason']}\n")

    # ── Generic fallback ───────────────────────────────────────────────────────
    else:
        lines.append(f"## {agent_name} Output\n")
        _flatten_to_markdown(data, lines, depth=0)

    return "\n".join(lines).strip()


_SKIP_KEYS = {
    "agent", "brand", "brand_slug", "generated_at", "timestamp", "run_at",
    "loop_header", "data_provenance", "provenance_validation", "decision_engine",
    "spec_path", "slide_image_paths", "elevenlabs_key_used", "fal_key_used",
}


def _human_block(value: Any, lines: list) -> None:
    """Render one human-facing field (str | list | dict) as readable markdown.
    Skips machine scaffolding keys — this is NOT the generic key-dump."""
    if isinstance(value, str):
        if value.strip():
            lines.append(value.strip())
    elif isinstance(value, list):
        for item in value:
            if isinstance(item, dict):
                head = item.get("pattern") or item.get("finding") or item.get("angle") \
                    or item.get("name") or item.get("title") or item.get("value") or ""
                why = item.get("why") or item.get("reason") or item.get("fix") \
                    or item.get("evidence") or item.get("description") or ""
                if head and why:
                    lines.append(f"- **{head}** — {why}")
                elif head or why:
                    lines.append(f"- {head or why}")
                else:
                    sub: list = []
                    _human_block(item, sub)
                    lines.extend(sub)
            elif isinstance(item, str) and item.strip():
                lines.append(f"- {item.strip()}")
    elif isinstance(value, dict):
        for k, v in value.items():
            if k in _SKIP_KEYS or v in (None, "", [], {}):
                continue
            label = str(k).replace("_", " ").capitalize()
            if isinstance(v, str):
                lines.append(f"**{label}:** {v}")
            elif isinstance(v, (int, float, bool)):
                lines.append(f"**{label}:** {v}")
            elif isinstance(v, list):
                lines.append(f"**{label}:**")
                _human_block(v, lines)
            # nested dicts beyond one level stay out of the human view
    lines.append("")


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
