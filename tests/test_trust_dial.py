"""Invariant tests for the per-agent trust dial (agents/_lib/trust_dial.py).

Ported from the GC Cleanroom Prototype comparison — trust-dial auto-advance
and its fail-safe default were flagged as untested (gap #6: "zero coverage
on ... trust_dial auto-advance").
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from agents._lib import trust_dial


def test_default_is_consult_for_unset_agent(monkeypatch, tmp_path):
    monkeypatch.setattr(trust_dial, "_BRANDS_DIR", tmp_path)
    assert trust_dial.get_level("brand-x", "script-writer") == "consult"


def test_set_and_get_level(monkeypatch, tmp_path):
    monkeypatch.setattr(trust_dial, "_BRANDS_DIR", tmp_path)
    trust_dial.set_level("brand-x", "script-writer", "automate")
    assert trust_dial.get_level("brand-x", "script-writer") == "automate"
    # Unrelated agent on the same brand is untouched (still default).
    assert trust_dial.get_level("brand-x", "strategy-agent") == "consult"


def test_invalid_level_rejected(monkeypatch, tmp_path):
    monkeypatch.setattr(trust_dial, "_BRANDS_DIR", tmp_path)
    try:
        trust_dial.set_level("brand-x", "script-writer", "yolo")
        assert False, "should have raised ValueError"
    except ValueError:
        pass
    # The rejected write must not have partially landed.
    assert trust_dial.get_level("brand-x", "script-writer") == "consult"


def test_corrupt_settings_file_fails_safe_to_consult(monkeypatch, tmp_path):
    monkeypatch.setattr(trust_dial, "_BRANDS_DIR", tmp_path)
    brand_dir = tmp_path / "brand-x"
    brand_dir.mkdir(parents=True)
    (brand_dir / "agent_trust_settings.json").write_text("{not valid json")
    # A corrupt file must never be read as an accidental auto-advance grant.
    assert trust_dial.get_level("brand-x", "script-writer") == "consult"
    assert trust_dial.get_all("brand-x") == {}


def test_per_brand_isolation(monkeypatch, tmp_path):
    monkeypatch.setattr(trust_dial, "_BRANDS_DIR", tmp_path)
    trust_dial.set_level("brand-a", "script-writer", "direct")
    assert trust_dial.get_level("brand-b", "script-writer") == "consult"
