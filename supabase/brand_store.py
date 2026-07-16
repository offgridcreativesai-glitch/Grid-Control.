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
import re
from datetime import datetime, timezone
from pathlib import Path

# Local sibling module (supabase/db.py), NOT the pip package. db raises at
# import when SUPABASE_* env is absent (e.g. CI) — mirror core.py's tolerance:
# store becomes a safe no-op instead of an import bomb.
try:
    import db
except Exception:
    db = None

BRANDS_DIR = Path(__file__).parent.parent / "brands"

# Core per-brand JSON files (docs/DATA_HOME_DESIGN.md map) — documentation of
# the known set. Any path-safe root-level *.json syncs (e.g. brand-book v7
# artifacts like brand_self_v7 / channel_scores_v7 / memory_doc), so new brand
# files never silently miss the durable home.
STATE_KEYS = (
    "brand_profile", "voice_profile", "content_calendar", "trends_live",
    "competitors_db", "performance_history", "contradictions", "session_state",
    "_state", "brand_narrative", "pivot_decision", "agent_trust_settings",
)

_KEY_RE = re.compile(r"^[a-z0-9_][a-z0-9_-]*$")


def _valid_key(file_key: str) -> bool:
    """Path-safe file key: bare name, no slashes/dots — blocks traversal."""
    return bool(_KEY_RE.match(file_key or ""))


def enabled() -> bool:
    return os.getenv("GRID_BRAND_STORE", "off").strip().lower() == "on"


def key_to_filename(file_key: str) -> str:
    return f"{file_key}.json"


def filename_to_key(filename: str) -> str | None:
    key = filename[:-5] if filename.endswith(".json") else filename
    return key if _valid_key(key) else None


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
    if not _valid_key(file_key):
        return False
    if db is None:
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
    """Push every root-level *.json in the brand dir. Returns count pushed."""
    brand_dir = BRANDS_DIR / brand_slug
    if not brand_dir.is_dir():
        return 0
    keys = {filename_to_key(p.name) for p in brand_dir.glob("*.json")}
    return sum(push(brand_slug, k, updated_by) for k in sorted(k for k in keys if k))


def hydrate_vault(brand_slug: str) -> int:
    """Cache-fill pending-vault files from agent_outputs rows (DB = truth).
    Filenames match the FE's synthesized `{agent_slug}_{id8}.json` (see
    routes/content.py get_pending_outputs DB path) so filename-based
    approve/reject resolve on a fresh server. Never overwrites existing files."""
    if db is None:
        return 0
    brand = db.get_brand(brand_slug)
    if not brand:
        return 0
    try:
        rows = db.get_pending_outputs(brand["id"])
    except Exception as e:
        print(f"[brand_store] hydrate_vault {brand_slug} failed: {e}")
        return 0
    pending_root = BRANDS_DIR / brand_slug / "outputs" / "pending_approval"
    written = 0
    for row in rows:
        slug_key = row.get("agent_slug") or ""
        rid = (row.get("id") or "")[:8]
        raw = row.get("raw_output")
        if not slug_key or not rid or not raw:
            continue
        path = pending_root / slug_key / f"{slug_key}_{rid}.json"
        if path.exists():
            continue
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(raw if isinstance(raw, str) else json.dumps(raw, indent=2))
        written += 1
    return written


def hydrate(brand_slug: str) -> int:
    """Pull this brand's state from Supabase into brands/<slug>/ (cache fill).
    Only writes files that are missing or older than the DB row.
    Returns count of files written. Safe no-op on any DB failure."""
    if db is None:
        return 0
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
        if not key or not _valid_key(key):
            continue
        path = brand_dir / key_to_filename(key)
        local_mtime = path.stat().st_mtime if path.exists() else None
        if needs_hydration(row.get("updated_at"), local_mtime):
            brand_dir.mkdir(parents=True, exist_ok=True)
            path.write_text(json.dumps(row.get("content") or {}, indent=2))
            written += 1
    return written
