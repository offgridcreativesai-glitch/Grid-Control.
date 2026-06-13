"""
refactor_group_agents.py — S3 of the backend structure pass.

Groups the flat agents/ folder into:
  agents/            — the runnable agents (launched by path) stay put
  agents/_lib/       — framework + shared helpers (base_agent, model_gateway, …)
  agents/intel/      — research/scraper modules (competitor_intel, website_intel, …)
  agents/renderers/  — HTML/PDF/visual renderers

Does three things deterministically:
  1. Rewrites every `agents.<X>` import repo-wide to its new dotted path.
  2. Fixes the `__file__`-relative repo-root computations in moved files
     (parent.parent -> parent.parent.parent), since they sink one level deeper.
  3. git-mv's the files and adds __init__.py to each new subpackage.

Verification is done separately (import every module + assert root resolves).
"""
from __future__ import annotations

import os
import re
import subprocess

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

GROUPS = {
    "_lib": [
        "base_agent", "model_gateway", "council", "cost_reporter",
        "_provenance", "_learnings", "_record_learning", "_state",
        "_untrusted", "tracing",
    ],
    "intel": [
        "competitor_intel", "channel_discovery", "channel_score",
        "website_intel", "audit_signals", "brand_self", "meta_insights",
        "ig_hashtag_search",
    ],
    "renderers": [
        "brand_book_renderer", "brand_book_v7_renderer",
        "carousel_editorial_renderer", "carousel_html_renderer",
    ],
}

# module name -> new dotted prefix (agents.<sub>)
NEW_PKG = {mod: f"agents.{sub}" for sub, mods in GROUPS.items() for mod in mods}

# Exact root-computation forms used in the repo; each sinks one level, so add one.
ROOT_FIXES = [
    ("os.path.dirname(os.path.dirname(os.path.abspath(__file__)))",
     "os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))"),
    (".resolve().parent.parent",
     ".resolve().parent.parent.parent"),
]


def rewrite_imports_everywhere():
    """Repo-wide: agents.<moved> -> agents.<sub>.<moved> (word-bounded)."""
    changed = []
    for dirpath, dirnames, filenames in os.walk(ROOT):
        if ("__pycache__" in dirpath or "/.git" in dirpath
                or "graphify-out" in dirpath or "/.claude" in dirpath):
            continue
        for fn in filenames:
            if not fn.endswith(".py"):
                continue
            p = os.path.join(dirpath, fn)
            src = open(p, encoding="utf-8").read()
            new = src
            for mod, pkg in NEW_PKG.items():
                # match agents.<mod> not followed by an identifier char (avoids
                # agents.brand_book matching agents.renderers.brand_book_renderer)
                new = re.sub(rf"\bagents\.{re.escape(mod)}(?![A-Za-z0-9_])",
                             f"{pkg}.{mod}", new)
            if new != src:
                open(p, "w", encoding="utf-8").write(new)
                changed.append(os.path.relpath(p, ROOT))
    return changed


def fix_roots_in_moved():
    """Apply +1-level root fixes inside the moved files (pre-move location)."""
    fixed = []
    for mod, pkg in NEW_PKG.items():
        p = os.path.join(ROOT, "agents", f"{mod}.py")
        if not os.path.exists(p):
            continue
        src = open(p, encoding="utf-8").read()
        new = src
        for old, repl in ROOT_FIXES:
            new = new.replace(old, repl)
        if new != src:
            open(p, "w", encoding="utf-8").write(new)
            fixed.append(f"agents/{mod}.py")
    return fixed


def move_files():
    moved = []
    for sub, mods in GROUPS.items():
        subdir = os.path.join(ROOT, "agents", sub)
        os.makedirs(subdir, exist_ok=True)
        init = os.path.join(subdir, "__init__.py")
        if not os.path.exists(init):
            open(init, "w", encoding="utf-8").write(
                f'"""agents.{sub} — see core structure pass S3."""\n')
        for mod in mods:
            src = os.path.join(ROOT, "agents", f"{mod}.py")
            dst = os.path.join(subdir, f"{mod}.py")
            if not os.path.exists(src):
                print(f"  SKIP missing agents/{mod}.py")
                continue
            subprocess.run(["git", "mv", src, dst], cwd=ROOT, check=True)
            moved.append(f"agents/{mod}.py -> agents/{sub}/{mod}.py")
    return moved


def main():
    print("== S3: group agents/ ==")
    fixed = fix_roots_in_moved()
    print(f"root-depth fixes : {len(fixed)} files")
    for f in fixed:
        print(f"   + {f}")
    changed = rewrite_imports_everywhere()
    print(f"import rewrites  : {len(changed)} files")
    for f in changed:
        print(f"   ~ {f}")
    moved = move_files()
    print(f"moved            : {len(moved)} files")
    for m in moved:
        print(f"   > {m}")


if __name__ == "__main__":
    main()
