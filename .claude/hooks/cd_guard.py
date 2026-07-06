#!/usr/bin/env python3
"""
CD-GUARD — mechanical enforcement of the "Creative Director handles content, not Claude" rule.

Standing instruction from Gaurav (violated 15+ times): all reel/carousel creative work
MUST be produced by the Creative Director agent (agents/reel_editor.py /
agents/carousel_designer*). Claude orchestrates and may FIX the agent's logic, but must
NOT hand-author the creative output in ad-hoc scripts or hand-fed plan_overrides.

This hook denies the bypass at the tool layer so it does not depend on Claude remembering.

ALLOWED (not blocked):
  - Editing the CD agents themselves (agents/reel_editor.py, agents/carousel*, etc.)
    -> this is the CORRECT fix when the CD's auto-plan is wrong.
  - Invoking the CD agent / running it as the pipeline.

BLOCKED:
  - Writing ad-hoc content composers:  scripts/_cd_*.py, scripts/_build_*.py, and other
    standalone reel/carousel compositing scripts under scripts/.
  - Passing a hand-authored plan_override (the literal plan that bypasses CD planning).
  - Raw ffmpeg / playwright commands that composite a brand content video by hand.

Override (human-in-the-loop only): Gaurav runs `export GRID_CD_GUARD=off` in the shell.
Claude must not set this itself.
"""
import json
import os
import re
import sys


def deny(reason: str) -> None:
    print(reason, file=sys.stderr)
    sys.exit(2)  # exit 2 => PreToolUse block, stderr shown to Claude


def main() -> None:
    if os.environ.get("GRID_CD_GUARD", "on").lower() == "off":
        sys.exit(0)

    try:
        d = json.load(sys.stdin)
    except Exception:
        sys.exit(0)  # never break the session on a parse error

    tool = d.get("tool_name", "")
    ti = d.get("tool_input", {}) or {}

    HOW = (
        "\n\nDo it the CORRECT way:\n"
        "  1. Invoke the Creative Director agent — agents/reel_editor.py build_reel(...) "
        "or the carousel designer — and let IT author the plan/stamps/b-roll.\n"
        "  2. If the CD's auto-plan is wrong, FIX agents/reel_editor.py (its planning logic). "
        "That edit is allowed.\n"
        "  3. Bring the CD's output to Gaurav for approval.\n"
        "Hand-authoring the creative output is the exact thing you were told 15+ times not to do."
    )

    # ---- Write / Edit / NotebookEdit ----
    if tool in ("Write", "Edit", "NotebookEdit"):
        path = ti.get("file_path", "") or ti.get("notebook_path", "")
        base = os.path.basename(path)
        # editing the CD agents themselves is the sanctioned fix — always allow
        if re.search(r"agents/(reel_editor|carousel|creative_director)", path):
            sys.exit(0)
        # ad-hoc content composers under scripts/
        if "/scripts/" in path or path.startswith("scripts/"):
            if re.match(r"_(cd|build|reel|broll|carousel|scene|still)[_\.]", base) or \
               re.search(r"(reel|broll|carousel)", base, re.I):
                deny(f"CD-GUARD: blocked ad-hoc content composer `{path}`." + HOW)
        # hand-authored plan_override anywhere
        blob = ti.get("content", "") or ti.get("new_string", "") or ""
        if re.search(r"plan_override\s*=\s*[\[\{]", blob):
            deny("CD-GUARD: blocked hand-authored `plan_override`. The Creative Director "
                 "must generate the plan." + HOW)
        sys.exit(0)

    # ---- Bash ----
    if tool == "Bash":
        cmd = ti.get("command", "") or ""
        low = cmd.lower()
        # running an ad-hoc composer script
        if re.search(r"python3?\s+.*scripts/_(cd|build|reel|broll|carousel|scene)", low):
            deny("CD-GUARD: blocked running an ad-hoc content composer script." + HOW)
        # raw ffmpeg/playwright building a brand content video by hand
        builds_content = re.search(r"(reel|broll|carousel|_stills|insert_)", low)
        if ("ffmpeg" in low or "playwright" in low) and builds_content and \
           "brands/" in low and re.search(r"\.(mp4|mov|webm)", low):
            deny("CD-GUARD: blocked raw ffmpeg/playwright compositing of a brand content "
                 "video. Route through the Creative Director agent." + HOW)
        sys.exit(0)

    sys.exit(0)


if __name__ == "__main__":
    main()
