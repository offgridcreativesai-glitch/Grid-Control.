#!/usr/bin/env python3
"""brain-map (OffGrid fork) — markdown folder -> interactive knowledge graph.

Based on zubair-trabzada/brain-map (MIT). Adds a third grouping mode, --by-type,
which colors/groups nodes by our memory frontmatter `type:` (user / feedback /
project / reference) instead of by folder. Auto-enabled when the vault has a
MEMORY.md index (our second-brain layout). Falls back to the upstream AIOS and
generic modes otherwise.

Usage:
    python3 build.py --vault <dir> [--by-type] [--out DIR]

Zero dependencies (Python 3 stdlib only).
"""
import os, re, json, argparse, shutil, sys, time

PKG = os.path.dirname(os.path.abspath(__file__))
SKIP_DIRS = {".git", ".obsidian", "node_modules", ".brain-map", "__pycache__",
             ".venv", "venv", "dist", "build", ".next", ".cache"}

# upstream AIOS group styles (CLAUDE.md + wiki/ vaults)
AIOS_GROUPS = {
    "router":   {"c": "#34d399", "r": 11,  "glow": 30, "name": "Router",   "pace": 0,   "pause": 0,   "major": True},
    "core":     {"c": "#e7e5e4", "r": 7,   "glow": 16, "name": "Wiki",     "pace": 480, "pause": 900, "major": True},
    "concept":  {"c": "#fbbf24", "r": 7.5, "glow": 20, "name": "Concepts", "pace": 230, "pause": 700, "major": True},
    "hub":      {"c": "#a78bfa", "r": 7,   "glow": 18, "name": "Suites",   "pace": 270, "pause": 800, "major": True, "cluster": True},
    "skill":    {"c": "#60a5fa", "r": 3.2, "glow": 0,  "name": "Skills",   "pace": 16,  "pause": 500, "major": False},
    "tool":     {"c": "#f472b6", "r": 5.5, "glow": 12, "name": "Tools",    "pace": 150, "pause": 700, "major": True},
    "world":    {"c": "#fb923c", "r": 5.5, "glow": 12, "name": "Worlds",   "pace": 150, "pause": 400, "major": True},
    "note":     {"c": "#34d399", "r": 5.5, "glow": 12, "name": "Notes",    "pace": 220, "pause": 400, "major": True},
    "external": {"c": "#3e4c63", "r": 2.1, "glow": 0,  "name": "Files",    "pace": 5,   "pause": 600, "major": False},
}
# OffGrid memory-type group styles (--by-type)
TYPE_GROUPS = {
    "router":    {"c": "#e7e5e4", "r": 12,  "glow": 34, "name": "Index (MEMORY.md)", "pace": 0,   "pause": 0,   "major": True},
    "user":      {"c": "#60a5fa", "r": 8,   "glow": 22, "name": "You",         "pace": 240, "pause": 800, "major": True},
    "project":   {"c": "#34d399", "r": 7.5, "glow": 20, "name": "Projects",    "pace": 200, "pause": 700, "major": True},
    "feedback":  {"c": "#f472b6", "r": 7.5, "glow": 20, "name": "Feedback",    "pace": 200, "pause": 700, "major": True},
    "reference": {"c": "#a78bfa", "r": 6.5, "glow": 16, "name": "Reference",   "pace": 230, "pause": 600, "major": True},
    "note":      {"c": "#94a3b8", "r": 5,   "glow": 0,  "name": "Untyped",     "pace": 120, "pause": 400, "major": False},
}
PALETTE = ["#60a5fa", "#fbbf24", "#f472b6", "#a78bfa", "#fb923c", "#22d3ee",
           "#f87171", "#4ade80", "#e879f9", "#facc15", "#94a3b8", "#2dd4bf"]

WIKILINK = re.compile(r"\[\[([^\]|#]+)(?:[|#][^\]]*)?\]\]")
MDLINK = re.compile(r"\]\(([^)#\s]+\.md)\)")
# matches `type: project` and `  type: feedback` but NOT `node_type: memory`
TYPE_RE = re.compile(r"^\s*type:\s*([A-Za-z]+)", re.M)


def collect_md(vault):
    files = []
    for root, dirs, names in os.walk(vault):
        dirs[:] = [d for d in dirs if d not in SKIP_DIRS and not d.startswith(".")]
        for n in names:
            if n.endswith(".md"):
                files.append(os.path.join(root, n))
    return files


def preview_of(path):
    return ""  # note previews are a Brain Studio (paid) feature

