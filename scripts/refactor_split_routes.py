"""
refactor_split_routes.py — S2b of the backend structure pass.

Splits dashboard_api.py's 113 @app.route endpoints into 7 domain blueprints
under routes/, grouped by URL prefix:

  routes/brands.py       /api/brands /brand /team /admin /auth
  routes/agents.py       /api/agents /agent-config /learning /contradictions /performance
  routes/content.py      /api/outputs /carousel /publish /published /pipeline /dashboard-output
  routes/brain.py        /api/brain /ceo /jarvis /operator-mode /standup /digest
  routes/billing.py      /api/billing
  routes/connections.py  /api/connections /voice /notion
  routes/system.py       /api/health /config /scheduler /events /notifications /webhooks (+ fallback)

dashboard_api.py becomes a thin entrypoint: `from core import *`, import each
blueprint, register on `app`, keep __main__. URLs are unchanged (full paths kept
on @bp.route, no url_prefix). gunicorn dashboard_api:app intact.
"""
from __future__ import annotations

import ast
import os
import re

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, "dashboard_api.py")

GROUP_OF_PREFIX = {
    "/api/brands": "brands", "/api/brand": "brands", "/api/team": "brands",
    "/api/admin": "brands", "/api/auth": "brands",
    "/api/agents": "agents", "/api/agent-config": "agents",
    "/api/learning": "agents", "/api/contradictions": "agents",
    "/api/performance": "agents",
    "/api/outputs": "content", "/api/carousel": "content", "/api/publish": "content",
    "/api/published": "content", "/api/pipeline": "content",
    "/api/dashboard-output": "content",
    "/api/brain": "brain", "/api/ceo": "brain", "/api/jarvis": "brain",
    "/api/operator-mode": "brain", "/api/standup": "brain", "/api/digest": "brain",
    "/api/billing": "billing",
    "/api/connections": "connections", "/api/voice": "connections",
    "/api/notion": "connections",
    "/api/health": "system", "/api/config": "system", "/api/scheduler": "system",
    "/api/events": "system", "/api/notifications": "system", "/api/webhooks": "system",
}
DEFAULT_GROUP = "system"
GROUP_ORDER = ["brands", "agents", "content", "brain", "billing", "connections", "system"]

ROUTE_DECOS = {"route", "get", "post", "put", "delete", "patch"}


def is_route(n):
    if not isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)):
        return False
    for d in n.decorator_list:
        t = d.func if isinstance(d, ast.Call) else d
        if (isinstance(t, ast.Attribute) and isinstance(t.value, ast.Name)
                and t.value.id == "app" and t.attr in ROUTE_DECOS):
            return True
    return False


def route_path(n, lines):
    for d in n.decorator_list:
        t = d.func if isinstance(d, ast.Call) else d
        if (isinstance(t, ast.Attribute) and isinstance(t.value, ast.Name)
                and t.value.id == "app" and t.attr in ROUTE_DECOS):
            if isinstance(d, ast.Call) and d.args and isinstance(d.args[0], ast.Constant):
                return d.args[0].value
            # fallback: regex the decorator source line
            ln = lines[d.lineno - 1]
            m = re.search(r"@app\.\w+\(\s*[\"']([^\"']+)", ln)
            if m:
                return m.group(1)
    return None


def group_of(path):
    if not path:
        return DEFAULT_GROUP
    m = re.match(r"(/api/[^/<]+)", path)
    pref = m.group(1) if m else path
    return GROUP_OF_PREFIX.get(pref, DEFAULT_GROUP)


def main():
    src = open(SRC, encoding="utf-8").read()
    lines = src.splitlines(keepends=True)
    tree = ast.parse(src)

    import_end = 0
    main_node = None
    routes = []
    for n in tree.body:
        if isinstance(n, ast.ImportFrom) and n.module == "core":
            import_end = n.end_lineno
        elif isinstance(n, ast.If):
            main_node = n
        elif is_route(n):
            routes.append(n)
    routes.sort(key=lambda n: n.lineno)
    main_start = main_node.lineno if main_node else len(lines) + 1

    # Partition [import_end, main_start) into per-route blocks (gap = leading
    # comments/blanks attach to the following route).
    blocks = []  # (group, text)
    prev_end = import_end
    for n in routes:
        start = min([n.lineno] + [d.lineno for d in n.decorator_list])
        block = "".join(lines[prev_end:n.end_lineno])  # gap + decorators + body
        # rewrite only the @app.<method> decorator -> @bp.<method>
        block = re.sub(r"(?m)^(\s*)@app\.(route|get|post|put|delete|patch)\b",
                       r"\1@bp.\2", block)
        path = route_path(n, lines)
        blocks.append((group_of(path), block))
        prev_end = n.end_lineno

    # trailing lines before __main__ (if any) -> append to last block
    if prev_end < main_start - 1 and blocks:
        tail = "".join(lines[prev_end:main_start - 1])
        if tail.strip():
            g, b = blocks[-1]
            blocks[-1] = (g, b + tail)

    main_block = "".join(lines[main_start - 1:]) if main_node else ""

    # write blueprint files
    by_group = {g: [] for g in GROUP_ORDER}
    for g, b in blocks:
        by_group.setdefault(g, []).append(b)

    os.makedirs(os.path.join(ROOT, "routes"), exist_ok=True)
    counts = {}
    for g in GROUP_ORDER:
        body = "".join(by_group.get(g, []))
        n_routes = body.count("@bp.")
        counts[g] = n_routes
        header = (
            f'"""routes/{g}.py — GRID CONTROL {g} endpoints (blueprint). S2b split."""\n'
            "from core import *  # noqa: F401,F403  (app, helpers, stdlib re-exports)\n"
            "from flask import Blueprint\n\n"
            f'bp = Blueprint("{g}", __name__)\n\n'
        )
        open(os.path.join(ROOT, "routes", f"{g}.py"), "w", encoding="utf-8").write(header + body)

    # new thin dashboard_api.py
    regs = "\n".join(f"from routes.{g} import bp as {g}_bp" for g in GROUP_ORDER)
    reg_calls = "for _bp in (" + ", ".join(f"{g}_bp" for g in GROUP_ORDER) + \
                "):\n    app.register_blueprint(_bp)\n"
    api = (
        '"""\n'
        "dashboard_api.py — GRID CONTROL API entrypoint.\n\n"
        "Thin: pulls the Flask `app` + helpers from core, registers the route\n"
        "blueprints (routes/*.py), and launches. gunicorn target: dashboard_api:app.\n"
        '"""\n'
        "from core import *  # noqa: F401,F403\n\n"
        + regs + "\n\n" + reg_calls + "\n\n" + main_block
    )
    open(SRC, "w", encoding="utf-8").write(api)

    print("== S2b: routes -> blueprints ==")
    for g in GROUP_ORDER:
        print(f"  routes/{g}.py : {counts[g]} routes")
    print(f"  TOTAL: {sum(counts.values())} routes")
    print(f"  dashboard_api.py: {api.count(chr(10))+1} lines (thin entrypoint)")


if __name__ == "__main__":
    main()
