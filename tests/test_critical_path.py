"""Critical-path smoke test — the spine that must never silently break:
auth gate → brand loads → pending output renders HUMAN-readable → approve moves
the file → reject of a ghost file is an honest 404 (never success:true).

Runs against the REAL Flask app (all blueprints) with the real routes; only the
Supabase seam is stubbed (auth user + _DB_AVAILABLE=False) so it works in CI with
no credentials and exercises the disk path — the same fallback the live app uses.
No agents run, nothing paid, nothing user-facing is triggered.

Run: `python3 -m pytest tests/test_critical_path.py -q` (repo root)
"""
import json
import shutil
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).parent.parent
sys.path.insert(0, str(REPO))

import core  # noqa: E402
import routes.content as content  # noqa: E402
from dashboard_api import app  # noqa: E402  (registers all blueprints; run() is __main__-guarded)

SLUG = "ci-smoke-fixture"
BRAND_DIR = REPO / "brands" / SLUG
PENDING = BRAND_DIR / "outputs" / "pending_approval" / "script-writer"
APPROVED = BRAND_DIR / "outputs" / "approved"
FILENAME = "20260715_000000_smoke_scripts.json"

PAYLOAD = {
    "scripts": [{
        "post_id": "smoke-1",
        "hook": "Nobody tells you this about organic cotton",
        "full_script": "Here is the honest truth about what organic really costs to make.",
        "caption": "The truth about organic cotton, in 30 seconds.",
    }]
}


@pytest.fixture()
def fixture_brand():
    PENDING.mkdir(parents=True, exist_ok=True)
    APPROVED.mkdir(parents=True, exist_ok=True)
    (PENDING / FILENAME).write_text(json.dumps(PAYLOAD))
    yield
    shutil.rmtree(BRAND_DIR, ignore_errors=True)


@pytest.fixture()
def client(monkeypatch, fixture_brand):
    """Authenticated client with the Supabase seam stubbed to the disk path."""
    monkeypatch.setattr(core, "_get_current_user",
                        lambda: {"id": "smoke-user", "email": "smoke@ci"})
    monkeypatch.setattr(content, "_DB_AVAILABLE", False)
    app.config["TESTING"] = True
    with app.test_client() as c:
        yield c


def test_unauthenticated_request_is_rejected(fixture_brand, monkeypatch):
    # The login gate: no JWT -> 401, never data.
    monkeypatch.setattr(core, "_get_current_user", lambda: None)
    app.config["TESTING"] = True
    with app.test_client() as c:
        r = c.get(f"/api/outputs/pending?brand_slug={SLUG}")
    assert r.status_code == 401


def test_pending_output_renders_human_not_json(client):
    r = client.get(f"/api/outputs/pending?brand_slug={SLUG}")
    assert r.status_code == 200
    items = r.get_json()["data"]
    assert len(items) == 1
    item = items[0]
    assert item["filename"] == FILENAME
    # The vault preview must be plain English, never raw JSON (the Jul-14 bug class)
    assert '{"' not in item["preview"]
    assert "full_script" not in item["preview"]
    assert "Nobody tells you this" in item["preview"]


def test_approve_moves_file_to_approved(client):
    r = client.post("/api/outputs/approve",
                    json={"brand_slug": SLUG, "filename": FILENAME})
    assert r.status_code == 200 and r.get_json()["success"] is True
    assert not (PENDING / FILENAME).exists(), "file still pending after approve"
    assert (APPROVED / FILENAME).exists(), "file did not land in approved/"


def test_reject_of_missing_file_is_honest_404(client):
    # Pinned Jul-14 bug: reject used to return success:true having removed nothing.
    r = client.post("/api/outputs/reject",
                    json={"brand_slug": SLUG, "filename": "ghost_file.json"})
    assert r.status_code == 404
    assert r.get_json()["success"] is False


def test_reject_removes_real_pending_file(client):
    r = client.post("/api/outputs/reject",
                    json={"brand_slug": SLUG, "filename": FILENAME})
    assert r.status_code == 200 and r.get_json()["success"] is True
    assert not (PENDING / FILENAME).exists()
