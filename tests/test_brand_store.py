"""Pins brand_store (slice 1.3): Supabase authoritative, disk = cache.
Fail-on-old: before this module existed, a wiped brands/ dir was DATA LOSS
(nothing rehydrated) and local edits never reached the DB. These tests prove
hydrate fills an empty cache, freshness never clobbers newer local work,
and push refuses corrupt/unknown data.

Run: `python3 -m pytest tests/test_brand_store.py -q`
"""
import json
import sys
import time
from pathlib import Path

REPO = Path(__file__).parent.parent
sys.path.insert(0, str(REPO / "supabase"))

import brand_store  # noqa: E402


def test_importable_and_noop_without_db(monkeypatch, tmp_path):
    # Pinned CI failure (run 29497431637): db.py raises at import without
    # SUPABASE_* env; brand_store must stay importable and no-op safely.
    monkeypatch.setattr(brand_store, "db", None)
    monkeypatch.setattr(brand_store, "BRANDS_DIR", tmp_path)
    (tmp_path / "acme").mkdir()
    (tmp_path / "acme" / "brand_profile.json").write_text("{}")
    assert brand_store.hydrate("acme") == 0
    assert brand_store.push("acme", "brand_profile") is False


def test_key_filename_roundtrip():
    assert brand_store.key_to_filename("_state") == "_state.json"
    assert brand_store.filename_to_key("brand_profile.json") == "brand_profile"
    # any path-safe root json syncs (brand-book v7 artifacts etc.)
    assert brand_store.filename_to_key("brand_self_v7.json") == "brand_self_v7"
    # traversal / unsafe names rejected
    assert brand_store.filename_to_key("../etc.json") is None
    assert brand_store.filename_to_key("a/b.json") is None


def test_needs_hydration_decision():
    now = time.time()
    assert brand_store.needs_hydration("2026-07-16T00:00:00Z", None)  # no cache -> fill
    assert not brand_store.needs_hydration(None, now)                 # no DB ts -> keep local
    assert not brand_store.needs_hydration("garbage", now)            # bad ts -> keep local
    # DB newer -> hydrate; local newer -> keep
    assert brand_store.needs_hydration("2999-01-01T00:00:00Z", now)
    assert not brand_store.needs_hydration("2020-01-01T00:00:00Z", now)


class _FakeTable:
    def __init__(self, rows):
        self.rows = rows
        self.upserted = []

    def select(self, *_): return self
    def eq(self, *_): return self
    def execute(self):
        return type("R", (), {"data": self.rows})()
    def upsert(self, payload, **_):
        self.upserted.append(payload)
        return self


class _FakeSvc:
    def __init__(self, rows): self.t = _FakeTable(rows)
    def table(self, _): return self.t


def _wire(monkeypatch, tmp_path, rows):
    """Replace the db module wholesale — on CI there are no SUPABASE_* secrets,
    so brand_store.db is None (import-tolerant); tests must not touch real db."""
    fake = _FakeSvc(rows)
    fake_db = type("FakeDB", (), {
        "get_brand": staticmethod(lambda slug: {"id": "b-1", "slug": slug}),
        "_svc": staticmethod(lambda: fake),
    })
    monkeypatch.setattr(brand_store, "BRANDS_DIR", tmp_path)
    monkeypatch.setattr(brand_store, "db", fake_db)
    return fake


def test_hydrate_fills_empty_cache(monkeypatch, tmp_path):
    _wire(monkeypatch, tmp_path, [
        {"file_key": "brand_profile", "content": {"brand_name": "Acme"},
         "updated_at": "2026-07-16T00:00:00Z"},
        {"file_key": "../../etc/passwd", "content": {"x": 1}, "updated_at": "2026-07-16T00:00:00Z"},
    ])
    written = brand_store.hydrate("acme")
    assert written == 1  # traversal file_key skipped
    saved = json.loads((tmp_path / "acme" / "brand_profile.json").read_text())
    assert saved == {"brand_name": "Acme"}


def test_hydrate_never_clobbers_newer_local(monkeypatch, tmp_path):
    _wire(monkeypatch, tmp_path, [
        {"file_key": "brand_profile", "content": {"brand_name": "OLD-DB"},
         "updated_at": "2020-01-01T00:00:00Z"},
    ])
    d = tmp_path / "acme"; d.mkdir()
    (d / "brand_profile.json").write_text('{"brand_name": "NEWER-LOCAL"}')
    assert brand_store.hydrate("acme") == 0
    assert "NEWER-LOCAL" in (d / "brand_profile.json").read_text()


def test_hydrate_vault_fills_pending_files(monkeypatch, tmp_path):
    # Slice 1.5: fresh server, DB has pending outputs -> files appear with the
    # FE's synthesized names so filename approve/reject resolve. Fail-on-old:
    # hydrate() alone never touched outputs/, so the vault stayed empty.
    fake = _wire(monkeypatch, tmp_path, [])
    fake_db = brand_store.db
    fake_db.get_pending_outputs = staticmethod(lambda bid: [
        {"id": "abcd1234-ffff", "agent_slug": "script-writer",
         "raw_output": {"scripts": [{"hook": "h"}]}},
        {"id": "ee990011-aaaa", "agent_slug": "", "raw_output": {"x": 1}},  # no slug -> skip
        {"id": "77665544-bbbb", "agent_slug": "data-analyst", "raw_output": None},  # no content -> skip
    ])
    written = brand_store.hydrate_vault("acme")
    assert written == 1
    f = tmp_path / "acme" / "outputs" / "pending_approval" / "script-writer" / "script-writer_abcd1234.json"
    assert f.exists() and "scripts" in f.read_text()
    # idempotent: existing file never overwritten
    assert brand_store.hydrate_vault("acme") == 0


def test_push_uploads_local_file(monkeypatch, tmp_path):
    fake = _wire(monkeypatch, tmp_path, [])
    d = tmp_path / "acme"; d.mkdir()
    (d / "voice_profile.json").write_text('{"tone": "warm"}')
    assert brand_store.push("acme", "voice_profile", updated_by="test")
    up = fake.t.upserted[0]
    assert up["brand_id"] == "b-1" and up["content"] == {"tone": "warm"}


def test_push_refuses_corrupt_unknown_missing(monkeypatch, tmp_path):
    _wire(monkeypatch, tmp_path, [])
    d = tmp_path / "acme"; d.mkdir()
    (d / "trends_live.json").write_text("{not json")
    assert not brand_store.push("acme", "trends_live")   # corrupt cache never overwrites DB
    assert not brand_store.push("acme", "../evil")       # unsafe key
    assert not brand_store.push("acme", "brand_profile") # missing file
