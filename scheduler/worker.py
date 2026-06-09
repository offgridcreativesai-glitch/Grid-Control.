"""
scheduler/worker.py — Phase E1 dedicated scheduler service.

Runs as a SEPARATE Railway worker (24×7, always-on) — NOT inside gunicorn and
NOT on Gaurav's Mac. Replaces the old in-process loop (which double-fires under
gunicorn --workers 2) and the local crontab (GRIDLOCK-AUTOPOST-04JUN, Mac-awake
dependency).

On each scheduled tick it POSTs to the web API's /api/scheduler/trigger with a
shared service token, so it reuses ALL the tested pipeline wiring (run rows,
GRID_RUN_ID cost capture, brand env overlay, narrative append, Notion push).

Config: scheduler/schedule_config.json
Env:
  GRID_API_BASE        — web API base URL (e.g. https://web-production-175d5.up.railway.app)
  GRID_SCHEDULER_TOKEN — shared secret, must match the web service's env
  SCHEDULER_TZ         — IANA tz for cron times (default Asia/Kolkata)

Run locally:  python3 scheduler/worker.py
Run once now: python3 scheduler/worker.py --once <brand_slug>
"""
import os
import sys
import json
import time
from pathlib import Path

import requests

_HERE = Path(__file__).resolve().parent
_CONFIG = _HERE / "schedule_config.json"

API_BASE = os.getenv("GRID_API_BASE", "http://localhost:5001").rstrip("/")
SERVICE_TOKEN = os.getenv("GRID_SCHEDULER_TOKEN", "").strip()
TZ = os.getenv("SCHEDULER_TZ", "Asia/Kolkata")


def _log(msg: str) -> None:
    from datetime import datetime
    print(f"[scheduler-worker | {datetime.now().isoformat(timespec='seconds')}] {msg}", flush=True)


def load_config() -> dict:
    if not _CONFIG.exists():
        _log(f"WARNING: {_CONFIG} not found — no jobs scheduled")
        return {"jobs": []}
    return json.loads(_CONFIG.read_text(encoding="utf-8"))


def trigger_pipeline(brand_slug: str) -> bool:
    """Fire the daily pipeline for one brand via the web API. Returns success."""
    if not SERVICE_TOKEN:
        _log("ERROR: GRID_SCHEDULER_TOKEN not set — cannot authenticate to API")
        return False
    try:
        r = requests.post(
            f"{API_BASE}/api/scheduler/trigger",
            json={"brand_slug": brand_slug},
            headers={"X-Grid-Service-Token": SERVICE_TOKEN},
            timeout=30,
        )
        ok = r.status_code == 200 and (r.json() or {}).get("success")
        _log(f"trigger {brand_slug} → {r.status_code} ok={ok}")
        return bool(ok)
    except Exception as e:
        _log(f"trigger {brand_slug} failed: {e}")
        return False


def main() -> None:
    # One-shot mode for testing: python3 scheduler/worker.py --once <brand>
    if "--once" in sys.argv:
        idx = sys.argv.index("--once")
        brand = sys.argv[idx + 1] if len(sys.argv) > idx + 1 else None
        if not brand:
            _log("usage: worker.py --once <brand_slug>")
            sys.exit(1)
        ok = trigger_pipeline(brand)
        sys.exit(0 if ok else 1)

    from apscheduler.schedulers.blocking import BlockingScheduler
    from apscheduler.triggers.cron import CronTrigger

    cfg = load_config()
    jobs = cfg.get("jobs", [])
    sched = BlockingScheduler(timezone=TZ)

    scheduled = 0
    for job in jobs:
        if not job.get("enabled", True):
            continue
        brand = job["brand_slug"]
        cron = job.get("cron", {})  # {hour, minute, day_of_week?}
        trigger = CronTrigger(
            hour=cron.get("hour", 6),
            minute=cron.get("minute", 30),
            day_of_week=cron.get("day_of_week"),
            timezone=TZ,
        )
        sched.add_job(
            trigger_pipeline, trigger, args=[brand],
            id=f"daily-{brand}", replace_existing=True, misfire_grace_time=3600,
        )
        scheduled += 1
        _log(f"scheduled {brand}: {cron} ({TZ})")

    _log(f"started — {scheduled} job(s), API_BASE={API_BASE}, tz={TZ}")
    if scheduled == 0:
        _log("no enabled jobs — idling (edit scheduler/schedule_config.json)")
    try:
        sched.start()
    except (KeyboardInterrupt, SystemExit):
        _log("shutting down")


if __name__ == "__main__":
    main()
