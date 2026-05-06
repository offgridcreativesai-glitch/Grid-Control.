# Subagent Orchestration — OffGrid Patterns

Ported from ECC iterative retrieval guidance. Defines WHEN and HOW the main Claude session should delegate to sub-agents to keep context lean and outputs high quality.

## The context problem
Main-session context is the most expensive resource. Every file read, every tool call, every long stdout — they all stack into the working memory and don't get freed until `/compact`. Sub-agents return ONE summary message — main context stays ~unchanged regardless of how much they read internally.

## When to use a sub-agent (rule)

| Trigger | Agent type | Why |
|---|---|---|
| Need to read >3 files to answer one question | `Explore` | Search-and-extract, returns summary |
| Open-ended research across web/docs/code | `general-purpose` | Multi-tool investigation, returns brief |
| Architectural plan needed before implementation | `Plan` | Designs implementation, returns plan |
| Code review on a specific change | `code-reviewer` (engineering:code-review skill) | Independent review pass |
| Domain-specific task that has a matching agent | use that agent type | Specialized prompts + tools |

If the task fits a Skill (e.g. `deep-research`, `market-research`, `brand-voice`) — invoke the skill, not a generic agent.

## When NOT to use a sub-agent

- Single targeted Read or Bash command (cheaper inline)
- Task requires conversational back-and-forth with the user
- Task needs decisions only the main session has context to make (taste calls, brand calls, money calls)

## The iterative retrieval pattern

For complex multi-faceted research tasks:

1. **Decompose** the question into 2-4 narrower sub-questions main session can hand off
2. **Spawn** the right sub-agent type per sub-question (parallel where possible)
3. **Aggregate** the summaries — main session synthesizes, doesn't re-read sources
4. **Verify** by spot-reading 1-2 critical files yourself (don't trust blindly)
5. **Decide** based on the synthesized picture

Bad pattern: main session reads 20 files trying to figure out the codebase.
Good pattern: Explore agent reads the 20 files, returns "this is what's there" — main session reads only the 2 files it actually needs to modify.

## Applying to CEOBrain

CEOBrain is OffGrid's Python-side orchestrator. The pattern translation:

- **save_agent_output** runs Contradiction Detector after every save → that's a sub-agent pattern (delegated decision)
- **save_agent_output** can also delegate Brand Guardian audit → sub-agent for soul-check
- **Daily pipeline** runs Trend Researcher + Data Analyst in parallel → already implemented via threading

Future upgrade: add a `CEOBrain.dispatch_subtask(agent_name, payload)` helper that:
1. Logs the dispatch
2. Runs the sub-agent in background thread
3. Captures the summary into session_state
4. Returns a handle main flow can wait on

This is documented; not built yet. Build trigger: when CEOBrain's main flow needs to coordinate >3 agents in a single user-action turn.

## Token math (why this matters)

Main session reading 10 files × 500 lines avg = ~50K tokens stuck in context until `/compact`.
Sub-agent reading the same 10 files + returning 200-line summary = ~2K tokens in main context.

Savings: ~96% on that operation.

For OffGrid agents this rule already applies via `_provenance.build_source_index()` — which builds a flat lookup that costs ~5K tokens vs reading source JSONs at ~30K each.
