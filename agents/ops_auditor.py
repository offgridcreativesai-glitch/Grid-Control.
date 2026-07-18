"""ops_auditor — platform-level production health checks ($0, no model calls).

Stands in for a human ops hire until GC has one (Gaurav decision, Jul 16).
Checks everything measurable — API health (local + deployed), dashboard,
CI status, paid-spend ledger vs cap, brand-store sync — and writes a
plain-English "Production Health" card. Zero fabrication: a check that cannot
run reports itself as unavailable with the reason, never a guessed status.

Platform-level (no brand): output goes to .grid_state/ops_health_latest.md
(+ .json), served by GET /api/ops/health (super-admin). Scheduled weekly via
the ops pipeline (disabled by default — Gaurav enables).

Run: `python3 agents/ops_auditor.py`
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
from datetime import datetime, timezone
from pathlib import Path

import requests  # bundles certifi — urllib false-failed HTTPS on bare python.org installs

BASE_DIR = Path(__file__).parent.parent
STATE_DIR = BASE_DIR / ".grid_state"

RAILWAY_URL = os.getenv("RAILWAY_PUBLIC_URL", "https://web-production-175d5.up.railway.app")
VERCEL_URL = os.getenv("DASHBOARD_PUBLIC_URL", "https://v0-grid-control-dashboard.vercel.app")


def _http_check(url: str, timeout: int = 10) -> dict:
    try:
        r = requests.get(url, timeout=timeout, headers={"User-Agent": "gc-ops-auditor"})
        return {"ok": 200 <= r.status_code < 400, "detail": f"HTTP {r.status_code}"}
    except Exception as e:
        return {"ok": False, "detail": str(e)[:150]}


def check_deployed_api() -> dict:
    return _http_check(f"{RAILWAY_URL}/api/health")


def check_dashboard() -> dict:
    return _http_check(VERCEL_URL)


def check_local_api() -> dict:
    return _http_check("http://localhost:5001/api/health", timeout=3)


def check_ci() -> dict:
    """Latest CI conclusion via gh CLI. Unavailable (not fabricated) without gh."""
    if not shutil.which("gh"):
        return {"ok": None, "detail": "unavailable: gh CLI not present on this machine"}
    try:
        out = subprocess.run(
            ["gh", "run", "list", "--limit", "1", "--json", "conclusion,displayTitle"],
            capture_output=True, text=True, timeout=20,
        )
        runs = json.loads(out.stdout or "[]")
        if not runs:
            return {"ok": None, "detail": "unavailable: no CI runs found"}
        c = runs[0].get("conclusion") or "in progress"
        return {"ok": c == "success", "detail": f"latest run: {c} — {runs[0].get('displayTitle', '')[:60]}"}
    except Exception as e:
        return {"ok": None, "detail": f"unavailable: {str(e)[:120]}"}


def ledger_status(ledger: dict, today: str, cap: float | None) -> dict:
    """Pure: today's spend vs cap. cap None -> report spend, flag missing cap."""
    spend = float(ledger.get(today, 0.0) or 0.0)
    if cap is None:
        return {"ok": None, "detail": f"spent ${spend:.2f} today — no daily cap set (GRID_DAILY_USD_CAP)"}
    return {"ok": spend <= cap, "detail": f"spent ${spend:.2f} of ${cap:.2f} daily cap"}


def check_paid_ledger() -> dict:
    path = STATE_DIR / "paid_ledger.json"
    if not path.exists():
        return {"ok": True, "detail": "no paid ledger yet — no spend recorded"}
    try:
        ledger = json.loads(path.read_text())
    except Exception:
        return {"ok": False, "detail": "paid_ledger.json unreadable — spend tracking broken"}
    cap_raw = os.getenv("GRID_DAILY_USD_CAP", "").strip()
    cap = float(cap_raw) if cap_raw else None
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    return ledger_status(ledger, today, cap)


def check_brand_store() -> dict:
    """Brands in Supabase vs their synced state rows. Unavailable without DB."""
    try:
        import sys
        sys.path.insert(0, str(BASE_DIR / "supabase"))
        import db  # noqa
        brands = db.get_all_brands() or []
        if not brands:
            return {"ok": None, "detail": "no brands registered yet"}
        counts = []
        for b in brands:
            try:
                res = db._svc().table("brand_state").select("file_key").eq("brand_id", b["id"]).execute()
                counts.append(f"{b.get('slug', '?')}: {len(res.data or [])} state files in cloud")
            except Exception:
                counts.append(f"{b.get('slug', '?')}: state rows unreadable")
        return {"ok": True, "detail": "; ".join(counts)}
    except Exception as e:
        return {"ok": None, "detail": f"unavailable: {str(e)[:120]}"}


CHECKS = {
    "Deployed API (Railway)": check_deployed_api,
    "Dashboard (Vercel)": check_dashboard,
    "Local API": check_local_api,
    "CI (GitHub Actions)": check_ci,
    "Spend vs cap": check_paid_ledger,
    "Brand data in cloud": check_brand_store,
}


def compose_report(results: dict[str, dict]) -> str:
    """Plain-English markdown card. No JSON ever reaches a human."""
    ok = sum(1 for r in results.values() if r.get("ok") is True)
    bad = [n for n, r in results.items() if r.get("ok") is False]
    lines = ["# Production Health", ""]
    lines.append(f"_{datetime.now(timezone.utc).strftime('%b %d, %Y %H:%M UTC')}_")
    lines.append("")
    if bad:
        lines.append(f"**Needs attention: {', '.join(bad)}.**")
    else:
        lines.append(f"**All clear — {ok} of {len(results)} checks healthy.**")
    lines.append("")
    for name, r in results.items():
        mark = "✅" if r.get("ok") is True else ("❌" if r.get("ok") is False else "◻️")
        lines.append(f"- {mark} **{name}** — {r.get('detail', '')}")
    lines.append("")
    lines.append("_◻️ = could not be checked from here (reason shown), not a failure._")
    return "\n".join(lines)


def run_audit() -> Path:
    results = {name: fn() for name, fn in CHECKS.items()}
    STATE_DIR.mkdir(exist_ok=True)
    md_path = STATE_DIR / "ops_health_latest.md"
    md_path.write_text(compose_report(results))
    (STATE_DIR / "ops_health_latest.json").write_text(json.dumps({
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "results": results,
    }, indent=2))
    return md_path


if __name__ == "__main__":
    path = run_audit()
    print(path.read_text())
