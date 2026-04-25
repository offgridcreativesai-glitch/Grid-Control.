"""
managed_agents/context_builder.py

Serialises per-brand data files into a human-readable text block that gets
prepended to every agent session's task prompt. Agents read this context to
know who they are working for, what the brand is, and what prior agents found.

Usage:
    from managed_agents.context_builder import build_context
    ctx = build_context("dropvolt")
    # ctx is a string you prepend to the task prompt
"""

import json
import pathlib
from typing import Any


BRANDS_DIR = pathlib.Path(__file__).parent.parent / "brands"


def _load_json(path: pathlib.Path) -> Any:
    """Load JSON file; return empty dict/list on missing or corrupt file."""
    try:
        with open(path) as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def _fmt_list(items: list, indent: int = 2) -> str:
    pad = " " * indent
    return "\n".join(f"{pad}- {item}" for item in items) if items else f"{' ' * indent}(none)"


def _fmt_dict(d: dict, indent: int = 2) -> str:
    pad = " " * indent
    lines = []
    for k, v in d.items():
        if isinstance(v, list):
            lines.append(f"{pad}{k}:")
            lines.append(_fmt_list(v, indent + 2))
        elif isinstance(v, dict):
            lines.append(f"{pad}{k}:")
            lines.append(_fmt_dict(v, indent + 2))
        else:
            lines.append(f"{pad}{k}: {v}")
    return "\n".join(lines)


def build_context(brand_slug: str) -> str:
    """
    Build a structured text context string from a brand's data files.
    Returns a multi-section string ready to prepend to any agent task prompt.
    """
    brand_dir = BRANDS_DIR / brand_slug
    if not brand_dir.exists():
        return f"[context_builder] ERROR: brand directory not found for slug '{brand_slug}'"

    sections: list[str] = []

    # ── BRAND PROFILE ────────────────────────────────────────────────────────
    profile = _load_json(brand_dir / "brand_profile.json")
    if profile:
        lines = [
            "## BRAND PROFILE",
            f"Name:        {profile.get('name', '?')}",
            f"Slug:        {brand_slug}",
            f"Niche:       {profile.get('niche', '?')}",
            f"Product:     {profile.get('product_description', '?')}",
            f"Target:      {profile.get('target_audience', '?')}",
            f"Tone:        {profile.get('tone', '?')}",
            f"Platforms:   {', '.join(profile.get('platforms', []))}",
            f"Competitors: {', '.join(profile.get('competitors', []))}",
            f"Goals:       {', '.join(profile.get('goals', []))}",
            f"Bottlenecks: {', '.join(profile.get('bottlenecks', []))}",
        ]
        # Social handles
        handles = profile.get("social_handles", {})
        if handles:
            lines.append("Social handles:")
            for platform, handle in handles.items():
                lines.append(f"  {platform}: {handle}")
        # Pricing
        pricing = profile.get("pricing", {})
        if pricing:
            lines.append(f"Pricing:     {json.dumps(pricing)}")
        sections.append("\n".join(lines))

    # ── SESSION STATE ─────────────────────────────────────────────────────────
    session = _load_json(brand_dir / "session_state.json")
    if session:
        pipeline = session.get("pipeline", {})
        completed = [k for k, v in pipeline.items() if v.get("status") == "done"]
        running   = [k for k, v in pipeline.items() if v.get("status") == "running"]
        lines = [
            "## PIPELINE STATE",
            f"Completed agents: {', '.join(completed) if completed else 'none'}",
            f"Currently running: {', '.join(running) if running else 'none'}",
        ]
        sections.append("\n".join(lines))

    # ── LIVE TRENDS ───────────────────────────────────────────────────────────
    trends = _load_json(brand_dir / "trends_live.json")
    if trends:
        top_trends = trends.get("top_trends", [])
        scraped_at = trends.get("scraped_at", "unknown")
        lines = ["## LIVE TREND DATA", f"Scraped at: {scraped_at}"]
        if top_trends:
            lines.append("Top trends (up to 10):")
            for t in top_trends[:10]:
                if isinstance(t, dict):
                    label = t.get("topic") or t.get("hashtag") or t.get("trend") or str(t)
                    score = t.get("relevance_score") or t.get("score") or ""
                    lines.append(f"  - {label}" + (f" (score: {score})" if score else ""))
                else:
                    lines.append(f"  - {t}")
        sections.append("\n".join(lines))

    # ── COMPETITORS DB ────────────────────────────────────────────────────────
    competitors = _load_json(brand_dir / "competitors_db.json")
    if competitors:
        lines = ["## COMPETITOR INTELLIGENCE"]
        comp_list = competitors if isinstance(competitors, list) else competitors.get("competitors", [])
        for c in comp_list[:5]:  # cap at 5 to save tokens
            if isinstance(c, dict):
                name = c.get("name") or c.get("handle") or "unknown"
                followers = c.get("followers") or c.get("follower_count") or "?"
                strategy  = c.get("strategy") or c.get("content_strategy") or ""
                lines.append(f"  {name}: {followers} followers. {strategy}")
        sections.append("\n".join(lines))

    # ── RECENT APPROVED OUTPUTS ───────────────────────────────────────────────
    approved_dir = brand_dir / "outputs" / "approved"
    if approved_dir.exists():
        approved_files = sorted(approved_dir.rglob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True)
        if approved_files:
            lines = ["## RECENT APPROVED OUTPUTS (last 3)"]
            for fp in approved_files[:3]:
                lines.append(f"\n### {fp.parent.name} / {fp.stem}")
                data = _load_json(fp)
                # Summarise — just first 600 chars of JSON to save tokens
                summary = json.dumps(data, indent=2)[:600]
                if len(json.dumps(data)) > 600:
                    summary += "\n  ... (truncated)"
                lines.append(summary)
            sections.append("\n".join(lines))

    if not sections:
        return f"[context_builder] No data files found for brand '{brand_slug}'"

    header = (
        f"╔══════════════════════════════════════════════════════════════╗\n"
        f"║  BRAND CONTEXT — {brand_slug.upper():<44}║\n"
        f"║  Injected by OffGrid Marketing OS context_builder           ║\n"
        f"╚══════════════════════════════════════════════════════════════╝\n"
    )

    return header + "\n\n".join(sections) + "\n\n---\n\n"
