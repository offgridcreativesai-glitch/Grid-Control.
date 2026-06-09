# GRID CONTROL Scheduler (Phase E1)

Dedicated 24×7 worker that triggers the daily agent pipeline **server-side** — no
Mac-awake dependency, no double-fire under gunicorn.

## How it works
`scheduler/worker.py` runs APScheduler (`BlockingScheduler`) as its own process.
On each cron tick it POSTs `/api/scheduler/trigger` on the web API with a shared
service token. The web service then runs `run_daily_pipeline(brand)` — reusing
all existing wiring (run rows, GRID_RUN_ID cost capture, brand env, narrative,
Notion). The worker stays thin and stateless.

Config: `scheduler/schedule_config.json` (per-brand cron times, IST by default).

## Local test
```bash
# one-shot trigger (web API must be running on :5001)
export GRID_SCHEDULER_TOKEN=dev-secret      # also set on the API
export GRID_API_BASE=http://localhost:5001
python3 scheduler/worker.py --once askgauravai

# run the scheduler loop locally
python3 scheduler/worker.py
```

## Railway deploy (Gaurav — provisioning spends ~$5/mo)
This repo's `Procfile` defines two processes: `web` and `worker`. Create a
**second Railway service** in the same project from the same repo:

1. Railway → project `9a2157e3-…` → **New Service → GitHub repo** (same repo).
2. Settings → **Start Command**: `python3 scheduler/worker.py`
   (or set the service's process to `worker` if using the Procfile selector).
3. This must be a **paid always-on** instance (hobby ~$5/mo) — not a sleeping
   free tier, or scheduled ticks are missed.
4. Service **variables** (must match the web service):
   - `GRID_SCHEDULER_TOKEN` — strong shared secret (set the SAME value on the
     **web** service so the trigger endpoint authenticates it).
   - `GRID_API_BASE=https://web-production-175d5.up.railway.app`
   - `SCHEDULER_TZ=Asia/Kolkata` (optional; default)
5. Deploy. Logs should show `started — N job(s)`.

The old in-process loop (`ENABLE_DAILY_SCHEDULER`) is legacy — leave it off once
the worker service is live.
