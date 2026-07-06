"""Invariant tests for the per-platform publish policy (agents/_lib/publish_policy.py).

Ported from the GC Cleanroom Prototype comparison — the "manual by default,
X always locked" invariant is the direct analogue of cleanroom's tested
"steer/high-stakes never gets grace" and "manual_only -> manual_handoff"
checks.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from agents._lib import publish_policy


def test_default_is_manual_for_unset_platform(monkeypatch, tmp_path):
    monkeypatch.setattr(publish_policy, "_BRANDS_DIR", tmp_path)
    assert publish_policy.get_policy("brand-x", "instagram") == "manual"


def test_set_and_get_policy(monkeypatch, tmp_path):
    monkeypatch.setattr(publish_policy, "_BRANDS_DIR", tmp_path)
    publish_policy.set_policy("brand-x", "instagram", "assisted")
    assert publish_policy.get_policy("brand-x", "instagram") == "assisted"
    # Unrelated platform on the same brand is untouched (still default).
    assert publish_policy.get_policy("brand-x", "linkedin") == "manual"


def test_x_twitter_always_manual_regardless_of_stored_value(monkeypatch, tmp_path):
    monkeypatch.setattr(publish_policy, "_BRANDS_DIR", tmp_path)
    assert publish_policy.get_policy("brand-x", "twitter") == "manual"


def test_x_twitter_cannot_be_set(monkeypatch, tmp_path):
    monkeypatch.setattr(publish_policy, "_BRANDS_DIR", tmp_path)
    for locked in ("twitter", "x"):
        try:
            publish_policy.set_policy("brand-x", locked, "assisted")
            assert False, f"should have raised ValueError for {locked}"
        except ValueError:
            pass
    assert publish_policy.get_policy("brand-x", "twitter") == "manual"


def test_invalid_level_rejected(monkeypatch, tmp_path):
    monkeypatch.setattr(publish_policy, "_BRANDS_DIR", tmp_path)
    try:
        publish_policy.set_policy("brand-x", "instagram", "auto-yolo")
        assert False, "should have raised ValueError"
    except ValueError:
        pass
    assert publish_policy.get_policy("brand-x", "instagram") == "manual"


def test_corrupt_settings_file_fails_safe_to_manual(monkeypatch, tmp_path):
    monkeypatch.setattr(publish_policy, "_BRANDS_DIR", tmp_path)
    brand_dir = tmp_path / "brand-x"
    brand_dir.mkdir(parents=True)
    (brand_dir / "publish_policy.json").write_text("{not valid json")
    # A corrupt file must never be read as an accidental auto-publish grant.
    assert publish_policy.get_policy("brand-x", "instagram") == "manual"
    assert publish_policy.get_all("brand-x") == {}


def test_per_brand_isolation(monkeypatch, tmp_path):
    monkeypatch.setattr(publish_policy, "_BRANDS_DIR", tmp_path)
    publish_policy.set_policy("brand-a", "instagram", "assisted")
    assert publish_policy.get_policy("brand-b", "instagram") == "manual"
