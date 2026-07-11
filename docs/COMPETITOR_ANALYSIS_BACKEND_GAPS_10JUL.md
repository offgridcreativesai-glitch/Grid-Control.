# Grid Control — Competitor Analysis + Backend Gap Deep-Research (Jul 10 2026)

Triggered by the 71-page Perplexity strategy PDF. Two tracks: (1) real web research on the
competitors it named, (2) graphify-verified audit of our own backend to find the true gaps.
All competitor facts are live-sourced (links at bottom). All gap claims are graphify-verified
against the actual repo, not inferred.

---

## 1. Competitor teardown (live data, Jul 2026)

### Birdeye — the north star (but a different shape)
- **What it is:** #1 agentic marketing platform for **multi-location** brands (healthcare, retail, franchises). 10+ BirdAI agents across reviews, listings, messaging, social; human-in-the-loop approvals on every AI output.
- **Pricing:** $299 Starter / $349 Growth / $449 Dominate — **per location, per month**. 4+ locations = custom. Month-to-month ~40% higher than annual.
- **Proof:** 4.7/5 on G2 (4,000+ reviews); G2 2026 "Top AI Product Globally" + Agentic AI category.
- **Why it matters to us:** it validates the *exact* model we're building (agents + approvals + unified surface). But its center of gravity is **reputation / local SEO / multi-location** — an enterprise wedge, not a D2C-founder wedge. We don't compete head-on; we borrow the pattern.

### NoimosAI — the closest mirror to GC
- **What it is:** "AI becomes your 24-hour marketing team." Autonomous, all-in-one. Named agents: Competitor Strategy, Social Listening, SEO, GEO, Industry News. Work lands in a **Feed** you approve; an **AI Chat** manages the team in natural language.
- **Pricing:** $99 Pro / $249 Team / $499 Advanced — **per user/month**, 7-day trial.
- **Why it matters:** their Feed = our approval gate; their AI Chat = The Brain; their agent roster overlaps ours. Their edge is a **strong creative agent** (image/video/carousel) and simpler, more human output. This is who we look most like — and who exposes our creative-OS + polish gap.

### Social Lollipop — the "simple next move" wedge
- **What it is:** "Turn the internet into your social media team." See any brand/competitor's **live ads**, break down the strategy in seconds relative to your brand, spot cultural/category trends, ship posts faster. Founder: Leo Morejon (Oreo, Trident).
- **Why it matters:** it's a **social + ad-intelligence** tool with a killer "what to do next in plain words" narration. This is precisely where our outputs read too technical. The lesson is a UX/language one, not an engine one.

### GoHighLevel — the white-label business model
- **What it is:** full CRM + funnels + automation; **SaaS Mode** on the $497/mo Agency Pro plan lets agencies **resell sub-accounts under their own brand** at their own price.
- **Reseller economics:** you pay ~$497/mo flat; charge clients $297–$997/mo each; ~10 clients ≈ $3,700/mo net margin; every new client is near-pure margin.
- **AI pricing pattern (usage-metered):** Conversation AI $0.02/msg, Voice AI ~$0.16/min, Reviews AI $0.08/response.
- **Why it matters:** this is the **eventual monetization shape** for GC's agency tier (white-label reseller). We have the multi-tenant primitives; we haven't packaged them as SaaS Mode.

---

## 2. Where Grid Control actually stands (scorecard)

Perplexity's headline after it finally read the repo: *"You're much further along than you think."*
GC is a production-deployed, multi-brand, multi-agent OS with approvals, pipelines, publishing,
funnels, and India-native billing. The gaps are **packaging, polish, and specific engines** — not the core.

