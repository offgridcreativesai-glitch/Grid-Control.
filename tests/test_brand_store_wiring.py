"""Pins slice 1.4 — brand_store wired into runtime chokepoints.
Fail-on-old: get_brand_dir 404'd a missing dir even when Supabase held the
brand (fresh/wiped server = every brand 'not found'). Fixed: hydration gets a
chance before the 404, TTL-gated; write-backs are flag-gated no-ops when off.

Run: `python3 -m pytest tests/test_brand_store_wiring.py -q`
"""
import sys
from pathlib import Path

import pytest
from werkzeug.exceptions import NotFound

REPO = Path(__file__).parent.parent
sys.path.insert(0, str(REPO))

import core  # noqa: E402


class _FakeStore:
    def __init__(self, on: bool, brands_dir: Path):
        self.on = on
        self.brands_dir = brands_dir
        self.hydrate_calls = 0
        self.pushed = []

    def enabled(self):
        return self.on

    def hydrate(self, slug):
        self.hydrate_calls += 1
        (self.brands_dir / slug).mkdir(parents=True, exist_ok=True)
        return 1

    def push(self, slug, key):
        self.pushed.append((slug, key))
        return True

    def push_all(self, slug):
        self.pushed.append((slug, "*"))
        return 1


@pytest.fixture()
def wired(monkeypatch, tmp_path):
    def _mk(on: bool):
        fake = _FakeStore(on, tmp_path)
        monkeypatch.setattr(core, "_brand_store", fake)
        monkeypatch.setattr(core, "BRANDS_DIR", tmp_path)
        monkeypatch.setattr(core, "_last_hydrate", {})
        return fake
    return _mk


def test_flag_off_preserves_404_and_never_hydrates(wired):
    fake = wired(on=False)
    with pytest.raises(NotFound):
        core.get_brand_dir("ghost-brand")
    assert fake.hydrate_calls == 0


def test_cold_cache_hydrates_instead_of_404(wired):
    # THE fix: on the old code this raised NotFound even though the DB had it.
    fake = wired(on=True)
    d = core.get_brand_dir("cloud-brand")
    assert d.exists() and fake.hydrate_calls == 1
    # warm hit within TTL: no second DB trip
    core.get_brand_dir("cloud-brand")
    assert fake.hydrate_calls == 1


def test_push_helper_is_flag_gated(wired):
    fake = wired(on=False)
    core._brand_store_push("b", "brand_profile")
    assert fake.pushed == []
    fake = wired(on=True)
    core._brand_store_push("b", "brand_profile")
    core._brand_store_push("b")  # no keys = push_all
    assert ("b", "brand_profile") in fake.pushed and ("b", "*") in fake.pushed
