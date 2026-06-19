# GRID CONTROL — Consolidated Repo Research Index (Jun 18 2026)

> Both research passes merged: **Gaurav's** (G) + **Claude's** (C). One table per agent.
> Verdicts: 🟢 **adopt full** · 🟡 **mine for skills** · 🔵 **study/borrow patterns** · ⚪ **reference only** · ❌ **skip**.
> "Verified" = we actually fetched it. "Inferred" = read from URL + context only — confirm before adopting.
> Doubles as a **freebee content asset** (full list of best-in-class AI-marketing repos = lead magnet).

## Roster updates this session
- **website-agent → REMOVED.** Lovable/Emergent builds sites. Work redistributes: copy/SEO → seo-aeo + script-writer; GA4 → data-analyst.
- **dm-customer-hunter → renamed "Lead Generator" (#14).**

---

## Section A — Per-Agent Expertise Repos

### Cross-cutting / Marketing (whole stack)
| Repo | Stars | Who | Status | Use for |
|---|---|---|---|---|
| [twentyhq/twenty](https://github.com/twentyhq/twenty) | (large) | G | 🔵 **architecture inspiration** | CRM, NOT expertise — code-first objects/workflows, AI-native extensibility = pattern for our multi-tenant + plugin model. *Verified.* |
| [coreyhaines31/marketingskills](https://github.com/coreyhaines31/marketingskills) | — | G+C | 🟡 mine | CRO, copy, SEO, analytics, growth (multi-agent) |
| [multica-ai/andrej-karpathy-skills](https://github.com/multica-ai/andrej-karpathy-skills) | **178K★** | G | 🟢 adopt as **coding discipline** (NOT marketing) | "Think before coding · Simplicity · Surgical changes · Goal-driven execution" → applies to **how Claude Code builds GRID itself**. Drop into our project CLAUDE.md. *Verified — confirmed it's SE methodology, not marketing.* |
| [thatrebeccarae/claude-marketing](https://github.com/thatrebeccarae/claude-marketing) (C) | — | C | 🟡 mine deeply | "Full marketing dept" — 56 skills, **benchmarks + audit checklists** per platform |
| [alirezarezvani/claude-skills](https://github.com/alirezarezvani/claude-skills) (C) | 5.2K★ | C | 🟡 mine | 330+ skills / 30+ agents — biggest library |
| [OpenClaudia/openclaudia-skills](https://github.com/OpenClaudia/openclaudia-skills) (C) | — | C | 🟡 mine | 67+ marketing skills (SEO/content/email/ads/growth) |
| [hyperfx-ai/marketing-skills](https://github.com/hyperfx-ai/marketing-skills) | — | G (under email) | 🟡 mine | broad marketing skills |
| [indranilbanerjee/digital-marketing-pro](https://github.com/indranilbanerjee/digital-marketing-pro) | — | G (under SEO) | 🟡 mine | broad digital marketing |

### 0 · ceo-brain / Chief of Staff
| Repo | Status | Use for |
|---|---|---|
| [wshobson/agents](https://github.com/wshobson/agents) | 🟢 **mine heavily** | 36.9K★, **192 agents / 156 skills / 102 commands marketplace** + 16 orchestrator templates. Cross-CLI. *Verified — biggest find of this section; use for CoS AND many other agents.* |
| [Yeachan-Heo/oh-my-claudecode](https://github.com/Yeachan-Heo/oh-my-claudecode) | 🔵 study | Claude Code config/skill patterns. *Inferred.* |
| [openai/swarm](https://github.com/openai/swarm) | 🔵 reference | OpenAI's lightweight multi-agent handoffs — *pattern reference only* (we're not on OpenAI runtime) |
| [kyegomez/swarms](https://github.com/kyegomez/swarms) | ⚪ reference | Multi-agent framework; large but hype-noisy |
| [D4Vinci/Scrapling](https://github.com/D4Vinci/Scrapling) | 🟡 tool | Anti-bot web scraping lib — useful tool for CoS/trend/ad-strategist (not an expertise pack) |
| [AICMO/AiCMO-Marketing-Prompt-Collection](https://github.com/AICMO/AiCMO-Marketing-Prompt-Collection) (C) | 🟡 mine | Autonomous marketing-dept prompts (CMO-level) |

### 1 · strategy-agent
| Repo | Status | Use for |
|---|---|---|
| [phuryn/pm-skills](https://github.com/phuryn/pm-skills) | 🟡 mine | PM/strategy skills — JTBD, positioning, roadmap |
| [ALwrity/ALwrity](https://github.com/ALwrity/ALwrity) | 🔵 study | AI content/marketing platform; check its strategy modules |
| [minhnv0807/ai-business-skills](https://github.com/minhnv0807/ai-business-skills) | 🟡 mine | Business-strategy skill set |
| [kostja94/marketing-skills](https://github.com/kostja94/marketing-skills) | 🟡 mine | Marketing skills (general) |
| [BrianRWagner/ai-marketing-claude-code-skills](https://github.com/BrianRWagner/ai-marketing-claude-code-skills) (C) | 🟡 mine | "Frameworks AI actually executes" |

### 2 · content-planner
| Repo | Status | Use for |
|---|---|---|
| OpenClaw (general framework) | 🟠 **borrow patterns, not adopt** | G's instinct is right that OpenClaw's heartbeat-cron + plan loop fits, but OpenClaw is a *runtime*, not content expertise. Borrow the autonomy loop; expertise comes from claude-marketing/openclaudia-skills. |
| [thatrebeccarae/claude-marketing](https://github.com/thatrebeccarae/claude-marketing) | 🟡 mine | Content calendar + pillars + cadence skills |
| [OpenClaudia/openclaudia-skills](https://github.com/OpenClaudia/openclaudia-skills) | 🟡 mine | Content modular skills |

### 3 · script-writer (you found "nothing appropriate")
| Repo | Status | Use for |
|---|---|---|
| (gaps here) | — | I'll search specifically for: viral-hook frameworks (Alex Hormozi/STEPPS), short-form video script libs, captions/CTA prompt banks |
| [MaxsPrompts/Marketing-Prompts](https://github.com/MaxsPrompts/Marketing-Prompts) (C) | 🟡 raw bank | 546 skills / 4368 prompts — mine for hooks |
| [coreyhaines31/marketingskills](https://github.com/coreyhaines31/marketingskills) | 🟡 mine | Copywriting frameworks |

### 4 · creative-director (+ #15 carousel-designer — same set)
| Repo | Status | Use for |
|---|---|---|
| [AgriciDaniel/banana-claude](https://github.com/AgriciDaniel/banana-claude) | 🟡 mine | Nano Banana / image gen skills |
| [AgriciDaniel/claude-ads](https://github.com/AgriciDaniel/claude-ads) | 🟡 mine | Ad creative skills |
| [ZeroLu/awesome-nanobanana-pro](https://github.com/ZeroLu/awesome-nanobanana-pro) | 🟡 mine | Nano Banana Pro prompt collection — pairs with our Higgsfield skills |

### 5 · ad-strategist
| Repo | Status | Use for |
|---|---|---|
| [AgriciDaniel/claude-ads](https://github.com/AgriciDaniel/claude-ads) | 🟡 mine | Ad strategy skills |
| [zubair-trabzada/geo-seo-claude](https://github.com/zubair-trabzada/geo-seo-claude) | 🟢 adopt | Already used by us — keep, deepen |
| [Auriti-Labs/geo-optimizer-skill](https://github.com/Auriti-Labs/geo-optimizer-skill) | 🟡 mine | GEO optimization |
| [yaojingang/GEOFlow](https://github.com/yaojingang/GEOFlow) | 🟡 mine | GEO workflow |
| [onvoyage-ai/gtm-engineer-skills](https://github.com/onvoyage-ai/gtm-engineer-skills) | 🟡 mine | GTM/ads engineer skills |
| [googleads/google-ads-python](https://github.com/googleads/google-ads-python) | 🟢 tool | Official Google Ads SDK — wire as connector |
| [googleads/googleads-python-lib](https://github.com/googleads/googleads-python-lib) | (note) | Deprecated alongside google-ads-python — verify |
| [googleads/googleads-mobile-unity](https://github.com/googleads/googleads-mobile-unity) | ❌ | Mobile SDK, not relevant |
| [fluxcd/flagger](https://github.com/fluxcd/flagger) · [splitrb/split](https://github.com/splitrb/split) | 🔵 pattern | A/B testing patterns (infra-level) |
| [TheCraigHewitt/seomachine](https://github.com/TheCraigHewitt/seomachine) | 🟡 mine | SEO automation |
| [AD-Security/AD_Miner](https://github.com/AD-Security/AD_Miner) | ❌ wrong "AD" | Active Directory security, NOT advertising — skip |
| [nowork-studio/NotFair](https://github.com/nowork-studio/NotFair) | 🔵 study | Need to verify |
| [AgriciDaniel/claude-blog](https://github.com/AgriciDaniel/claude-blog) | 🟡 mine | Blog/content skills |
| [D4Vinci/Scrapling](https://github.com/D4Vinci/Scrapling) | 🟡 tool | (shared) — competitor ad scraping |

### 6 · data-analyst
| Repo | Status | Use for |
|---|---|---|
| [irinabuht12-oss/google-meta-ads-ga4-mcp](https://github.com/irinabuht12-oss/google-meta-ads-ga4-mcp) | 🟢 **adopt** | **MCP for Google Ads + Meta Ads + GA4 = the live-metrics gap we flagged. Best find for #6.** |
| [Zafer-Liu/Data-Analysis-Agent](https://github.com/Zafer-Liu/Data-Analysis-Agent) | 🟡 mine | Data-analysis agent patterns |
| [plausible/analytics](https://github.com/plausible/analytics) | 🔵 study | Privacy analytics platform; pattern only |
| [OpenBB-finance/OpenBB](https://github.com/OpenBB-finance/OpenBB) | ⚪ ref | Finance-focused; pattern for terminal-style data agent |
| [amundsen-io/amundsen](https://github.com/amundsen-io/amundsen) | ⚪ ref | Data discovery (Lyft); enterprise pattern |
| [GoogleCloudPlatform/training-data-analyst](https://github.com/GoogleCloudPlatform/training-data-analyst) | ⚪ ref | GCP training samples |
| [mrankitgupta/Data-Analyst-Roadmap](https://github.com/mrankitgupta/Data-Analyst-Roadmap) | ⚪ ref | Roadmap, not skills |
| [cognyai/claude-code-marketing-skills](https://github.com/cognyai/claude-code-marketing-skills) (C) | 🟢 **adopt** | Live-MCP connectors (Google Ads, GA4, Meta, GSC, LinkedIn, Klaviyo). Pair with irinabuht12 above. |

### 7 · funnel-specialist
| Repo | Status | Use for |
|---|---|---|
| [coreyhaines31/marketingskills](https://github.com/coreyhaines31/marketingskills) | 🟡 mine | CRO + funnel skills (shared) |
| (gap) | — | I'll search: landing-page copy banks, WhatsApp/email nurture frameworks |

### 8 · trend-researcher
| Repo | Status | Use for |
|---|---|---|
| [Affitor/affiliate-skills](https://github.com/Affitor/affiliate-skills) | 🟡 mine | Affiliate/trend hunting |
| [ruvnet/guardrail](https://github.com/ruvnet/guardrail) | 🔵 study | "Human emotion" guardrails (your note) — interesting for sentiment-aware trends |
| [oxylabs/how-to-scrape-google-trends](https://github.com/oxylabs/how-to-scrape-google-trends) | 🟢 tool | Google Trends scraper — wire as connector |
| [D4Vinci/Scrapling](https://github.com/D4Vinci/Scrapling) | 🟡 tool | (shared) |

### 9 · ~~website-agent~~ — REMOVED. Work redistributed: copy/SEO → seo-aeo + script-writer; GA4 → data-analyst; site build → Lovable/Emergent (handled outside agent system).

### 10 · brand-guardian
| Repo | Status | Use for |
|---|---|---|
| [thepotato0/Brand-guardian](https://github.com/thepotato0/Brand-guardian) | 🟡 mine | Direct namesake — voice/compliance |
| [Kshitij-AI-Architect/Brand-Guardian-Compliance](https://github.com/Kshitij-AI-Architect/Brand-Guardian-Compliance) | 🟡 mine | Brand compliance checks |
| [arnabbagxd/Brand-building-skills](https://github.com/arnabbagxd/Brand-building-skills) | 🟡 mine | Brand-building frameworks |

### 11 · seo-aeo-agent
| Repo | Status | Use for |
|---|---|---|
| [zubair-trabzada/geo-seo-claude](https://github.com/zubair-trabzada/geo-seo-claude) | 🟢 keep | already in use |
| [AgriciDaniel/claude-seo](https://github.com/AgriciDaniel/claude-seo) | 🟡 mine | Claude SEO skills |
| [aaron-he-zhu/seo-geo-claude-skills](https://github.com/aaron-he-zhu/seo-geo-claude-skills) | 🟡 mine | SEO + GEO skills |
| [sethblack/python-seo-analyzer](https://github.com/sethblack/python-seo-analyzer) | 🟢 tool | Site analyzer — wire as connector |
| [spatie/schema-org](https://github.com/spatie/schema-org) · [google/schema-dts](https://github.com/google/schema-dts) | 🟢 tool | Schema.org generators (PHP/TS) |
| [harlan-zw/nuxt-seo](https://github.com/harlan-zw/nuxt-seo) | ⚪ ref | Nuxt-specific; pattern only |
| [onvoyage-ai/gtm-engineer-skills](https://github.com/onvoyage-ai/gtm-engineer-skills) | 🟡 mine | (shared) |
| [Auriti-Labs/geo-optimizer-skill](https://github.com/Auriti-Labs/geo-optimizer-skill) | 🟡 mine | (shared) |
| [indranilbanerjee/digital-marketing-pro](https://github.com/indranilbanerjee/digital-marketing-pro) | 🟡 mine | (shared) |

### 12 · email-marketing-agent
| Repo | Status | Use for |
|---|---|---|
| [telexintegrations/email-marketing-agent](https://github.com/telexintegrations/email-marketing-agent) | 🟡 mine | Direct namesake |
| [hyperfx-ai/marketing-skills](https://github.com/hyperfx-ai/marketing-skills) | 🟡 mine | (shared) |
| [klaviyo/klaviyo-api-node](https://github.com/klaviyo/klaviyo-api-node) | 🟢 tool | Official Klaviyo API (when needed) |

### 13 · community-manager
| Repo | Status | Use for |
|---|---|---|
| [nz-m/SocialEcho](https://github.com/nz-m/SocialEcho) | 🔵 pattern | Social-network app — *pattern*, not skills |
| [Cog-Creators/Red-DiscordBot](https://github.com/Cog-Creators/Red-DiscordBot) · [PhantomBot/PhantomBot](https://github.com/PhantomBot/PhantomBot) | ⚪ ref | Discord/Twitch bots — community-mgmt patterns only |
| (gap) | — | Need IG/LinkedIn-specific reply frameworks; I'll search |

### 14 · Lead Generator (was dm-customer-hunter)
| Repo | Status | Use for |
|---|---|---|
| [omkarcloud/google-maps-scraper](https://github.com/omkarcloud/google-maps-scraper) | 🟢 tool | Lead discovery via Maps |
| [kenny589/gtm-flywheel](https://github.com/kenny589/gtm-flywheel) | 🟡 mine | GTM flywheel patterns |
| (add) | — | Will search ICP-scoring + outbound DM frameworks |

### 15 · carousel-designer — same as #4

### 16 · AI Setter (new agent)
| Repo | Status | Use for |
|---|---|---|
| [chaitanyya/sales](https://github.com/chaitanyya/sales) | 🟡 mine | Sales DM skills |
| [kaymen99/sales-outreach-automation-langgraph](https://github.com/kaymen99/sales-outreach-automation-langgraph) | 🟢 mine | **LangGraph sales-outreach reference — closest match to F3 architecture** |
| [manychat/manychat-api-php](https://github.com/manychat/manychat-api-php) | 🟢 tool | Official ManyChat API (we're on Python — note language) |

### 17 · trend-sentinel (pure-math)
| Repo | Status | Use for |
|---|---|---|
| [getsentry/sentry](https://github.com/getsentry/sentry) | ❌ wrong namesake | Error-monitoring SaaS, NOT trend signals — skip |
| [abusufyanvu/6S191_MIT_DeepLearning](https://github.com/abusufyanvu/6S191_MIT_DeepLearning) | ⚪ ref | MIT deep-learning course |
| [SMByC/CCD-Plugin](https://github.com/SMByC/CCD-Plugin) | 🔵 study | "Continuous Change Detection" — algorithmic change-point detection = good for trend-sentinel's math layer |

### 18 · performance-tracker (pure-math)
| Repo | Status | Use for |
|---|---|---|
| (no repos assigned) | — | Math layer; pattern-detection libs from #17 may transfer |

---

## Section A2 — The "Freebee" list (additional repos from your misc list)

These are platform/tooling, not per-agent. Worth studying; bundle into the lead-magnet doc.

| Link | What it is | Verdict / use |
|---|---|---|
| [fountn.design](https://fountn.design/) | Design system / inspiration | 🔵 design ref for the dashboard |
| [supadata.ai](https://supadata.ai/) | Content research API | 🟡 evaluate for content-planner/trend-researcher data pipe |
| [humanizr/humanizer](https://github.com/humanizr/humanizer) | Manipulate text/dates/quantities naturally | 🟢 tool — humanize agent output (counts, time-ago, etc.) |
| [can1357/oh-my-pi](https://github.com/can1357/oh-my-pi) | (need to fetch) | 🔵 study |
| [affaan-m/ECC](https://github.com/affaan-m/ECC) | (need to fetch) | 🔵 study |
| [garrytan/gstack](https://github.com/garrytan/gstack) | Garry Tan's stack | 🔵 study — opinionated startup stack |
| [JuliusBrussee/caveman](https://github.com/JuliusBrussee/caveman) | Token saving | 🟢 **adopt principle** for our model_gateway → directly tackles cost-control |
| [ruvnet/ruflo](https://github.com/ruvnet/ruflo) | (need to fetch) | 🔵 study |
| [hesreallyhim](https://github.com/hesreallyhim) | Curates `awesome-claude-code` | 🔵 **navigation hub** — periodic check for new skills/agents/plugins. *Verified.* |
| [affaan-m/agentshield](https://github.com/affaan-m/agentshield) | Agent security | 🟢 **adopt** when we do AgentShield security scan (pre-client launch) |
| [multica-ai/andrej-karpathy-skills](https://github.com/multica-ai/andrej-karpathy-skills) | SE methodology for Claude | 🟢 adopt as project CLAUDE.md discipline layer (NOT an agent expertise) |

**Lead-magnet asset:** this whole list + Section A = a *real* curated "best AI-marketing repos 2026" PDF/page → use as content for askgauravai. High share value.

---

## Section B — Platform / Multi-tenant Foundation (technical; you asked me to guide)

This is what makes GRID a *pro* multi-tenant product vs an agency tool. Three decisions to lock.

| Decision | Options | My recommendation | Why |
|---|---|---|---|
| **Storage** | (a) File-based (today) (b) Supabase Postgres + RLS | **(b) Supabase** | We already pay Supabase; have 9 tables + RLS; only way to be safe multi-tenant 24/7. Already locked yesterday. |
| **Memory layer** | (a) Hand-roll the 3-scope memory in Supabase (b) [Mem0](https://github.com/mem0ai/mem0) — user/session/agent scopes match our Brand/Personal/Account (c) [Zep](https://github.com/getzep/zep) — temporal KG | **(b) Mem0 (now) + revisit Zep later** | Mem0's scopes literally match ours; battle-tested; ~5 lines; self-hosts on Postgres. Saves us building memory CRUD from scratch tonight. Zep's temporal KG is better if we need "facts that change over time" — defer to v2. |
| **Observability + cost + eval** | (a) Hand-extend our `cost_tracker` + eval-harness (b) [Langfuse](https://github.com/langfuse/langfuse) self-host | **(b) Langfuse** | Open-source, self-hosted (data stays with us), per-brand/per-agent/per-run cost + tracing + LLM-as-judge eval. Productizes our cost-transparency wedge + fixes the cost-drain incident. |
| **Multi-provider routing** | LiteLLM | ✅ already have | Validates the model-fit research finding (Haiku/Flash/GPT-Mini for high-volume grunt). Just enable. |
| **Self-serve product runtime** | [Suna (Kortix)](https://github.com/kortix-ai/suna) — OSS Manus | 🔵 **study, don't migrate** | Closest OSS mirror to our whole product. Learn execution-runtime + chat-UX patterns; keep our marketing specialization as the moat. |
| **Self-host hosting** | Railway (have) + Vercel (have) + Supabase Pro ($25/mo at launch) | ✅ keep | Free tier is fine to build; upgrade to Supabase Pro at launch (kills 7-day auto-pause + adds daily backups). |

**Three things I'll wire into tonight's backend plan once you say go:**
1. **Mem0** as the 3-scope memory backbone (Brand/Personal/Account).
2. **Langfuse** as observability + cost + eval (replaces our hand-built tracker).
3. **LiteLLM policy change** to enable cheaper models for high-volume grunt (community/lead-generator/AI-Setter).

---

## What I will do next (after your go)

1. **Deeper-fetch the high-value repos** (5–8 max, not 60): wshobson/agents, claude-marketing, openclaudia-skills, AgriciDaniel/claude-ads, kaymen99/sales-outreach, irinabuht12 google-meta-ads-ga4-mcp, Mem0, Langfuse — enough to confirm the picks.
2. **Author the first expertise pack** (one agent, end-to-end, as the template) so we *see* a non-generic agent working before mass-producing the rest.
3. Save this list as a **lead-magnet draft** for askgauravai content.

---

## Section C — Verified deep-fetch results (Jun 18 2026 — every repo, no skipping)

> Done per Gaurav's "no page un-turned" instruction. Every repo fetched (stars rounded). One line per repo. Verdicts: 🟢 ADOPT · 🟡 MINE · 🔵 STUDY · ⚪ REFERENCE · ❌ SKIP.

### C0 — System foundation
| Repo | ★ | What | Best fit | Verdict |
|---|---|---|---|---|
| [mem0ai/mem0](https://github.com/mem0ai/mem0) | 58.8k | Universal memory layer (user/session/agent scopes) | system memory | 🟢 ADOPT — already locked, deepen 3-scope wiring |
| [langfuse/langfuse](https://github.com/langfuse/langfuse) | 29.3k | OSS LLM observability + eval + prompt platform | system obs | 🟢 ADOPT — ship traces from all 18 agents |
| [kortix-ai/suna](https://github.com/kortix-ai/suna) | 19.9k | OSS agent command center | ceo-brain pattern | 🟢 ADOPT — chat-runs-real-work pattern |
| [langflow-ai/langflow](https://github.com/langflow-ai/langflow) | 150k | Visual workflow builder | foundation | 🔵 STUDY — off our chat-first paradigm |
| [FlowiseAI/Flowise](https://github.com/FlowiseAI/Flowise) | 53.7k | Visual no-code agent builder | foundation | ❌ SKIP — off-paradigm vs Suna |
| [langgenius/dify](https://github.com/langgenius/dify) | 146k | LLM app platform (workflows/RAG/agents) | foundation | 🔵 STUDY — mine RAG patterns, don't replatform |
| [getzep/zep](https://github.com/getzep/zep) | 4.7k | Managed agent memory + temporal KG | memory alt | ⚪ REFERENCE — Mem0 chosen, keep as fallback |
| [BerriAI/litellm](https://github.com/BerriAI/litellm) | 50.8k | Unified 100+ LLM gateway + cost | gateway | 🟢 ADOPT — already locked |
| [langchain-ai/langgraph](https://github.com/langchain-ai/langgraph) | 35.1k | Stateful agent orchestration | ceo-brain | 🔵 STUDY — graph state for CoS |
| [crewAIInc/crewAI](https://github.com/crewAIInc/crewAI) | 53.9k | Multi-agent collaboration | ceo-brain | 🔵 STUDY — role/task fits 18-roster |
| [huggingface/smolagents](https://github.com/huggingface/smolagents) | 27.9k | Code-action lightweight agents | foundation | ⚪ REFERENCE — off SDK |
| [openai/swarm](https://github.com/openai/swarm) | 21.6k | Educational multi-agent (deprecated) | reference | ❌ SKIP — superseded |
| [kyegomez/swarms](https://github.com/kyegomez/swarms) | 6.9k | Hierarchical orchestration | ceo-brain | ⚪ REFERENCE — pattern only |

### C1 — Marketing layer (cross-agent)
| Repo | ★ | What | Best fit | Verdict |
|---|---|---|---|---|
| [twentyhq/twenty](https://github.com/twentyhq/twenty) | 50.3k | OSS AI-native CRM (Salesforce alt) | lead-gen + AI-setter | 🔵 STUDY — possible CRM layer |
| [coreyhaines31/marketingskills](https://github.com/coreyhaines31/marketingskills) | 33.9k | 50+ marketing skills | cross-agent | 🟡 MINE — biggest pack, harvest selectively |
| [multica-ai/andrej-karpathy-skills](https://github.com/multica-ai/andrej-karpathy-skills) | 178k | Coding methodology for Claude Code | system discipline | ❌ SKIP for agents (use for Claude Code that BUILDS GRID) |
| [alirezarezvani/claude-skills](https://github.com/alirezarezvani/claude-skills) | 18.4k | 337 skills across 17 domains | cross-agent | 🟡 MINE — growth/CMO subset |
| [thatrebeccarae/claude-marketing](https://github.com/thatrebeccarae/claude-marketing) | 0.06k | 56 paid/ecom/content/analytics skills | cross-agent | 🟡 MINE — focused paid+ecom |
| [OpenClaudia/openclaudia-skills](https://github.com/OpenClaudia/openclaudia-skills) | 0.48k | 67+ modular skills as marketing dept | cross-agent | 🟡 MINE — clean modular packaging |
| [cognyai/claude-code-marketing-skills](https://github.com/cognyai/claude-code-marketing-skills) | 0.05k | SEO/ad/competitor/lead-qual skills | seo+ads+leadgen | 🟡 MINE — small but live-data hooks |
| [zubair-trabzada/ai-marketing-claude](https://github.com/zubair-trabzada/ai-marketing-claude) | 1.9k | Marketing analysis + automation | cross-agent | 🟡 MINE — same author as geo-seo |
| [hyperfx-ai/marketing-skills](https://github.com/hyperfx-ai/marketing-skills) | 0.04k | Skills on Hyper MCP | cross-agent | ⚪ REFERENCE — MCP-specific |
| [kostja94/marketing-skills](https://github.com/kostja94/marketing-skills) | 0.62k | 160+ open marketing skills | cross-agent | 🟡 MINE — unique templates |
| [indranilbanerjee/digital-marketing-pro](https://github.com/indranilbanerjee/digital-marketing-pro) | 0.15k | 158 skills + 25 agents · 50-60 docs/brand | ceo-brain + strategy | 🔵 STUDY — closest agency-workflow analog |
| [jmedia65/awesome-ai-marketing](https://github.com/jmedia65/awesome-ai-marketing) | 0.006k | Curated list | reference | ⚪ REFERENCE — list |
| [AICMO/AiCMO-Marketing-Prompt-Collection](https://github.com/AICMO/AiCMO-Marketing-Prompt-Collection) | 0.17k | CMO-automation prompts | strategy + planner | 🟡 MINE — CMO-shaped prompts |
| [MaxsPrompts/Marketing-Prompts](https://github.com/MaxsPrompts/Marketing-Prompts) | 0.06k | 4,368 prompts CSV / 546 skills | reference | ⚪ REFERENCE — mine selectively |

### C2 — ceo-brain / CoS
| Repo | ★ | What | Best fit | Verdict |
|---|---|---|---|---|
| [wshobson/agents](https://github.com/wshobson/agents) | 36.9k | 192 agents + 156 skills + 102 commands | ceo-brain + all 18 | 🟡 MINE — biggest cross-harness library |
| [Yeachan-Heo/oh-my-claudecode](https://github.com/Yeachan-Heo/oh-my-claudecode) | 36.6k | Teams-first multi-agent orchestration | ceo-brain | 🔵 STUDY — zero-config delegation |
| [D4Vinci/Scrapling](https://github.com/D4Vinci/Scrapling) | 64.7k | Adaptive scraper + anti-bot + AI hooks | trend-researcher + strategy | 🟢 ADOPT — pair with Apify for resilience |

### C3 — Strategy
| Repo | ★ | What | Best fit | Verdict |
|---|---|---|---|---|
| [phuryn/pm-skills](https://github.com/phuryn/pm-skills) | 19.5k | 68+ PM skills (discovery/strategy/launch/growth) | strategy + planner | 🟡 MINE — discovery+launch frameworks |
| [ALwrity/ALwrity](https://github.com/ALwrity/ALwrity) | 1.1k | Contextual content OS + brand brain | strategy + planner + guardian | 🔵 STUDY — brand-brain parallels CoS |
| [minhnv0807/ai-business-skills](https://github.com/minhnv0807/ai-business-skills) | 0.46k | 63 bilingual marketing/branding skills | strategy + guardian | 🟡 MINE — positioning + personal-brand |

### C4 — Creative Director / Carousel Designer
| Repo | ★ | What | Best fit | Verdict |
|---|---|---|---|---|
| [AgriciDaniel/banana-claude](https://github.com/AgriciDaniel/banana-claude) | 0.71k | Claude-as-creative-director for Gemini image gen | CD | 🟡 MINE — matches our CD prompt pattern |
| [AgriciDaniel/claude-ads](https://github.com/AgriciDaniel/claude-ads) | 6.2k | 250+ paid ad audit checks + creative pipeline | ad-strategist + CD | 🟢 ADOPT — twofer, load-bearing |
| [ZeroLu/awesome-nanobanana-pro](https://github.com/ZeroLu/awesome-nanobanana-pro) | 10.1k | 100+ Nano Banana Pro prompt patterns | CD + carousel | 🟡 MINE — image consistency |

### C5 — Ad Strategist
| Repo | ★ | What | Best fit | Verdict |
|---|---|---|---|---|
| [zubair-trabzada/geo-seo-claude](https://github.com/zubair-trabzada/geo-seo-claude) | 8.2k | GEO-first SEO skill for AI search | seo-aeo | 🟢 ADOPT — already foundation |
| [nowork-studio/NotFair](https://github.com/nowork-studio/NotFair) | 2.9k | Audit/optimize Google+Meta Ads + SEO | ads + seo | 🟡 MINE — direct ad-account audit |
| [yaojingang/GEOFlow](https://github.com/yaojingang/GEOFlow) | 2.6k | AI content + multi-site dist + RAG | planner + seo | 🔵 STUDY — WordPress dist |
| [onvoyage-ai/gtm-engineer-skills](https://github.com/onvoyage-ai/gtm-engineer-skills) | 1.2k | GTM workflows for AI discoverability | seo + strategy | 🟡 MINE — GTM signal patterns |
| [AgriciDaniel/claude-blog](https://github.com/AgriciDaniel/claude-blog) | 1.1k | 5-gate blog quality contract (90/100) | planner + script-writer | 🟡 MINE — quality-gate pattern for AutoResearch |
| [Auriti-Labs/geo-optimizer-skill](https://github.com/Auriti-Labs/geo-optimizer-skill) | 0.48k | AI answer-engine citation audit | seo-aeo | 🟡 MINE — focused AEO checks |
| [fluxcd/flagger](https://github.com/fluxcd/flagger) | 5.4k | K8s progressive delivery | n/a | ❌ SKIP — infra |
| [splitrb/split](https://github.com/splitrb/split) | 2.7k | Rack/Rails A/B testing | ads A/B | ⚪ REFERENCE — Ruby, port stats approach |
| [googleads/googleads-python-lib](https://github.com/googleads/googleads-python-lib) | 0.74k | Legacy Ad Manager SOAP client | ads | ❌ SKIP — legacy |
| [googleads/google-ads-python](https://github.com/googleads/google-ads-python) | 0.72k | Official Google Ads API client | ads | 🟢 ADOPT — when paid budgets confirmed |
| [googleads/googleads-mobile-unity](https://github.com/googleads/googleads-mobile-unity) | — | Mobile Unity SDK | n/a | ❌ SKIP — irrelevant |
| [TheCraigHewitt/seomachine](https://github.com/TheCraigHewitt/seomachine) | 7.1k | Claude SEO blog workspace | seo + planner | 🟡 MINE — long-form SEO shape |
| [AD-Security/AD_Miner](https://github.com/AD-Security/AD_Miner) | — | Active Directory security | n/a | ❌ SKIP — namesake |

### C6 — Data Analyst
| Repo | ★ | What | Best fit | Verdict |
|---|---|---|---|---|
| [OpenBB-finance/OpenBB](https://github.com/OpenBB-finance/OpenBB) | 69.4k | Open data platform + MCP servers | data-analyst | ⚪ REFERENCE — finance-shaped, MCP useful |
| [GoogleCloudPlatform/training-data-analyst](https://github.com/GoogleCloudPlatform/training-data-analyst) | 8.6k | GCP training labs | n/a | ❌ SKIP — training |
| [amundsen-io/amundsen](https://github.com/amundsen-io/amundsen) | 4.8k | Metadata-driven data discovery | data-analyst | ⚪ REFERENCE — overkill |
| [Zafer-Liu/Data-Analysis-Agent](https://github.com/Zafer-Liu/Data-Analysis-Agent) | 1.8k | Conversational NL→SQL agent | data-analyst | 🔵 STUDY — NL-to-insight |
| [mrankitgupta/Data-Analyst-Roadmap](https://github.com/mrankitgupta/Data-Analyst-Roadmap) | 1k | Learning roadmap | n/a | ❌ SKIP — learning |
| [plausible/analytics](https://github.com/plausible/analytics) | 27.2k | Privacy-first GA alt | data-analyst + website | 🟢 ADOPT — drop-in GA4 alt for client sites |
| [irinabuht12-oss/google-meta-ads-ga4-mcp](https://github.com/irinabuht12-oss/google-meta-ads-ga4-mcp) | 1k | Unified MCP Google/Meta Ads + GA4 (250+ tools) | data-analyst + ads | 🟢 ADOPT — unblocks live-metrics gap |

### C7 — Trend Researcher
| Repo | ★ | What | Best fit | Verdict |
|---|---|---|---|---|
| [Affitor/affiliate-skills](https://github.com/Affitor/affiliate-skills) | 0.47k | 52 affiliate workflow skills | leadgen + trend | 🟡 MINE — trend-scouting patterns |
| [ruvnet/guardrail](https://github.com/ruvnet/guardrail) | 0.15k | Sentiment + trend detection (AiEQ) | trend-researcher + sentinel | 🔵 STUDY — sentiment math |
| [oxylabs/how-to-scrape-google-trends](https://github.com/oxylabs/how-to-scrape-google-trends) | 2.6k | Google Trends scrape guide | trend-researcher | ⚪ REFERENCE — vendor-locked |

### C8 — Brand Guardian
| Repo | ★ | What | Best fit | Verdict |
|---|---|---|---|---|
| [thepotato0/Brand-guardian](https://github.com/thepotato0/Brand-guardian) | 0.002k | Reddit brand-mention notifier | guardian | ❌ SKIP — toy |
| [Kshitij-AI-Architect/Brand-Guardian-Compliance](https://github.com/Kshitij-AI-Architect/Brand-Guardian-Compliance) | 0.001k | YouTube compliance auditor LangGraph+Azure | guardian | 🔵 STUDY — RAG compliance pattern |
| [arnabbagxd/Brand-building-skills](https://github.com/arnabbagxd/Brand-building-skills) | 0.19k | Brand strategy/naming/voice skills | guardian + strategy | 🟡 MINE — direct brand-building set |

### C9 — SEO/AEO
| Repo | ★ | What | Best fit | Verdict |
|---|---|---|---|---|
| [spatie/schema-org](https://github.com/spatie/schema-org) | 1.5k | PHP Schema.org JSON-LD builder | seo-aeo | ⚪ REFERENCE — PHP, port idea |
| [google/schema-dts](https://github.com/google/schema-dts) | 1.2k | TS JSON-LD types | website + seo | 🟢 ADOPT — use in dashboard FE |
| [harlan-zw/nuxt-seo](https://github.com/harlan-zw/nuxt-seo) | 1.4k | Nuxt SEO + AEO modules | website | ⚪ REFERENCE — Nuxt, port concepts |
| [AgriciDaniel/claude-seo](https://github.com/AgriciDaniel/claude-seo) | 9.2k | 25 sub-skills + 18 agents full SEO audit | seo-aeo | 🟢 ADOPT — mirror fleet structure |
| [aaron-he-zhu/seo-geo-claude-skills](https://github.com/aaron-he-zhu/seo-geo-claude-skills) | 2.2k | 20 SEO+GEO skills | seo-aeo | 🟡 MINE — complement to zubair |
| [sethblack/python-seo-analyzer](https://github.com/sethblack/python-seo-analyzer) | 1.5k | Python crawler + Claude SEO | seo + website | 🟡 MINE — port crawler core |

### C10 — Email
| Repo | ★ | What | Best fit | Verdict |
|---|---|---|---|---|
| [telexintegrations/email-marketing-agent](https://github.com/telexintegrations/email-marketing-agent) | 0.008k | Telex/Groq integration | email | ❌ SKIP — low signal |
| [klaviyo/klaviyo-api-node](https://github.com/klaviyo/klaviyo-api-node) | 0.08k | Klaviyo Node SDK | email | ⚪ REFERENCE — port REST to Python |

### C11 — Community Manager
| Repo | ★ | What | Best fit | Verdict |
|---|---|---|---|---|
| [nz-m/SocialEcho](https://github.com/nz-m/SocialEcho) | 2.4k | NLP-moderated social network | community | ⚪ REFERENCE — moderation NLP only |
| [Cog-Creators/Red-DiscordBot](https://github.com/Cog-Creators/Red-DiscordBot) | 5.6k | Discord bot framework | community | ❌ SKIP — Discord-only |
| [PhantomBot/PhantomBot](https://github.com/PhantomBot/PhantomBot) | 0.84k | Twitch bot | community | ❌ SKIP — Twitch-only |

### C12 — Lead Generator (ex-DM-hunter)
| Repo | ★ | What | Best fit | Verdict |
|---|---|---|---|---|
| [omkarcloud/google-maps-scraper](https://github.com/omkarcloud/google-maps-scraper) | 2.7k | 50+ biz data points from Maps | leadgen | 🟢 ADOPT — local-biz ICP harvesting |
| [kenny589/gtm-flywheel](https://github.com/kenny589/gtm-flywheel) | 0.05k | 15 GTM frameworks (ICP/cold/signals) | leadgen + ai-setter | 🟡 MINE — exact GTM shape |

### C13 — AI Setter
| Repo | ★ | What | Best fit | Verdict |
|---|---|---|---|---|
| [chaitanyya/sales](https://github.com/chaitanyya/sales) | 0.35k | Claude lead research + qualification | leadgen + ai-setter | 🔵 STUDY — ICP-scoring pattern |
| [kaymen99/sales-outreach-automation-langgraph](https://github.com/kaymen99/sales-outreach-automation-langgraph) | 0.32k | LangGraph CRM outreach automation | ai-setter | 🟡 MINE — port flow to our SDK |
| [manychat/manychat-api-php](https://github.com/manychat/manychat-api-php) | 0.02k | PHP ManyChat wrapper | ai-setter IG DM | ⚪ REFERENCE — hit REST direct |

### C14 — Trend Sentinel (namesake checks)
| Repo | ★ | What | Best fit | Verdict |
|---|---|---|---|---|
| [getsentry/sentry](https://github.com/getsentry/sentry) | — | Error monitoring | n/a | ❌ SKIP — wrong namesake |
| [abusufyanvu/6S191_MIT_DeepLearning](https://github.com/abusufyanvu/6S191_MIT_DeepLearning) | 0.25k | MIT 6.S191 course | n/a | ❌ SKIP — coursework |
| [SMByC/CCD-Plugin](https://github.com/SMByC/CCD-Plugin) | 0.05k | QGIS satellite time-series change detection | sentinel math | ⚪ REFERENCE — CCD breakpoint math = the pattern |

### C15 — System / freebee misc
| Repo | ★ | What | Best fit | Verdict |
|---|---|---|---|---|
| [fountn.design](https://fountn.design/) | n/a | Design-resource directory | dashboard FE | ⚪ REFERENCE — visual inspo |
| [supadata.ai](https://supadata.ai/) | n/a | YT/TikTok/IG → transcripts API | trend + CD | 🟢 ADOPT — replaces fragile Whisper |
| [humanizr/humanizer](https://github.com/humanizr/humanizer) | 9.7k | .NET string humanization | n/a | ❌ SKIP — .NET-only |
| [can1357/oh-my-pi](https://github.com/can1357/oh-my-pi) | 13.3k | Terminal AI agent (LSP/debugger/40+ LLMs) | dev tooling | ⚪ REFERENCE — dev workflow |
| [affaan-m/ECC](https://github.com/affaan-m/ECC) | 212k | Agent harness OS · 67 agents/271 skills · AgentShield | foundation | 🟡 MINE — lift continuous-learning + AgentShield |
| [garrytan/gstack](https://github.com/garrytan/gstack) | 111k | Virtual eng-team (CEO/QA/release) | dev + ceo-brain | 🔵 STUDY — sprint loop → CoS process |
| [JuliusBrussee/caveman](https://github.com/JuliusBrussee/caveman) | 74.3k | ~65% output-token reduction skill | system cost | 🟢 ADOPT — directly hits cost-drain incident |
| [ruvnet/ruflo](https://github.com/ruvnet/ruflo) | 60k | Multi-agent swarm + self-learning + federation | ceo-brain | 🔵 STUDY — swarm/federation for cross-brand |
| [hesreallyhim](https://github.com/hesreallyhim) | 46.8k | Curated awesome-Claude-Code list | reference | ⚪ REFERENCE — discovery index |
| [affaan-m/agentshield](https://github.com/affaan-m/agentshield) | 0.89k | Agent security scanner (configs/MCP/perms) | system security | 🟢 ADOPT — pre-client security gate |

### Top 10 picks across everything
1. **AgriciDaniel/claude-ads** — 250+ paid-ad audit checks + creative pipeline; ads + CD twofer.
2. **wshobson/agents** — Largest cross-harness library; lift agent shapes for 18-roster.
3. **affaan-m/ECC** — Continuous-learning + AgentShield directly address cost + security gaps.
4. **AgriciDaniel/claude-seo** — 25 sub-skills/18 agents mirrors our seo-aeo structure.
5. **zubair-trabzada/geo-seo-claude** — Already SEO foundation; deepen integration.
6. **JuliusBrussee/caveman** — 65% token reduction directly fixes credit-drain incident.
7. **D4Vinci/Scrapling** — Anti-bot scraping hardens Apify trend/strategy pipeline.
8. **irinabuht12-oss/google-meta-ads-ga4-mcp** — One MCP unblocks Data Analyst live-metrics gate.
9. **supadata.ai** — Drop-in video→transcript replaces Whisper for trend-researcher.
10. **AgriciDaniel/banana-claude** — Creative-Director-as-prompt-architect; exact CD match.

### Surprises / repos that changed my mind
- **indranilbanerjee/digital-marketing-pro** — Only repo encoding a true agency engagement spine (50-60 docs/brand, resumable workflows); closest competitor pattern.
- **caveman + ECC pairing** — Together answer open cost-control incident *and* AgentShield-before-client item; higher-impact than expected.
- **ALwrity** — "Brand brain" framing maps 1:1 onto our CoS direction; smaller-than-expected but conceptually validating.
- **gstack at 111k stars** — Garry Tan's sprint loop (Think→Plan→Build→Review→Ship→Reflect) is closer to a CoS process template than most "marketing" repos here.
- **manychat-api-php** — Notable only because ManyChat is dominant IG-DM rail; the wrapper is thin — for AI Setter hit REST directly from Python.
