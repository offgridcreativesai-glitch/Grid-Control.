"""
supabase/etl.py — GRID CONTROL One-Time Migration
Migrates all existing JSON data from brands/ into Supabase.
Run: python3 supabase/etl.py
"""

import sys
import os
import json
import glob
from pathlib import Path
from datetime import datetime, timezone
from dotenv import load_dotenv

# Resolve project root
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "supabase"))

load_dotenv(ROOT / ".env", override=True)

import db

BRAND_SLUG = "offgrid-creatives-ai"
BRAND_NAME = "OffGrid Creatives AI"
BRAND_DIR  = ROOT / "brands" / BRAND_SLUG

# ── Helpers ───────────────────────────────────────────────────────────────────

def _folder_to_slug(folder_name: str) -> str:
    return folder_name.lower().replace(" ", "-").replace("+", "").replace("&", "").strip("-")

def _parse_loop_header(text: str) -> dict:
    """Extract Loop Header keys from plain-text block before '---'."""
    header = {}
    for line in text.splitlines():
        if ":" in line:
            k, _, v = line.partition(":")
            header[k.strip().upper()] = v.strip()
    return header

def _read_output_file(filepath: Path) -> tuple[dict, dict]:
    """
    Read an agent output file.
    Returns (raw_payload, loop_header).
    Handles both pure JSON and LoopHeader + '---' + JSON formats.
    """
    raw_text = filepath.read_text(encoding="utf-8")
    loop_header: dict = {}

    if "\n---\n" in raw_text:
        parts = raw_text.split("\n---\n", 1)
        loop_header = _parse_loop_header(parts[0])
        payload_text = parts[1].strip()
    else:
        payload_text = raw_text.strip()

    # Try to parse JSON payload
    try:
        payload = json.loads(payload_text)
        if not isinstance(payload, dict):
            payload = {"content": payload}
    except Exception:
        payload = {"raw_text": payload_text}

    return payload, loop_header

def _most_recent(files: list[Path]) -> Path | None:
    """Return the most recently modified file from a list."""
    valid = [f for f in files if f.is_file()]
    if not valid:
        return None
    return max(valid, key=lambda f: f.stat().st_mtime)

# ── Migration report state ────────────────────────────────────────────────────

report = {
    "brand":          None,
    "session_state":  None,
    "pending":        [],
    "approved":       [],
    "training_notes": 0,
    "errors":         [],
}

# ═══════════════════════════════════════════════════════════════════════════════
print("=" * 60)
print("GRID CONTROL — Supabase ETL Migration")
print(f"Brand: {BRAND_SLUG}")
print("=" * 60)

# ── STEP 1: Migrate brand profile ─────────────────────────────────────────────

print("\n[1] Migrating brand profile...")
profile_path = BRAND_DIR / "brand_profile.json"
if profile_path.exists():
    try:
        profile = json.loads(profile_path.read_text())
        brand_row = db.upsert_brand(BRAND_SLUG, BRAND_NAME, profile)
        if brand_row:
            brand_id = brand_row["id"]
            report["brand"] = f"Upserted — id: {brand_id}"
            print(f"  ✓ Brand upserted — id: {brand_id}")
        else:
            raise RuntimeError("upsert_brand returned None")
    except Exception as e:
        msg = f"brand_profile migration failed: {e}"
        report["errors"].append(msg)
        print(f"  ✗ {msg}")
        sys.exit(1)
else:
    print(f"  ✗ brand_profile.json not found at {profile_path}")
    sys.exit(1)

# ── STEP 2: Migrate session state ─────────────────────────────────────────────

print("\n[2] Migrating session state...")
ss_path = BRAND_DIR / "session_state.json"
if ss_path.exists():
    try:
        state = json.loads(ss_path.read_text())
        existing = db._client.table("session_state").select("id").eq("brand_id", brand_id).execute()
        if existing.data:
            res = db._client.table("session_state").update(
                {"state": state, "updated_at": datetime.now(timezone.utc).isoformat()}
            ).eq("brand_id", brand_id).execute()
        else:
            res = db._client.table("session_state").insert(
                {"brand_id": brand_id, "state": state, "updated_at": datetime.now(timezone.utc).isoformat()}
            ).execute()
        report["session_state"] = "Upserted"
        print(f"  ✓ session_state upserted ({len(state)} top-level keys)")
    except Exception as e:
        msg = f"session_state migration failed: {e}"
        report["errors"].append(msg)
        print(f"  ✗ {msg}")
else:
    print("  — session_state.json not found, skipping")

# ── STEP 3: Migrate pending outputs ───────────────────────────────────────────

print("\n[3] Migrating pending_approval/ outputs...")
pending_root = BRAND_DIR / "outputs" / "pending_approval"

