# Brand Onboarding — The Repeatable Flow

> One flow, every brand, same order. Minimal and easy: from gathering brand info
> to fully wired into Grid Control. Machine-checkable via
> `scripts/onboard_brand.py`. **Zero assumptions — every field is a real answer
> from the brand owner, never inferred.**

## The 6 steps

| # | Step | Who | Produces | Gate |
|---|------|-----|----------|------|
| 1 | **Intake** | Owner fills `/onboarding` form | `brand_profile.json` | real answers only |
| 2 | **Scaffold** | `POST /api/brands/create` (form does it) | dirs, profile, memory, Supabase row, `session_state.json` | auto |
| 3 | **Voice** | `/api/voice/extract-profile` from real sample posts | `voice_profile.json` | required before Script Writer |
| 4 | **Connect** | Owner pastes tokens on Connections page | `brands/<slug>/.env` | ≥1 platform |
| 5 | **Verify** | `python3 scripts/onboard_brand.py --verify <slug>` | WIRED ✅ | all core ✅ |
| 6 | **Kick off** | Run pipeline in order | trends → strategy → calendar → content | first post via approval gate |

## Step 1 — Intake (the minimal form)

Collect only what the agents actually consume. Required:
- **Brand name** + **slug**
- **Product** (one line) + **price** (India / intl / beta if any)
- **Target audience** (who buys) + **ICP segments**
- **Instagram handle** + other **platform handles**
- **Competitor handles** (3–6 real accounts — drives Strategy Agent scrape)
- **Tone specifics** + **what to never say**
- **Brand face** (Person / Faceless) · **90-day goal** · **weekly post target**

Anything unknown → leave blank, do NOT guess. Agents treat blanks as "no data".

## Step 2 — Scaffold (automatic)

`create_brand` builds: `outputs/{pending_approval,approved}/<agent>/`, `brand_profile.json`,
brand memory + market-intelligence folders, Supabase `brands` + `session_state` rows,
and `session_state.json` (next_agent = `trend-researcher`).

CLI fallback: `python3 scripts/onboard_brand.py --scaffold <slug>`.

## Step 3 — Voice

Extract `voice_profile.json` from the brand's **real** existing posts / brand brief.
No samples yet → capture the owner's written voice notes; never synthesise a fake voice.

## Step 4 — Connect platforms

Connections page → paste each token into `brands/<slug>/.env`. **Owner pastes; tokens
are never displayed or echoed.** Per-platform keys:

| Platform | Env key(s) |
|----------|-----------|
| Instagram (publish + insights) | `META_GRAPH_API_TOKEN`, `IG_USER_ID` — **one** Instagram Login token covers both posting and audience/reach insights (scope `instagram_business_manage_insights`). No Facebook Page needed. |
| LinkedIn | `LINKEDIN_ACCESS_TOKEN`, `LINKEDIN_URN` (auto-captured) |
| YouTube | `YOUTUBE_REFRESH_TOKEN` + `YOUTUBE_CLIENT_ID/SECRET` |
| X / Twitter | 4 OAuth1 keys (optional — manual posting is fine) |

## Step 5 — Verify

```
python3 scripts/onboard_brand.py --verify <slug>
```
Must print **WIRED** (core files + ≥1 connection). Fix any ❌ before kicking off agents.

## Step 6 — Kick off intelligence

Run in order (each gated by approval):
`trend-researcher → strategy-agent → content-planner → script-writer → (creative/carousel)`.
First content → `outputs/pending_approval/` → owner approves → publish.

A brand is **not live** until Step 5 = WIRED and Step 6 has one approved post.
