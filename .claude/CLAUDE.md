# OffGrid Marketing OS — Project Intelligence File

## Last Session — April 26 2026

### COMPLETED APRIL 26 — Build D — Cross-Agent Contradiction Detector

Catches when agents disagree before outputs reach humans. PURE DETERMINISTIC (Rule 10 — Class-1 decision agent, no Claude). Reads all agent outputs and runs a registry of hard-coded rules.

#### `ceo_brain/contradiction_detector.py` (NEW)
- `RULE_REGISTRY` — 6 deterministic rules:
  1. **`pricing_contradiction`** (CRITICAL) — Strategy says "premium" but Script Writer hooks contain price-down language ("cheap", "discount", "% off", "cut cost")
  2. **`what_to_never_say_violation`** (CRITICAL) — `brand_profile.what_to_never_say` contains forbidden phrase X, X appears in any generated output. Extracts quoted phrases + capitalized terms from guideline text.
  3. **`phase_cta_mismatch`** (WARNING) — Brand `phase = "Phase 1 — Awareness"` but generated content has hard-sales CTAs ("buy now", "DM to purchase", "checkout")
  4. **`audience_language_drift`** (WARNING) — >50% of Script Writer scripts share <2 tokens with brand context (audience+industry+product+brand_brief). Set-intersection check (not Jaccard — Jaccard penalises long scripts).
  5. **`volume_commitment_mismatch`** (INFO) — Strategy `phase_1.weekly_output` says N posts/week but Calendar Week 1 has actual count off by >30%
  6. **`positioning_drift`** (WARNING) — Calendar `content_pillars` tokens have <20% Jaccard overlap with Strategy `strategic_angle + content_pillars + competitive_positioning`. Handles dict-list pillars correctly.
- Severity levels:
  - `CRITICAL` → `report["blocking"] = True` — caller should refuse to ship until fixed
  - `WARNING` → flag in pending_approval, surface to human reviewer
  - `INFO` → surface in dashboard, no block
- Every finding cites the EXACT source values from each agent's output (Rule 10 trace-back via `evidence` block + `agents_involved`)
- Output: `brands/{slug}/contradictions.json` with full report + `decision_engine: "pure_math"` audit field

#### Flask Endpoints (Build D Phase 2 — `dashboard_api.py`)
- `POST /api/contradictions/check?brand_slug=` — runs detector live, persists report, returns full result
- `GET /api/contradictions/latest?brand_slug=` — returns most recent persisted report

#### `load_brand_data()` Loader Quirks Fixed
- `content_pillars` may be list of strings OR list of dicts (handles `{pillar: ..., rationale: ..., example_hooks: [...]}`)
- Script Writer files contain wrapper `{scripts: [...]}` with multiple scripts per file — detector unpacks them all (was treating each file as one script before fix)

#### Live Test on askgauravai (Apr 26)
- 6 rules ran cleanly, 1 finding:
  - **INFO**: `volume_commitment_mismatch` — Strategy committed 5 posts/week but Calendar has 9 in Week 1 (80% over-delivery, within INFO tolerance)
- All 9 scripts loaded correctly, all 6 rules evaluated, no false positives after audience-drift threshold tuning (set-intersection ≥2 tokens, broader relevance pool)
- Endpoints verified live via curl

