# Brand-Book / Brand-Intelligence Report — Research + Redesign Spec (Jun 9 2026)

> **One artifact, two uses** (locked): the sellable **Reporting SaaS deliverable** (cold lead magnet,
> ₹2.5–7k) AND the **onboarding brand-book sign-off gate** (Step 3.5). Built once.
> Scope = **data-driven brand audit only** — NO logo/visual-identity design audit.
> Baseline reviewed: `SahilPrints_Report_V5.pdf` (13 sections, strong) + `Mystical_Vibes_FINAL_V4.pdf`.
> Verdict: the current report is already strong — **evolve it, don't rebuild.** This spec = the gaps to
> close + the best-in-class section architecture + the two-use fork. Companion to
> `AGENCY_WORKFLOW_RESEARCH.md`, `FLOW_V2_DECISIONS.md`.

## 1. What the current report already does well (keep)
- Brutal, specific, all-real-Instagram-data. Founder-to-founder voice, "show the receipts," zero-assumption.
- Strong spine (V5): Exec Scorecard → Competitor Comparison → Category Leaderboard → Where You Stand →
  Who's Winning → Brand vs Market → What Stops the Scroll → Who's Watching → Content-Ready-for-Ads →
  30-Day Playbook → Stop These → 5 Priority Actions → Trends → New Channels → Appendix (top posts).
- Real competitor numbers, real post views/hooks, ranked action plan, ad-creative playbook, legal notice.

