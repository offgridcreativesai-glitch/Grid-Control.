---
type: community
cohesion: 0.11
members: 37
---

# Agent System — Trend, Api

**Cohesion:** 0.11 - loosely connected
**Members:** 37 nodes

## Members
- [[._extract_whisper_transcripts()]] - code - agents/trend_researcher.py
- [[._load_winning_topics()]] - code - agents/trend_researcher.py
- [[._quality_gate()]] - code - agents/trend_researcher.py
- [[._run_topic_clustering()]] - code - agents/trend_researcher.py
- [[._score_posts()]] - code - agents/trend_researcher.py
- [[.apify_fetch_results()]] - code - agents/trend_researcher.py
- [[.apify_start_run()]] - code - agents/trend_researcher.py
- [[.log()_8]] - code - agents/trend_researcher.py
- [[.run()_7]] - code - agents/trend_researcher.py
- [[.save_trends_live()]] - code - agents/trend_researcher.py
- [[.scrape_brand_instagram()]] - code - agents/trend_researcher.py
- [[.scrape_competitor_profiles()]] - code - agents/trend_researcher.py
- [[.scrape_google_trends()]] - code - agents/trend_researcher.py
- [[.scrape_instagram_hashtags()]] - code - agents/trend_researcher.py
- [[.scrape_twitter()]] - code - agents/trend_researcher.py
- [[.scrape_youtube_shorts()]] - code - agents/trend_researcher.py
- [[Extract audio transcripts from top video posts using Whisper.         Requires]] - rationale - agents/trend_researcher.py
- [[Fetch dataset items from a completed Apify run.]] - rationale - agents/trend_researcher.py
- [[Filter out posts that look like engagement pods, bought views, or bot-comment-fl]] - rationale - agents/trend_researcher.py
- [[Full agent run sequence         1. Scrape all available data sources         2.]] - rationale - agents/trend_researcher.py
- [[Group top scored posts into named topic clusters using Claude.         Returns d]] - rationale - agents/trend_researcher.py
- [[Pure deterministic. Reads performance_history.json and returns a flat set of]] - rationale - agents/trend_researcher.py
- [[Score all scraped posts across Instagram, YouTube, Twitter.         Formula Vie]] - rationale - agents/trend_researcher.py
- [[Scrape Google Trends for keywords relevant to this brand's niche.         Uses p]] - rationale - agents/trend_researcher.py
- [[Scrape Instagram posts by hashtag for the brand's niche.         Uses apifyinst]] - rationale - agents/trend_researcher.py
- [[Scrape TwitterX for brand niche keywords.         Uses apifytwitter-scraper. G]] - rationale - agents/trend_researcher.py
- [[Scrape YouTube Shorts for brand niche keywords.         Uses apifyyoutube-scrap]] - rationale - agents/trend_researcher.py
- [[Scrape the brand's own Instagram profile to understand baseline performance.]] - rationale - agents/trend_researcher.py
- [[Scrape top posts from each competitor's Instagram profile.         Uses apifyin]] - rationale - agents/trend_researcher.py
- [[Start an Apify actor run. Returns run ID or None on failure.]] - rationale - agents/trend_researcher.py
- [[Trend Classification (FADMICRO_TRENDSTRUCTURAL_SHIFT)]] - concept - .claude/agents/trend-researcher.md
- [[Trend Classification System]] - rationale
- [[Trend Researcher]] - document - .claude/agents/trend-researcher.md
- [[Trend Researcher Goal Trend Relevance Score]] - rationale
- [[Trend Researcher — OffGrid Marketing OS Agent ID 8  Sequence position 1 (alwa]] - rationale - agents/trend_researcher.py
- [[Write trends_live.json to brands{slug}.         This file is read by all downs]] - rationale - agents/trend_researcher.py
- [[int_7]] - code - agents/trend_researcher.py

## Live Query (requires Dataview plugin)

```dataview
TABLE source_file, type FROM #community/Agent_System__Trend_Api
SORT file.name ASC
```

## Connections to other communities
- 13 edges to [[_COMMUNITY_Agent System — Trend, Ui]]
- 5 edges to [[_COMMUNITY_Agent System — Strategy, Trend]]
- 3 edges to [[_COMMUNITY_Agent System — Ui, Trend]]
- 3 edges to [[_COMMUNITY_Managed Agent Prompts — Pipeline]]
- 1 edge to [[_COMMUNITY_Ceo_Brain — Agent]]
- 1 edge to [[_COMMUNITY_Claude Skills — Brand, Brain]]

## Top bridge nodes
- [[Trend Researcher]] - degree 37, connects to 6 communities
- [[.log()_8]] - degree 19, connects to 2 communities
- [[.run()_7]] - degree 15, connects to 1 community
- [[.apify_fetch_results()]] - degree 10, connects to 1 community
- [[.apify_start_run()]] - degree 9, connects to 1 community