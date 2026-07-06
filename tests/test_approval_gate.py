"""Invariant test for the K1 approval-gate boundary: publishers may only ever
locate a file in outputs/approved/, never outputs/pending_approval/ — this is
what makes "approve" the ONLY path from a generated draft to publication.

Ported from the GC Cleanroom Prototype comparison (its own smoke_test.py has
the equivalent "publish before approval blocked" check); flagged as an
untested invariant path in gap #6 of docs/fable5_review/01_GAP_RISK_REPORT.md.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from core import _find_output


def test_pending_only_file_is_not_findable(tmp_path):
    pending = tmp_path / "outputs" / "pending_approval" / "script-writer"
    pending.mkdir(parents=True)
    (pending / "draft.json").write_text("{}")
    # K1: a file that only exists in pending_approval/ must be invisible to
    # the publisher lookup — approval is the only path to publication.
    assert _find_output(tmp_path, "draft.json") is None


def test_approved_file_is_findable(tmp_path):
    approved = tmp_path / "outputs" / "approved"
    approved.mkdir(parents=True)
    (approved / "draft.json").write_text("{}")
    found = _find_output(tmp_path, "draft.json")
    assert found is not None
    assert found.name == "draft.json"


def test_approved_takes_precedence_when_both_exist(tmp_path):
    """Same filename queued in pending_approval AND already approved (e.g. a
    re-run) — the lookup must resolve to the approved copy, never the
    pending one, regardless of directory scan order."""
    pending = tmp_path / "outputs" / "pending_approval" / "script-writer"
    pending.mkdir(parents=True)
    (pending / "draft.json").write_text('{"stage": "pending"}')
    approved = tmp_path / "outputs" / "approved"
    approved.mkdir(parents=True)
    (approved / "draft.json").write_text('{"stage": "approved"}')

    found = _find_output(tmp_path, "draft.json")
    assert found is not None
    assert "approved" in found.parts
    assert "pending_approval" not in found.parts
