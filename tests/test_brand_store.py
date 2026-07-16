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


def test_key_filename_roundtrip():
    assert brand_store.key_to_filename("_state") == "_state.json"
    assert brand_store.filename_to_key("brand_profile.json") == "brand_profile"
    assert brand_store.filename_to_key("evil.json") is None  # unknown keys rejected


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
    fake = _FakeSvc(rows)
    monkeypatch.setattr(brand_store, "BRANDS_DIR", tmp_path)
    monkeypatch.setattr(brand_store.db, "get_brand", lambda slug: {"id": "b-1", "slug": slug})
    monkeypatch.setattr(brand_store.db, "_svc", lambda: fake)
    return fake


def test_hydrate_fills_empty_cache(monkeypatch, tmp_path):
    _wire(monkeypatch, tmp_path, [
        {"file_key": "brand_profile", "content": {"brand_name": "Acme"},
         "updated_at": "2026-07-16T00:00:00Z"},
        {"file_key": "evil_key", "content": {"x": 1}, "updated_at": "2026-07-16T00:00:00Z"},
    ])
    written = brand_store.hydrate("acme")
    assert written == 1  # unknown file_key skipped
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
    assert not brand_store.push("acme", "evil_key")      # unknown key
    assert not brand_store.push("acme", "brand_profile") # missing file
