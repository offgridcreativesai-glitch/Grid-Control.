"""
agents/_lib/trust_dial.py — GRIDLOCK-PROGRAM-01JUL Stage 5: per-agent trust dial.

Three levels, layered ON TOP of the existing approval gate (never replacing it):

  consult  (default, every agent, every brand) — current behavior, unchanged.
           Output lands in outputs/pending_approval/; a human must click Approve.
  automate — output still gets fully generated, still lands in pending_approval/
           first (full audit trail preserved — nothing is silent), but is then
           auto-advanced to outputs/approved/ immediately, without waiting for
           a human click. This is what the plan's own Stage 5 bullet describes
           ("Automate lets a specific agent's output auto-advance without a card").
  direct   — same auto-advance behavior as automate today. Reserved as a
           distinct, more-autonomous tier for when GC's publish pipeline (see
           CLAUDE.md "Pending in Priority Order" #2 — LinkedIn/YouTube/X
           publishers + create->approval->publish flow) is fully built for a
           given platform; at that point "direct" is the tier that would also
           auto-trigger publish_runner, while "automate" stops at approved/
           and still waits for a manual publish click. That publish-side
           distinction is NOT wired yet — auto-publish is a real, external,
           hard-to-reverse action (a live post going out) and deliberately
           needs its own explicit go-ahead before being wired to fire
           automatically, separate from just building this settings layer.

Default is ALWAYS consult for every agent on every brand unless a human has
explicitly set something else via the FE control (routes/brands.py trust-dial
endpoints) — building this module changes nothing about default behavior.

Storage: brands/{slug}/agent_trust_settings.json — a plain dict of
{agent_slug: "consult"|"automate"|"direct"}. Missing file or missing key both
mean "consult" (fail-safe, not fail-open — an unreadable/corrupt settings file
must never accidentally unlock auto-advance).
"""
from __future__ import annotations

import json
from pathlib import Path

LEVELS = ("consult", "automate", "direct")
DEFAULT_LEVEL = "consult"

_BASE_DIR = Path(__file__).resolve().parent.parent.parent
_BRANDS_DIR = _BASE_DIR / "brands"


def _settings_path(brand_slug: str) -> Path:
    return _BRANDS_DIR / brand_slug / "agent_trust_settings.json"


def is_valid_level(level: str | None) -> bool:
    return level in LEVELS


def get_all(brand_slug: str) -> dict[str, str]:
    """All configured overrides for this brand. Agents not present here are
    implicitly 'consult' — this only returns what's been explicitly set."""
    path = _settings_path(brand_slug)
    if not path.exists():
        return {}
    try:
        data = json.loads(path.read_text())
        return {k: v for k, v in data.items() if is_valid_level(v)}
    except Exception:
        # Fail-SAFE: an unreadable/corrupt file must never unlock auto-advance.
        return {}


def get_level(brand_slug: str, agent_slug: str) -> str:
    """This agent's trust level for this brand. Defaults to 'consult' if
    unset, unreadable, or the agent isn't in the file at all — fail-safe."""
    return get_all(brand_slug).get(agent_slug, DEFAULT_LEVEL)


def set_level(brand_slug: str, agent_slug: str, level: str) -> dict[str, str]:
    """Set one agent's trust level for this brand. Returns the full updated
    settings dict. Raises ValueError on an invalid level (fail loud, not
    silently ignore a typo'd level that could be misread as still-safe)."""
    if not is_valid_level(level):
        raise ValueError(f"invalid trust level '{level}' — must be one of {LEVELS}")
    current = get_all(brand_slug)
    current[agent_slug] = level
    path = _settings_path(brand_slug)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(current, indent=2))
    return current
