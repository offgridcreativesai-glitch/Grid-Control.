# Agent System — Trend, Api

> 37 nodes · cohesion 0.11

## Key Concepts

- **Trend Researcher** (37 connections) — `.claude/agents/trend-researcher.md`
- **.log()** (19 connections) — `agents/trend_researcher.py`
- **.run()** (15 connections) — `agents/trend_researcher.py`
- **.apify_fetch_results()** (10 connections) — `agents/trend_researcher.py`
- **.apify_start_run()** (9 connections) — `agents/trend_researcher.py`
- **.scrape_competitor_profiles()** (7 connections) — `agents/trend_researcher.py`
- **.scrape_brand_instagram()** (6 connections) — `agents/trend_researcher.py`
- **.scrape_instagram_hashtags()** (6 connections) — `agents/trend_researcher.py`
- **.scrape_twitter()** (6 connections) — `agents/trend_researcher.py`
- **.scrape_youtube_shorts()** (6 connections) — `agents/trend_researcher.py`
- **._run_topic_clustering()** (5 connections) — `agents/trend_researcher.py`
- **._score_posts()** (5 connections) — `agents/trend_researcher.py`
- **._extract_whisper_transcripts()** (4 connections) — `agents/trend_researcher.py`
- **._quality_gate()** (4 connections) — `agents/trend_researcher.py`
- **.save_trends_live()** (4 connections) — `agents/trend_researcher.py`
- **.scrape_google_trends()** (4 connections) — `agents/trend_researcher.py`
- **._load_winning_topics()** (3 connections) — `agents/trend_researcher.py`
- **int** (1 connections) — `agents/trend_researcher.py`
- **Trend Researcher — OffGrid Marketing OS Agent ID: 8 | Sequence position: 1 (alwa** (1 connections) — `agents/trend_researcher.py`
- **Pure deterministic. Reads performance_history.json and returns a flat set of** (1 connections) — `agents/trend_researcher.py`
- **Filter out posts that look like engagement pods, bought views, or bot-comment-fl** (1 connections) — `agents/trend_researcher.py`
- **Group top scored posts into named topic clusters using Claude.         Returns d** (1 connections) — `agents/trend_researcher.py`
- **Write trends_live.json to brands/{slug}/.         This file is read by all downs** (1 connections) — `agents/trend_researcher.py`
- **Full agent run sequence:         1. Scrape all available data sources         2.** (1 connections) — `agents/trend_researcher.py`
- **Start an Apify actor run. Returns run ID or None on failure.** (1 connections) — `agents/trend_researcher.py`
- *... and 12 more nodes in this community*

## Relationships

- [[Agent System — Trend, Ui]] (13 shared connections)
- [[Agent System — Strategy, Trend]] (5 shared connections)
- [[Agent System — Ui, Trend]] (3 shared connections)
- [[Managed Agent Prompts — Pipeline]] (3 shared connections)
- [[Ceo_Brain — Agent]] (1 shared connections)
- [[Claude Skills — Brand, Brain]] (1 shared connections)

## Source Files

- `.claude/agents/trend-researcher.md`
- `agents/trend_researcher.py`

## Audit Trail

- EXTRACTED: 169 (99%)
- INFERRED: 1 (1%)
- AMBIGUOUS: 0 (0%)

---

*Part of the graphify knowledge wiki. See [[index]] to navigate.*