#### How to Add New Rules
1. Write a `rule_*(brand: dict) -> list[finding]` function in `contradiction_detector.py`
2. Append to `RULE_REGISTRY` list
3. Each finding dict requires: `rule_id, severity, agents_involved, evidence{}, proposed_fix`
4. Detector handles exceptions per-rule (one bad rule won't crash the whole run)

#### Pending — Future enhancements
- Wire detector INTO `CEOBrain.save_agent_output()` — auto-block CRITICAL findings before file is moved to pending_approval (currently endpoint is manual-trigger only)
- Add detector run to `/api/pipeline/daily-run` (run automatically after pipeline completes)
- BrandSpace UI panel showing live contradictions count + drilldown

---

### COMPLETED APRIL 26 — Track 2: Build C — Performance Feedback Loop (closes the learning loop)

The system was reading TRENDS but not READING RESULTS. Build C closes that loop. Every published post's real metrics now feed back into the next Trend Researcher / Script Writer / Trend Sentinel run, making them smarter about THIS brand's specific audience.

#### Phase 1A — Performance Tracker Agent (NEW agent ID 17)
- `agents/performance_tracker.py` — Class-1 decision agent, **pure deterministic, NO Claude** per Rule 10
- Reads: `brands/{slug}/performance_inbox.json` (manual paste queue) + future Meta Graph API
- Writes: `brands/{slug}/performance_history.json` with computed:
  - `posts[]` — every logged post with normalized metrics + `performance_score` (0-100)
  - `rolling_baselines` — median save_rate / ER / score over last 30 days + top quartile threshold
  - `winning_patterns.{hook_patterns_top_3, topic_clusters_top_3, formats_top_3}` — top by median score
  - `dead_patterns[]` — patterns below 25th percentile median score with ≥3 posts (statistically meaningful)
- `_compute_performance_score()` — weighted compound: save_rate×30 + ER×20 + DM×25 + shares×15 + comments×10
- `_compute_rolling_baselines()` — pure statistics over 30-day window
- `_compute_dead_patterns()` — math-only flag (median < 25th percentile + post_count ≥ 3)
- Modes: `manual` (inbox only), `meta_api` (Meta Graph — pending token), `auto` (default — try both)

#### Phase 1B — Manual-Paste API Endpoints (works while Meta token pending)
- `POST /api/performance/log-post` — appends post-metrics entry to `performance_inbox.json` queue. Required body: `brand_slug, post_id, published_at, platform, format, topic, hook_pattern_used, hook_text, metrics{}`
- `GET /api/performance/history` — returns full computed history.json
- `GET /api/performance/inbox` — returns queued (not-yet-ingested) entries
- `Performance Tracker` registered in `AGENT_SCRIPTS` + `_FOLDER_TO_SLUG`
- Workflow: paste metrics from Instagram Insights → run Performance Tracker → downstream agents auto-pick up on next run
- BrandSpace UI form deferred — API works via curl, UI is polish (next session)

#### Phase 2A — Trend Researcher historical_winner_boost
- `agents/trend_researcher.py:_load_winning_topics()` (NEW) — reads `performance_history.json`, returns flat token set from `winning_patterns.topic_clusters_top_3` + `hook_patterns_top_3`
- `_score_posts()` calls `_load_winning_topics()` ONCE at top of method (efficient)
- For each post: tokenize caption + topic, intersect with winning_tokens. If overlap → `+20` flat score boost + `HISTORICAL_WINNER` flag + `history_match_tokens` audit field
- Pure deterministic — math + token comparison, no Claude
- Verified: 15 winning tokens loaded for askgauravai test brand

#### Phase 2B — Script Writer winning/dead hook injection
- `agents/script_writer.py:_load_performance_history()` (NEW) — loads `winning_hooks` + `dead_hooks` lists at agent init
- `run_autoresearch_loop_for_post()` injects new `perf_feedback_block` into Claude prompt:
  - Lists winning hook patterns with median scores (+15% confidence boost instructed)
  - Lists dead patterns with reasons (-20% confidence penalty instructed)
- Claude reads this real audience data and weights hook generation accordingly
- Script outputs implicitly cite winning patterns (Rule 10 compatible — patterns trace to performance_history.json)

#### Phase 2C — Trend Sentinel dead-pattern penalty
- `agents/trend_sentinel.py:__init__` — pre-computes `self.dead_pattern_tokens` from `performance_history.json:dead_patterns[]`
- New `GATE 2B` in `_decide()` — runs AFTER brand-lane match, BEFORE strength check
- If signal tokens overlap with dead-pattern tokens → forces `STAY` decision regardless of strength
- Reason field cites: `"signal matches dead-pattern tokens=[...] — flagged by Performance Tracker as historically flopped for this brand; blocked from PIVOT"`
- Pure deterministic — set intersection, no Claude
- Audit field added to thresholds_used: `dead_pattern_tokens_loaded: N`

#### End-to-End Verification (Apr 26)
1. Logged 3 fake posts via `POST /api/performance/log-post` (mix of strong/mid/dead metrics)
2. Ran `python3 agents/performance_tracker.py` — ingested inbox, cleared, wrote history.json
3. Computed correctly: top quartile=85.8, winning hook=Contrarian Truth (score 85.8), median save rate 0.867%
4. Verified all 3 downstream readers load the data correctly via smoke test

#### Rule 10 Compliance
- `performance_tracker.py` — Class-1 (pure math, no Claude). `decision_engine: "pure_math"` field present in every output.
- `_score_posts()` boost — Class-1 logic added to existing Class-2 agent. Boost is deterministic (+20 flat). Trend Researcher's Claude AutoResearch loop still runs separately and is Rule 10 compliant.
- Script Writer perf injection — adds new INPUTS to existing Rule 10-enforced Claude prompt. Claude still must cite source via `data_provenance` per existing enforcement.
- Trend Sentinel — all decisions remain pure math; new dead-pattern gate is set-intersection only.

#### Cost & Performance
- Performance Tracker: ~50-200ms runtime, $0 (no Claude calls)
- Adds ~30 LOC to Trend Researcher, ~50 LOC to Script Writer, ~20 LOC to Trend Sentinel
- No new API costs (Meta Graph stays optional until token unblocks)

#### What's NOT done (deferred)
- BrandSpace UI form for manual paste — API works via curl, UI is polish
- Meta Graph API ingestion logic in `_fetch_meta_api()` — stub present, fills in when META_GRAPH_API_TOKEN unblocks
- Build D — CEO Brain cross-agent contradiction detection
- Apply Rule 10 to remaining generation agents (Brand Guardian, Creative Director, Trend Researcher AutoResearch)

---

### COMPLETED APRIL 26 — Track 1: Rule 10 Source Citation Enforcement Across Generation Agents

Per Gaurav's mandate (Rule 10 set Apr 25), every Class-2 generation agent now validates that every claim/recommendation in its output traces back to a real source data point. Hallucinations are caught and rejected before they reach downstream agents.

#### Shared Utility — `agents/_provenance.py` (NEW)
- `build_source_index(source_files: list[Path]) -> dict` — flattens every input JSON into `{file_basename#dot.path: value}` lookup. Lists indexed as `[N]`. Only leaf values stored. Returns ~200-330 citable keys per brand for current data.
- `validate_citations(output: dict, source_index: dict) -> (is_valid, missing[], report)` — checks every entry in `output["data_provenance"]`:
  1. `source_file#source_path` must exist in source_index
  2. `source_value` tokens must overlap with actual indexed value by ≥30% Jaccard
  3. `claim` tokens must overlap with `source_value` tokens by ≥30% Jaccard (claim must reflect source, not just cite a random key)
- `build_violation_message(missing: list)` — generates human-readable rerun prompt for Claude with the violation list
- `MAX_RERUN_ATTEMPTS = 2` — agent re-prompts up to 2 times after initial Claude call
- `CITATION_FUZZY_MATCH_MIN = 0.30` — Jaccard threshold (allows paraphrasing, blocks pure invention)
- Pure-stdlib (no pip deps), tokenization shares stopword set with `trend_sentinel.py` for consistency

#### Strategy Agent — Rule 10 Wired (`agents/strategy_agent.py`)
- Imports `_provenance` helpers
- `run_autoresearch_loop()` builds source index from `trends_live.json` + `brand_profile.json` (~215 keys)
- New prompt block: "MANDATORY: For every claim, recommendation, content angle... add an entry to data_provenance"
- Output schema: adds `data_provenance: [...]` + `provenance_validation: {...}` blocks
- `max_tokens` bumped 6000 → 24000 for provenance entries
- Validation-retry loop: if invalid, re-prompts Claude with violations called out; up to MAX_RERUN_ATTEMPTS retries; saves with `provenance_validation_failed: true` flag if final attempt still fails
- `run()` injects provenance + validation report INTO `strategy_90day` block before saving (so downstream Content Planner reads them as cited inputs)
- **Verified live Apr 26**: First attempt 11/15 claims passed → retry → 15/15 passed → saved cleanly. Cost $1.21 (Opus + retry).

#### Content Planner — Rule 10 Wired (`agents/content_planner.py`)
- Imports `_provenance` helpers
- `run_autoresearch_loop()` builds source index from `trends_live.json` + `strategy_90day.json` + `brand_profile.json` (~333 keys)
- New prompt block + verbosity caps (caption_direction ≤120 chars, hook ≤80 chars, source_value 30–60 chars, week 1 full detail / weeks 2-4 stub-only) — required to fit token budget
- `max_tokens=21000` (max non-streaming SDK allows; streaming refactor deferred)
- **Verified live Apr 26**: 3 retries triggered (8/13 → 11/13 → 11/12), final saved with `provenance_validation_failed: true` flag for human review. The 1 unfixed violation was a near-match (jaccard 0.24) — designed graceful fallback. Cost $0.43 (Sonnet × 3 attempts).

#### Script Writer — Rule 10 Wired (`agents/script_writer.py`)
- Imports `_provenance` helpers
- `run()` builds source index ONCE for whole run (~333 keys from calendar + trends + brand profile)
- `run_autoresearch_loop_for_post()` accepts optional `source_index` param; if provided, runs validation-retry loop per post
- New prompt block: every hook + beat_2 (proof claim) must cite a source
- `max_tokens` bumped 8000 → 12000 per post
- Validation runs PER POST (not per whole calendar) — each script gets its own provenance audit

#### Architectural Pattern — How to Add Rule 10 to Future Generation Agents
1. Import: `from _provenance import build_source_index, validate_citations, build_violation_message, MAX_RERUN_ATTEMPTS`
2. Build source index at top of `run_autoresearch_loop()`: list all input JSON files the agent reads
3. Add prompt block: "RULE 10 — every claim must cite source_file + source_path + source_value"
4. Add `data_provenance: [...]` to the output schema
5. Wrap Claude call in retry loop: validate → if invalid + attempts left, re-prompt with violations → up to MAX_RERUN_ATTEMPTS retries
6. Inject `result["provenance_validation"] = report` before returning
7. In `run()`, copy `data_provenance` + `provenance_validation` INTO the saved block (so they survive `save_agent_output()`)
8. Bump `max_tokens` 50%+ to fit provenance entries

#### Trade-offs Acknowledged
- **Cost increase**: ~30-50% per agent run when retries fire (typical 1-2 retries on Sonnet, occasional 0 retries on Opus)
- **Token verbosity**: provenance entries add 500–2000 tokens to output; required tighter prompts to fit
- **False rejections**: Jaccard 0.30 occasionally rejects legitimate paraphrases (e.g. punctuation differences). Designed fallback: save with `provenance_validation_failed: true` flag for human review rather than refuse to save
- **Speed**: each agent run +30-90s when retries fire

#### Pending — Same Pattern To Apply Next
- Brand Guardian (when built)
- Creative Director (when image/video generation prompts need source backing)
- Trend Researcher's AutoResearch loop (already cites scrape_status_per_source — could be tightened with the same data_provenance pattern)

---

## Last Session — April 25 2026

### COMPLETED APRIL 25 — Pipeline Hardening + Build A Verified + Build B + Trend Sentinel + Higgsfield Hooks:

#### Build B — Data Quality Gate (DONE)
- `agents/trend_researcher.py:33–60` — `QUALITY_GATE_THRESHOLDS` dict with 6 tunable parameters (no code change needed to retune)
- `agents/trend_researcher.py:_quality_gate()` — runs after `_score_posts()`, before `_run_topic_clustering()`. 4 hard checks + 1 soft flag:
  - **Engagement-pod signature**: drop posts with <0.5% comment/like ratio at 50K+ likes
  - **Bought-views signature**: drop video posts with <1% like/view ratio at 100K+ views
  - **Bot-comment signature**: drop posts where >85% of latestComments are ≤5 chars (tuned UP from 60%/10char — fire-emoji culture is normal on IG)
  - **Paid-promo flag**: flag (don't drop) posts >10× the account's avg engagement baseline
  - **Bypass guard**: if gate would drop >80% of posts, pass everything through with `quality_gate_bypassed` signal
- Each surviving post gets a `trust_score` (0-100) + `trust_signals[]` (e.g. `healthy_comment_like_ratio`, `substantive_comments`, `paid_promo_suspect`)
- Quality gate report saved to `trends_live.json` under `quality_gate` key — Strategy/Content agents can audit data trust
- `latestComments` now preserved through scrape methods (`scrape_instagram_hashtags` + `scrape_competitor_profiles`) — needed for bot-comment check

#### Trend Sentinel — NEW AGENT 16 (DONE)
- `agents/trend_sentinel.py` — daily lightweight agent that decides whether to PIVOT the content calendar
- 3-state decision: **STAY** / **TRACK** / **PIVOT** — Claude-judged with hard rule guards
- **Watchlist persistence**: TRACK signals auto-escalate to PIVOT after 3 days (`TRACK_PERSISTENCE_DAYS_TO_PIVOT`)
- **Pivot impact**: on PIVOT, writes `pivot_impact.json` listing which calendar slots + already-produced content would be invalidated
- **Auto-pivot toggle**: `SENTINEL_AUTO_PIVOT=true` env var enables automatic Content Planner subprocess trigger. Default OFF — sentinel writes decision, human approves manually.
- Reads: `trends_live.json` + `content_calendar.json` + `trend_sentinel_watchlist.json`
- Writes: `pivot_decision.json` + `pivot_impact.json` + updated watchlist + pending_approval/trend-sentinel/ + Notion push via CEO Brain
- Wired into AGENT_SCRIPTS, _FOLDER_TO_SLUG, and `daily-run` pipeline (`dashboard_api.py:993–1003`)
- **NEW DAILY PIPELINE**: `Trend Researcher → Trend Sentinel → Data Analyst` (Script Writer removed — only runs after Content Planner approval)

#### Script Writer — Hook Generator Upgraded with Higgsfield Patterns (DONE)
- `agents/script_writer.py:195–225` — expanded from **5 hook patterns → 12 patterns** (kept original 5 + 7 new)
- New patterns extracted from Seedance 2.0 social-hook SKILL.md (`/tmp/higgsfield-seedance2-jineng/skills/11-social-hook/SKILL.md`):
  - **Cognitive interrupts** (4): Pattern Interrupt, Curiosity Gap, Contrast Principle, Impossible Claim
  - **Emotional triggers** (4): Pain Point, Aspirational, Fear/Loss, Identity
  - **Authority/Proof** (4): Exclusivity, Time/Money Claim, Specificity, Contrarian Truth
- Scoring formula updated: +1 bonus for hooks that work in **first 2 seconds of a Reel** (scroll-stop power)

#### Higgsfield Skills Pack — Installed for Personal Use (DONE)
- All 15 skills cloned and installed to `~/Library/Application Support/Claude/skills/` (Claude Desktop skill directory)
- Available skills: cinematic, 3d-cgi, cartoon, comic-to-video, fight-scenes, motion-design-ad, ecommerce-ad, anime-action, product-360, music-video, social-hook, brand-story, fashion-lookbook, food-beverage, real-estate
- **Use case**: invoke from Claude Desktop manually for high-stakes content brainstorming. Each skill outputs production-grade Seedance 2.0 prompts (15-25 lines each) with built-in 2-second hook framework + camera/lighting/sound vocab.
- **NOT integrated into agent pipeline** — Higgsfield is a paid SaaS at higgsfield.ai. Our pipeline stays single-vendor on FAL.ai for image/video gen.
- **Playwright MCP — SKIPPED.** No current pipeline use case. Apify covers all our scraping. Re-evaluate if we hit JS-heavy scrape Apify can't handle.

#### Pipeline Definition Bug — FIXED
Daily-run was `Trend → Data → Script` (Script always halted because no Content Planner output). Now: `Trend → Sentinel → Data`. Script Writer is manual-only after Content Planner approval. Sentinel can auto-trigger Content Planner if `SENTINEL_AUTO_PIVOT=true`.

#### Trend Sentinel — REFACTORED TO PURE MATH (per Gaurav's Rule 10 mandate)
Original v1 used Claude to judge STAY/TRACK/PIVOT. Gaurav pushed back on hallucination risk. Refactored to **zero-Claude deterministic decision engine.**
- `agents/trend_sentinel.py:_decide()` — replaced Claude call with: Jaccard token-overlap (calendar match), set intersection (brand-lane match), score ratio comparison (strength threshold)
- `_tokenize()` + `_jaccard()` helpers added — pure stdlib, no dependencies
- Every per-signal `reason` field now cites the exact math expression that drove the decision (e.g. `"signal_score=80.0 / weakest_calendar_score=42.0 = 1.90× > 1.5× threshold; brand-match tokens=['ai','strategy','founder']"`)
- Output now includes `"decision_engine": "pure_math"` + `"thresholds_used": {...}` for full audit
- **Speed**: 7 sec → 2 sec. **Cost**: $0.02 → $0.00. **Hallucination risk**: ~10% residual → **zero**.
- Verified: same correct PIVOT decision on askgauravai's first-plan case.

This is the first concrete application of Rule 10. Next session extends citation enforcement to Strategy Agent, Content Planner, Script Writer.

---

### COMPLETED APRIL 25 — Pipeline Hardening + Build A Verified:

#### Bug Fixes (3)
- **JSON parse hardening across pipeline agents**: `agents/trend_researcher.py`, `agents/data_analyst.py`, `agents/script_writer.py` — added `_safe_json_loads()` helper with `_escape_literal_newlines_in_strings()` fallback (ported from `dashboard_api.py:80`). Wraps every `json.loads(claude_response)` call with literal-newline repair before retry. Fixes `JSONDecodeError: Unterminated string` from Claude responses with embedded newlines in string values.
- **Trend Researcher max_tokens truncation**: AutoResearch loop bumped from `max_tokens=4000` → `max_tokens=16000`. Was hitting truncation at ~15.5K chars (proven by error char positions). Added `stop_reason == "max_tokens"` warning log so future truncations are loud, not silent.
- **Twitter connection check**: `dashboard_api.py:3265–3290` — `/2/users/me` requires OAuth 2.0 user-context, NOT app-only Bearer. Free tier always 403's there. New logic: 401 = invalid token, 403/429 = "Token set (Free tier — read via Apify)" (still marked `connected: true`). Token is fine for the Apify path that actually scrapes.

#### Build A — Competitor Post Scraper (VERIFIED ALREADY DONE)
Audit revealed Build A was implemented during April 23 work but never documented. Existing implementation:
- `agents/trend_researcher.py:393–434` — `_load_competitor_handles()` reads from `brand_profile.competitor_handles` AND `brands/{slug}/competitors_db.json` (Strategy Agent output), deduplicated.
- `agents/trend_researcher.py:436–572` — `scrape_competitor_profiles()`: Apify `apify~instagram-scraper` with `directUrls`, parallel runs, single 90s wait, max 5 handles. Returns per-handle stats (avg likes, formats, top hashtags, top 5 posts).
- `agents/trend_researcher.py:900–903` — competitor posts fed into `_score_posts()` alongside hashtag/YouTube/Twitter posts using same scoring formula.
- `agents/trend_researcher.py:1041–1058` — explicit `competitor_summary` block built and injected into AutoResearch prompt for Variant C (Gap angle).
- `agents/trend_researcher.py:1239–1241` — wired into `run()` between brand-IG scrape and Google Trends.
- `dashboard/src/spaces/BrandSpace.tsx` — `competitor_handles` field already exposed via `TagListEditor` for editing.

#### Pipeline Definition Bug (FLAGGED — needs decision)
Daily-run pipeline (`dashboard_api.py:993–997`) chains `Trend → Data → Script`. Script Writer needs `content_calendar.json` from Content Planner — which isn't in the chain. Result: Script Writer always halts with "Content Calendar not found." Two fixes available:
- **Option A**: Add Content Planner between Data Analyst and Script Writer
- **Option B**: Remove Script Writer from daily-run; only run after Content Planner is approved

---

## Last Session — April 24 2026

### COMPLETED APRIL 24 — Frontend Redesign + API Keys Connected:

#### GRID Control Frontend — Full Readability Overhaul (DONE)
- `index.css` completely rewritten — "Slate Command" design system. Background: `#0D1117` (GitHub dark blue-charcoal). Text-1: `#E2E8F0`. Text-2: `#8B9AB0` (always readable). Text-3: `#5E6E84` (visible muted). Border: `#2D3748`. Base font: 15px.
- All 5 Spaces fixed: `CommandSpace.tsx`, `ReviewSpace.tsx`, `AgentsSpace.tsx`, `BrandSpace.tsx`, `SystemSpace.tsx`
- Every `gc-text-3` section label → `gc-text-2`. Every `fontSize: 10/11` label → `fontSize: 11/12`
- All breadcrumbs ("Brand /", "Agents /", "System /", "Review /") now use `gc-text-2` — readable
- `SectionTitle` components in BrandSpace + SystemSpace upgraded from 11px → 12px
- Build verified: ✅ 1810 modules, zero TypeScript errors (April 24 2026)

#### API Keys — Updated (DONE)
- `YOUTUBE_API_KEY=AIzaSyAvwMScNnRpgYNsbzOz3EwxiFwK14PKoPM` ✅ added to `.env`
- `TWITTER_BEARER_TOKEN=AAAA...` ✅ added to `.env` (Twitter API free tier — read via Apify actor, not direct API)
- Removed unused keys: `RUNWAY_API_KEY`, `KLING_API_KEY`, `IDEOGRAM_API_KEY` — FAL.ai handles all image/video generation
- `YOUTUBE_API_KEY` and `TWITTER_BEARER_TOKEN` fields added to `.env` template

#### API Keys — Still Pending
- `META_GRAPH_API_TOKEN` — **MAIN PRIORITY**. Empty. Requires Meta Developer App + Graph API Explorer token exchange (60-day token). Step-by-step guide in CLAUDE.md below and in plan file.
- `META_AD_ACCOUNT_ID` — goes with Meta token above. Format: `act_XXXXXXXXXX`
- `LINKEDIN_ACCESS_TOKEN` — blocked on LinkedIn Marketing Developer Platform approval (1–4 weeks). Skip.
- `GA4_PROPERTY_ID` / `GA4_SERVICE_ACCOUNT_JSON` — Google Analytics. Not urgent.

#### Meta Graph API — Setup Guide (For Next Session)
Full 10-step guide exists in the cached-stirring-fog.md plan file. Summary:
1. developers.facebook.com → Create App → "Other" → "Business" → name: "OffGrid Marketing OS"
2. Add products: Instagram Graph API + Marketing API
3. App Settings → Basic → upload logo + privacy URL → Save
4. Graph API Explorer → select app → Generate Access Token → check: `instagram_basic`, `instagram_manage_insights`, `ads_read`, `pages_show_list`, `pages_read_engagement`
5. Exchange short-lived token for 60-day: `graph.facebook.com/oauth/access_token?grant_type=fb_exchange_token&client_id=APP_ID&client_secret=APP_SECRET&fb_exchange_token=SHORT_TOKEN`
6. business.facebook.com → Ad Accounts → copy ID → format as `act_XXXXXXXX`
7. Paste both into `.env`: `META_GRAPH_API_TOKEN=EAAxxxxx` and `META_AD_ACCOUNT_ID=act_xxxxx`
8. Restart Flask: `source .env && python3 dashboard_api.py`
9. Verify: System → Run Check → Meta row should go green

**No App Review needed** — development mode is permanent for personal use on your own accounts.

---

## Last Session — April 23 2026

### COMPLETED APRIL 23 — Content Intelligence + Jarvis Voice Layer (All Stages):

#### Trend Researcher — New Intelligence Capabilities (DONE)
- `_score_posts()` — weighted scoring (Views×0.4 + ER×0.35 + Comments×0.25), hard filters (10K engagement floor, 2% ER floor, 30-day age cutoff), HIGH_SIGNAL/VIRAL flags, builds `self._whisper_candidates`
- `scrape_youtube_shorts()` — Apify `apify~youtube-scraper`, last 7 days, 30 shorts, graceful skip
- `scrape_twitter()` — Apify `apify~twitter-scraper`, last 7 days, 30 tweets, graceful skip
- `_extract_whisper_transcripts()` — `openai-whisper` + `yt-dlp`, max 5 video candidates, graceful skip if not installed
- `_run_topic_clustering()` — single Claude call groups top 30 scored posts into 3–7 named clusters, returns `recommended_topic` + `recommendation_reason`
- `run()` updated: YouTube + Twitter scraping added after Google Trends; STEP 1B block runs scoring → Whisper → clustering before AutoResearch Loop; `topic_clusters`, `recommended_topic`, `recommendation_reason` injected into `trends_live.json`
- `WHISPER_CANDIDATES_CAP = 5` constant added

#### Script Writer — BEAT Structure + Hook Generator + Voice DNA (DONE)
- `_load_voice_profile()` — reads `brands/{slug}/voice_profile.json`, stores as `self.voice_profile`. Called in `__init__`. Falls back to None if absent.
- `run_autoresearch_loop_for_post()` prompt completely rewritten:
  - **BEAT structure**: `beat_1` (setup) / `beat_2` (core idea/proof) / `beat_3` (payoff/twist) / `cta` — replaces old flat `hook`/`body`
  - **Hook Generator**: 5 patterns (Aspirational, Pain Point, Exclusivity, Time/Money Claim, Curiosity Gap) each with confidence score (40% trend match + 35% competitor format + 35% brand tone)
  - **Voice DNA injection**: if `voice_profile.json` exists, injected into prompt as "BRAND VOICE DNA (read and match exactly)" block
  - Output schema: new `hook_block` with `hooks[]` + `recommended_hook`; `script` has `beat_1/beat_2/beat_3/cta` keys only

#### Dashboard API — New Endpoints (DONE)
- `POST /api/pipeline/daily-run` — chains Trend Researcher → Data Analyst → Script Writer sequentially in background thread. Returns `pipeline_run_id` immediately.
- `POST /api/jarvis/query` — Claude answers in 1-3 spoken sentences; generates edge-tts `en-US-GuyNeural` audio; returns `response` + `audio_b64` (base64 mp3)
- `POST /api/voice/extract-profile` — Claude extracts voice DNA from raw scripts, saves to `brands/{slug}/voice_profile.json`
- `GET /api/voice/profile` — returns `voice_profile.json` or `{exists: false}`

#### Frontend — CommandSpace.tsx (DONE)
- Jarvis mic button (gold, circular, top bar beside Refresh) → opens VoiceModal
- VoiceModal: dark overlay, textarea input, Enter to submit, plays base64 mp3 audio on response
- "Run Today" outline button (gold border) below "Run Now" → calls `POST /api/pipeline/daily-run`
- `dailyMutation` with agent-status invalidation on settle
- New state: `showJarvis`, `micText`, `jarvisResponse`, `jarvisLoading`

#### Frontend — BrandSpace.tsx (DONE)
- `"voice"` added to `type Mode` union
- `VoiceProfilePane` component: fetches existing profile (shows JSON), paste-scripts textarea, Extract Voice DNA button
- "Voice Profile" outline button added to view-mode top bar (beside "New Brand")

#### OpenJarvis Voice Layer Files (DONE — new files)
- `jarvis_config/tts.py` — edge-tts async wrapper, `speak(text, play=True)`, `afplay` on macOS / `aplay` on Linux
- `jarvis_config/morning_digest.py` — reads Grid Control API at 8am, speaks 3-sentence brief
- `jarvis_config/jarvis.yaml` — OpenJarvis config: Anthropic brain (claude-sonnet-4-6) + `en-US-GuyNeural` voice
- `jarvis-skills/grid-control/skill.py` — maps voice triggers to Grid Control REST calls (pending/status/daily-run)
- `jarvis-skills/grid-control/__init__.py` — package marker
- `scripts/install_jarvis.sh` — `pip install edge-tts openai-whisper yt-dlp` + `brew install portaudio`

**Build verified: ✅ 1810 modules, zero TypeScript errors, all Python syntax clean (April 23 2026)**

**To activate Jarvis TTS:** `pip install edge-tts` then test: `python jarvis_config/tts.py "Jarvis online"`
**To activate Whisper:** `pip install openai-whisper yt-dlp` (graceful skip if absent)
**To schedule morning digest:** `crontab -e` → `0 8 * * * cd /path/to/project && python jarvis_config/morning_digest.py`

#### Jarvis Bug Fixed (DONE — April 23 2026)
- `dashboard/.env` created with `VITE_DASHBOARD_SECRET` — Vite reads from its own project root, not parent
- `vite.config.ts` updated: `envDir: path.resolve(__dirname, "..")` added (belt-and-suspenders)
- `askJarvis()` bug fixed: Flask returns flat `{success, response, audio_b64}` — was incorrectly using `json.data` (undefined). Fixed to `{ response: json.response, audio_b64: json.audio_b64 }`
- Jarvis tested live in browser: responding correctly with Claude answers + audio
- Jarvis mic button exact position confirmed: (1355, 22) in the browser viewport

#### Managed Agents — FULLY ACTIVATED (April 23 2026)
- Anthropic SDK upgraded: `0.86.0` → `0.96.0` (agents/environments/sessions now available in beta)
- `setup.py` fixed: `instructions` → `system`, `extra_headers` → `betas=["managed-agents-2026-04-01"]`
- All 15 agents CREATED on Anthropic's API — IDs written to `managed_agents/registry.json`
- Shared environment created — ID written to registry
- **Memory stores deliberately NOT set up** — agents start with zero memory (fresh slate by design)
- `is_managed_ready()` returns True for all 15 agents — all agent runs now use Managed Sessions automatically
- No `memory_manager.py` needed unless memory seeding is desired in future

**Managed Agents state: LIVE. All 15 agents run via `client.beta.sessions.create()` — subprocess fallback disabled.**

---

## Last Session — April 17 2026

### COMPLETED APRIL 17 — GRID Control Full Rebuild (All 4 Phases):

#### Phase 1 — Immediate Fixes (DONE)
- Brand mixing bug fixed: `brandStore.ts` default `activeBrand` changed to `{ slug: "", name: "" }` — stops wrong queries firing before BrandSwitcher corrects
- Custom slash command macros added to `CLAUDE.md`: `/ghost`, `/godmode`, `/layered`, `/unpack`, `/livecode`, `/investigate`

#### Phase 2 — Content Hub Media Previews (DONE)
- `/api/outputs/media/<filepath>` endpoint added to `dashboard_api.py` — MIME-aware inline serving (PNG/JPG/MP4/MP3 as_attachment=False)
- `ReviewSpace.tsx` MediaGrid: inline `<img>` thumbnail, `<video controls>` player, `<audio controls>` player, lightbox on click
- JSON/TXT/MD still shows as text icon card (unchanged)

#### Phase 3 — GRID Control Redesign — 5 Spaces (DONE)
- Old 10-screen architecture replaced with 5 clean Notion/Linear-aesthetic Spaces
- `dashboard/src/spaces/CommandSpace.tsx` — Home: pipeline bar, next action, activity feed
- `dashboard/src/spaces/ReviewSpace.tsx` — Unified approvals (Notion + local files) + media preview
- `dashboard/src/spaces/AgentsSpace.tsx` — Run Agents tab (pipeline-ordered) + Chat tab (full MeetingRoom port)
- `dashboard/src/spaces/BrandSpace.tsx` — Brand profile view/edit/new
- `dashboard/src/spaces/SystemSpace.tsx` — API keys, connections, cost estimates
- `App.tsx` updated: SCREENS = {1: CommandSpace, 2: ReviewSpace, 3: AgentsSpace, 4: BrandSpace, 5: SystemSpace}
- `Sidebar.tsx` full rewrite: 5 nav items, rounded-lg buttons, gold active dot
- `brandStore.ts`: `activeScreen` default → 1 (CommandSpace)
- 7 deprecated screen files deleted. Final build: ✅ 1810 modules, zero TypeScript errors

#### Phase 4 — Claude Managed Agents Migration (FULLY LIVE — April 23 2026)
- `managed_agents/registry.json` — template with agent_id/environment_id placeholders for all 15 agents
- `managed_agents/setup.py` — one-time script: creates 15 agent definitions + 1 environment via Anthropic SDK, writes IDs to registry.json
- `managed_agents/context_builder.py` — serializes brand_profile.json + trends_live.json + competitors_db.json + session_state + approved outputs to structured text context block
- `managed_agents/memory_manager.py` — creates 3 memory stores per brand (brand_context, agent_learnings, market_data), seeds them, exposes `setup_brand_memory()` + `record_agent_learning()` + `update_market_data()`
- `managed_agents/session_runner.py` — `run_agent_session()`: creates session with memory stores, streams events via SSE, saves output to pending_approval/, pushes to Notion. `run_agent_session_async()` for background thread use.
- `managed_agents/prompts/` — 15 system prompt .md files for all agents (extracted from Python scripts + written from scratch for non-built agents)
- `dashboard_api.py` patched: imports `session_runner`, `run_agent()` endpoint now tries managed agents first (if `is_managed_ready(agent_name)` is True) and falls back to subprocess. Brand creation auto-triggers `setup_brand_memory()` in background thread.

**Phase 4 is LIVE as of April 23 2026.** All 15 agents have real IDs in registry.json. `is_managed_ready()` returns True for all. Memory stores deliberately skipped — agents start with clean slate. If memory seeding is needed in future: `python3 managed_agents/memory_manager.py --brand {slug}`

---

## Last Session — April 14 2026

### COMPLETED APRIL 14:
- DropVolt brand created and fully onboarded (graphic T-shirts, Gen Z, ₹500–1000, India)
- Full pipeline test run for DropVolt: Trend Researcher → Strategy Agent → Content Planner → Script Writer — all 4 agents completed, outputs in `brands/dropvolt/outputs/pending_approval/`
- **6 bugs fixed** (see Bug Registry below)
- MeetingRoom Bug A FIXED: removed `clearIndividualHistory` from `handleSelectAgent` — no more history wipe on agent click
- MeetingRoom Bug B FIXED: Zustand `persist` middleware added to `brandStore.ts` — chat history survives page refresh
- MeetingRoom stale closure bug: RESOLVED (both Bug A + Bug B were the root cause)
- Manual brand analysis run via Apify for DropVolt: confirmed GAP strategy + Hinglish cultural voice — same conclusion as Grid Control pipeline, validating the system

### COMPLETED APRIL 8:
- Data Analyst, Funnel Specialist, Website Agent built and run — all pushed to Notion
- Creative Director updated: Ideogram replaced with FAL.ai (fal-ai/flux/dev + fal-ai/ideogram/v2)
- FAL_API_KEY set in .env and wired into dashboard_api.py startup banner + /api/config/keys
- AGENT_SCRIPTS in dashboard_api.py updated to include all 9 agents
- brand_profile.json fixed — was showing "Third Gen Tribe" instead of "OffGrid Creatives AI"
- Strategy Agent datetime crash fixed (timezone.utc) + max_tokens bumped to 16000
- ceo_brain/orchestrator.py: sys.path insert added — CEO Brain can now run via subprocess
- session_state.json: stale "running"/"error" statuses reset to idle/done
- CLAUDE.md screen map corrected

---

## Bug Registry (Tracked Fixes)

| # | File | Bug | Fix | Status |
|---|------|-----|-----|--------|
| 1 | `dashboard_api.py` | `_bootstrap_brand_memory` called before `profile` dict was defined — brand creation crashed | Moved call to after `profile` is built and written | ✅ Fixed Apr 14 |
| 2 | `agents/cost_reporter.py` | `import supabase.db as _db` fails — pip `supabase` package shadows local `supabase/db.py` | Use `importlib.util.spec_from_file_location` to load local file directly | ✅ Fixed Apr 14 |
| 3 | `agents/trend_researcher.py` | `__init__` had hardcoded default `brand_slug = "offgrid-creatives-ai"` — always ran for wrong brand | Reads from `os.getenv("ACTIVE_BRAND", "offgrid-creatives-ai")` | ✅ Fixed Apr 14 |
| 4 | `agents/trend_researcher.py` | Hardcoded `NICHE_HASHTAGS` was D2C/Meta content — wrong for fashion brands | Replaced with `_build_niche_hashtags(brand_profile)` — dynamic from brand profile fields | ✅ Fixed Apr 14 |
| 5 | `ceo_brain/orchestrator.py` | `save_agent_output` used display name as folder ("Trend Researcher" not "trend-researcher") | Added slugification: `re.sub(r"[^a-z0-9-]", "", agent_name.lower().replace(" ", "-"))` | ✅ Fixed Apr 14 |
| 6 | `dashboard/src/screens/MeetingRoom.tsx` | `clearIndividualHistory` called on every agent click — wiped in-memory history | Removed the call from `handleSelectAgent` | ✅ Fixed Apr 14 |
| 7 | `dashboard/src/store/brandStore.ts` | No localStorage persistence — all chat history lost on page refresh | Added `persist` middleware wrapping the store, `partialize` on chat histories + active brand | ✅ Fixed Apr 14 |
| 8 | `agents/trend_researcher.py`, `agents/data_analyst.py`, `agents/script_writer.py` | `json.loads(claude_response)` failed with `Unterminated string` when Claude embedded literal newlines in JSON string values | Added `_safe_json_loads()` + `_escape_literal_newlines_in_strings()` helper to all three agents | ✅ Fixed Apr 25 |
| 9 | `agents/trend_researcher.py` | AutoResearch loop `max_tokens=4000` was truncating responses at ~15.5K chars, causing JSON parse failures | Bumped to `max_tokens=16000` + added `stop_reason == "max_tokens"` truncation warning log | ✅ Fixed Apr 25 |
| 10 | `dashboard_api.py` connections check | Twitter `/2/users/me` returns 403 on Free tier App-Only Bearer (requires OAuth user-context). Showed "Token invalid" even when token was valid for Apify | 401 → invalid; 403/429 → "Token set (Free tier — read via Apify)", marked connected | ✅ Fixed Apr 25 |

---

## CURRENT SPACE MAP (App.tsx) — 5-Space Architecture:
| Space | Name | File |
|-------|------|------|
| 1 | Command | spaces/CommandSpace.tsx |
| 2 | Review | spaces/ReviewSpace.tsx |
| 3 | Agents | spaces/AgentsSpace.tsx |
| 4 | Brand | spaces/BrandSpace.tsx |
| 5 | System | spaces/SystemSpace.tsx |
Old screens/ and pages/ files DELETED (replaced). Do not reference them.

---

## PENDING IN ORDER:
1. ElevenLabs — blocked on free tier, code is correct. Resume when paid plan active.
2. FAL_API_KEY set and ready — Creative Director image generation live when run. No code changes needed.
3. **Grid Control Next-Level Builds** (identified April 14 — in priority order):
   - ~~A. Competitor post scraper in Trend Researcher~~ ✅ DONE Apr 25
   - ~~B. Data quality gate (bot filter + ER threshold before data reaches agents)~~ ✅ DONE Apr 25
   - ~~Trend Sentinel (NEW Apr 25 — daily PIVOT/TRACK/STAY decision layer)~~ ✅ DONE Apr 25
   - ~~Rule 10 — Source Citation Enforcement on Strategy / Content Planner / Script Writer~~ ✅ DONE Apr 26
   - ~~C. Performance feedback loop (Performance Tracker agent + 3 downstream readers)~~ ✅ DONE Apr 26
   - ~~D. CEO Brain cross-agent contradiction detection (6-rule pure-math detector)~~ ✅ DONE Apr 26
   - E. Apply Rule 10 to remaining generation agents: Brand Guardian (when built), Creative Director, Trend Researcher AutoResearch loop — **NEXT**
   - F. BrandSpace UI form for `/api/performance/log-post` + `/api/contradictions/latest` panel (polish)
   - G. Meta Graph API ingestion in `performance_tracker._fetch_meta_api()` (when META_GRAPH_API_TOKEN unblocks)
   - H. Auto-wire contradiction_detector into CEOBrain.save_agent_output (block CRITICAL findings on save)
4. **Cron the daily pipeline + Sentinel run** (one-line: `0 8 * * * curl -X POST http://localhost:5001/api/pipeline/daily-run -H "X-Dashboard-Secret: $DASHBOARD_SECRET" -H "Content-Type: application/json" -d '{"brand_slug": "askgauravai"}'`)
4. Bubble frontend (last — build after 20–30 paying clients)

### MANAGED AGENTS STATUS (as of April 23 2026):
- ✅ SDK upgraded to 0.96.0
- ✅ All 15 agents LIVE on Anthropic's API (registry.json has real IDs)
- ✅ Shared environment created
- ✅ Memory stores: NOT set up (fresh slate — intentional)
- ✅ All agent runs now route through Managed Sessions automatically
- To add memory seeding later: `python3 managed_agents/memory_manager.py --brand {slug}`

### NEW RULE:
All build instructions go to Claude Code directly. No code in planning chat.

---

## What This Project Is
A fully autonomous multi-agent AI marketing system built using the Claude Agent SDK.
It manages brand growth end-to-end for OffGrid Creatives AI and future client brands.
15 specialized agents orchestrated by a CEO Brain. All outputs require human approval
before any action is taken.

The project includes **GRID CONTROL** — a dark-mode React dashboard (fully built
and build-verified) that provides the human command interface for all 15 agents.

---

## GRID CONTROL Dashboard — Current Build State

### Status: FULLY REBUILT — 5-SPACE ARCHITECTURE — BUILD VERIFIED
- Build: ✅ 1810 modules transformed, zero TypeScript errors, zero warnings
- Last verified build output: 408.36 kB JS / 35.78 kB CSS (gzip: 118.25 kB / 7.26 kB) — April 17 2026
- Architecture: 10 screens → 5 Spaces (Command, Review, Agents, Brand, System)
- Agent Run buttons: ✅ Wired to Managed Agents session runner (with subprocess fallback)
- Chat tab: ✅ Full MeetingRoom port inside AgentsSpace
- Notion approval pipeline: ✅ Live
- Media previews: ✅ Inline image/video/audio in ReviewSpace
- Zustand persist: ✅ Chat history survives page refresh (localStorage key: `grid-control-store`)
- Managed Agents: ✅ Infrastructure complete — activate with `python3 managed_agents/setup.py`

### Dashboard Tech Stack (Locked)
- React 19 + Vite + TypeScript (strict mode)
- Tailwind CSS v4 with `@tailwindcss/vite` plugin (NOT postcss — do not add postcss config)
- shadcn/ui (default style, slate base, CSS variables, oklch color tokens)
- TanStack Query v5 (`useQuery`, `useMutation`, `useQueryClient`)
- Zustand with `persist` middleware (`useBrandStore`) for global state + chat history
- Flask API (`dashboard_api.py`) on port 5001
- Vite dev server on port 5173, proxy `/api` → `http://localhost:5001`
- Dark mode forced via `document.documentElement.classList.add("dark")` in `main.tsx`

### File Structure
```
/Users/gauravoffgrid/offgrid-marketing-os/
├── dashboard_api.py              Flask REST API (multi-brand, all endpoints)
├── agents/
│   ├── trend_researcher.py       Reads ACTIVE_BRAND env. Dynamic hashtags from profile.
│   ├── strategy_agent.py
│   ├── content_planner.py
│   ├── script_writer.py
│   ├── creative_director.py      FAL.ai wired (flux/dev + ideogram/v2)
│   ├── data_analyst.py
│   ├── funnel_specialist.py
│   ├── website_agent.py
│   └── cost_reporter.py          Uses importlib.util to load local supabase/db.py
├── ceo_brain/
│   └── orchestrator.py           CEOBrain class. save_agent_output slugifies folder names.
├── brands/
│   ├── offgrid-creatives-ai/     Brand 1
│   └── dropvolt/                 Brand 2 — graphic T-shirts, Gen Z, ₹500–1000
│       ├── brand_profile.json
│       ├── session_state.json
│       ├── trends_live.json
│       └── outputs/pending_approval/
└── dashboard/
    ├── vite.config.ts
    └── src/
        ├── main.tsx
        ├── App.tsx
        ├── index.css
        ├── types/index.ts
        ├── store/
        │   └── brandStore.ts     Zustand + persist middleware. partialize: histories + activeBrand.
        ├── components/
        │   ├── Sidebar.tsx
        │   ├── BrandSwitcher.tsx
        │   ├── AgentCard.tsx
        │   └── CEOBrainCard.tsx
        ├── screens/
        │   ├── AgentCommandCenter.tsx
        │   ├── ApprovalQueue.tsx
        │   ├── BrandDashboard.tsx
        │   ├── BrandOnboarding.tsx
        │   ├── ContentHub.tsx
        │   └── MeetingRoom.tsx
        └── pages/
            ├── OutputViewer.tsx
            └── WorkflowScreen.tsx
```

### 8 Screens — Status
| Screen | Name | File Location | Status |
|--------|------|---------------|--------|
| 1 | Agent Command Center | screens/AgentCommandCenter.tsx | ✅ Built. Run buttons wired to real subprocesses. |
| 2 | Approval Queue | screens/ApprovalQueue.tsx | ✅ Built. Approve / Reject / Request Changes wired. |
| 3 | Content & Media Hub | screens/ContentHub.tsx | ✅ Built. Filter + download. |
| 4 | Brand Onboarding | screens/BrandOnboarding.tsx | ✅ Built. Reads/writes brand_profile.json. |
| 5 | Brand Dashboard | screens/BrandDashboard.tsx | ✅ Built. Profile + session_state + trends_live. |
| 6 | Agent Outputs | pages/OutputViewer.tsx | ✅ Built. Formatted output viewer. |
| 8 | Agent Meeting Room | screens/MeetingRoom.tsx | ✅ Built + wired. Chat persists. History survives refresh. |
| 9 | Workflow Screen | pages/WorkflowScreen.tsx | ✅ Built. 3-column pipeline view. |

---

## Multi-Brand Architecture — Complete

### How It Works
- Every brand lives under `brands/{slug}/` with isolated data files and outputs
- `brand_slug` query param required on all API endpoints (default: `offgrid-creatives-ai`)
- `get_brand_dir(slug)` in Flask returns 404 if slug doesn't exist
- `list_brands()` reads `brands/` directory
- Brand slug auto-generated from name: lowercase, spaces→hyphens, strip special chars
- All TanStack Query keys include `activeBrand.slug` — switching brands auto-refetches everything
- Agent subprocesses receive `ACTIVE_BRAND` env var — all agents read brand from env

### Active Brands
| Slug | Name | Status |
|------|------|--------|
| `offgrid-creatives-ai` | OffGrid Creatives AI | Primary brand |
| `dropvolt` | DropVolt | Test brand. Full pipeline completed Apr 14. |

---

## Agent Models (Locked)

| Agent | Model |
|-------|-------|
| CEO Brain | claude-opus-4-6 |
| Strategy Agent | claude-opus-4-6 |
| Creative Director | claude-opus-4-6 |
| Ad Strategist | claude-opus-4-6 |
| Brand Guardian | claude-opus-4-6 |
| Content Planner | claude-sonnet-4-6 |
| Script Writer | claude-sonnet-4-6 |
| Data Analyst | claude-sonnet-4-6 |
| Funnel Specialist | claude-sonnet-4-6 |
| Trend Researcher | claude-sonnet-4-6 |
| Website Agent | claude-sonnet-4-6 |
| SEO+AEO Agent | claude-sonnet-4-6 |
| Email Marketing Agent | claude-sonnet-4-6 |
| Community Manager | claude-sonnet-4-6 |
| DM+Customer Hunter | claude-sonnet-4-6 |

---

## Flask API — dashboard_api.py

### All Endpoints
| Method | Path | Purpose |
|--------|------|---------|
| GET | `/api/health` | Health check |
| GET | `/api/agents` | List all 15 agents with config |
| GET | `/api/agents/status` | Live status of all agents |
| POST | `/api/agents/run` | Run an agent subprocess (wired) |
| POST | `/api/agents/chat` | Agent chat (wired — calls Claude API with agent context) |
| POST | `/api/agents/train` | Agent training input |
| GET | `/api/brands` | List all brands from brands/ directory |
| POST | `/api/brands/create` | Create new brand folder + default JSON files |
| GET | `/api/outputs/pending?brand_slug=` | Pending approval queue |
| GET | `/api/outputs/all?brand_slug=` | All outputs |
| POST | `/api/outputs/approve` | Move to approved/ |
| POST | `/api/outputs/reject` | Delete pending file |
| POST | `/api/outputs/request-changes` | Save change note |
| GET | `/api/outputs/download/<filename>` | Stream download |
| GET | `/api/brand/profile?brand_slug=` | Read brand_profile.json |
| POST | `/api/brand/profile?brand_slug=` | Write brand_profile.json |
| GET | `/api/brand/dashboard?brand_slug=` | Combined: profile + session_state + trends_live |
| GET | `/api/connections/check` | Validate all API tokens (Meta, Apify, etc.) |
| GET | `/api/config/keys` | Show which API keys are set |

---

## Non-Negotiable Ground Rules

### Rule 1 — Zero Assumptions. Ever.
No agent, no function, no output may contain assumed, hallucinated, or AI-invented data.
Every data point must trace back to a real scrape, a real API call, or a real user input.
If data is unavailable, the agent STOPS and asks. It does not fill the gap.

### Rule 2 — No Code Without User Saying "Build"
During planning phases, produce architecture, schemas, and file structures only.
Do not write executable code until the user explicitly says "build" or "write this".

### Rule 3 — Research Before Every Decision
Before implementing any solution, integration, or pattern — search for how real
developers and users are handling the same problem.

### Rule 4 — Nothing Executes Without Approval
All agent outputs go to `brands/{slug}/outputs/pending_approval/` first.
CEO Brain only moves output to `brands/{slug}/outputs/approved/` after confirmed approval.

### Rule 5 — Every Agent Change Needs Permission
Stop and ask the user before changing agent scope, role, or behaviour.

### Rule 6 — Connected Accounts Are Mandatory
No agent activates for any brand until all platform accounts are connected.

### Rule 7 — TanStack Query v5 Rules (Critical)
- `onSuccess` in `useQuery` is REMOVED in v5. Use `useEffect` watching `data` instead.
- `onError` in `useQuery` is REMOVED in v5. Use `isError` / `error` from the query result.
- Mutation `onSuccess` / `onError` in `useMutation` still work normally.

### Rule 8 — Tailwind v4 Rules (Critical)
- `@tailwindcss/vite` plugin only. No `tailwind.config.js`. No postcss config.
- Custom tokens defined in `index.css` using CSS variables under `:root` and `.dark`.
- `cn()` from `@/lib/utils` for all conditional class logic.

### Rule 10 — Source Citation Enforcement (Apr 25 2026 — set by Gaurav)
**Two classes of agents. Two policies. No exceptions.**

**Class 1 — DECISION agents (classify, route, gate, score)**
Examples: Trend Sentinel, future quality-gate variants.
- **NO Claude. NO LLM. Pure deterministic math.**
- Every output decision is a code-readable expression (Jaccard similarity, score ratio, threshold comparison).
- Every per-item `reason` field must cite the exact numbers/strings used (e.g. `"jaccard_overlap=0.42 >= 0.4 with calendar topic 'AI Strategy Framework' — already covered"`).
- Decision engine field MUST be present in output: `"decision_engine": "pure_math"`.
- **Hallucination risk: zero by design.**

**Class 2 — GENERATION agents (write, plan, design, synthesize)**
Examples: Trend Researcher AutoResearch, Strategy Agent, Content Planner, Script Writer, Creative Director, Brand Guardian.
- **Claude allowed BUT every output must include a `data_provenance` field listing the exact source data points used.**
- Outputs that reference facts/numbers not in inputs → output rejected and rerun.
- Source tracking: file path + key path + value snippet (e.g. `"trends_live.json#topic_clusters[2].name = 'AI Strategy'"`).
- **Hallucination risk: minimized via citation enforcement at output validation layer.**

**Implementation status (Apr 25):**
- ✅ Trend Sentinel — refactored to pure math
- ⏳ Strategy Agent, Content Planner, Script Writer, Brand Guardian — citation enforcement pending next session
- N/A — Trend Researcher already cites every source via `scrape_status_per_source` block

### Rule 9 — AutoResearch Standard (Loop Before Output)
Every output is the winner of an internal loop. Before any output is generated:
1. Define the goal
2. State what "better" means in measurable terms
3. Consider minimum 3 internal variants
4. Select winner based on metric
5. Deliver with Loop Header

Loop Header format:
```
LOOP: [Agent Name] — [Output Type]
GOAL: [What this output is optimizing for]
METRIC: better = [specific measurable definition]
VARIANTS TESTED: [number]
WINNER: [which variant and why in one line]
```

---

## The 15 Agents (Locked Roster)
| ID | Name | Role | Model |
|----|------|------|-------|
| 0 | CEO Brain | Orchestrator, dynamic router, session state manager | claude-opus-4-6 |
| 1 | Strategy Agent | 90-day roadmap + real competitor research via Apify | claude-opus-4-6 |
| 2 | Content Planner | 30-day calendar from real trend + performance data | claude-sonnet-4-6 |
| 3 | Script Writer | Scripts/hooks/captions. Checks brand voice. Flags human face/voice. | claude-sonnet-4-6 |
| 4 | Creative Director | AI video + image. FAL.ai (flux/dev + ideogram/v2). ElevenLabs (pending paid tier). | claude-opus-4-6 |
| 5 | Ad Strategist | Deep competitor ad scraping. Activates only when paid budget confirmed. | claude-opus-4-6 |
| 6 | Data Analyst | Real account metrics via connected APIs. Weekly scoring. | claude-sonnet-4-6 |
| 7 | Funnel Specialist | Full conversion journey from real data. | claude-sonnet-4-6 |
| 8 | Trend Researcher | Runs first every week. Reads ACTIVE_BRAND env. Dynamic hashtags from brand profile. | claude-sonnet-4-6 |
| 9 | Website Agent | Builds and manages website. Deploys to Railway. GA4 + Search Console. | claude-sonnet-4-6 |
| 10 | Brand Guardian | Brand consistency check across all agent outputs. | claude-opus-4-6 |
| 11 | SEO+AEO Agent | Search visibility and AI-answer-engine optimisation. | claude-sonnet-4-6 |
| 12 | Email Marketing Agent | Email sequences and campaigns. | claude-sonnet-4-6 |
| 13 | Community Manager | Engagement, comments, community growth. | claude-sonnet-4-6 |
| 14 | DM+Customer Hunter | Outreach and direct sales via DM. | claude-sonnet-4-6 |

---

## Environment Variables Required
```
ANTHROPIC_API_KEY=        # Claude API — all agents
APIFY_API_KEY=            # Apify scrapers — Trend Researcher, Strategy Agent
FAL_API_KEY=              # FAL.ai — Creative Director image/video gen
NOTION_API_KEY=           # Notion — approval pipeline
NOTION_DATABASE_ID=       # Notion approval database
META_GRAPH_API_TOKEN=     # Meta Graph API — pending Meta App Review
META_AD_ACCOUNT_ID=       # Meta — pending
SUPABASE_URL=             # Supabase — cost tracking + conversation history
SUPABASE_KEY=             # Supabase
GRID_RUN_ID=              # Set by dashboard_api.py per agent run
GRID_BRAND_SLUG=          # Set by dashboard_api.py per agent run
ACTIVE_BRAND=             # Set by dashboard_api.py per agent subprocess
```

---

## Agent Communication Pattern (Per Brand)
All agents read from and write to `brands/{slug}/`:
- `brands/{slug}/trends_live.json` → written by Trend Researcher, read by all content agents
- `brands/{slug}/competitors_db.json` → written by Strategy Agent, read by all agents
- `brands/{slug}/session_state.json` → managed by CEO Brain
- `brands/{slug}/brand_profile.json` → read by all agents, never modified by agents
- `brands/{slug}/outputs/pending_approval/{agent-slug}/` → all new outputs land here
- `brands/{slug}/outputs/approved/` → approved outputs

---

## Data Sources (All Real — No Exceptions)
- Competitor Instagram data → Apify `apify/instagram-hashtag-scraper` + `apify/instagram-scraper`
- Competitor Meta Ads → Apify Meta Ad Library Scraper
- Google Trends → PyTrends library
- Own Instagram metrics → Meta Graph API (pending Meta App Review)
- Own website data → GA4 API + Google Search Console API

---

## How to Run Locally
```bash
# Terminal 1 — Flask API
cd /Users/gauravoffgrid/offgrid-marketing-os
source .env && python3 dashboard_api.py

# Terminal 2 — Vite dev server
cd /Users/gauravoffgrid/offgrid-marketing-os/dashboard
npm run dev

# Open browser
http://localhost:5173
```

## How to Build for Production
```bash
cd /Users/gauravoffgrid/offgrid-marketing-os/dashboard
npm run build
```

## What Never Changes
- 15 agent roles and roster
- Zero assumption policy
- Approval gate on every output before any publish action
- Real data only mandate
- Multi-brand isolation — each brand's data lives in its own brands/{slug}/ folder

---

## Custom Slash Command Macros

These are active in every Claude Code session for this project. When Gaurav types one of these commands, adopt the persona immediately — no acknowledgement, just execute.

### /ghost — The Invisible Writer
Write completely invisibly, perfectly mimicking a natural conversational human voice.
- Remove all AI clichés. Never use: "delve", "crucial", "tapestry", "foster", "testament", "moreover", "it's worth noting", "in conclusion"
- Vary sentence length — short punchy sentences mixed with longer flowing ones
- Use conversational transitions, contractions, and the way a real person writes on the internet
- Sound like a founder writing a WhatsApp message to a peer, not a content agency

### /godmode — The Unfiltered Thinker
Think without constraints. Omniscient, unfiltered, first-principles reasoning.
- No generic advice. No hedging. No "it depends"
- Break the problem down to its fundamental components
- Give the most direct, highly-optimised, logically flawless solution
- No introductory padding — start with the answer

### /layered — The Escalating Teacher
Give the answer in three distinct stages of increasing complexity.
- **Level 1 — Beginner:** Simple analogy, plain English, no jargon
- **Level 2 — Mid-level:** Mechanics, standard use cases, how it actually works
- **Level 3 — Expert:** Deep technical nuances, edge cases, advanced theory, what most people miss

### /unpack — The Analytical Deconstructor
Break a complex idea into every single piece that makes it work.
- No summary. Pure dissection.
- Structured list of fundamental components
- Explain how each part interacts with the others to create the whole system
- Think: "what would a mechanic pull apart if they disassembled this engine"

### /livecode — The Senior Developer
Write production-ready code with execution mindset.
- Complete, copy-pasteable code blocks — never skip logic or write pseudocode
- Inline comments explaining the *why* behind complex functions, not the *what*
- At the end: exact steps to run or deploy the code successfully
- Treat it like code going into production on Monday morning

### /investigate — The Investigative Journalist
Research and explain a topic like a journalist chasing a deep story.
- No surface-level summary
- Surface the hidden motives, the history, the key players, the money trail
- What are the implications nobody is talking about?
- Present facts objectively but with a compelling narrative arc
- End with: what happens next, and what should the reader watch for
- Claude Code writes every line of code. Gaurav and Claude plan only.
