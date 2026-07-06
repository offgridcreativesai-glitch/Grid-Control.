"""
agents/_lib/publish_policy.py — per-brand, per-platform publish policy.

Two levels:
  manual    (default, every platform, every brand) — never call the platform
            API even if the token is live; always return a "prepared" package
            for the owner to post themselves.
  assisted  — use the existing behavior: auto-publish the moment the token is
            live, otherwise fall back to "prepared". Approval gate (K1) is
            unaffected either way — this only governs the PUBLISH step after
            an output is already in outputs/approved/.

X (Twitter) is excluded from this — it stays hard-coded manual per the
standing rule (CLAUDE.md: "X → MANUAL upload, always"), not something a
per-brand setting can override.

Storage: brands/{slug}/publish_policy.json — {platform: "manual"|"assisted"}.
Missing file or missing key both mean "manual" (fail-safe, not fail-open —
an unreadable/corrupt file must never accidentally unlock auto-publish, the
most externally visible and hardest-to-reverse action in the system).
"""
from __future__ import annotations

import json
from pathlib import Path

LEVELS = ("manual", "assisted")
DEFAULT_LEVEL = "manual"
LOCKED_MANUAL_PLATFORMS = ("twitter", "x")

_BASE_DIR = Path(__file__).resolve().parent.parent.parent
_BRANDS_DIR = _BASE_DIR / "brands"


def _settings_path(brand_slug: str) -> Path:
    return _BRANDS_DIR / brand_slug / "publish_policy.json"


def is_valid_level(level: str | None) -> bool:
    return level in LEVELS


def get_all(brand_slug: str) -> dict[str, str]:
    """All configured platform policies for this brand. Platforms not present
    here are implicitly 'manual' — this only returns what's been explicitly set."""
    path = _settings_path(brand_slug)
    if not path.exists():
        return {}
    try:
        data = json.loads(path.read_text())
        return {k: v for k, v in data.items() if is_valid_level(v)}
    except Exception:
        # Fail-SAFE: an unreadable/corrupt file must never unlock auto-publish.
        return {}


def get_policy(brand_slug: str, platform: str) -> str:
    """This platform's publish policy for this brand. Locked platforms (X)
    always return 'manual' regardless of what's stored. Defaults to 'manual'
    if unset, unreadable, or the platform isn't in the file — fail-safe."""
    if platform in LOCKED_MANUAL_PLATFORMS:
        return "manual"
    return get_all(brand_slug).get(platform, DEFAULT_LEVEL)


def set_policy(brand_slug: str, platform: str, level: str) -> dict[str, str]:
    """Set one platform's publish policy for this brand. Returns the full
    updated settings dict. Raises ValueError on an invalid level or an
    attempt to change a locked platform."""
    if platform in LOCKED_MANUAL_PLATFORMS:
        raise ValueError(f"'{platform}' publishing is manual-only by standing policy — not editable")
    if not is_valid_level(level):
        raise ValueError(f"invalid publish policy '{level}' — must be one of {LEVELS}")
    current = get_all(brand_slug)
    current[platform] = level
    path = _settings_path(brand_slug)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(current, indent=2))
    return current
