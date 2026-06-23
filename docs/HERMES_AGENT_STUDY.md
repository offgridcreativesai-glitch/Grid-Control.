# Hermes Agent — Deep Study (Jun 23 2026)

Source: https://github.com/NousResearch/hermes-agent (MIT). Studied: AGENTS.md (1371-line
architecture doc), the agent loop, provider abstraction, security/approval model, plugin system.

## What it is
A **model-agnostic personal-agent framework** by Nous Research — the **successor to OpenClaw**
(we run OpenClaw for community-manager + dm-hunter; Hermes ships `hermes claw migrate`). One
agent core across CLI, TUI, Electron desktop, and a **messaging gateway (~20 platforms:
Telegram/Discord/Slack/WhatsApp/Signal/Email…)**. ~17k tests / ~900 files. **It is NOT a model**
— the Nous "Hermes" LLM is one of 29 pluggable providers it can drive.

## The two design laws
1. **Per-conversation prompt caching is sacred.** Never mutate past context, swap toolsets, or
   rebuild the system prompt mid-conversation — it invalidates the cache and multiplies cost.
   Only exception: context compression. Slash commands that change state default to *deferred
   invalidation* (`--now` to opt in). → directly relevant to our cost-drain incident.
2. **Narrow waist, capability at the edges.** Every core tool ships on every API call. New
   capability climbs a **Footprint Ladder**: extend existing → CLI+skill → service-gated tool →
   plugin → MCP server → (last resort) core tool.

## Architecture
- `run_agent.py AIAgent` — ~12k-LOC synchronous tool-calling loop (OpenAI msg format,
  `handle_function_call`, interrupt checks, iteration + budget caps).
- **`providers/base.py ProviderProfile`** — *declarative* provider dataclass: auth, endpoints,
  vision, model catalog, per-provider request quirks, `api_mode`
  (`chat_completions`|`codex_responses`|anthropic…). 29 bundled providers (Anthropic, OpenAI,
  Bedrock, Gemini, OpenRouter, Ollama, DeepSeek, xAI, Nous…). Add one = a plugin calling
  `register_provider()`. **Cleanest multi-model-routing reference seen.**
- **`auxiliary_client`** — side-LLM lane; curator/vision/embeddings/title/session-search each
  pin their own cheap provider/model. Built-in cheap/expensive split.
- **Toolsets** (`toolsets.py`) — 30 toolsets, per-platform bundles, auto-discovered.
- **Extension model** — plugins with lifecycle hooks (`pre/post_tool_call`, `pre/post_llm_call`,
  session start/end); pluggable memory providers via `MemoryProvider` ABC (honcho/mem0/
  supermemory…); pluggable context engines + image-gen. Plugins may NOT touch core files.

## Subsystems
- **Skills + Curator** — self-improving loop: agent creates skills from experience; a background
  curator tracks per-skill usage and auto-archives stale *agent-created* skills (never deletes,
  pinned exempt, restorable). More mature version of our agent_learnings + skill loop.
- **Delegation** — `delegate_task` spawns isolated subagents; `leaf` vs `orchestrator` roles,
  depth/concurrency caps, `background=true` async completion queue.
- **Kanban** — durable SQLite multi-agent work queue: **board = hard isolation, tenant = soft
  namespace within a board**; dispatcher reclaims stale claims, auto-blocks after N failures.
  ≈ our `brands/{slug}/` isolation as a durable parallel queue.
- **Cron** — NL scheduled jobs; 3-min hard interrupt, catchup/grace windows, file-lock vs dup
  ticks, `skip_memory` default.
- **Approval/security** — `write_approval.py` gates memory/skill writes: foreground prompts
  inline; background-review writes **stage to a disk pending store** (`pending/{memory,skills}/
  <id>.json`) reviewed out-of-band (CLI/gateway/dashboard). Plus `tirith` pre-exec command
  scanning (homograph URLs, pipe-to-interpreter), `path_security`, `url_safety`, strict
  dependency-pinning policy (written after the litellm compromise + Shai-Hulud worm).

## Map to Grid Control pending items
| Our pending item | Mine from Hermes |
|---|---|
| Cost control / token drain | `auxiliary_client` cheap-lane + `smart_model_routing` + "caching is sacred" discipline |
| Multi-model routing (LiteLLM tier) | `providers/base.py ProviderProfile` (declarative, 29 providers) |
| #6 Subagent orchestration upgrade | `delegate_task` leaf/orchestrator + async completion queue |
| #7 Parallelization | delegation batch `max_concurrent_children` |
| #8 AgentShield security scan | `tirith` pre-exec scan + `path/url_safety` + dep-pinning policy |
| Approval gate hardening | `write_approval` foreground-inline vs background-staged-pending |
| Notifications / chat console | the gateway (Telegram/WhatsApp into The Brain) |

## Verdict
- It's a **framework/harness, not a model** — settle that first.
- **Do NOT replatform Grid Control onto it** — it's single-user/personal-assistant shaped; our
  value (18 roles, multi-brand isolation, human-gated marketing OS, The Brain) isn't what it does.
- **Do** treat it as a **reference codebase** for the mapped items; consider migrating the 2
  OpenClaw agents onto it before OpenClaw rots.
- If the goal stays **cheaper inference**: cheap model behind a router for low-stakes agents —
  `ProviderProfile` + `auxiliary_client` are exactly how to wire it.

Clone studied at `/tmp/hermes-agent` (ephemeral).
