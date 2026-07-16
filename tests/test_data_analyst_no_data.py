"""Pins the Data Analyst zero-fabrication HALT (found Jul 1: on an empty brand
with no connections it invented '16 followers / 460 reach / 3 posts' instead of
saying "no data"). The gate: no live insights + zero output files -> honest $0
no-data card, and the model is NEVER called.

Run: `python3 -m pytest tests/test_data_analyst_no_data.py -q`
"""
import json
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).parent.parent
sys.path.insert(0, str(REPO))

from agents.data_analyst import DataAnalyst, no_data_halt_reason  # noqa: E402


def test_halts_on_empty_brand():
    # THE bug: this exact state used to reach the model and come back with numbers.
    assert no_data_halt_reason({"connected": False}, {"total_files": 0})
    assert no_data_halt_reason({}, {})
    assert no_data_halt_reason(None, None)


def test_no_halt_with_live_insights():
    assert no_data_halt_reason({"connected": True}, {"total_files": 0}) is None


def test_no_halt_with_real_output_files():
    # Inventory-only reporting is grounded (real files on disk) — allowed.
    assert no_data_halt_reason({"connected": False}, {"total_files": 7}) is None


class _FakeCEO:
    def __init__(self):
        self.saved = None
        self.completed = None

    def save_agent_output(self, **kw):
        self.saved = kw

    def mark_agent_complete(self, slug):
        self.completed = slug


def test_run_on_empty_brand_saves_honest_card_and_never_calls_model(tmp_path, monkeypatch):
    for var in ("META_GRAPH_API_TOKEN", "IG_USER_ID", "LINKEDIN_ACCESS_TOKEN",
                "GA4_PROPERTY_ID", "SEARCH_CONSOLE_SITE_URL"):
        monkeypatch.delenv(var, raising=False)

    # __new__ skips __init__ (which builds CEOBrain + Anthropic client) — the
    # established pattern for testing agent guard logic without a paid run.
    da = DataAnalyst.__new__(DataAnalyst)
    da.brand_slug = "empty-test-brand"
    da.brand_dir = tmp_path
    da.brand_profile = {}
    da._total_input_tokens = 0
    da._total_output_tokens = 0
    da.ceo = _FakeCEO()

    def _model_called(self, package):
        raise AssertionError("model was called on a brand with no real data")

    monkeypatch.setattr(DataAnalyst, "run_autoresearch_loop", _model_called)

    da.run()  # must take the halt branch, not raise

    files = list((tmp_path / "outputs" / "pending_approval" / "Data Analyst").glob("*.json"))
    assert len(files) == 1 and "no_data" in files[0].name
    saved = json.loads(files[0].read_text())
    assert saved["status"] == "no_data"
    assert "Nothing real to report" in saved["executive_summary"]
    assert da.ceo.saved is not None and "no data" in da.ceo.saved["output_type"].lower()
    assert da.ceo.completed == "data-analyst"


if __name__ == "__main__":
    test_halts_on_empty_brand()
    test_no_halt_with_live_insights()
    test_no_halt_with_real_output_files()
    print("no-data halt tests passed (run the tmp_path test via pytest)")
