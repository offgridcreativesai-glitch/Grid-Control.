---
name: brainmap
description: Regenerate and open the interactive brain-map of our knowledge — the memory second-brain vault rendered as a living, type-grouped force graph. Use when the user types /brainmap or asks to see/refresh the brain map, memory graph, knowledge graph of our memories, or "show me the brain".
---

# brain-map — interactive memory graph

Turns the memory second-brain vault into an interactive knowledge graph (force-directed,
grows node-by-node, click to isolate connections). Grouped/colored by memory `type:`
(Index / Projects / Feedback / Reference). Complements graphify (which builds/queries the
repo graph) — this is the live visual lens on the memory vault.

OffGrid fork of zubair-trabzada/brain-map (MIT). Zero deps (Python stdlib + d3 from CDN).

## When invoked

Run the one-liner — it rebuilds from the current state of memory (~1s) and opens the browser:

```bash
./scripts/brainmap/brainmap.sh
```

Default vault is the memory dir:
`/Users/gauravoffgrid/.claude/projects/-Users-gauravoffgrid-offgrid-marketing-os/memory`

To map a different markdown folder, pass it as an arg:
```bash
./scripts/brainmap/brainmap.sh /path/to/folder
```

The server runs in the foreground (it IS the process) at http://localhost:4710 — tell the
user to Ctrl+C the terminal to stop. Re-run anytime memory grows.

## Controls (tell the user)
- Plays a growth animation on load — press **R** to replay.
- **Drag** empty space to pan, **scroll** to zoom, **click** a node to light its connections
  (Esc / click again to release), **search** box flies the camera to a note.
- Legend top-right: colors = memory types.

## If you need a static screenshot instead of the live server
Headless Chrome can't run the timed growth animation, so build, then render the pre-settled
copy the wrapper does NOT create by default. Generate `index_shot.html` (activate all nodes +
pre-tick the sim + fit camera) in the output `.brain-map/` dir and screenshot that with
`--virtual-time-budget`. See git history of scripts/brainmap for the settle snippet.

## How grouping works
`scripts/brainmap/build.py` reads each file's frontmatter `type:` (user/feedback/project/
reference); `MEMORY.md` is the central Index hub; untyped files under `context_packages/`
default to project. Auto-enabled by `--by-type` when the vault has a `MEMORY.md`.
