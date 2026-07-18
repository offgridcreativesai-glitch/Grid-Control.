"""Pins the ops-auditor (Phase 4.1): the human-ops stand-in must report
honestly — real statuses for what it can check, explicit 'unavailable' for
what it can't, plain English always, and correct spend-vs-cap math.
Fail-on-old: before this worker existed nothing watched production between
sessions; a silent regression here would recreate that blindness.

Run: `python3 -m pytest tests/test_ops_auditor.py -q`
"""
import sys
from pathlib import Path

REPO = Path(__file__).parent.parent
sys.path.insert(0, str(REPO))

from agents.ops_auditor import compose_report, ledger_status, run_audit  # noqa: E402


def test_ledger_math():
    ledger = {"2026-07-16": 3.25}
    ok = ledger_status(ledger, "2026-07-16", cap=5.0)
    assert ok["ok"] is True and "$3.25" in ok["detail"] and "$5.00" in ok["detail"]
    over = ledger_status(ledger, "2026-07-16", cap=2.0)
    assert over["ok"] is False
    nocap = ledger_status(ledger, "2026-07-16", cap=None)
    assert nocap["ok"] is None and "no daily cap" in nocap["detail"]
    empty_day = ledger_status(ledger, "2026-07-17", cap=5.0)
    assert empty_day["ok"] is True and "$0.00" in empty_day["detail"]


def test_report_is_plain_english_and_honest():
    md = compose_report({
        "Deployed API (Railway)": {"ok": True, "detail": "HTTP 200"},
        "CI (GitHub Actions)": {"ok": False, "detail": "latest run: failure — broke a thing"},
        "Brand data in cloud": {"ok": None, "detail": "unavailable: no DB access here"},
    })
    assert '{"' not in md and '":' not in md  # never raw JSON to a human
    assert "Needs attention: CI (GitHub Actions)" in md
    assert "unavailable: no DB access here" in md  # can't-check stated, not guessed
    assert "not a failure" in md  # ◻️ legend explains itself


def test_all_clear_summary():
    md = compose_report({
        "A": {"ok": True, "detail": "fine"},
        "B": {"ok": True, "detail": "fine"},
    })
    assert "All clear — 2 of 2 checks healthy." in md


def test_run_audit_writes_card(monkeypatch, tmp_path):
    import agents.ops_auditor as oa
    monkeypatch.setattr(oa, "STATE_DIR", tmp_path)
    monkeypatch.setattr(oa, "CHECKS", {"Stub": lambda: {"ok": True, "detail": "fine"}})
    md_path = oa.run_audit()
    assert md_path.exists() and "Production Health" in md_path.read_text()
    assert (tmp_path / "ops_health_latest.json").exists()
