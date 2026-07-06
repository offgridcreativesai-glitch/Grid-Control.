"""
agents/_lib/cost_caps.py — per-brand daily spend cap, owner-editable.

Before this module, agents/_lib/paid_ops.py enforced a single GLOBAL cap
from the env var GRID_DAILY_USD_CAP — the same $5/day ceiling shared across
every brand, invisible and uneditable from the dashboard. This gives each
brand its own cap, visible and settable by the brand owner in Settings.

Storage: brands/{slug}/cost_caps.json — {"daily_usd_cap": 5.0}. Missing file
or missing key means "no override" — paid_ops falls back to the global env
default (fail-safe: absence of a per-brand file must never mean "uncapped").
"""
from __future__ import annotations

import json
from pathlib import Path

_BASE_DIR = Path(__file__).resolve().parent.parent.parent
_BRANDS_DIR = _BASE_DIR / "brands"


def _settings_path(brand_slug: str) -> Path:
    return _BRANDS_DIR / brand_slug / "cost_caps.json"


def get_override(brand_slug: str) -> float | None:
    """This brand's daily cap override in USD, or None if unset/unreadable —
    callers (paid_ops.daily_cap_usd) fall back to the global default on None."""
    path = _settings_path(brand_slug)
    if not path.exists():
        return None
    try:
        data = json.loads(path.read_text())
        val = data.get("daily_usd_cap")
        return float(val) if val is not None and float(val) > 0 else None
    except Exception:
        # Fail-SAFE: an unreadable/corrupt file must never be read as "uncapped".
        return None


def set_override(brand_slug: str, daily_usd_cap: float) -> dict:
    """Set this brand's daily cap override. Raises ValueError on a non-positive
    value (a zero or negative cap is ambiguous — use the kill-switch instead)."""
    if daily_usd_cap is None or daily_usd_cap <= 0:
        raise ValueError("daily_usd_cap must be a positive number")
    path = _settings_path(brand_slug)
    path.parent.mkdir(parents=True, exist_ok=True)
    data = {"daily_usd_cap": round(float(daily_usd_cap), 2)}
    path.write_text(json.dumps(data, indent=2))
    return data
