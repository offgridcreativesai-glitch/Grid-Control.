# Second Brain — Answer + What Was Built (Fable 5 review, Jul 3 2026)

## The question (brief §7)
Should GC's 18 agents have an Obsidian-style persistent, linked knowledge system —
beyond per-brand `brand_memory/` JSON and the Supabase `brand_memory` /
`grid_control_memory_vec` tables?

## The honest answer: yes to LINKING, no to another STORE

GC does not have a memory shortage. It has a memory **fragmentation** problem.
Today one brand's knowledge is spread across **five disconnected stores**:

| Store | Where | Written by | Readable by humans? | Linked? |
|---|---|---|---|---|
| KV memory | Supabase `brand_memory` | `BaseAgent.remember()` | No (DB rows) | No |
| Semantic memory | Supabase `brand_memory_vec` (Voyage 512-dim pgvector) | `semantic_remember()` | No | No |
| Narrative | Supabase `brand_narrative` | `narrative_append()` | No | No |
| Learnings | `brands/{slug}/agent_learnings.jsonl` | `session_end()` | Barely (JSONL) | No |
| Skills | `brands/{slug}/skills/{agent}/*.md` | approval/rejection hooks | Yes | No |

No store references another. No agent (or Gaurav) can traverse
*"this hook won → because this audience insight → which came from this scrape"*.
A sixth store would make that worse. The Obsidian idea's actual value is the
**graph** — notes that cite sources and link to each other — not the app.

`graphify-out/obsidian/` proves the pattern works but is a vault of the
**codebase**, for developers. The agents need the same pattern over
**brand knowledge**, per brand, isolated.

## What was built (working, tested)

**`agents/_lib/second_brain.py`** — per-brand linked-markdown vault at
`brands/{slug}/second_brain/`:

- `note(agent, title, body, kind, source, links)` — one fact per file, YAML
  frontmatter, `[[wikilinks]]`. **Sourceless insights are refused** (zero-fabrication:
  every note must name the run/file/scrape that grounds it; only `kind=decision`
  — human decisions — may be sourceless).
- `sync()` — renders the five existing stores into linked notes. Idempotent,
  no LLM, **zero API cost**. brand_profile + brand_archetype become root nodes;
  learnings/skills/narrative link back to them. Supabase-backed stores sync
  best-effort (silent skip offline).
- `context_block(agent, query, budget_chars)` — ONE call that replaces juggling
  five recall APIs: keyword-ranks the index, pulls best notes + their 1-hop
  linked notes, returns a prompt-ready block under a char budget. Free, offline.
- **BaseAgent glue**: `brain()`, `brain_note()`, `brain_context()`;
  `session_start()` now auto-loads the brain block into session context and
  `session_end()` auto-syncs the vault. Existing agents get it with no code change.

Vector recall (`_mem0_client.py`) stays — it's the fuzzy-recall complement,
not a competitor. The vault is the canonical, inspectable layer; pgvector is
an index over it.

Tests: `tests/test_second_brain.py` (5 tests — write/index, sourceless refusal,
sync rendering, link traversal, per-brand isolation). All pass.

## Why file-first (and not Supabase-first)

1. **Human-inspectable + git-diffable** — the approval-gate philosophy extended
   to memory. Gaurav can open the vault in Obsidian directly.
2. **Approval-compatible** — a note is a file; review/edit/delete like any
   brand-memory file. Supabase rows are invisible until queried.
3. **Offline-safe** — agents keep their memory when Supabase/Voyage keys are
   absent (the current stores silently no-op in that case).
4. **Invariant 3 (isolation) is structural** — the vault lives under
   `brands/{slug}/`, same as everything else.

## What NOT to do

- Don't buy a memory SaaS (Mem0 cloud, Zep, LangMem) — GC's moat is that brand
  memory is the client's owned artifact; shipping it to a third party weakens
  the pitch and adds a per-seat cost.
- Don't LLM-summarize on sync — sync must stay free or it becomes another
  cost-drain scheduler incident (Jun 15-16 pattern).
- Don't let agents write unlimited notes — `sync()` caps learnings at last 50;
  a future pruning pass (monthly program) should merge/retire stale notes.

## Follow-ups (not blocking)
1. Wire `brain_context()` into the 4 content agents' prompts (they currently get
   it via session_start; direct prompt injection like the archetype block is a
   1-line change each).
2. Add a `second_brain/` browser to the Memory page in the dashboard (it already
   renders memory docs; point it at INDEX.md).
3. Monthly prune/merge pass as part of run_monthly_program (pure-math class,
   no LLM: retire notes whose source files no longer exist).
