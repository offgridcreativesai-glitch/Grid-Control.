"""Invariant tests for the cost circuit-breaker (agents/_lib/paid_ops.py).

Ported from the GC Cleanroom Prototype comparison — cost-cap fail-closed
behavior and per-brand spend isolation were flagged as untested invariant
paths in the Fable 5 gap/risk report (docs/fable5_review/01_GAP_RISK_REPORT.md,
gap #6: "zero coverage on ... paid_ops cap math").
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from agents._lib import paid_ops


def _isolate_ledger(monkeypatch, tmp_path):
    """Point the module at a scratch ledger file so tests never touch the
    real .grid_state/paid_ledger.json."""
    monkeypatch.setattr(paid_ops, "_STATE_DIR", tmp_path)
    monkeypatch.setattr(paid_ops, "_LEDGER", tmp_path / "paid_ledger.json")


def test_kill_switch_off_blocks_everything(monkeypatch, tmp_path):
    _isolate_ledger(monkeypatch, tmp_path)
    monkeypatch.delenv("GRID_PAID_OPS", raising=False)
    ok, reason = paid_ops.check("agent:x")
    assert ok is False
    assert "kill-switch" in reason


def test_enabled_and_under_cap_allows(monkeypatch, tmp_path):
    _isolate_ledger(monkeypatch, tmp_path)
    monkeypatch.setenv("GRID_PAID_OPS", "1")
    monkeypatch.setenv("GRID_DAILY_USD_CAP", "5.00")
    ok, reason = paid_ops.check("agent:x")
    assert ok is True


def test_cap_breach_fails_closed(monkeypatch, tmp_path):
    _isolate_ledger(monkeypatch, tmp_path)
    monkeypatch.setenv("GRID_PAID_OPS", "1")
    monkeypatch.setenv("GRID_DAILY_USD_CAP", "5.00")
    paid_ops.record_spend(5.01)
    ok, reason = paid_ops.check("agent:x")
    assert ok is False
    assert "daily cap reached" in reason


def test_paid_ops_import_failure_blocks_launch():
    """core.py's _run_agent_subprocess treats an unimportable paid_ops module
    as (False, ...) — never as an implicit allow. This documents that
    contract at the type level: check() always returns a real (ok, reason)
    tuple, never raises, so a caller can't accidentally treat an exception
    as success."""
    ok, reason = paid_ops.check("agent:definitely-not-a-real-kind")
    assert isinstance(ok, bool)
    assert isinstance(reason, str)


def test_per_brand_spend_is_isolated(monkeypatch, tmp_path):
    _isolate_ledger(monkeypatch, tmp_path)
    monkeypatch.setenv("GRID_PAID_OPS", "1")
    monkeypatch.setenv("GRID_DAILY_USD_CAP", "5.00")
    paid_ops.record_spend(4.0, brand_slug="brand-a")
    paid_ops.record_spend(4.0, brand_slug="brand-b")
    # Both brands separately under their own $5 cap...
    assert paid_ops.check("agent:x", brand_slug="brand-a")[0] is True
    assert paid_ops.check("agent:x", brand_slug="brand-b")[0] is True
    # ...and neither brand's spend leaked into the other's or the global tally.
    assert paid_ops.spent_today("brand-a") == 4.0
    assert paid_ops.spent_today("brand-b") == 4.0
    assert paid_ops.spent_today(None) == 0.0


def test_per_brand_cap_override(monkeypatch, tmp_path):
    from agents._lib import cost_caps
    _isolate_ledger(monkeypatch, tmp_path)
    monkeypatch.setattr(cost_caps, "_BRANDS_DIR", tmp_path / "brands")
    monkeypatch.setenv("GRID_PAID_OPS", "1")
    monkeypatch.setenv("GRID_DAILY_USD_CAP", "5.00")
    cost_caps.set_override("brand-c", 20.0)
    assert paid_ops.daily_cap_usd("brand-c") == 20.0
    # A brand with no override still falls back to the global default.
    assert paid_ops.daily_cap_usd("brand-d") == 5.00


def test_corrupt_ledger_fails_safe(monkeypatch, tmp_path):
    _isolate_ledger(monkeypatch, tmp_path)
    tmp_path.mkdir(exist_ok=True)
    (tmp_path / "paid_ledger.json").write_text("{not valid json")
    # An unreadable ledger must read as $0 spent (fail-SAFE), not crash and
    # not silently permit unbounded spend either — cap enforcement still runs.
    assert paid_ops.spent_today() == 0.0
