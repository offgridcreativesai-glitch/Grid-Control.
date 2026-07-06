# Agent Upgrade Build — applying the repo studies to Grid Control's agents

Jun 23 2026. Purpose: the four repo studies (brain-map, Hermes, x1xhlol system-prompts,
Claude Fable 5) + scroll-cinematic were done to **upgrade Grid Control's agents**. This is the
build log. Done in one pass (no phased gating, per directive).

## Reference studies (saved)
- `docs/HERMES_AGENT_STUDY.md` — model-agnostic agent framework (routing, approval, delegation).
- `docs/AI_TOOLS_SYSTEM_PROMPTS_STUDY.md` — 33 tools' leaked prompts + tool schemas.
- Claude Fable 5 product prompt (CL4R1T4S) — Anthropic's own consumer prompt anatomy.
- `docs/SCROLL_CINEMATIC_STUDY.md` — Higgsfield 3D-scroll site skill.
- brain-map → shipped as the `/brainmap` tool (`scripts/brainmap/`).

## DONE — OPERATING FRAMEWORK rolled out to ALL agents
`agents/_lib/_agent_framework.py` — a lean (~370-token) shared operating contract distilled from
the studies: agent loop (analyze→plan→ground→deliver) + source-hierarchy/anti-fabrication
(`INSUFFICIENT DATA`) + notify-vs-ask (approval gate) + output discipline (schema-only) +
guardrails (brand_profile/Brand Guardian deference, never name internal infra, English only).

Maps to existing ground rules: Manus event-loop, our Zero-Assumption + Rule-10 provenance, the
approval gate, THE SECRET, terse-response. Class-1 pure-math agents get an empty block.

Wired into **both** agent systems:
- **14 Class-2 Python agents** (`agents/*.py`) — each prepends `operating_framework(2)` to its
  generation prompt: strategy, content_planner, script_writer, creative_director, data_analyst,
  funnel_specialist, trend_researcher, website_agent, brand_guardian, carousel_designer,
  email_marketing, community_manager, dm_customer_hunter, brand_book_v7.
  - Skipped (correct): trend_sentinel + performance_tracker (Class-1 pure math), reel_editor
    (ffmpeg, no Claude), cost_tracker (utility).
- **All 23 managed agents** (`managed_agents/`) — injected once in `session_runner.run_agent_session`
  (`full_prompt = operating_framework(2) + context + task_prompt`); the async path wraps it, so
  every managed-agent session is covered (includes the Tier-A adopted agents: sales strategists,
  pricing analyst, growth hacker, reality checker, executive summary generator).

All files byte-compile clean.

## ADDED — scroll-cinematic skill
Installed at `~/.claude/skills/scroll-cinematic/` (skill `scroll-cinematic`). For the Grid Control
landing (Atlas turntable scroll hero) + as the Higgsfield pipeline reference for the creative
engine rebuild. **Gated on Higgsfield MCP** connection (PRO plan).

## Follow-ups (documented — deliberately NOT done blind, they touch the live/deploy surface or external deps)
1. **Re-provision managed agents** so the framework is baked into each `agent_id` (durable) rather
   than runtime-injected. Runtime injection covers it functionally today; re-provisioning needs
   Agent SDK re-registration. Also fold framework text into `managed_agents/prompts/*.md` sources.
2. **Hermes infra** — write-approval *staging* (foreground-inline vs background-staged pending) and
   delegation leaf/orchestrator roles for CEO Brain orchestration. Touches the deployed approval
   system; do supervised with eval coverage.
3. **scroll-cinematic on the landing** — once Higgsfield MCP is connected.
4. **Tool-schema craft** (x1xhlol/Fable5) — absorbed into the framework's output discipline for
   now; revisit if/when agents expose real structured tools.

## Verify before relying in prod
Run an eval pass (`docs/EVAL_HARNESS.md`) on one Class-2 agent (e.g. script_writer) to confirm the
framework preamble improves grounding/concision without regressing output schema.