## 2. Gaps to close (decided with Gaurav, Jun 9)
1. **Brand Foundation is missing.** Report diagnoses positioning but never **codifies the go-forward
   brand DNA** the client signs off on (positioning statement, value prop, 3–5 messaging pillars +
   proof points, voice & tone do/don't + vocabulary, ICP/personas, 90-day north-star metric). This
   block is what makes it a **sign-off GATE**, not just an audit — and it feeds `brand_profile.json` +
   `voice_profile.json`. (Standard brand-book components per research: purpose, value prop, pillars,
   audience segments, tone of voice, proof points, positioning statement.)
2. **Real audience demographics (onboarding version).** Today audience is *inferred* from engagement.
   For onboarded brands we have OAuth → pull **real Instagram Insights**: age (7 brackets), gender,
   top cities/countries (up to 45 each), follower active-hours, reach/impressions/profile-views/
   follower-growth. (Requires Business/Creator acct + 100+ followers; data can lag ≤48h; only for the
   authenticated owner's account.) Cold sellable version stays inferred.
3. **Category-wide benchmarking, not just the 3 named competitors.** Benchmark the brand against the
   **3 submitted competitors + the FULL category**: category average + median per metric, the brand's
   **percentile rank** (below-median 25–50 / solid 50–75 / top-quartile 75–90 / exceptional >95), and
   **Share of Voice** (`brand metric ÷ total category metric × 100`; leaders hold 25–40%). V5's
   leaderboard is the seed — make it a rigorous benchmark layer.
4. **Minimize estimates, maximize real.** Mark every number REAL (scraped/Insights) vs AI-ESTIMATED.
   Push estimated metrics (save-rate, reach, conversion) toward real wherever access allows.
5. **Reliability / productize.** The two samples look partly hand-tuned. Lock a **template contract +
   eval rubric** so every run hits this quality (see §5).

## 3. Best-in-class section architecture (redesigned)
Keep the diagnostic spine; add Foundation + upgrade Competitor/Audience. Organized into Parts:

**PART 0 — Cover + Executive Scorecard**
Brand, category, market, date, version, data-basis line ("built from N real posts across M accounts").
Scorecard: followers, engagement rate, posting cadence, format mix, reels perf, bio. (REAL.)

**PART 1 — BRAND FOUNDATION** *(NEW — the sign-off block)*
- Positioning statement (one line: for [ICP], [brand] is the [category] that [unique value], unlike [alt]).
- Value proposition (functional + emotional).
- 3–5 **messaging pillars** + proof points each (the themes all content returns to).
- **Voice & tone**: personality, do/don't list, brand vocabulary (words we use / never use).
- **ICP / personas** (who we're for; for onboarding, validated against real demographics in Part 5).
- **90-day north-star metric** (the one number that defines winning + targets).
- *Onboarding use:* client **approves/edits this block** → writes to `brand_profile.json` +
  `voice_profile.json`. *Sellable use:* presented as "recommended foundation."

**PART 2 — WHERE YOU STAND** *(diagnostic + upgraded benchmarking)*
- Honest position assessment (the "hard truth").
- **Competitor head-to-head** (the 3 named) — metric table.
- **FULL-CATEGORY benchmark** *(NEW)*: category avg + median per metric, brand **percentile rank**,
  **Share of Voice %**, full leaderboard (rank out of N). Auto-discovered category set + the 3 named.

**PART 3 — THE MARKET** — Who is winning & why (competitor deep-dive) + Brand vs Market Reality.

**PART 4 — CONTENT INTELLIGENCE** — What stops the scroll (hooks + formats), proven hook formulas from
the brand's *own* data, format gaps.

**PART 5 — AUDIENCE INTELLIGENCE** — *Onboarding:* REAL Insights (age/gender/geo/active-hours +
audience-you're-missing). *Sellable:* inferred from engagement signals. Validates Part-1 personas.

**PART 6 — GROWTH PLAYBOOK** — Content-ready-for-paid-ads (ad-creative playbook + budget) · exact
30-day content playbook · Stop These Immediately · 5 Priority Actions ranked by impact.

**PART 7 — HORIZON** — Trends & opportunities before they peak · New channels to expand onto.

**APPENDIX** — Top-performing posts · **Data provenance & methodology** (sources, scrape date, what's
real vs estimated, category-set selection logic).

## 4. The two-use fork (same skeleton, different depth)
| | **Sellable (cold lead magnet)** | **Onboarding (sign-off gate)** |
|---|---|---|
| Access | Scrape-only, no account | OAuth-connected account |
| Part 1 Foundation | "Recommended" (inferred) | **Co-created + client sign-off** → brand_profile/voice_profile |
| Part 5 Audience | Inferred from engagement | **Real Instagram Insights demographics** |
| Estimates | More AI-estimated | Mostly real, fewer estimates |
| Output | PDF (foot-in-door audit) | Portal review + PDF, versioned, approve/change |
| Price/role | ₹2.5–7k product + ascension hook | Included in retainer; the alignment gate |

## 5. Reliability (make the agent produce this quality every run)
- **Template contract:** each Part declares required data fields; the agent cannot emit a Part without
  real numbers in those fields (no generic filler).
- **Provenance per metric** (Rule 10): every figure carries source_file + path + value; REAL vs
  ESTIMATED tag rendered in the report.
- **AutoResearch loop:** generate 3 variants of the narrative sections, score, ship the winner.
- **Eval rubric (pass/fail before delivery):** (a) every section cites ≥1 real scraped number;
  (b) competitor + full-category benchmark present; (c) brand-voice check (founder-to-founder, no fluff,
  no fabricated stats); (d) Part 1 foundation complete; (e) no "AI flag" filler language.
- Render via the existing carousel/HTML→PDF pipeline (Playwright); **force white bg** (dark-mode bug).

## 6. Data sources per section (provenance map)
- Scorecard / competitor / category / hooks / formats / top posts → **scraped IG data** (Apify/Scrapling). REAL.
- Audience demographics → **Instagram Graph API Insights** (onboarding only). REAL.
- Save-rate / reach / conversion where not exposed → **AI-ESTIMATED**, tagged.
- Foundation (Part 1) → synthesized from brand_profile + scrape + (onboarding) client input. Codified.
- Trends / new channels → trend-researcher cache + category scan.

## 7. v7 EVOLUTION (Jun 12 2026) — Multi-platform GTM intelligence: WHERE + HOW to promote

> **Decided with Gaurav, Jun 12.** Trigger: the pilot's first cold report (offgrid = B2B ad-intel SaaS)
> failed G6 `has_real_number` because its competitors barely use Instagram (real posts pull 6–8 likes).
> Lesson: **single-platform IG-engagement benchmarking is the wrong lens for a category that isn't won
> on IG.** v7 fixes this by making the report's PRIMARY job a **go-to-market route call** —
> *where should this brand promote, and how* — proven across every public channel, not just IG.
> Evolve v6, don't rebuild: the v6 audit/foundation content is retained and reframed in service of the
> route recommendation. **One report, two interrelated halves** (Social = organic; Marketing = paid +
> distribution), tied together by the Channel Map (spine) and The Route Forward (payoff).

### 7.1 North star
The report answers ONE question: **"Given what's working for the 3 competitors across every channel,
where should this brand promote, with what content, in what order — and where's the gap to own?"**
Output must *look* like intelligence — **stat cards, charts, real creative images** — not text walls.

### 7.2 Competitor scope (locked)
- **3 competitors, user-provided** → deep **multi-platform** profile each (full brand + performance picture).
- Then **category-level scan** across the same platforms (auto-discovered set) for the benchmark + gaps.

### 7.3 Per-platform source + REAL vs ESTIMATED map (zero-assumption)
| Platform | What we pull | Source | Tag |
|---|---|---|---|
| **LinkedIn** | company followers, post cadence, engagement, top posts/topics | Apify (public) | REAL |
| **YouTube** | subs, video count, views, top videos, cadence | YouTube Data API / Apify | REAL |
| **X / Twitter** | followers, posts, engagement, top posts | Apify (public, best-effort) | REAL* |
| **Instagram** | followers, posts, engagement, formats | Apify instagram-scraper | REAL* (likes often hidden → flag partial) |
| **Website** | positioning, messaging, pricing, offers, tech stack | scrape (public pages) | REAL (content) |
| **Web traffic** | total visits, **traffic-source split** (search/social/direct/referral/paid), top keywords | SimilarWeb-type | **ESTIMATED** |
| **Meta Ad Library** | active ads, count, **longevity**, creative angles, formats | Meta Ad Library / Apify FB-ads (public) | REAL |
| **Google Ads** | keyword/ad presence | SEMrush/SpyFu-type | **ESTIMATED** |
| **GA4 / Google Analytics** | — | **PRIVATE** — own/client-granted only, **NEVER competitor** | n/a for competitors |
> `*` REAL but coverage-dependent — if a platform returns hidden/partial engagement or error stubs
> (`no_items`/`not_found`), the figure is dropped, the handle marked partial/failed, and the report says
> so. **Error stubs are never counted as data** (the v6-era bug; fixed in v7).

### 7.4 The money signal — Ad-Longevity Scorer (highest-confidence WHERE evidence)
Brands don't keep ads running that lose money. Per competitor, from Ad Library:
`# active ads · days-running (longevity) · # distinct creatives · platforms running`.
Channel **profitability-proxy score** = weighted(longevity, volume, sustained presence). **Long-running,
high-volume ads on a channel ⇒ that channel converts for the category.** This drives the route call with
the strongest defensible claim. (Deterministic / pure-math = Class-1.)

### 7.5 Channel-score & verdict engine (the spine — WHERE)
Per platform, per competitor + aggregated:
`Presence (profile/ads exist) + Effort (cadence/volume) + Traction (engagement/views/traffic share) +
Money-signal (ad longevity)`. → Verdict per channel: **RIDE** (proven + room) · **TEST** (signal,
unproven) · **SKIP** (category absent/dead). Plus **GAP** flag (channel underused by all = the wedge).
Deterministic; every input tagged REAL/ESTIMATED.

### 7.6 Content intelligence (HOW)
Across the 3 competitors per platform: top **formats**, top **hooks/angles**, posting cadence, topics,
best example posts (rendered as **image thumbnails**). Charts: format-mix, engagement-by-format, cadence.
→ "promote this way."

### 7.7 Section architecture v7 (the inners — one report, interrelated halves)
0. **Executive Snapshot** — 3–5 verdicts as **stat cards** ("Ride LinkedIn. Skip IG. Paid wins on Meta.").
1. **Brand Foundation** *(retained from v6 Part 1 — sign-off block; feeds brand_profile/voice_profile)*.
2. **Channel Map — WHERE** *(spine)* — every platform scored, **heatmap/bar grid**, RIDE/TEST/SKIP verdict.
3. **Ad Intelligence — the money signal** *(Marketing half)* — Ad-Library volume + **longevity timeline**,
   top ad creatives as **images** + the angle that's working.
4. **What Content Is Working — HOW** *(Social half)* — format-mix donut, engagement-by-format bars,
   cadence, real example posts as **images**.
5. **Traffic & Distribution** *(Marketing half)* — **traffic-source split** donut/stacked bar (ESTIMATED),
   SEO/keyword territory, website + pricing teardown.
6. **The Gap / Wedge** — channels competitors ignore/do badly = the opening; channel map with gaps lit.
7. **The Route Forward** *(payoff)* — ranked channels to promote on + content approach per channel +
   paid/organic split, as a **prioritized roadmap timeline**.
8. **Appendix + Provenance** — every figure REAL vs ESTIMATED, source + scrape date, category-set logic.
> The two halves are **interrelated, not siloed**: Channel Map sets WHERE, Content + Ad sections prove HOW,
> Route Forward fuses both into one sequenced plan.

### 7.8 Visual system (kills the "boring text wall")
Stat cards · channel heatmap/bar grid · ad-longevity timeline · format/traffic donuts · **real creative
thumbnails** · brand-color theme. Charts via server-rendered SVG or Chart.js inside the existing
Playwright **HTML→PDF** pipeline (**force white bg** — dark-mode bug). Every section is a visual block, not
a paragraph.

### 7.9 Eval rubric v7 (mode + category aware — supersedes §5 for v7)
- **`has_real_evidence`** *(replaces `has_real_number`)*: report cites ≥1 REAL observed data point —
  a number **or** a concrete scraped fact. A cold B2B brand with no meaningful numbers **passes** on real
  qualitative evidence + honest absence (no manufactured benchmark).
- **`channel_recommendation_present`**: explicit WHERE + HOW route call, backed by evidence.
- **`ad_signal_assessed`**: Ad Library checked — "no competitor is advertising" is itself a valid finding.
- **`honest_absence`**: where a competitor/channel is inactive, said plainly ("this category isn't won
  here"), never blanked or faked.
- **error-stub filtering**: `no_items`/`not_found`/hidden-engagement never counted as data.
- Retained: `no_ai_filler`, `foundation_complete`, `all_parts_present`, REAL/ESTIMATED tag on every figure.

### 7.10 Honest-absence rule (the principle we agreed)
If competitors aren't measurably active on a channel, the report **states the absence and what it means**
("category isn't won on IG — competitors average 6–8 likes; the battleground is X"). The "no data" becomes
the insight. Never invent a number to satisfy a rubric.

### 7.11 Build implications (phased — blueprint locked here, build separate, per the no-code-without-go rule)
- **B-1** Multi-platform competitor scrapers (LinkedIn · YT · X · Website · Meta Ad Library) + SimilarWeb
  estimate adapter. Research layer (extend `trend_researcher` / a `competitor_intel` module), additive,
  per `apify-strategy` rules. **No new agent / no roster change.**
- **B-2** Ad-Longevity scorer + **B-3** Channel-score/verdict engine — deterministic, Class-1 (pure math).
- **B-4** Chart/data-viz render layer (HTML + SVG/Chart.js → Playwright PDF).
- **B-5** `brand_book` v7 assembly + eval v7. Class-2 narrative on Opus with `data_provenance`.
- **Reuse:** the IG `competitor_metrics` wiring already committed (`f056430`) becomes the **IG slice** of the
  multi-platform layer (right for D2C/consumer categories) — with the error-stub fix from §7.3.
- **Supersedes:** v7 extends **Phase G**; v6's IG-only report becomes the **IG deep-dive within v7**.

## Sources
Brand audit/book: [Armada](https://armadadigital.co/brand-audit-go-to-market-strategy/) ·
[Ainoa checklist](https://www.ainoa.agency/blog/brand-audit-complete-checklist-2025) ·
[Canny deliverables](https://www.canny-creative.com/blog/complete-list-branding-services-deliverables/).
Messaging/voice/pillars: [Asana](https://asana.com/resources/brand-messaging-framework) ·
[Huddle pillars](https://www.huddlecreative.com/blog/defining-the-brand-messaging-pillars) ·
[Reforge templates](https://www.reforge.com/blog/messaging-framework-templates) ·
[Amelie Pollak hierarchy](https://www.ameliepollak.com/blog/brand-message-hierarchy-the-full-guide).
Positioning/value-prop: [Fabrik](https://fabrikbrands.com/branding-matters/brand-strategy/ultimate-brand-positioning-framework/) ·
[Product Marketing Alliance](https://www.productmarketingalliance.com/brand-positioning-strategy-framework-template/).
IG Insights API: [Phyllo demographics](https://www.getphyllo.com/post/instagram-audience-demographics-for-influencer-marketing-platforms) ·
[insightIQ Insights API](https://www.insightiq.ai/blog/instagram-insights-api) ·
[bundle.social](https://bundle.social/instagram-audience-demographics).
Benchmarking/SOV: [Meltwater](https://www.meltwater.com/en/blog/share-of-voice-definition-measurement) ·
[Improvado benchmarks](https://improvado.io/blog/social-media-benchmarking) ·
[Sprout competitive analysis](https://sproutsocial.com/insights/social-media-competitive-analysis/).
Audit structure: [Sprout audit](https://sproutsocial.com/insights/social-media-audit/) ·
[Asana audit](https://asana.com/resources/social-media-audit-template) ·
[DigitalApplied 2026](https://www.digitalapplied.com/blog/social-media-audit-template-2026-complete-guide).
