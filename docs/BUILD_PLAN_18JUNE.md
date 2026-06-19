# GRID CONTROL — Build Plan (Jun 18 2026)

> Safe word: **GRIDLOCK-RESUME-18JUNE**. Supersedes [GRIDLOCK-RESUME-16JUN].
> Master sequence (Gaurav, unchanged): **Backend → Frontend → Stitch → Test brand → Launch.**
> This plan finishes step 1 (backend) and merges the Jun 16 remainder with the Jun 18 repo-research adopts.

## 0 · Why this exists

After the Jun 18 deep-fetch of ~71 repos (Section C of `REPO_RESEARCH_INDEX.md`), two pieces of system-level infrastructure showed up that fundamentally improve memory and observability/cost for the 18 GRID agents: **Mem0** (3-scope memory) and **Langfuse** (obs + cost + eval). These touch every agent — so they go FIRST, before per-agent expertise packs land on the new substrate. One painful migration, then 25 expertise packs. **caveman** is separate — it's a Claude-Code-session ergonomics skill (cuts MY chat tokens with Gaurav), NOT a production-cost lever for the 18 agents. It rides along as a low-risk dev-ergonomics install.

Picsart Agents was reviewed Jun 18; it's image-editing-only, validates our approval gate, and adds **one** backlog item: WhatsApp/Telegram as future CoS channels (post-launch). No structural change to this plan.

## 1 · Phase 1 — Foundation upgrades (1–2 days · $0)

These touch every agent; do them first.

| # | Item | What it does | Source |
|---|---|---|---|
| 1a | **Wire Mem0 as 3-scope memory backbone** | Brand / Personal / Account scopes; migrate scattered files (`brand_profile.json`, `voice_profile.json`, `performance_history.json`, `agent_learnings.jsonl`) | `mem0ai/mem0` |
| 1b | **Wire Langfuse (self-hosted)** | Traces + per-agent cost + LLM-as-judge eval; retire hand-built `cost_reporter` and most of the eval harness — gives REAL cost data before Phase 4 policy change so we can measure the win | `langfuse/langfuse` |
| 1c | **Fix rate_limit decorator-order bug** | Open chip from Jun 16 — rate limits silently inactive across `routes/*.py` | internal |
| 1d | **AgentShield baseline scan** | Run once, log findings, defer fixes to pre-client gate | `affaan-m/agentshield` |
| 1e | **caveman skill install** (Claude-Code session ergonomics, NOT production cost) | Clone → inspect `install.sh` → install. Cuts MY chat-token use with Gaurav during the build. Does NOT touch the 18 agents' API calls. | `JuliusBrussee/caveman` |

**Exit criteria:** all 18 agents log to Langfuse, read/write memory via Mem0. Hand-built `cost_reporter` retired. Rate-limit middleware actually active. caveman live in this Claude Code session (separate concern, low-risk).

## 2 · Phase 2 — Data & research hardening (1 day · $0)

| # | Item | What it does | Source |
|---|---|---|---|
| 2a | **Scrapling alongside Apify** | Anti-bot resilience for trend-researcher + strategy-agent | `D4Vinci/Scrapling` |
| 2b | **supadata.ai for video → transcript** | Replaces Whisper pipeline in trend-researcher (key-gated) | supadata.ai |
| 2c | **irinabuht12 google-meta-ads-ga4 MCP** | Live metrics for data-analyst — closes the META_GRAPH_API_TOKEN gap | `irinabuht12-oss/google-meta-ads-ga4-mcp` |

**Exit criteria:** trend-researcher survives 5 consecutive scrapes without bot-block; data-analyst returns real GA4/Meta/Google-Ads metrics for askgauravai.

## 3 · Phase 3 — Expertise packs, one agent at a time (2–3 days · $0)

Per Gaurav's "feed each agent hands-on" rule. **3a is the template** — finish it, then mass-produce.

| # | Agent | Pack source(s) | Notes |
|---|---|---|---|
| 3a | **ad-strategist** | `AgriciDaniel/claude-ads` (250+ audit checks + creative pipeline) | **Template pack — finish first.** |
| 3b | **seo-aeo-agent** | `AgriciDaniel/claude-seo` (25 sub-skills/18 agents) + `zubair-trabzada/geo-seo-claude` (foundation) + `aaron-he-zhu/seo-geo-claude-skills` | Mirror the 25-subskill fleet structure |
| 3c | **creative-director** | `AgriciDaniel/banana-claude` + `ZeroLu/awesome-nanobanana-pro` prompt library | Higgsfield engine stays gated on PRO |
| 3d | **strategy-agent** | `phuryn/pm-skills` + `minhnv0807/ai-business-skills` + `AICMO/AiCMO-Marketing-Prompt-Collection` | Discovery + launch + CMO frames |
| 3e | **brand-guardian** | `arnabbagxd/Brand-building-skills` | Naming + voice + positioning |
| 3f | **content-planner** | `coreyhaines31/marketingskills` + `OpenClaudia/openclaudia-skills` | Calendar skills |
| 3g | **script-writer** | `AgriciDaniel/claude-blog` (5-gate 90/100 quality contract) | Applies our AutoResearch loop |
| 3h | **carousel-designer** | `banana-claude` + nano-banana prompts (shared with CD) | Image consistency |
| 3i | **data-analyst** | `cognyai/claude-code-marketing-skills` + `Zafer-Liu/Data-Analysis-Agent` (NL→SQL pattern) | Live-data hooks |
| 3j | **funnel-specialist** | `coreyhaines31/marketingskills` CRO subset | |
| 3k | **trend-researcher** | `Affitor/affiliate-skills` + `ruvnet/guardrail` (sentiment math) | Trend-scouting patterns |
| 3l | **seo subagents** | already mostly covered by 3b | |
| 3m | **email-marketing-agent** | `OpenClaudia/openclaudia-skills` (email subset) + Klaviyo REST direct | |
| 3n | **community-manager** | mostly LLM + policy; light pack | LiteLLM tier change in Phase 4 |
| 3o | **Lead Generator** (ex-DM-hunter) | `kenny589/gtm-flywheel` (15 GTM frames) + `omkarcloud/google-maps-scraper` | Local-biz ICP |
| 3p | **AI-setter** | `kaymen99/sales-outreach-automation-langgraph` + `chaitanyya/sales` (ICP-scoring) | Port flow to our SDK |

