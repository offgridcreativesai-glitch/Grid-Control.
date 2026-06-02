#!/usr/bin/env bash
# Pre-flight check before any expensive ASKGauravAI agent run.
# Checks: Anthropic SDK works, Notion database accessible, key envs set, cost forecast surfaced.
# Exit non-zero on any failure.

set -e
cd "$(dirname "$0")/.."

# shellcheck disable=SC1091
set -a
source .env
set +a

echo "=== ASKGauravAI Pre-flight ==="
echo

fail=0

# 1) Required envs
for var in ANTHROPIC_API_KEY APIFY_API_KEY NOTION_API_KEY; do
  if [ -z "${!var}" ]; then
    echo "FAIL  $var not set"
    fail=1
  else
    echo "OK    $var set"
  fi
done

# 2) Anthropic — tiny test call (verifies key + non-zero credits)
echo
echo "Testing Anthropic SDK with 1-token call..."
python3 - <<'PY'
import os, sys
try:
    from anthropic import Anthropic
    c = Anthropic()
    r = c.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=10,
        messages=[{"role": "user", "content": "hi"}],
    )
    print("OK    Anthropic SDK live —", r.stop_reason, "—", len(r.content[0].text), "chars")
except Exception as e:
    print("FAIL  Anthropic call failed:", e)
    sys.exit(1)
PY

# 3) Notion ping
echo
echo "Testing Notion..."
python3 - <<'PY'
import os, sys, requests
tok = os.environ["NOTION_API_KEY"]
db = os.environ.get("NOTION_DATABASE_ID", "")
r = requests.get("https://api.notion.com/v1/users/me",
    headers={"Authorization": f"Bearer {tok}", "Notion-Version": "2022-06-28"}, timeout=10)
if r.status_code == 200:
    print("OK    Notion auth live —", r.json().get("name", "bot"))
else:
    print("FAIL  Notion auth:", r.status_code, r.text[:200])
    sys.exit(1)
if db:
    r = requests.get(f"https://api.notion.com/v1/databases/{db}",
        headers={"Authorization": f"Bearer {tok}", "Notion-Version": "2022-06-28"}, timeout=10)
    print("OK    Notion DB" if r.status_code == 200 else f"WARN  Notion DB {r.status_code}")
PY

# 4) Cost forecast
echo
echo "=== Cost forecast for next pipeline run ==="
echo "  Strategy Agent (Opus)             ~ \$1.00 — \$1.50"
echo "  Content Planner (Sonnet, retries) ~ \$0.30 — \$0.60"
echo "  Script Writer × 9 posts (Sonnet)  ~ \$1.50 — \$2.50"
echo "  Brand Guardian (Opus)             ~ \$0.30 — \$0.60"
echo "  Contradiction Detector            ~ \$0.00 (pure math)"
echo "  -----"
echo "  TOTAL forecast                    ~ \$3.10 — \$5.20"
echo
echo "If Anthropic balance is below \$8 — TOP UP before continuing."
echo
if [ $fail -eq 0 ]; then
  echo "PRE-FLIGHT: PASS"
  exit 0
else
  echo "PRE-FLIGHT: FAIL"
  exit 1
fi
