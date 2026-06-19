# Agent ↔ LLM Model-Fit Research (Jun 17 2026)

> RESEARCH ONLY — no implementation. Goal: per agent, find the best-fit LLM across ALL providers
> (not Anthropic-only), compare to our current model (`agents/_lib/model_gateway.py`), and flag the
> GAPS where another model fits better. We "build the gap" later, after confirming with eval-harness.
> Gaurav is running a parallel research pass; diff against this.

## Current routing (source of truth: model_gateway.py)
- Opus (`claude-opus-4-8`): ceo-brain, strategy-agent, script-writer, creative-director, ad-strategist, brand-guardian, brand-book
- Sonnet (`claude-sonnet-4-6`, the "floor"): content-planner, carousel-designer, data-analyst, funnel-specialist, trend-researcher, website-agent, seo-aeo-agent, email-marketing-agent, community-manager, dm-customer-hunter
- None (pure-math): trend-sentinel, performance-tracker, cost-tracker, contradiction-detector
- Unassigned (new): AI-setter (propose Sonnet→ likely cheaper tier), reel-editor (deterministic)
- Policy (Jun 9): Anthropic-only, Sonnet = floor, NO Haiku/Ollama (chosen for consistency). ← this research reopens it.

## Findings by cluster (current → research-best → verdict)
| Cluster / agents | Current | Research best-fit | Verdict |
|---|---|---|---|
| Reasoning/decisions: ceo-brain, strategy, brand-guardian, brand-book | Opus | Claude Opus ≈ GPT-5.5 ≈ Gemini 3 Pro (no clear winner; Claude strong on multi-tool orchestration + reasoning chains, writing quality) | FIT — keep Opus |
| Long-form / brand-voice copy: email, briefs | Sonnet/Opus | Claude (least AI-sounding, best brand-voice adherence) | FIT — keep Claude |
| Hooks / short-form ad copy: script-writer | Opus | GPT-5.4 leads direct-response (headlines/CTAs, AIDA/PAS); Claude wins brand-voice/long-form | GAP — A/B GPT-5.4 for hooks specifically |
| High-volume conversational: community-manager, dm-hunter, AI-setter | Sonnet | Haiku 4.5 ($0.25/$1.25) / Gemini 2.5 Flash ($0.30/$2.50) / GPT-5 Mini ($0.75/$4.50) — 5–12× cheaper, acceptable quality | BIGGEST GAP — Sonnet overkill; reopen no-Haiku floor here |
| Vision / image understanding: carousel-designer, creative-director | Sonnet/Opus | Gemini 3 Flash leads vision (79 MMMU-Pro); GPT-5 strong; Claude behind on pure vision | GAP — Gemini for visual-analysis steps |
| Big-context research: data-analyst, trend-researcher, seo-aeo | Sonnet | Gemini 3 Pro (cost-efficient frontier) / Claude (long-context reasoning) / Llama 4 Scout (10M ctx) | minor — Sonnet fine; Gemini if cost bites |
| Pure-math: trend-sentinel, performance-tracker, cost-tracker, contradiction-detector | none | — | no LLM, no gap |

## The headline gap
Our "Sonnet-floor / no-Haiku" rule makes us pay Sonnet prices for high-volume grunt (comment & DM
drafting, AI Setter's hundreds of convos). Cheaper tiers (Haiku 4.5 / Gemini Flash / GPT-5 Mini) do
that at a fraction of cost. Biggest cost lever; ties to the Jun 15-16 cost-control incident. LiteLLM
gateway already supports per-agent provider routing → policy change, not a rebuild.

## Caveats
- Model versions in the wild are noisy (Claude 4.5/4.7/4.8, GPT-5.4/5.5, Gemini 3 Pro/Flash). The durable
  signal = **which provider/tier wins each task-type**, not the exact number.
- Multi-provider adds: extra API keys, per-provider cost tracking, output-consistency testing. Confirm any
  switch with a quick eval-harness run BEFORE building the gap.

## GitHub repos to mine for expertise (pair with per-agent search terms)
- github.com/ARUNAGIRINATHAN-K/awesome-ai-agents-2026 — 300+ agents/frameworks + benchmarks
- github.com/jmedia65/awesome-ai-marketing — marketing tools+prompts by function
- github.com/AICMO/AiCMO-Marketing-Prompt-Collection — autonomous-marketing-dept prompts/playbooks (closest)
- github.com/MaxsPrompts/Marketing-Prompts — 546 skills / 4368 prompts
- github.com/0xeb/TheBigPromptLibrary — system prompts across Claude/GPT/Gemini
- github.com/promptslab/Awesome-Prompt-Engineering ; github.com/danielrosehill/awesome-llm-prompt-libraries
- GitHub topic `ai-marketing`: a "150 skills / 25 agents / 12-part strategy / 6-platform AEO-GEO" plugin — chase it.

## Sources
Vellum & clickrank LLM leaderboards 2026 · adlibrary copywriting 2026 · cometapi/tokenmix/devtk pricing 2026 ·
whatllm agentic + vision Jan 2026 · azumo/zapier June 2026 rankings.