def label_of(rel):
    stem = os.path.splitext(os.path.basename(rel))[0]
    if stem in ("SKILL", "README", "INDEX", "index"):
        parent = os.path.basename(os.path.dirname(rel))
        return parent or stem
    return stem


def group_aios(rel):
    if rel == "CLAUDE.md":
        return "router"
    if rel.startswith("wiki/concepts/"):
        return "concept"
    if rel.startswith("wiki/skills/") and rel.count("/") == 2:
        return "hub"
    if rel.startswith("wiki/skills/"):
        return "skill"
    if rel.startswith("wiki/tools/"):
        return "tool"
    if rel.startswith("wiki/worlds/"):
        return "world"
    if rel.startswith(("wiki/", "cadence/")):
        return "core"
    if rel.startswith(("projects/", "brainstorm/")):
        return "note"
    if os.sep not in rel and "/" not in rel:
        return "note"
    return "external"


def group_by_type(path, rel):
    """Group a memory file by its frontmatter `type:`. MEMORY.md is the router hub."""
    if os.path.basename(rel) == "MEMORY.md":
        return "router"
    try:
        head = open(path, encoding="utf-8", errors="ignore").read(1200)
    except OSError:
        return "note"
    m = TYPE_RE.search(head)
    if m:
        t = m.group(1).lower()
        if t in ("user", "feedback", "project", "reference"):
            return t
    # context packages are project memories even when the type line is missing
    if rel.replace(os.sep, "/").startswith("context_packages/"):
        return "project"
    return "note"


