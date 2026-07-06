#!/bin/bash
# Daily pipeline cron — runs at 8am IST every day
# Triggers: Trend Researcher → Trend Sentinel → Data Analyst → Contradiction Detector

set -e
cd /Users/gauravoffgrid/offgrid-marketing-os
source .env 2>/dev/null || true

GRID_SCHEDULER_TOKEN="${GRID_SCHEDULER_TOKEN:-}"
BRAND_SLUG="${1:-askgauravai}"
LOG_FILE="/tmp/grid_daily_pipeline_$(date +%Y%m%d).log"

echo "[$(date '+%Y-%m-%d %H:%M:%S')] Starting daily pipeline for brand: $BRAND_SLUG" >> "$LOG_FILE"

# Verify Flask is up; start if not
if ! curl -s --max-time 5 http://localhost:5001/api/health > /dev/null 2>&1; then
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] Flask API not running. Starting..." >> "$LOG_FILE"
    nohup python3 dashboard_api.py > /tmp/flask_api.log 2>&1 &
    sleep 5
fi

# Trigger pipeline
RESPONSE=$(curl -s -X POST http://localhost:5001/api/pipeline/daily-run \
    -H "Content-Type: application/json" \
    -H "X-Grid-Service-Token: $GRID_SCHEDULER_TOKEN" \
    -d "{\"brand_slug\": \"$BRAND_SLUG\"}")

echo "[$(date '+%Y-%m-%d %H:%M:%S')] Pipeline trigger response: $RESPONSE" >> "$LOG_FILE"
echo "[$(date '+%Y-%m-%d %H:%M:%S')] Pipeline kicked off — runs in background. Check ~/offgrid-marketing-os/brands/$BRAND_SLUG/session_state.json for progress." >> "$LOG_FILE"