Pure-math agents (trend-sentinel, performance-tracker, cost-tracker) need NO expertise pack.

**Exit criteria:** each agent has a `program.md` derived from its pack source(s); first-run output passes provenance + brand-voice checks.

## 4 · Phase 4 — LiteLLM policy + new capabilities (½ day)

| # | Item | What it does | Source |
|---|---|---|---|
| 4a | **LiteLLM routing change** for high-volume grunt | Haiku 4.5 / Gemini 2.5 Flash / GPT-5 Mini for community-manager, Lead Generator, AI-setter → 5–12× cost cut | `agents/_lib/model_gateway.py` |
| 4b | **google-maps-scraper wired into Lead Generator** | Local-biz ICP harvesting | `omkarcloud/google-maps-scraper` |
| 4c | **google-ads-python client** added (gated) | Fires only when paid budgets confirmed per brand | `googleads/google-ads-python` |

**Exit criteria:** Langfuse shows the 3 high-volume agents on cheaper tiers; weekly cost projection drops ≥40%.

## 5 · Phase 5 — Validation gate (½ day)

| # | Item | What it does |
|---|---|---|
| 5a | F4 magnet copy via `funnel_specialist` | Closes the F4 funnel item (parked since Jun 16) |
| 5b | One supervised paid validation run | `GRID_PAID_OPS=1`, $5/day cap on, watch Langfuse |
| 5c | End-to-end smoke test | askgauravai full pipeline trace, golden-path + 2 edges |

**Exit criteria of Phase 5 = exit criteria of Master-Sequence Step 1 (Backend).** Then move to Step 2 (Lovable front-end).

## 6 · Deferred (do NOT do in this plan)

- **Higgsfield PRO** + per-agent creative work (Master-Sequence Step 5)
- **Front-end (Lovable/v0)** (Master-Sequence Step 2)
- **ManyChat F3 / AI Setter live** — needs live offer + 2 links (purchase + Calendly)
- **Open Design mining** → `CREATIVE_PROMPTING_NOTES.md` (post-Phase-3 nice-to-have)
- **WhatsApp / Telegram CoS channels** — Picsart-inspired backlog item, post-launch
- **Postiz on Hetzner CX22** — Phase M, post-launch

### Phase-1 caveat (Jun 18, post-verification)
Caveman is Claude-Code-session terseness — it reduces MY tokens in the build chat with Gaurav, not the 18 agents' production costs. Real production cost wins come from Phase 4a (LiteLLM Haiku/Flash policy on high-volume agents) and from observability via Langfuse. Caveman = dev-ergonomics, demoted to 1e and explicitly scoped.

## 7 · Backlog carried from Jun 16 (status check)

| Item | Status |
|---|---|
| Apply 006 migration to prod | ✅ DONE (Jun 16 part 2) |
| Scheduler worker deployed to Railway | ✅ DONE (Jun 16 part 2) |
| Phase J concierge router | ✅ DONE |
| K3 revision cap + scope-creep | ✅ DONE |
| YouTube OAuth permanent | ✅ DONE |
| F4 magnet copy | ⏳ → Phase 5a |
| Supervised paid validation run | ⏳ → Phase 5b |
| rate_limit decorator-order bug | ⏳ → Phase 1d |
| Wave-3 hardening | ⏳ folded into Phase 1–4 (caveman + Langfuse + AgentShield together cover it) |
| Open Design mining | ⏳ deferred — Section 6 |

## 8 · Picsart synthesis (1-paragraph reference)

Picsart Agents (TechCrunch Mar 16 2026): 4 agents — Flair (Shopify), Resize Pro, Remix, Swap. Image-editing only. WhatsApp + Telegram access. "Autonomy levels" = approval gate. Free + ~$10/mo. **Wedge they own:** Shopify integration + Picsart image library. **Wedge we own:** 18-agent full-funnel marketing OS (strategy → content → publish → measure → learn). **Borrow:** WA/TG as future CoS channels (post-launch). **Tagline for the freebee:** "Picsart = 4 image agents. GRID = full marketing department on autopilot."

## 9 · Verification points (already confirmed by Gaurav Jun 18)

1. ✅ Order is correct: Foundation → Data → Expertise → Policy → Validation.
2. ✅ Higgsfield-PRO / Open-Design / ManyChat / FE stay deferred.
3. ✅ Phase-1 substrate migration BEFORE expertise packs (one painful migration, then 25 packs land on the new substrate).
4. ✅ Picsart triggers no structural change — only WA/TG backlog add.

---

*Related: [REPO_RESEARCH_INDEX](REPO_RESEARCH_INDEX.md) · [CREATIVE_ENGINE_REBUILD](CREATIVE_ENGINE_REBUILD.md) · [ONBOARDING_CLONE_SPEC](ONBOARDING_CLONE_SPEC.md) · [AGENT_MODEL_FIT_RESEARCH](AGENT_MODEL_FIT_RESEARCH.md).*
