"""
paid_ops.py — GRID CONTROL cost circuit-breaker.

WHY: Jun 15-16 incident — auto-refresh + duplicate schedulers ran paid agents
(Apify scrape + Claude) with nothing in the way. This makes paid work **opt-in
and bounded** instead of opt-out-by-luck.

TWO controls:
  1. MASTER KILL-SWITCH — env `GRID_PAID_OPS`. Default OFF. Paid external calls
     (Apify runs, agent LLM runs) refuse to spend unless it is explicitly "1".
  2. DAILY USD CAP — env `GRID_DAILY_USD_CAP` (default 5.00). Real spend is
     tallied per-day in a small local ledger; once the day's spend hits the cap,
     further paid calls are blocked even if the switch is ON.

USAGE:
  from agents._lib import paid_ops
  ok, reason = paid_ops.check("apify")          # before a paid call
  if not ok: ... degrade gracefully (return None / "prepared, not run") ...
  # cost_reporter.record() calls paid_ops.record_spend(total_usd) automatically.

Pure stdlib. Never raises from check()/record_spend(); fail-closed on the switch
(unknown/unset → OFF), fail-open on the ledger (if the ledger file is unreadable,
the cap can't be enforced but the switch still governs — and the switch is OFF by
default, so the safe state holds).
"""
from __future__ import annotations

import os
import json
import threading
from datetime import datetime
from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parents[2]
_STATE_DIR = _PROJECT_ROOT / ".grid_state"
_LEDGER = _STATE_DIR / "paid_ledger.json"
_LOCK = threading.Lock()

_TRUTHY = {"1", "true", "yes", "on"}
_DEFAULT_CAP_USD = 5.00


class PaidOpsBlocked(Exception):
    """Raised by guard() when a paid call is not permitted."""


def enabled() -> bool:
    """Master kill-switch. Default OFF (fail-closed)."""
    return os.getenv("GRID_PAID_OPS", "").strip().lower() in _TRUTHY


def daily_cap_usd() -> float:
    try:
        return float(os.getenv("GRID_DAILY_USD_CAP", str(_DEFAULT_CAP_USD)))
    except (TypeError, ValueError):
        return _DEFAULT_CAP_USD


def _today() -> str:
    return datetime.now().strftime("%Y-%m-%d")


def _read_ledger() -> dict:
    try:
        return json.loads(_LEDGER.read_text())
    except Exception:
        return {}


def spent_today() -> float:
    return float(_read_ledger().get(_today(), 0.0))


def cap_remaining() -> float:
    return max(0.0, daily_cap_usd() - spent_today())


def record_spend(usd: float) -> None:
    """Add real spend to today's tally. Never raises (best-effort ledger)."""
    if not usd or usd <= 0:
        return
    try:
        with _LOCK:
            _STATE_DIR.mkdir(exist_ok=True)
            led = _read_ledger()
            led[_today()] = round(float(led.get(_today(), 0.0)) + float(usd), 6)
            # keep the ledger small: retain only the last ~14 days
            keys = sorted(led.keys())
            for k in keys[:-14]:
                led.pop(k, None)
            _LEDGER.write_text(json.dumps(led, indent=2))
    except Exception:
        pass  # ledger is best-effort; the switch is the hard gate


def check(kind: str = "paid", est_usd: float = 0.0) -> tuple[bool, str]:
    """Return (ok, reason). ok=True means the paid call may proceed.

    kind  — short label for logging ("apify", "agent:<slug>", "llm").
    est_usd — optional pre-call estimate to pre-check against the cap.
    """
    if not enabled():
        return False, (
            f"GRID_PAID_OPS off — '{kind}' blocked (kill-switch). "
            f"Set GRID_PAID_OPS=1 to allow paid runs."
        )
    spent = spent_today()
    cap = daily_cap_usd()
    if spent + max(0.0, est_usd) > cap:
        return False, (
            f"daily cap reached — '{kind}' blocked "
            f"(spent ${spent:.2f} / cap ${cap:.2f} today). "
            f"Raise GRID_DAILY_USD_CAP to continue."
        )
    return True, ""


def guard(kind: str = "paid", est_usd: float = 0.0) -> None:
    """Exception form of check() for call sites that prefer to raise."""
    ok, reason = check(kind, est_usd)
    if not ok:
        raise PaidOpsBlocked(reason)


def status() -> dict:
    """Snapshot for logging / a future dashboard meter."""
    return {
        "enabled": enabled(),
        "spent_today_usd": round(spent_today(), 4),
        "daily_cap_usd": daily_cap_usd(),
        "remaining_usd": round(cap_remaining(), 4),
        "date": _today(),
    }