def build(vault, out, by_type_flag):
    vault = os.path.abspath(os.path.expanduser(vault))
    if not os.path.isdir(vault):
        sys.exit(f"vault not found: {vault}")
    aios = os.path.exists(os.path.join(vault, "CLAUDE.md")) and os.path.isdir(os.path.join(vault, "wiki"))
    by_type = (not aios) and (by_type_flag or os.path.exists(os.path.join(vault, "MEMORY.md")))
    files = collect_md(vault)
    if not files:
        sys.exit("no markdown files found in that folder")
    rels = {f: os.path.relpath(f, vault) for f in files}

    groups = {}
    node_group = {}
    if aios:
        groups = {k: dict(v) for k, v in AIOS_GROUPS.items()}
        for f in files:
            node_group[rels[f]] = group_aios(rels[f])
    elif by_type:
        groups = {k: dict(v) for k, v in TYPE_GROUPS.items()}
        for f in files:
            node_group[rels[f]] = group_by_type(f, rels[f])
    else:
        tops = {}
        for f in files:
            rel = rels[f]
            top = rel.split(os.sep)[0] if os.sep in rel else "_root"
            tops.setdefault(top, []).append(rel)
        groups["router"] = dict(AIOS_GROUPS["router"])
        ordered_tops = sorted(tops.items(), key=lambda kv: len(kv[1]))
        for i, (top, members) in enumerate(ordered_tops):
            key = "root" if top == "_root" else top
            big = len(members) > 60
            groups[key] = {
                "c": PALETTE[i % len(PALETTE)], "r": 3.5 if big else 6,
                "glow": 0 if big else 14, "name": "Loose notes" if key == "root" else top,
                "pace": max(8, min(400, 2200 // max(1, len(members)))),
                "pause": 450, "major": not big,
            }
            for rel in members:
                node_group[rel] = key
        for f in files:
            if rels[f] == "CLAUDE.md":
                node_group["CLAUDE.md"] = "router"

    # generic vaults get a structural tree so link-free folders still render
    # connected. AIOS and by-type vaults are already link-connected, so skip it.
    tree_links = set()
    if not aios and not by_type:
        root_id = "__vault__"
        node_group[root_id] = "router"
        groups["router"]["name"] = os.path.basename(vault) or "Vault"
        for f in files:
            rel = rels[f]
            top = rel.split(os.sep)[0] if os.sep in rel else None
            if top:
                did = "__dir__" + top
                if did not in node_group:
                    key = node_group.get(rel, "root")
                    node_group[did] = key
                    groups[key]["cluster"] = True
                    tree_links.add((root_id, did))
                tree_links.add((did, rel))
            else:
                tree_links.add((root_id, rel))

    # links
    stem_map = {}
    for f in files:
        stem_map.setdefault(os.path.splitext(os.path.basename(f))[0].lower(), rels[f])
    nodes, links, ext = {}, set(tree_links), {}
    if not aios and not by_type:
        for nid, grp in node_group.items():
            if nid.startswith("__"):
                nodes[nid] = grp
    for f in files:
        rel = rels[f]
        nodes[rel] = node_group.get(rel, "note")
        try:
            text = open(f, encoding="utf-8", errors="ignore").read()
        except OSError:
            continue
        for m in WIKILINK.finditer(text):
            tgt = stem_map.get(m.group(1).strip().lower())
            if tgt and tgt != rel:
                links.add((rel, tgt))
        for m in MDLINK.finditer(text):
            raw = m.group(1)
            if raw.startswith(("http:", "https:")):
                continue
            tgt_abs = os.path.normpath(os.path.join(os.path.dirname(f), raw))
            if not os.path.exists(tgt_abs):
                continue
            try:
                tgt_rel = os.path.relpath(tgt_abs, vault)
            except ValueError:
                continue
            if tgt_rel.startswith(".."):
                continue
            if tgt_rel in nodes or tgt_rel in rels.values():
                if tgt_rel != rel:
                    links.add((rel, tgt_rel))
            else:
                ext[tgt_rel] = "external"
                links.add((rel, tgt_rel))
    if ext and "external" not in groups:
        groups["external"] = dict(AIOS_GROUPS["external"])
    nodes.update(ext)

    # drop isolated nodes (link-connected modes only)
    if aios or by_type:
        degree = {}
        for a, b in links:
            degree[a] = degree.get(a, 0) + 1
            degree[b] = degree.get(b, 0) + 1
        nodes = {rel: g for rel, g in nodes.items() if degree.get(rel)}

    group_order = {g: i for i, g in enumerate(groups)}
    def sort_key(item):
        rel, grp = item
        sub = os.path.dirname(rel)
        return (0 if grp == "router" else group_order.get(grp, 99) + 1, sub, rel)
    ordered = sorted(nodes.items(), key=sort_key)
    index = {rel: i for i, (rel, _) in enumerate(ordered)}
    def node_label(rel):
        if rel == "__vault__":
            return os.path.basename(vault) or "Vault"
        if rel.startswith("__dir__"):
            return rel[7:]
        return label_of(rel)
    out_nodes = [{"id": rel, "label": node_label(rel), "g": grp,
                  "p": "" if rel.startswith("__") else preview_of(os.path.join(vault, rel))}
                 for rel, grp in ordered]
    out_links = [{"s": index[a], "t": index[b]} for a, b in sorted(links) if a in index and b in index]

    brand = {"name": "BRAIN MAP", "logo": False}

    os.makedirs(out, exist_ok=True)
    stamp = int(time.time())
    html = open(os.path.join(PKG, "index.html"), encoding="utf-8").read()
    html = re.sub(r"graph-data\.js(\?v=\d+)?", f"graph-data.js?v={stamp}", html)
    open(os.path.join(out, "index.html"), "w", encoding="utf-8").write(html)
    with open(os.path.join(out, "graph-data.js"), "w") as f:
        f.write("const GRAPH = ")
        json.dump({"brand": brand, "groups": groups, "nodes": out_nodes, "links": out_links}, f)
        f.write(";\n")
    with open(os.path.join(out, "serve.py"), "w") as f:
        f.write("import http.server, os, webbrowser\n"
                "os.chdir(os.path.dirname(os.path.abspath(__file__)))\n"
                "try:\n"
                "    srv = http.server.HTTPServer(('127.0.0.1', 4710), http.server.SimpleHTTPRequestHandler)\n"
                "except OSError:\n"
                "    srv = http.server.HTTPServer(('127.0.0.1', 0), http.server.SimpleHTTPRequestHandler)\n"
                "port = srv.server_address[1]\n"
                "print(f'brain-map -> http://localhost:{port}', flush=True)\n"
                "webbrowser.open(f'http://localhost:{port}')\n"
                "srv.serve_forever()\n")
    mode = "AIOS layout" if aios else ("memory type grouping" if by_type else "generic folder grouping")
    print(f"✓ {len(out_nodes)} notes · {len(out_links)} links · {mode}")
    print(f"✓ output: {out}")
    print(f"→ run:  python3 '{os.path.join(out, 'serve.py')}'")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--vault", required=True)
    ap.add_argument("--out", default=None)
    ap.add_argument("--by-type", action="store_true", help="force grouping by memory frontmatter type")
    a = ap.parse_args()
    out = a.out or os.path.join(os.path.expanduser(a.vault), ".brain-map")
    build(a.vault, out, a.by_type)
