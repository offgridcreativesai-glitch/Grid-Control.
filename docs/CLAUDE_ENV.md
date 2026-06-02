# Environment Variables Required

```
ANTHROPIC_API_KEY        # Claude API — all agents + The Brain
APIFY_API_KEY            # Apify scrapers — Trend Researcher, Strategy Agent
FAL_API_KEY              # FAL.ai — Creative Director image/video gen
NOTION_API_KEY           # Notion — approval pipeline
NOTION_PAGE_ID           # Notion parent page (DB auto-created)
NOTION_CONTENT_CALENDAR_DB_ID  # Optional — content calendar DB ID
META_GRAPH_API_TOKEN     # Meta Graph API — STILL PENDING (blocks Data Analyst real metrics)
META_AD_ACCOUNT_ID       # Meta — pending
SUPABASE_URL             # Supabase — cost tracking + conversation history
SUPABASE_KEY             # Supabase
YOUTUBE_API_KEY          # YouTube Data API (set)
TWITTER_BEARER_TOKEN     # Twitter Free tier — read via Apify (set)
DASHBOARD_SECRET         # Flask auth header
GRID_RUN_ID              # Set by dashboard_api.py per agent run
GRID_BRAND_SLUG          # Set by dashboard_api.py per agent run
ACTIVE_BRAND             # Set by dashboard_api.py per agent subprocess
```

## Data Sources (All Real — No Exceptions)

- Competitor Instagram → Apify `apify/instagram-hashtag-scraper` + `apify/instagram-scraper`
- Competitor Meta Ads → Apify Meta Ad Library Scraper
- Google Trends → PyTrends library
- Own Instagram metrics → Meta Graph API (pending Meta App Review)
- Own website data → GA4 API + Google Search Console API
- YouTube Shorts → Apify `apify~youtube-scraper`
- Twitter → Apify `apify~twitter-scraper`
- Voice transcripts → openai-whisper + yt-dlp
