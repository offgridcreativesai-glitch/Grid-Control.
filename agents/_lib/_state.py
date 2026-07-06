"""Brand state compaction.

Builds `brands/{slug}/_state.json` — a ~3KB summary that agents can read
instead of loading 7+ JSON files (50-100KB) on every run.

Agents call `load_brand_state(slug)` to get the compact dict. If `_state.json`
is stale (>1 hour old) or missing, it auto-rebuilds.

Use this for any agent that needs lightweight context (voice, audience,
do-not-post, current trends, winning patterns). Agents that need full detail
still read the original files directly.
"""
from __future__ import annotations
import json
import os
import time
from pathlib import Path
from typing import Any

from . import phases as _phases

BASE_DIR = Path(__file__).resolve().parent.parent.parent
STATE_TTL_SECONDS = 3600  # 1 hour


def _safe_load(path: Path) -> dict | list | None:
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text())
    except Exception:
        return None


def _truncate(s: Any, max_chars: int) -> str:
    if not isinstance(s, str):
        s = str(s) if s else ""
    return s[:max_chars]


def build_brand_state(slug: str) -> dict:
    """Construct compact state from full brand files. Returns dict."""
    brand_dir = BASE_DIR / "brands" / slug
    if not brand_dir.exists():
        return {"error": f"brand {slug} not found", "slug": slug}

    bp = _safe_load(brand_dir / "brand_profile.json") or {}
    vp = _safe_load(brand_dir / "voice_profile.json") or {}
    cc = _safe_load(brand_dir / "content_calendar.json") or {}
    ph = _safe_load(brand_dir / "performance_history.json") or {}
    tl = _safe_load(brand_dir / "trends_live.json") or {}
    cd = _safe_load(brand_dir / "contradictions.json") or {}

    # Extract winning + dead patterns (concise list of strings)
    wins: list[str] = []
    if isinstance(ph, dict):
        wp = ph.get("winning_patterns", {}) or {}
        for arr_key in ("hook_patterns_top_3", "topic_clusters_top_3", "formats_top_3"):
            arr = wp.get(arr_key) or []
            if isinstance(arr, list):
                for item in arr:
                    if isinstance(item, str):
                        wins.append(item[:200])
                    elif isinstance(item, dict):
                        label = item.get("label") or item.get("name") or item.get("pattern") or ""
                        if label:
                            wins.append(str(label)[:200])
    deads: list[str] = []
    dp = (ph or {}).get("dead_patterns") or []
    if isinstance(dp, list):
        for d in dp[:8]:
            if isinstance(d, str):
                deads.append(d[:200])
            elif isinstance(d, dict):
                deads.append(str(d.get("label") or d.get("name") or d.get("pattern") or "")[:200])

    # Extract trending topics (top names only)
    trending: list[str] = []
    if isinstance(tl, dict):
        clusters = tl.get("topic_clusters") or []
        if isinstance(clusters, list):
            for c in clusters[:6]:
                if isinstance(c, dict):
                    name = c.get("name") or c.get("title") or c.get("topic")
                    if name:
                        trending.append(str(name)[:120])
                elif isinstance(c, str):
                    trending.append(c[:120])

    # Extract calendar headline (next 5 scheduled posts only)
    upcoming: list[dict] = []
    posts = (cc or {}).get("posts") or []
    if isinstance(posts, list):
        for p in posts[:5]:
            if isinstance(p, dict):
                upcoming.append({
                    "platform": _truncate(p.get("platform"), 30),
                    "scheduled_for": _truncate(p.get("scheduled_for") or p.get("scheduled_time"), 40),
                    "hook": _truncate(p.get("hook") or p.get("caption") or p.get("title"), 200),
                })

    # Open contradictions (just IDs + severity)
    open_contradictions: list[dict] = []
    findings = (cd or {}).get("findings") or []
    if isinstance(findings, list):
        for f in findings:
            if isinstance(f, dict) and f.get("status") == "open":
                open_contradictions.append({
                    "id": f.get("id"),
                    "severity": f.get("severity"),
                    "summary": _truncate(f.get("summary"), 200),
                })

    state = {
        "_meta": {
            "slug": slug,
            "generated_at": time.time(),
            "generator_version": 1,
            "note": "Auto-generated compact summary. Agents read this instead of full files.",
        },
        "brand": {
            "name": bp.get("brand_name") or bp.get("name") or slug,
            "handle": bp.get("instagram_handle") or bp.get("handle") or "",
            "phase": _truncate(bp.get("phase"), 200),
            "program_phase": _phases.normalize_phase(bp.get("program_phase")),
            "industry": _truncate(bp.get("industry"), 100),
            "business_type": _truncate(bp.get("business_type"), 100),
            "founder": _truncate(bp.get("founder_identity"), 300),
            "product": _truncate(bp.get("product"), 300),
            "unique_tension": _truncate(bp.get("unique_tension"), 400),
            "audience": _truncate(bp.get("audience") or bp.get("target_audience") or bp.get("audience_primary"), 400),
            "not_for_audience": _truncate(bp.get("not_for_audience"), 300),
            "platforms": bp.get("platforms") if isinstance(bp.get("platforms"), list) else [],
            "primary_platform": _truncate(bp.get("primary_platform_phase_1"), 50),
        },
        "voice": {
            "summary": _truncate(vp.get("voice_dna_summary_for_script_writer") or vp.get("brand_personality"), 600),
            "blend_directive": _truncate(vp.get("voice_blend_directive"), 300),
            "must": (vp.get("scripts_must") or [])[:8] if isinstance(vp.get("scripts_must"), list) else [],
            "must_not": (vp.get("scripts_must_not") or [])[:8] if isinstance(vp.get("scripts_must_not"), list) else [],
            "cta_style": _truncate(vp.get("cta_style"), 200),
        },
        "performance": {
            "winning_patterns": wins[:8],
            "dead_patterns": deads[:8],
        },
        "trends": {"topics": trending},
        "calendar": {"upcoming": upcoming},
        "contradictions_open": open_contradictions,
    }
    return state


def write_brand_state(slug: str) -> Path:
    """Build and persist `_state.json`. Returns path."""
    brand_dir = BASE_DIR / "brands" / slug
    brand_dir.mkdir(parents=True, exist_ok=True)
    state = build_brand_state(slug)
    state_path = brand_dir / "_state.json"
    state_path.write_text(json.dumps(state, indent=2, ensure_ascii=False))
    return state_path


def load_brand_state(slug: str, force_rebuild: bool = False) -> dict:
    """Get compact brand state. Auto-rebuilds if missing or stale.

    Use this in agents instead of reading 7 separate JSON files.
    """
    state_path = BASE_DIR / "brands" / slug / "_state.json"
    if not state_path.exists() or force_rebuild:
        write_brand_state(slug)
    else:
        try:
            existing = json.loads(state_path.read_text())
            age = time.time() - (existing.get("_meta", {}).get("generated_at") or 0)
            if age > STATE_TTL_SECONDS:
                write_brand_state(slug)
        except Exception:
            write_brand_state(slug)
    return json.loads(state_path.read_text())


if __name__ == "__main__":
    # CLI: python3 agents/_state.py <slug>
    import sys
    slug = sys.argv[1] if len(sys.argv) > 1 else os.getenv("ACTIVE_BRAND", "askgauravai")
    p = write_brand_state(slug)
    sz = p.stat().st_size
    print(f"Wrote {p} ({sz} bytes)")
