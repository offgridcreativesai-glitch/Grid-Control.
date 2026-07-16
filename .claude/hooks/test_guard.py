#!/usr/bin/env python3
"""
TEST-GUARD — mechanical enforcement of "every fix ships with a test" (Jul 14 rule).

The same bugs regressed 5-6 times because nothing CHECKED the rule. This hook
denies `git commit` at the tool layer when app code is staged with no test file,
so the rule does not depend on any model remembering it.

BLOCKED:  a `git commit` whose staged files include app code
          (core.py, dashboard_api.py, routes/, agents/, utils/, scheduler/,
          publishing/, dashboard/src/) but include NO test file
          (test_*.py, *_test.py, *.test.ts[x], *.spec.ts[x], tests/ dir).

ALLOWED:  docs/config/asset-only commits (no app code staged) — pass untouched.
          commits that stage a test alongside the app change — the correct way.

Override (human-in-the-loop only): Gaurav runs `export GRID_TEST_GUARD=off`
for genuine non-logic app commits (comment/string/config tweaks). Claude must
not set this itself — same contract as cd_guard.py's GRID_CD_GUARD.

Self-check: `python3 .claude/hooks/test_test_guard.py` (or pytest).
"""
import json
import os
import re
import subprocess
import sys

APP_CODE = re.compile(
    r"^(core\.py|dashboard_api\.py"
    r"|routes/.+\.py"
    r"|agents/.+\.py"
    r"|utils/.+\.py"
    r"|scheduler/.+\.py"
    r"|publishing/.+\.py"
    r"|dashboard/src/.+\.(ts|tsx|js|jsx))$"
)

TEST_FILE = re.compile(
    r"(^|/)(test_[^/]+\.py|[^/]+_test\.py"
    r"|[^/]+\.(test|spec)\.(ts|tsx|js|jsx))$"
)

TEST_DIR = re.compile(r"(^|/)(tests|__tests__)/")


def is_test(path: str) -> bool:
    return bool(TEST_FILE.search(path) or TEST_DIR.search(path))


def decide(staged: list[str]) -> tuple[bool, list[str]]:
    """Pure decision: (block?, offending app files).
    Block when app code is staged and no test file is staged with it."""
    seen = sorted(set(staged))
    app = [p for p in seen if APP_CODE.match(p) and not is_test(p)]
    tests = [p for p in seen if is_test(p)]
    return (bool(app) and not tests), app


def paths_from_command(cmd: str) -> list[str]:
    """Paths named in the command itself. Critical: `git add X && git commit`
    stages X only AFTER this hook runs, so the index check alone sees nothing —
    the first live demo of this guard slipped through exactly that way."""
    toks = [t.strip("'\"`;()") for t in cmd.split()]
    return [t for t in toks if APP_CODE.match(t) or is_test(t)]


def broad_add(cmd: str) -> bool:
    """`git add -A` / `git add .` / `git add --all` — contents unknowable from
    the command text; caller falls back to the full working-tree state."""
    return bool(re.search(r"\bgit\b[^|;&]*\badd\b[^|;&]*(\s-A\b|\s--all\b|\s\.(\s|$))", cmd))


def working_tree_files(repo: str) -> list[str]:
    out = subprocess.run(
        ["git", "-C", repo, "status", "--porcelain"],
        capture_output=True, text=True, timeout=10,
    ).stdout.splitlines()
    return [ln[3:].strip() for ln in out if len(ln) > 3]


def staged_files(repo: str, include_unstaged_tracked: bool = False) -> list[str]:
    out = subprocess.run(
        ["git", "-C", repo, "diff", "--cached", "--name-only"],
        capture_output=True, text=True, timeout=10,
    ).stdout.splitlines()
    if include_unstaged_tracked:  # `git commit -a` also sweeps modified tracked files
        out += subprocess.run(
            ["git", "-C", repo, "diff", "--name-only"],
            capture_output=True, text=True, timeout=10,
        ).stdout.splitlines()
    return [p.strip() for p in out if p.strip()]


def main() -> None:
    if os.environ.get("GRID_TEST_GUARD", "on").lower() == "off":
        sys.exit(0)
    try:
        d = json.load(sys.stdin)
    except Exception:
        sys.exit(0)  # never break the session on a parse error
    if d.get("tool_name") != "Bash":
        sys.exit(0)
    cmd = (d.get("tool_input") or {}).get("command", "") or ""
    if not re.search(r"\bgit\b[^|;&]*\bcommit\b", cmd):
        sys.exit(0)

    repo = os.environ.get("CLAUDE_PROJECT_DIR") or d.get("cwd") or os.getcwd()
    try:
        commits_all = bool(re.search(r"\bcommit\b.*(\s-a\b|\s--all\b|\s-am\b)", cmd))
        candidates = staged_files(repo, include_unstaged_tracked=commits_all)
        # `git add ... && git commit` in ONE command stages after this hook runs:
        # the index is blind to it, so paths in the command text count too.
        candidates += paths_from_command(cmd)
        if broad_add(cmd):
            candidates += working_tree_files(repo)
    except Exception:
        sys.exit(0)  # git unavailable/broken -> don't brick commits

    block, app = decide(candidates)
    if block:
        print(
            "TEST-GUARD: blocked commit — app code staged with NO test file.\n"
            f"App files staged: {', '.join(app[:10])}\n\n"
            "The Jul-14 standing rule: every fix ships with a test "
            "(fail-on-old, pass-on-fix, wired into the real code path).\n"
            "Do it the CORRECT way:\n"
            "  1. Write/extend a test (test_*.py or *.test.ts) that pins this change.\n"
            "  2. `git add` the test in the SAME commit and retry.\n"
            "Docs/config-only commits pass automatically.\n"
            "Genuine non-logic app tweak (comment, string)? Ask Gaurav to run "
            "`export GRID_TEST_GUARD=off` — human-only override, do not set it yourself.",
            file=sys.stderr,
        )
        sys.exit(2)  # exit 2 => PreToolUse block, stderr shown to Claude
    sys.exit(0)


if __name__ == "__main__":
    main()
