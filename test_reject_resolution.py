"""Pins the reject/approve silent-no-op bug (Jul 14): approve+reject act on
pending_approval/ files but resolved filenames with _find_output (approved/ only),
so rejects reported success while the file stayed. _find_pending_output resolves the
pending side; _find_output must stay scoped to approved/.

Run: `python3 test_reject_resolution.py`  (or via pytest once backend CI exists)
"""
import tempfile
from pathlib import Path
from core import _find_pending_output, _find_output


def _make_brand():
    d = Path(tempfile.mkdtemp())
    pending = d / "outputs" / "pending_approval" / "brand-book"
    approved = d / "outputs" / "approved"
    pending.mkdir(parents=True)
    approved.mkdir(parents=True)
    (pending / "20260709_brand_book_v7.json").write_text("{}")
    (approved / "already_approved.json").write_text("{}")
    return d


def test_pending_resolver_finds_pending_file():
    d = _make_brand()
    hit = _find_pending_output(d, "20260709_brand_book_v7.json")
    assert hit is not None and hit.exists()


def test_approved_resolver_does_NOT_reach_pending():
    # THE bug: reject used _find_output for a pending file → None → silent no-op.
    d = _make_brand()
    assert _find_output(d, "20260709_brand_book_v7.json") is None
    # sanity: it still finds genuinely-approved files
    assert _find_output(d, "already_approved.json") is not None


def test_missing_filename_returns_none():
    d = _make_brand()
    assert _find_pending_output(d, "nope.json") is None


if __name__ == "__main__":
    test_pending_resolver_finds_pending_file()
    test_approved_resolver_does_NOT_reach_pending()
    test_missing_filename_returns_none()
    print("reject-resolution tests passed")
