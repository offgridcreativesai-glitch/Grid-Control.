# Graphify vs Obsidian for Grid Control — Research Report

*Generated: 2026-06-06 | Sources: 12 web + local skill inspection | Confidence: High*

## Executive Summary

Graphify and Obsidian are **not competitors** — they solve different problems. Graphify turns **code** into a queryable AST knowledge graph (understand structure, trace dependencies). Obsidian is a **markdown knowledge/memory layer** for humans and AI agents (notes, decisions, cross-linked memory). The honest finding: for Grid Control's actual pain point — *consistent cross-session memory and agent-readable knowledge* — Obsidian (via its free Local REST API MCP) is the better fit. Graphify is the right *category* of tool for code understanding but is currently **unused dead weight** because nobody queries it and it goes stale. Critically, **graphify can export directly into an Obsidian vault** — so this isn't strictly either/or.

---

## 1. What Each Tool Actually Does

### Graphify (the tool we already have)
- AST-based code knowledge graph: nodes = files/functions/modules, edges = calls/imports/relationships ([graphify SKILL.md, local](~/.claude/skills/graphify/SKILL.md))
- Commands: `query` (BFS context), `path` (shortest path between two concepts), `explain` (plain-language node summary)
- Community detection (clusters related code), "god nodes" (high-connectivity hubs), honest audit trail (EXTRACTED/INFERRED/AMBIGUOUS)
- Outputs: interactive HTML, GraphRAG JSON, `GRAPH_REPORT.md`, plus exports to Neo4j / GraphML / SVG
- **Has an MCP server mode** (`--mcp`) for agent access, and `--watch` mode that rebuilds on code change with no LLM cost
- **Can write directly to an Obsidian vault** (`--obsidian --obsidian-dir`)

