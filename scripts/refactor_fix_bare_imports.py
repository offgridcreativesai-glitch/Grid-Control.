"""
refactor_fix_bare_imports.py — S3 follow-up.

The runnable agents put agents/ on sys.path and used BARE sibling imports
(`import cost_reporter`, `from _provenance import ...`). Those broke when the
siblings moved into agents/_lib, agents/intel, agents/renderers. Since every
agent/core/script already has repo-ROOT on sys.path, rewrite the bare imports
to the new dotted paths:

  import <mod>                -> from <pkg> import <mod>
  import <mod> as <a>         -> import <pkg>.<mod> as <a>
  from <mod> import <names>   -> from <pkg>.<mod> import <names>
"""
from __future__ import annotations

import os
import re

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

GROUPS = {
    "_lib": ["base_agent", "model_gateway", "council", "cost_reporter",
             "_provenance", "_learnings", "_record_learning", "_state",
             "_untrusted", "tracing"],
    "intel": ["competitor_intel", "channel_discovery", "channel_score",
              "website_intel", "audit_signals", "brand_self", "meta_insights",
              "ig_hashtag_search"],
    "renderers": ["brand_book_renderer", "brand_book_v7_renderer",
                  "carousel_editorial_renderer", "carousel_html_renderer"],
}
NEW_PKG = {m: f"agents.{sub}" for sub, mods in GROUPS.items() for m in mods}


def fix_line(line: str) -> str:
    for mod, pkg in NEW_PKG.items():
        me = re.escape(mod)
        # from <mod> import ...
        m = re.match(rf"^(\s*)from {me} import (.*)$", line)
        if m:
            return f"{m.group(1)}from {pkg}.{mod} import {m.group(2)}\n"
        # import <mod> as <alias>
        m = re.match(rf"^(\s*)import {me} as (\w+)(.*)$", line)
        if m:
            return f"{m.group(1)}import {pkg}.{mod} as {m.group(2)}{m.group(3)}\n"
        # plain import <mod>  (optional trailing comment)
        m = re.match(rf"^(\s*)import {me}(\s*(#.*)?)$", line)
        if m:
            return f"{m.group(1)}from {pkg} import {mod}{m.group(2)}\n"
    return line


def main():
    changed = []
    for dirpath, _dn, filenames in os.walk(ROOT):
        if ("__pycache__" in dirpath or "/.git" in dirpath
                or "graphify-out" in dirpath or "/.claude" in dirpath):
            continue
        for fn in filenames:
            if not fn.endswith(".py"):
                continue
            p = os.path.join(dirpath, fn)
            lines = open(p, encoding="utf-8").read().splitlines(keepends=True)
            out = [fix_line(ln) for ln in lines]
            if out != lines:
                open(p, "w", encoding="utf-8").write("".join(out))
                changed.append(os.path.relpath(p, ROOT))
    print(f"bare-import fixes: {len(changed)} files")
    for f in changed:
        print(f"   ~ {f}")


if __name__ == "__main__":
    main()
