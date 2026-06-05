#!/usr/bin/env python3
"""
onboard_brand.py — the repeatable brand-onboarding checklist + verifier.

ONE command to scaffold or verify any brand's wiring into Grid Control. Minimal
by design: it never fabricates data and never prints tokens (only presence).

Usage:
    python3 scripts/onboard_brand.py --verify <slug>     # check a brand is fully wired
    python3 scripts/onboard_brand.py --scaffold <slug>   # create the required file skeleton
    python3 scripts/onboard_brand.py --checklist          # print the human onboarding steps

The canonical narrative lives in docs/BRAND_ONBOARDING.md. This script is the
machine-checkable version of that doc — run --verify before kicking off agents.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BRANDS = ROOT / "brands"

# Files every brand needs to be considered "wired". (file, required?, written_by)
REQUIRED_FILES = [
    ("brand_profile.json", True,  "Intake form / create_brand"),
    ("voice_profile.json", True,  "Voice extraction (Stage 2)"),
    ("session_state.json", True,  "create_brand bootstrap"),
    (".env",               True,  "Connections page (Stage 3)"),
]
# Files produced by the intelligence pipeline — absent on day 0, present after kickoff.
PIPELINE_FILES = [
    ("trends_live.json",         "Trend Researcher"),
    ("strategy_90day.json",      "Strategy Agent"),
    ("competitors_db.json",      "Strategy Agent"),
    ("content_calendar.json",    "Content Planner"),
    ("performance_history.json", "Performance Tracker"),
]
# Connection env keys we look for (presence only, never value).
CONNECTION_KEYS = [
    ("META_GRAPH_API_TOKEN", "Instagram publish + insights (Instagram Login API)"),
    ("IG_USER_ID",           "Instagram account id"),
    ("LINKEDIN_ACCESS_TOKEN","LinkedIn post"),
    ("YOUTUBE_REFRESH_TOKEN","YouTube upload (OAuth)"),
    ("TWITTER_API_KEY",      "X post (OAuth 1.0a) — optional, manual ok"),
]


def _read_env_keys(env_path: Path) -> set[str]:
    keys: set[str] = set()
    if not env_path.exists():
        return keys
    for line in env_path.read_text().splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, v = line.split("=", 1)
            if v.strip():  # only count keys that actually have a value
                keys.add(k.strip())
    return keys


def verify(slug: str) -> int:
    bdir = BRANDS / slug
    if not bdir.exists():
        print(f"❌ Brand dir not found: brands/{slug}/  — run --scaffold {slug} first.")
        return 2

    print(f"\n  BRAND ONBOARDING — VERIFY  ·  {slug}")
    print("  " + "─" * 48)

    ok = True

    print("\n  Core files (required):")
    for fname, required, who in REQUIRED_FILES:
        exists = (bdir / fname).exists()
        mark = "✅" if exists else ("❌" if required else "—")
        if required and not exists:
            ok = False
        print(f"    {mark}  {fname:<24} {who}")

    print("\n  Platform connections (in brands/{}/.env):".format(slug))
    keys = _read_env_keys(bdir / ".env")
    for env_key, label in CONNECTION_KEYS:
        present = env_key in keys
        mark = "✅" if present else "○"
        print(f"    {mark}  {env_key:<24} {label}")
    if not any(k in keys for k, _ in CONNECTION_KEYS):
        print("    ⚠️  No platform connected yet — agents will not run until at least one is.")
        ok = False

    print("\n  Intelligence pipeline (built after kickoff):")
    for fname, who in PIPELINE_FILES:
        exists = (bdir / fname).exists()
        mark = "✅" if exists else "○ pending"
        print(f"    {mark:<9} {fname:<24} {who}")

    print("\n  " + "─" * 48)
    if ok:
        print("  ✅ WIRED — core files + ≥1 connection present. Safe to run agents.")
    else:
        print("  ⛔ NOT READY — fix the ❌ items above, then re-run --verify.")
    print()
    return 0 if ok else 1


def scaffold(slug: str) -> int:
    bdir = BRANDS / slug
    (bdir / "outputs" / "pending_approval").mkdir(parents=True, exist_ok=True)
    (bdir / "outputs" / "approved").mkdir(parents=True, exist_ok=True)
    (bdir / "outputs" / "blocked").mkdir(parents=True, exist_ok=True)
    # Minimal stubs only where safe; never fabricate brand content.
    sess = bdir / "session_state.json"
    if not sess.exists():
        sess.write_text(json.dumps({
            "current_agent": None, "next_agent": "trend-researcher",
            "pipeline_status": "not_started", "completed_agents": [], "last_completed": None,
        }, indent=2))
    env = bdir / ".env"
    if not env.exists():
        env.write_text("# Per-brand platform tokens (gitignored). Paste via Connections page.\n")
    print(f"✅ Scaffolded brands/{slug}/ (outputs dirs + session_state + empty .env).")
    print(f"   Next: fill brand_profile.json (use the API/onboarding form), extract voice, connect platforms.")
    print(f"   Then: python3 scripts/onboard_brand.py --verify {slug}")
    return 0


CHECKLIST = """
  OFFGRID BRAND ONBOARDING — the 6 steps (every brand, same order)

  1. INTAKE      Fill the onboarding form (/onboarding) → brand_profile.json.
                 Minimum: name, product, audience, IG handle, competitor handles,
                 tone, what-to-never-say. (No assumptions — real answers only.)
  2. SCAFFOLD    POST /api/brands/create (the form does this) builds dirs,
                 brand_profile.json, memory, Supabase row, session_state.
  3. VOICE       Extract voice_profile.json from real sample posts / brand brief
                 (/api/voice/extract-profile). Required before Script Writer runs.
  4. CONNECT     Connections page → paste each platform token into brands/<slug>/.env.
                 At least one platform required. (You paste; tokens never shown.)
  5. VERIFY      python3 scripts/onboard_brand.py --verify <slug>  → all ✅.
  6. KICK OFF    Run the intelligence pipeline in order:
                 trend-researcher → strategy-agent → content-planner → (content agents).
                 First content → approval gate → publish.

  Rule: a brand is not "live" until step 5 shows WIRED and step 6 has produced
  its first approved post. Same flow for every brand — minimal, repeatable.
"""


def main() -> int:
    ap = argparse.ArgumentParser(description="Brand onboarding checklist + verifier")
    ap.add_argument("--verify", metavar="SLUG", help="verify a brand is fully wired")
    ap.add_argument("--scaffold", metavar="SLUG", help="create the required file skeleton")
    ap.add_argument("--checklist", action="store_true", help="print the human onboarding steps")
    args = ap.parse_args()

    if args.checklist:
        print(CHECKLIST)
        return 0
    if args.scaffold:
        return scaffold(args.scaffold)
    if args.verify:
        return verify(args.verify)
    ap.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