### Obsidian + plugin ecosystem
- Plain markdown vault, local-first, Git-friendly ([Obsidian dev docs](https://docs.obsidian.md/Home))
- **Local REST API & MCP plugin** ([coddingtonbear/obsidian-local-rest-api](https://github.com/coddingtonbear/obsidian-local-rest-api)) — ships a **built-in MCP server** at `https://127.0.0.1:27124/mcp/`. Full CRUD on notes, surgical section patching (target a heading/block/frontmatter key), full-text + JsonLogic structured search. This is the key bridge for agents.
- **Dataview** ([blacksmithgu/obsidian-dataview](https://github.com/blacksmithgu/obsidian-dataview)) — query notes' *metadata* like a database (DQL + JS API). **Limitation: cannot query note *contents***, only frontmatter/tags/metadata ([Dataview docs](https://blacksmithgu.github.io/obsidian-dataview/))
- **Smart Connections** ([brianpetro/obsidian-smart-connections](https://github.com/brianpetro/obsidian-smart-connections)) — local embeddings, semantic "related notes" + chat-with-vault (RAG). **Now $20/month** (was free) ([Code Culture comparison](https://codeculture.store/blogs/developer-culture/obsidian-ai-plugin-comparison-2025)). No official MCP server; community bridges have varying maintenance ([3sztof blog](https://3sztof.github.io/posts/obsidian-smart-connections-mcp/))
- Supporting plugins: Templater (dynamic note generation), obsidian-git (auto Git backup/sync), Tasks, Kanban, QuickAdd, Calendar, Linter (auto-format frontmatter on save), Excalidraw (diagrams)

---

## 2. Mapping to Grid Control's Three Jobs

### (a) For the AI agents themselves
- Agents already emit human-readable markdown (output_formatter → Notion, pending_approval files). An Obsidian vault is a natural home: agents write notes, link them, query each other's outputs.
- The **Local REST API MCP** lets any agent read/write/patch the vault over a clean tool interface — better than ad-hoc file writes.
- Graphify gives agents code-structure answers ("what writes `trends_live.json`?") via its MCP mode — but agents rarely need to understand *code*; they need to understand *brand state, past outputs, decisions*. That's Obsidian's domain.
- **Winner for agents: Obsidian** (knowledge/memory), with graphify only if agents need to reason about the codebase itself (rare).

### (b) For Grid Control codebase/structure management
- This is graphify's home turf: AST graph, dependency tracing, community detection across 18 agents + Flask + React.
- BUT: the codebase is mid-sized and already well-documented (CLAUDE.md + docs/). The graph's value scales with codebase complexity and *actual query usage*. Today it's neither large enough nor queried enough to earn its keep.
- **Winner for codebase: Graphify in principle, unused in practice.**

### (c) For Claude Code (me) maintaining cross-session memory
- My current memory is already file-based: `~/.claude/projects/.../memory/` + MEMORY.md index + context packages (the GRIDLOCK-* files). This works and is what we actually use.
- Obsidian would *upgrade* this: same markdown files, but with backlinks, graph view, Dataview dashboards over frontmatter, and (optionally) semantic recall. The memory files already use `[[wikilink]]` syntax — **they are already Obsidian-compatible.**
- Graphify helps me understand *code* on cold start, but grep + CLAUDE.md already does that faster for a codebase this size.
- **Winner for my memory: Obsidian** (it's a strict upgrade to the memory system we already run).

---

## 3. The Cost & Maintenance Reality

| Option | Cost | Maintenance burden |
|--------|------|-------------------|
| Graphify (as-is) | $0 (AST, no API) | "Update after every change" rule — **never followed → stale** |
| Obsidian app | $0 (personal use) | Low — it's just markdown |
| Local REST API MCP | $0 | One-time setup, runs in Obsidian |
| Dataview / Templater / Git / Tasks | $0 (open source) | Low |
| Smart Connections | **$20/mo** | Medium; no official MCP |

Key point: the **Obsidian Local REST API MCP is free and official-grade**. You do NOT need the $20/mo Smart Connections to get agent read/write + structured search. Semantic search is a later nice-to-have, and even then a free community embedding MCP or our own Anthropic embeddings could substitute.

---

## 4. The Insight That Resolves the Either/Or

**Graphify exports to Obsidian.** (`graphify --obsidian`). So the optimal architecture isn't "pick one":

```
CODE  → graphify (on-demand, when onboarding/refactoring) → exports nodes into →
                                                                                  ⤵
KNOWLEDGE/MEMORY/BRAND STATE → Obsidian vault ← agents read/write via Local REST API MCP
                                              ← Claude Code (me) reads/writes memory + context packages
                                              ← Gaurav reads/edits in the Obsidian app
```

Obsidian becomes the **single shared surface** for me, the agents, and you. Graphify becomes an **on-demand code-mapping tool** that can dump into that surface when needed — not a daemon we pretend to maintain.

---

## Key Takeaways

1. **They're complementary, not rivals.** Graphify = code structure. Obsidian = knowledge/memory.
2. **Obsidian is the higher-value investment for Grid Control** because the real need is shared, human+agent-readable memory — and our memory files are already markdown with `[[wikilinks]]`.
3. **Use the free Local REST API MCP, skip the $20/mo Smart Connections** until semantic recall is proven necessary.
4. **Graphify should be demoted** from "always-on, update-every-change" to "on-demand code map." Drop the rule I never follow; run it when actually onboarding to or refactoring the codebase.
5. **Don't over-commit:** adopting Obsidian is meaningful setup. It earns its place only if you (and the agents) actually open and write to the vault. If it'd sit unused like graphify did, the file-based memory we already have is fine.

---

## Sources
1. [coddingtonbear/obsidian-local-rest-api](https://github.com/coddingtonbear/obsidian-local-rest-api) — official REST API + built-in MCP server for vaults
2. [Obsidian MCP Server (MarkusPfundstein)](https://mcpservers.org/servers/MarkusPfundstein/mcp-obsidian) — community MCP, list/read/search/patch tools
3. [ToKiDoO/mcp-obsidian-advanced](https://github.com/ToKiDoO/mcp-obsidian-advanced) — structure/link-aware MCP for agents
4. [blacksmithgu/obsidian-dataview](https://github.com/blacksmithgu/obsidian-dataview) + [docs](https://blacksmithgu.github.io/obsidian-dataview/) — metadata query engine; cannot query note contents
5. [brianpetro/obsidian-smart-connections](https://github.com/brianpetro/obsidian-smart-connections) — local-embedding semantic search + chat
6. [Code Culture: Obsidian AI plugin comparison 2025](https://codeculture.store/blogs/developer-culture/obsidian-ai-plugin-comparison-2025) — Smart Connections $20/mo; Claude Code = cheapest/most control
7. [3sztof: Obsidian + AI full agent integration](https://3sztof.github.io/posts/obsidian-smart-connections-mcp/) — 3-tier agent memory architecture; semantic MCP fragmentation
8. [Code Culture: Karpathy's Obsidian + Codex setup](https://codeculture.store/blogs/developer-culture/andrej-karpathy-obsidian-codex-setup) — code-aware tool indexing an Obsidian vault
9. [Obsidian Developer Docs](https://docs.obsidian.md/Home) — markdown, local-first, Git-friendly
10. graphify SKILL.md (local) — AST graph, query/path/explain, MCP mode, `--obsidian` export, `--watch`

## Methodology
4 web searches across MCP/AI-plugin/developer-KB angles + 2 full-source deep reads + local inspection of the graphify skill and our existing memory system. Sub-questions: what each tool does; how Obsidian serves agents/code/my-memory; cost & maintenance; whether they combine.
