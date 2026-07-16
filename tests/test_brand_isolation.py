"""Pins the brand-isolation landmine: 25 endpoints silently defaulted a missing
brand_slug to "offgrid-creatives-ai", so any FE call that omitted the slug read
or wrote ANOTHER BRAND'S data with a 200. On the old code these tests FAIL
(request without a slug returned data); on the fix they PASS (honest 400).

All routes now go through core.require_brand_slug() — also asserted here so a
new endpoint can't quietly reintroduce a hardcoded default.

Run: `python3 -m pytest tests/test_brand_isolation.py -q`
"""
import re
import sys
from pathlib import Path

import pytest
from werkzeug.exceptions import BadRequest

REPO = Path(__file__).parent.parent
sys.path.insert(0, str(REPO))

import core  # noqa: E402
from dashboard_api import app  # noqa: E402


def test_require_brand_slug_returns_valid_slug():
    with app.test_request_context("/x?brand_slug=third-gen-tribe"):
        assert core.require_brand_slug() == "third-gen-tribe"
    with app.test_request_context("/x", method="POST", json={"brand_slug": "third-gen-tribe"}):
        assert core.require_brand_slug() == "third-gen-tribe"


def test_require_brand_slug_400s_on_missing_or_invalid():
    with app.test_request_context("/x"):
        with pytest.raises(BadRequest):
            core.require_brand_slug()
    with app.test_request_context("/x?brand_slug=../../etc"):
        with pytest.raises(BadRequest):
            core.require_brand_slug()


@pytest.fixture()
def auth_client(monkeypatch):
    monkeypatch.setattr(core, "_get_current_user",
                        lambda: {"id": "iso-user", "email": "iso@ci"})
    app.config["TESTING"] = True
    with app.test_client() as c:
        yield c


def test_slugless_requests_get_400_not_another_brands_data(auth_client):
    # THE bug: each of these used to answer 200 with offgrid-creatives-ai's data.
    assert auth_client.get("/api/outputs/pending").status_code == 400
    assert auth_client.get("/api/outputs/all").status_code == 400
    assert auth_client.post("/api/outputs/approve", json={"filename": "x.json"}).status_code == 400
    assert auth_client.post("/api/outputs/reject", json={"filename": "x.json"}).status_code == 400


def test_no_route_hardcodes_a_default_brand():
    # Static net: a new endpoint reintroducing the default fails CI immediately.
    offenders = []
    for f in (REPO / "routes").glob("*.py"):
        for i, line in enumerate(f.read_text().splitlines(), 1):
            if re.search(r'get\(\s*"brand_slug"\s*,\s*"[a-z0-9-]+"\s*\)', line):
                offenders.append(f"{f.name}:{i}")
    assert not offenders, f"hardcoded brand_slug defaults reintroduced: {offenders}"


if __name__ == "__main__":
    test_require_brand_slug_returns_valid_slug()
    test_require_brand_slug_400s_on_missing_or_invalid()
    test_no_route_hardcodes_a_default_brand()
    print("brand-isolation tests passed (run client tests via pytest)")
