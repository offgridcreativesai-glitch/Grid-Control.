---
name: gc-verify
description: MANDATORY before claiming any Grid Control change is "done", "fixed", or "works". Codifies GC's real end-to-end verification — Flask restart rules, endpoint check, FE render check, captured proof. Use whenever about to report a fix/feature complete, or when Gaurav asks "does it work?".
---

# gc-verify — prove it before you say it

Gaurav is non-technical. A "done" he can't see verified is indistinguishable from a lie,
and unverified "done"s are what destroyed trust in July 2026. This skill is the checklist
that turns "done" into "verified: X by Y". **No done-claim without completing it.**

## The procedure

### 1. Know what kind of change you made
- **Python (backend)** — Flask runs with `debug=False`: **NO auto-reload**. Your change
  is NOT live until you restart:
  ```bash
  pkill -f dashboard_api.py; sleep 1
  cd /Users/gauravoffgrid/offgrid-marketing-os && source .env && nohup python3 dashboard_api.py > /tmp/gc_flask.log 2>&1 &
  sleep 3 && curl -s -o /dev/null -w "%{http_code}" http://localhost:5001/api/health
  ```
  Skipping the restart and testing the OLD code is the classic false-verify.
- **Frontend (dashboard/)** — Vite HMR reloads automatically; no restart needed.
  If the dev server isn't up, start it via the browser preview tool (never Bash).
- **Pure function / test-only** — run the test; that IS the verification.

### 2. Exercise the REAL path, not a copy
- Hit the affected endpoint with `curl` (or the browser) and read the actual response.
- If the change is user-visible: load http://localhost:5280 in the browser preview,
  navigate to the affected page, and check the rendered result (read_page/screenshot).
- Watch for errors: `tail -20 /tmp/gc_flask.log`, browser console messages.
- If the fix has a test (it must, per the standing rule): run it and confirm it FAILS
  on the old logic / PASSES on the new — fail-then-pass is the proof that rebuilt trust.

### 3. Capture proof Gaurav can see
One of: a screenshot of the fixed UI · the curl output showing the corrected response ·
the test output (red on old, green on new) · the green check in GitHub → Actions.
Include it (or describe it precisely) in the message that claims completion.

### 4. Say it in the verified form
Not: "Done, the reject button works now."
But: "Verified this session: restarted Flask, POST /api/outputs/reject with a fake
filename now returns 404 (was success:true); real filename deletes the file — curl
output above. Test test_reject_resolution.py passes."

## Hard rules
- Never claim verification you did not do THIS session with a tool.
- Never verify against a stale server (rule 1) — restart first for Python changes.
- Never trigger user-facing GC actions (agent runs, publishes, approvals) to "verify" —
  those are Gaurav's clicks. Verify at the endpoint/render level; ask him for the click.
- If verification fails or is impossible right now, SAY THAT — an honest "built but
  not yet verified because X" keeps trust; a hopeful "done" spends it.

## Self-check
`ls .claude/skills/gc-verify/SKILL.md` — this file existing + being invoked before
done-claims is the check. The SessionStart ground-rules hook points here.