| Capability | Birdeye | NoimosAI | Social Lollipop | GHL | **Grid Control** |
|---|---|---|---|---|---|
| Multi-agent orchestration + approval gate | 4 | 4 | 3 | 3 | **4 (strong — CEO Brain + gate)** |
| Brand OS / onboarding audit | 3 | 3 | 3 | 3 | **4 (brand-book v7, just deepened)** |
| Reputation / reviews / listings / local SEO | **5** | 2 | 2 | 4 | **1 (none — see gap #1)** |
| Creative asset OS (image/video/library) | 3 | **5** | 3 | 3 | **3 (Higgsfield+CD, no library)** |
| Social + ad intelligence UX | 3 | 4 | **5** | 2 | **3 (data exists, UX weak)** |
| Analytics cockpit (polished, client-facing) | 4 | 4 | 4 | 4 | **3 (data_analyst, thin UI)** |
| White-label / SaaS reseller packaging | 3 | 2 | 1 | **5** | **2 (multi-tenant, unpackaged)** |
| Humanized, founder-readable output | 3 | 4 | **5** | 3 | **2→ improving (fix shipped today)** |

---

## 3. Backend gaps — graphify-verified against the repo

Ranked by leverage. Each verified with `graphify query`, not assumed.

1. **Reputation / reviews / listings engine — MISSING.** graphify finds only ads/SEO *skill markdown*
   for "local SEO/reviews" — no agent, no code, no pipeline. This is Birdeye's whole moat. For our
   D2C/founder wedge it's lower priority than for multi-location, but it's the single biggest
   capability we have zero of. **Decision needed: in scope or explicitly out?**

2. **White-label / SaaS-Mode packaging — PARTIAL.** We have the hard parts (brand isolation per
   `brands/<slug>/`, Supabase RLS, Razorpay, per-brand secrets). We do **not** have the reseller
   layer: agency-owned sub-accounts, per-seat pricing, brand-your-own-cockpit. GHL proves the
   economics. This is a **packaging** build on top of existing primitives, not new infra.

3. **Creative asset OS — PARTIAL.** `creative_director` + the Higgsfield product-photoshoot skill
   generate assets, but graphify shows outputs land in per-brand file storage (`content.py` /
   `get_brand_dir`) with **no versioned library, gallery, or reuse layer**. NoimosAI's edge. Medium
   lift, high visible value.

4. **Social listening / brand-mention monitoring — PARTIAL.** We have `community_manager` (replies)
   + `inbound_comments`, but **no broad web/social mention + sentiment tracking** (Noimos + Birdeye
   both have it). Depends on a data source (Apify/paid) — gate behind `GRID_PAID_OPS`.

5. **Analytics cockpit — PARTIAL.** `data_analyst` agent + eval-harness produce the numbers; the
   **client-facing analytics surface is thin** (Insights page exists, not a real dashboard). Polish, not engine.

6. **Humanized reasoning layer — WAS the deepest gap. ADDRESSED TODAY (see §5).** Every Class-2 agent
   now carries a "think like a business owner, not a dashboard" reasoning contract.

Already covered (not gaps): GEO/AEO (`seo-aeo-agent`), ads intelligence data (Meta Ad Library via
intel), multi-brand isolation, approval gate, publishing, provenance/Rule-10.

---

## 4. Positioning recommendation (the Phase 1 wedge)

Don't chase Birdeye's multi-location reputation game or GHL's CRM breadth. **Own the wedge no one owns
cleanly:** an **AI marketing team for D2C/founder & small-agency brands** that (a) audits the brand in
plain founder language, (b) runs a curated, phased plan under human approval, (c) is India-native on
billing. That's:

> **"Connect your brand + socials → get a clear audit and a 90-day plan → your AI team executes it, you approve."**

- **Phase 1 (now):** Brand OS + Audit + Content OS — mostly UX + language + light wiring; the backend
  exists. This is exactly the onboarding→report→approve→content flow we're testing. **Validated.**
- **Phase 2:** Social + Ad-Intelligence UX (the Social Lollipop angle) — competitor/ad panel + "next best move" cards on top of the intel we already scrape.
- **Phase 3:** Creative OS (gap #3) + White-label SaaS Mode (gap #2) — the agency-reseller monetization tier.

Reputation/local-SEO (gap #1) is a **later, optional** vertical expansion — only if we go after
multi-location clients. Otherwise consciously out of scope.

---

## 5. What we shipped today (first gap-closes, from the PDF)

The PDF's two deepest insights, both now in code (uncommitted):

- **Humanized judgment layer** (gap #6) — `agents/_lib/_agent_framework.py`: every generation agent
  now reasons "what's the ONE thing that matters → what context changes its meaning → what TYPE of
  problem is this → what would a smart operator say in 30s," leads with that, ranks findings, writes
  in operator language. Model-agnostic; lifts all agents at once. Directly answers Perplexity's
  "agents think like a dashboard, not a business owner" and your own long-standing "too technical" complaint.

- **Reactivation detection** (the "15-months-inactive miss") — `agents/intel/brand_self.py` now
  computes dormancy from real post timestamps (`activity` block). Verified on TGT: **dormant, 9.5
  months dark, was posting 10×/month.** The brand-book (`brand_book_v7.py` + renderer) now opens with
  a **SITUATION banner** that names the audit type (Reactivation/Launch/Growth/Reposition) and, when
  dormant, reframes the whole report as a restart — not a growth audit. New eval check `situation_named`.

These are the first two items off the gap list; positioning (§4) is a decision, not a build.

---

## Sources
- Birdeye: [birdeye.com](https://birdeye.com/), [birdeye.com/ai](https://birdeye.com/ai/), [Analytics Insight review 2026](https://www.analyticsinsight.net/artificial-intelligence/birdeye-platform-review-2026-features-pricing-pros-cons), [G2](https://www.g2.com/products/birdeye/reviews)
- NoimosAI: [noimosai.com/pricing](https://noimosai.com/en/pricing), [Software Advice](https://www.softwareadvice.com/product/535203-NoimosAI/)
- Social Lollipop: [sociallollipop.com](https://sociallollipop.com/)
- GoHighLevel: [SaaS Mode / white-label guide](https://www.highlevel.ai/gohighlevel-white-label-guide), [pricing 2026](https://netpartners.marketing/gohighlevel-pricing-plans-explained-features-value-cost-comparison-2026/)
