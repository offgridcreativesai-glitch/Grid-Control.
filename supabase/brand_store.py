"""brand_store — Supabase is the durable home for per-brand JSON state;
`brands/<slug>/` is a rehydratable CACHE (a wiped dir is a cache miss, not
data loss). ONE module owns sync so the 30+ file readers stay untouched.
Design: docs/DATA_HOME_DESIGN.md. Table: public.brand_state (slice 1.2).

Feature flag: GRID_BRAND_STORE=on enables hydrate/push (default off until
slice 1.6 verifies end-to-end). Import pattern mirrors core.py: supabase/ is
on sys.path, so `import brand_store` next to `import db`.
"""
import json
import os
from datetime import datetime, timezone
from pathlib import Path

import db  # local sibling module (supabase/db.py), NOT the pip package

BRANDS_DIR = Path(__file__).parent.parent / "brands"

# The per-brand JSON files that live in brand_state (docs/DATA_HOME_DESIGN.md map).
STATE_KEYS = (
    "brand_profile", "voice_profile", "content_calendar", "trends_live",
    "competitors_db", "performance_history", "contradictions", "session_state",
    "_state", "brand_narrative", "pivot_decision", "agent_trust_settings",
)


def enabled() -> bool:
    return os.getenv("GRID_BRAND_STORE", "off").strip().lower() == "on"


def key_to_filename(file_key: str) -> str:
    return f"{file_key}.json"


def filename_to_key(filename: str) -> str | None:
    key = filename[:-5] if filename.endswith(".json") else filename
    return key if key in STATE_KEYS else None


def needs_hydration(db_updated_at_iso: str | None, local_mtime_epoch: float | None) -> bool:
    """DB is authoritative: hydrate when the local cache is missing or older.
    Unparseable/missing DB timestamp -> keep local (never clobber on bad data)."""
    if local_mtime_epoch is None:
        return True
    if not db_updated_at_iso:
        return False
    try:
        db_ts = datetime.fromisoformat(db_updated_at_iso.replace("Z", "+00:00")).timestamp()
    except ValueError:
        return False
    return db_ts > local_mtime_epoch + 1  # 1s slack for fs timestamp granularity


def push(brand_slug: str, file_key: str, updated_by: str = "system") -> bool:
    """Upsert one local brand file's JSON content up to Supabase. True on success."""
    if file_key not in STATE_KEYS:
        return False
    path = BRANDS_DIR / brand_slug / key_to_filename(file_key)
    if not path.exists():
        return False
    try:
        content = json.loads(path.read_text())
    except (json.JSONDecodeError, OSError):
        return False  # never push a corrupt cache over good DB data
    brand = db.get_brand(brand_slug)
    if not brand:
        return False
    try:
        db._svc().table("brand_state").upsert({
            "brand_id": brand["id"],
            "file_key": file_key,
            "content": content,
            "updated_at": datetime.now(timezone.utc).isoformat(),
            "updated_by": updated_by,
        }, on_conflict="brand_id,file_key").execute()
        return True
    except Exception as e:
        print(f"[brand_store] push {brand_slug}/{file_key} failed: {e}")
        return False


def push_all(brand_slug: str, updated_by: str = "system") -> int:
    """Push every present local state file. Returns count pushed."""
    return sum(push(brand_slug, k, updated_by) for k in STATE_KEYS)


def hydrate(brand_slug: str) -> int:
    """Pull this brand's state from Supabase into brands/<slug>/ (cache fill).
    Only writes files that are missing or older than the DB row.
    Returns count of files written. Safe no-op on any DB failure."""
    brand = db.get_brand(brand_slug)
    if not brand:
        return 0
    try:
        res = db._svc().table("brand_state").select(
            "file_key,content,updated_at").eq("brand_id", brand["id"]).execute()
        rows = res.data or []
    except Exception as e:
        print(f"[brand_store] hydrate {brand_slug} failed: {e}")
        return 0
    brand_dir = BRANDS_DIR / brand_slug
    written = 0
    for row in rows:
        key = row.get("file_key")
        if key not in STATE_KEYS:
            continue
        path = brand_dir / key_to_filename(key)
        local_mtime = path.stat().st_mtime if path.exists() else None
        if needs_hydration(row.get("updated_at"), local_mtime):
            brand_dir.mkdir(parents=True, exist_ok=True)
            path.write_text(json.dumps(row.get("content") or {}, indent=2))
            written += 1
    return written
