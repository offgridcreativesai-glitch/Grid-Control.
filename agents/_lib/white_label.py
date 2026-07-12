"""
agents/_lib/white_label.py — per-brand white-label branding, owner-editable (gap #4, Jul 12 2026).

The reseller/agency capability GC was missing (GoHighLevel's whole game). This is the branding
MECHANISM: an agency reselling GC can make its client see the agency's name / logo / accent
instead of "GRID CONTROL". The reseller ECONOMICS (per-seat vs markup pricing, billing, seat
management) is a separate business decision and deliberately NOT here.

Storage: brands/{slug}/white_label.json. Empty/missing → the FE falls back to the default
GRID CONTROL wordmark. Fields (all optional): brand_name, logo_url, accent (hex), support_email,
custom_domain. No secrets here — pure display config, safe to serve to any brand member.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

_BASE_DIR = Path(__file__).resolve().parent.parent.parent
_BRANDS_DIR = _BASE_DIR / "brands"

FIELDS = ("brand_name", "logo_url", "accent", "support_email", "custom_domain")
_HEX_RE = re.compile(r"^#(?:[0-9a-fA-F]{3}|[0-9a-fA-F]{6})$")


def _path(brand_slug: str) -> Path:
    return _BRANDS_DIR / brand_slug / "white_label.json"


def get(brand_slug: str) -> dict:
    """This brand's white-label config, or {} when unset/unreadable (→ default branding)."""
    p = _path(brand_slug)
    if not p.exists():
        return {}
    try:
        data = json.loads(p.read_text())
        return {k: data[k] for k in FIELDS if data.get(k)}
    except Exception:
        return {}


def set_config(brand_slug: str, patch: dict) -> dict:
    """Merge patch into the stored config. A field set to "" clears it. Validates accent as
    a hex color and support_email as an address; raises ValueError otherwise."""
    current = get(brand_slug)
    for k, v in (patch or {}).items():
        if k not in FIELDS:
            continue
        v = (v or "").strip() if isinstance(v, str) else v
        if not v:
            current.pop(k, None)
            continue
        if k == "accent" and not _HEX_RE.match(v):
            raise ValueError("accent must be a hex color like #22d3ee")
        if k == "support_email" and "@" not in v:
            raise ValueError("support_email must be a valid email")
        current[k] = v
    p = _path(brand_slug)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(current, indent=2))
    return current


if __name__ == "__main__":  # ponytail self-check
    import tempfile
    _BRANDS_DIR = Path(tempfile.mkdtemp())
    assert get("x") == {}
    assert set_config("x", {"brand_name": "Acme", "accent": "#22d3ee"})["brand_name"] == "Acme"
    assert get("x")["accent"] == "#22d3ee"
    assert set_config("x", {"brand_name": ""}) == {"accent": "#22d3ee"}  # clear
    try:
        set_config("x", {"accent": "blue"}); assert False
    except ValueError:
        pass
    print("white_label self-check ok")