if pending_root.exists():
    for agent_folder in sorted(pending_root.iterdir()):
        if not agent_folder.is_dir():
            continue
        agent_slug = _folder_to_slug(agent_folder.name)
        # Collect only .json files (skip audio, .changes.txt, etc.)
        json_files = list(agent_folder.glob("*.json"))
        # Exclude duplicated double-timestamp files (e.g. 20260404_171001_20260404_171001_creatives.json)
        # Keep the cleaner filename (shorter name) when both exist
        seen_bases: dict[str, Path] = {}
        for f in json_files:
            # Use last segment of name as dedup key (e.g. "creatives.json", "funnel.json")
            base_key = f.name.split("_", 2)[-1] if f.name.count("_") >= 2 else f.name
            # Prefer shorter filename (no double timestamp)
            if base_key not in seen_bases:
                seen_bases[base_key] = f
            else:
                # Keep the one with shorter name (no duplicate timestamp prefix)
                existing = seen_bases[base_key]
                if len(f.name) < len(existing.name):
                    seen_bases[base_key] = f
        # Take the most recent among deduplicated files
        target = _most_recent(list(seen_bases.values()))
        if not target:
            continue
        try:
            payload, loop_header = _read_output_file(target)
            run = db.save_agent_run(brand_id=brand_id, agent_slug=agent_slug)
            if not run:
                raise RuntimeError("save_agent_run returned None")
            output = db.save_agent_output(
                brand_id=brand_id,
                agent_run_id=run["id"],
                agent_slug=agent_slug,
                output_type="migrated",
                raw_output=payload,
                formatted_output={},
                loop_header=loop_header,
            )
            if not output:
                raise RuntimeError("save_agent_output returned None")
            db.update_agent_run_status(run["id"], "done")
            db.log_audit(brand_id, "output_migrated_pending", "etl", {"agent": agent_slug, "file": target.name})
            entry = f"{agent_folder.name} ({target.name})"
            report["pending"].append(entry)
            print(f"  ✓ {entry}")
        except Exception as e:
            msg = f"pending/{agent_folder.name}: {e}"
            report["errors"].append(msg)
            print(f"  ✗ {msg}")
else:
    print("  — pending_approval/ folder not found, skipping")

# ── STEP 4: Migrate approved outputs ──────────────────────────────────────────

print("\n[4] Migrating approved/ outputs...")
approved_root = BRAND_DIR / "outputs" / "approved"

if approved_root.exists():
    for agent_folder in sorted(approved_root.iterdir()):
        if not agent_folder.is_dir():
            continue
        agent_slug = _folder_to_slug(agent_folder.name)
        json_files = list(agent_folder.glob("*.json"))
        seen_bases: dict[str, Path] = {}
        for f in json_files:
            base_key = f.name.split("_", 2)[-1] if f.name.count("_") >= 2 else f.name
            if base_key not in seen_bases:
                seen_bases[base_key] = f
            else:
                existing = seen_bases[base_key]
                if len(f.name) < len(existing.name):
                    seen_bases[base_key] = f
        target = _most_recent(list(seen_bases.values()))
        if not target:
            continue
        try:
            payload, loop_header = _read_output_file(target)
            run = db.save_agent_run(brand_id=brand_id, agent_slug=agent_slug)
            if not run:
                raise RuntimeError("save_agent_run returned None")
            output = db.save_agent_output(
                brand_id=brand_id,
                agent_run_id=run["id"],
                agent_slug=agent_slug,
                output_type="migrated",
                raw_output=payload,
                formatted_output={},
                loop_header=loop_header,
            )
            if not output:
                raise RuntimeError("save_agent_output returned None")
            db.update_agent_run_status(run["id"], "done")
            db.approve_output(output["id"])
            db.log_audit(brand_id, "output_migrated_approved", "etl", {"agent": agent_slug, "file": target.name})
            entry = f"{agent_folder.name} ({target.name})"
            report["approved"].append(entry)
            print(f"  ✓ {entry}")
        except Exception as e:
            msg = f"approved/{agent_folder.name}: {e}"
            report["errors"].append(msg)
            print(f"  ✗ {msg}")
else:
    print("  — approved/ folder not found or empty, skipping")

# ── STEP 5: Migrate training notes ────────────────────────────────────────────

print("\n[5] Migrating training notes...")
training_dir = BRAND_DIR / "training_notes"
if training_dir.exists():
    for jsonl_file in sorted(training_dir.glob("*.jsonl")):
        for line in jsonl_file.read_text().splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                note = json.loads(line)
                db.log_audit(brand_id, "training_note_migrated", "etl", note)
                report["training_notes"] += 1
            except Exception as e:
                report["errors"].append(f"training_note parse error: {e}")
    if report["training_notes"] > 0:
        print(f"  ✓ {report['training_notes']} training notes migrated")
    else:
        print("  — No training notes found in .jsonl files")
else:
    print("  — training_notes/ directory not found, skipping")

# ── FINAL REPORT ──────────────────────────────────────────────────────────────

print("\n" + "=" * 60)
print("MIGRATION REPORT")
print("=" * 60)
print(f"\nBrand:            {report['brand']}")
print(f"Session state:    {report['session_state'] or 'skipped'}")
print(f"\nPending outputs migrated: {len(report['pending'])}")
for item in report["pending"]:
    print(f"  • {item}")
print(f"\nApproved outputs migrated: {len(report['approved'])}")
for item in report["approved"]:
    print(f"  • {item}")
if not report["approved"]:
    print("  (none — no approved/ folder found)")
print(f"\nTraining notes migrated: {report['training_notes']}")
print(f"\nErrors: {len(report['errors'])}")
for err in report["errors"]:
    print(f"  ✗ {err}")

if not report["errors"]:
    print("\n✓ ETL complete — zero errors")
else:
    print(f"\n⚠ ETL complete with {len(report['errors'])} error(s) — check above")

print("=" * 60)
