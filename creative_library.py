"""
creative_library.py — GRID CONTROL Creative Library (gap #3, Jul 11 2026).

The unified asset layer GC was missing: the Creative Director + Carousel Designer generate
visuals/audio/reels into scattered per-agent folders, but there was no single browsable,
tagged, versioned library to find and reuse them. This builds that index.

Design (asset model borrowed from AtroDAM / ResourceSpace, gallery UX from jaaz):
  - The FILESYSTEM is the source of truth for assets — we scan, never duplicate bytes.
  - Each asset gets a stable id (hash of its repo-relative path), derived metadata (kind,
    source agent, category, approval state, post_id), and a serving path the existing
    /api/outputs/media route can stream.
  - VARIANTS/VERSIONS: assets sharing a group_key (post_id, else base name) are one family.
  - TAGS are user-added, persisted in brands/<slug>/creative_library.json (a sidecar overlay;
    the scan stays live so new generations appear automatically).

Zero-assumption: pure stdlib, never raises from the public API (returns [] / {} on trouble).
"""
from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path

_ROOT = Path(__file__).resolve().parent
_BRANDS = _ROOT / "brands"

# Media we index, grouped into a coarse kind.
_KIND = {
    ".png": "image", ".jpg": "image", ".jpeg": "image", ".webp": "image", ".gif": "image",
    ".mp4": "video", ".mov": "video", ".webm": "video",
    ".mp3": "audio", ".wav": "audio", ".m4a": "audio",
}

# Scan roots under a brand dir (label = coarse origin). visuals/ = generated-but-not-yet-in-approval.
_SCAN_ROOTS = [
    ("outputs/pending_approval", "pending"),
    ("outputs/approved", "approved"),
    ("visuals", "generated"),
]

_TS_PREFIX = re.compile(r"^\d{6,}[_-]")          # strip leading timestamp for a stable base name
_POSTID_IN_CAROUSEL = re.compile(r"carousels/\d{8}_([A-Za-z0-9\-]+)/")


def _sidecar(slug: str) -> Path:
    return _BRANDS / slug / "creative_library.json"


def _load_tags(slug: str) -> dict:
    p = _sidecar(slug)
    if not p.exists():
        return {}
    try:
        return (json.loads(p.read_text()) or {}).get("tags", {}) or {}
    except Exception:
        return {}


def _save_tags(slug: str, tags: dict) -> None:
    p = _sidecar(slug)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps({"tags": tags, "updated": _now()}, indent=2, ensure_ascii=False))


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _asset_id(rel: str) -> str:
    return hashlib.sha1(rel.encode("utf-8")).hexdigest()[:12]


def _source_agent(rel_parts: tuple[str, ...]) -> str:
    """Best-effort origin agent from the path (e.g. '.../Creative Director/images/x.png')."""
    known = {"creative director", "creative-director", "carousel designer", "carousel-designer"}
    for seg in rel_parts:
        if seg.lower() in known:
            return seg.replace("-", " ").title()
    if "carousels" in rel_parts or "visuals" in rel_parts:
        return "Carousel Designer"
    return "unknown"


def _post_id(rel: str, stem: str) -> str | None:
    m = _POSTID_IN_CAROUSEL.search(rel)
    if m:
        return m.group(1)
    return None


def _group_key(post_id: str | None, stem: str) -> str:
    if post_id:
        return f"post:{post_id}"
    return "base:" + _TS_PREFIX.sub("", stem).lower()


def build_index(slug: str) -> list[dict]:
    """Live scan of a brand's creative assets → list of asset records (newest first)."""
    brand_dir = _BRANDS / slug
    if not brand_dir.exists():
        return []
    tags = _load_tags(slug)
    assets: list[dict] = []
    for sub, state in _SCAN_ROOTS:
        root = brand_dir / sub
        if not root.exists():
            continue
        for fp in root.rglob("*"):
            if not fp.is_file() or fp.name.startswith("."):
                continue
            kind = _KIND.get(fp.suffix.lower())
            if not kind:
                continue
            try:
                rel = str(fp.relative_to(_ROOT))
                stat = fp.stat()
            except Exception:
                continue
            rel_parts = fp.relative_to(brand_dir).parts
            aid = _asset_id(rel)
            post_id = _post_id(rel, fp.stem)
            assets.append({
                "id": aid,
                "brand_slug": slug,
                "filename": fp.name,
                "kind": kind,
                "ext": fp.suffix.lower().lstrip("."),
                "source_agent": _source_agent(rel_parts),
                "approval_state": state,
                "post_id": post_id,
                "group_key": _group_key(post_id, fp.stem),
                "size_bytes": stat.st_size,
                "created": datetime.fromtimestamp(stat.st_mtime, timezone.utc).isoformat(),
                # served by the existing inline-media route
                "media_url": f"/api/outputs/media/{rel}",
                "path": rel,
                "tags": sorted(tags.get(aid, [])),
            })
    assets.sort(key=lambda a: a["created"], reverse=True)
    return assets


def list_assets(slug: str, *, kind: str | None = None, source_agent: str | None = None,
                approval_state: str | None = None, tag: str | None = None,
                q: str | None = None) -> list[dict]:
    """Filtered view of the library. All filters optional and ANDed."""
    out = build_index(slug)
    if kind:
        out = [a for a in out if a["kind"] == kind]
    if source_agent:
        out = [a for a in out if a["source_agent"].lower() == source_agent.lower()]
    if approval_state:
        out = [a for a in out if a["approval_state"] == approval_state]
    if tag:
        out = [a for a in out if tag.lower() in [t.lower() for t in a["tags"]]]
    if q:
        ql = q.lower()
        out = [a for a in out if ql in a["filename"].lower()
               or ql in (a["post_id"] or "").lower()
               or any(ql in t.lower() for t in a["tags"])]
    return out


def variants(slug: str, group_key: str) -> list[dict]:
    """All assets in one variant family (same post / base name)."""
    return [a for a in build_index(slug) if a["group_key"] == group_key]


def facets(slug: str) -> dict:
    """Counts for the library filter UI (kinds, agents, states, all tags)."""
    items = build_index(slug)
    def _count(key):
        d: dict[str, int] = {}
        for a in items:
            d[a[key]] = d.get(a[key], 0) + 1
        return d
    all_tags: dict[str, int] = {}
    for a in items:
        for t in a["tags"]:
            all_tags[t] = all_tags.get(t, 0) + 1
    return {"total": len(items), "kind": _count("kind"), "source_agent": _count("source_agent"),
            "approval_state": _count("approval_state"), "tags": all_tags}


def set_tags(slug: str, asset_id: str, new_tags: list[str]) -> dict:
    """Replace an asset's user tags. Returns the updated asset (or {} if not found)."""
    tags = _load_tags(slug)
    cleaned = sorted({t.strip() for t in new_tags if t and t.strip()})
    if cleaned:
        tags[asset_id] = cleaned
    else:
        tags.pop(asset_id, None)
    _save_tags(slug, tags)
    return next((a for a in build_index(slug) if a["id"] == asset_id), {})
