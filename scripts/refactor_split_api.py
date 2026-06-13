"""
refactor_split_api.py — S2a of the backend structure pass.

Deterministically splits the dashboard_api.py monolith into:
  core.py            — imports, constants, globals, app creation, infra hooks,
                       errorhandlers, and ALL ~209 helper functions. Exports
                       everything via __all__ (incl. _underscore names).
  dashboard_api.py   — `from core import *` + ONLY the @app.route endpoints
                       + the __main__ launch block. Becomes the route catalog.

Backward-compatible: `dashboard_api:app` (gunicorn) and any
`from dashboard_api import helper` keep working via the * re-export.

AST-driven, line-range slicing (preserves comments/formatting). No model cost.
Run:  python3 scripts/refactor_split_api.py        # writes core.py + candidate
It writes core.py and dashboard_api_candidate.py; a separate validator swaps.
"""
from __future__ import annotations

import ast
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, "dashboard_api.py")

ROUTE_DECOS = {"route", "get", "post", "put", "delete", "patch"}
HOOK_DECOS = {
    "before_request", "after_request", "teardown_request",
    "teardown_appcontext", "errorhandler", "before_first_request",
}


def deco_kind(node) -> str | None:
    """Return 'route' / 'hook' if decorated with @app.<x>, else None."""
    for d in node.decorator_list:
        target = d.func if isinstance(d, ast.Call) else d
        if (isinstance(target, ast.Attribute)
                and isinstance(target.value, ast.Name)
                and target.value.id == "app"):
            if target.attr in ROUTE_DECOS:
                return "route"
            if target.attr in HOOK_DECOS:
                return "hook"
    return None


def block_span(node) -> tuple[int, int]:
    """1-based inclusive line span INCLUDING decorators."""
    start = node.lineno
    if node.decorator_list:
        start = min(start, min(d.lineno for d in node.decorator_list))
    return start, node.end_lineno


def main():
    src = open(SRC, encoding="utf-8").read()
    lines = src.splitlines(keepends=True)
    n = len(lines)
    tree = ast.parse(src)

    # tag[i] for 1-based line i -> 'core' (default) | 'api' | 'main'
    tag = ["core"] * (n + 1)

    for node in tree.body:
        # __main__ launch block -> dashboard_api
        if (isinstance(node, ast.If)
                and isinstance(node.test, ast.Compare)
                and isinstance(node.test.left, ast.Name)
                and node.test.left.id == "__name__"):
            for i in range(node.lineno, node.end_lineno + 1):
                tag[i] = "main"
            continue
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            kind = deco_kind(node)
            if kind == "route":
                s, e = block_span(node)
                for i in range(s, e + 1):
                    tag[i] = "api"
            # hooks + helpers -> core (default)

    # Pull contiguous leading comment/blank lines into each route block so
    # section banners ("# ---- BRANDS ----") travel WITH the routes.
    i = 1
    while i <= n:
        if tag[i] == "api":
            j = i - 1
            while j >= 1 and tag[j] == "core":
                stripped = lines[j - 1].strip()
                if stripped == "" or stripped.startswith("#"):
                    tag[j] = "api"
                    j -= 1
                else:
                    break
        i += 1

    core_lines = [lines[i - 1] for i in range(1, n + 1) if tag[i] == "core"]
    api_lines = [lines[i - 1] for i in range(1, n + 1) if tag[i] == "api"]
    main_lines = [lines[i - 1] for i in range(1, n + 1) if tag[i] == "main"]

    core_src = "".join(core_lines)

    # Compute __all__ = every top-level bound name in core (incl. underscores).
    core_tree = ast.parse(core_src)
    names: list[str] = []
    seen = set()

    def add(name: str):
        if name and name not in seen:
            seen.add(name)
            names.append(name)

    for node in core_tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            add(node.name)
        elif isinstance(node, ast.Assign):
            for t in node.targets:
                if isinstance(t, ast.Name):
                    add(t.id)
                elif isinstance(t, (ast.Tuple, ast.List)):
                    for el in t.elts:
                        if isinstance(el, ast.Name):
                            add(el.id)
        elif isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
            add(node.target.id)
        elif isinstance(node, (ast.Import, ast.ImportFrom)):
            for a in node.names:
                add(a.asname or a.name.split(".")[0])

    all_block = "\n\n# Re-exported so `from core import *` carries every name,\n" \
                "# including _underscore helpers, into the route modules.\n" \
                "__all__ = [\n" + \
                "".join(f"    {n!r},\n" for n in names) + "]\n"

    core_header = (
        '"""\n'
        "core.py — GRID CONTROL backend foundation (extracted from dashboard_api.py, S2a).\n\n"
        "Holds imports, constants, globals, the Flask `app`, infra hooks/errorhandlers,\n"
        "and all helper functions. Routes live in dashboard_api.py (`from core import *`).\n"
        '"""\n'
    )
    core_out = core_header + core_src + all_block

    api_header = (
        '"""\n'
        "dashboard_api.py — GRID CONTROL route catalog.\n\n"
        "Every HTTP endpoint lives here, grouped by URL prefix. Infra, helpers and the\n"
        "Flask `app` come from core.py. gunicorn entrypoint is still `dashboard_api:app`.\n"
        '"""\n'
        "from core import *  # noqa: F401,F403  (app, helpers, constants, stdlib re-exports)\n\n"
    )
    api_out = api_header + "".join(api_lines)
    if main_lines:
        api_out += "\n\n" + "".join(main_lines)

    open(os.path.join(ROOT, "core.py"), "w", encoding="utf-8").write(core_out)
    open(os.path.join(ROOT, "dashboard_api_candidate.py"), "w", encoding="utf-8").write(api_out)

    print(f"core.py            : {core_out.count(chr(10))+1} lines, {len(names)} exported names")
    print(f"dashboard_api(cand): {api_out.count(chr(10))+1} lines, {len(api_lines)} route-section lines")
    print("AST check:",
          "core OK" if ast.parse(core_out) is not None else "core FAIL",
          "/ candidate OK" if ast.parse(api_out) is not None else "/ candidate FAIL")


if __name__ == "__main__":
    main()
