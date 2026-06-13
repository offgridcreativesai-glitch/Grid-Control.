# File Structure

```
/Users/gauravoffgrid/offgrid-marketing-os/
├── core.py                       Backend foundation: imports, constants, Flask `app`, infra
│                                 hooks/errorhandlers + ALL ~209 helpers. Dynamic __all__ re-export.
├── dashboard_api.py              Thin entrypoint (24 lines): `from core import *`, register
│                                 route blueprints, launch. gunicorn `dashboard_api:app`. (S2a+S2b)
├── routes/                       113 endpoints as 7 domain blueprints (full paths, no url_prefix):
│   ├── brands.py (44)  /api/brands /brand /team /admin /auth
│   ├── agents.py (21)  /api/agents /agent-config /learning /contradictions /performance
│   ├── content.py (17) /api/outputs /carousel /publish /published /pipeline /dashboard-output
│   ├── brain.py (7)    /api/brain /ceo /jarvis /operator-mode /standup /digest
│   ├── billing.py (8)  /api/billing
│   ├── connections.py (8)  /api/connections /voice /notion
│   └── system.py (7)   /api/health /config /scheduler /events /notifications /webhooks
├── agents/                       Runnable agents at root (launched by path string); support in subpkgs.
│   ├── trend_researcher.py       Reads ACTIVE_BRAND env. Apify + Whisper + clustering.
│   ├── strategy_agent.py         Rule 10 wired. Opus.
│   ├── content_planner.py        Rule 10 wired. Sonnet.
│   ├── script_writer.py          Rule 10 wired. Voice DNA. Performance feedback injection.
│   ├── creative_director.py      Rule 10 wired. FAL.ai (flux/dev + ideogram/v2 + recraft-v3).
│   ├── data_analyst.py
│   ├── funnel_specialist.py
│   ├── website_agent.py
│   ├── brand_guardian.py         Rule 10 wired. Soul check.
│   ├── trend_sentinel.py         Pure math (Rule 10 Class-1).
│   ├── performance_tracker.py    Pure math (Rule 10 Class-1).
│   ├── carousel_designer.py      Sonnet content + Pillow OR Playwright HTML render. Multi-brand.
│   ├── cost_tracker.py · brand_book.py · brand_book_v7.py · reel_editor.py
│   ├── _lib/                     Framework + shared helpers (imported, never launched):
│   │   ├── base_agent.py · model_gateway.py · council.py · cost_reporter.py · tracing.py
│   │   └── _provenance.py · _learnings.py · _record_learning.py · _state.py · _untrusted.py
│   ├── intel/                    Research/scrapers: competitor_intel · channel_discovery ·
│   │                             channel_score · website_intel · audit_signals · brand_self ·
│   │                             meta_insights · ig_hashtag_search
│   ├── renderers/                brand_book_renderer · brand_book_v7_renderer ·
│   │                             carousel_editorial_renderer · carousel_html_renderer
│   └── references/
│       └── meta_ads_framework.json   10-pillar Meta Ads framework — read by Ad Strategist.
├── ceo_brain/
│   ├── orchestrator.py           CEOBrain class. save_agent_output runs contradiction check + scoped auto-block.
│   └── contradiction_detector.py 6-rule pure-math cross-agent contradiction detector.
├── notion_integration/
│   ├── notion_pusher.py          Approval DB push. NotionAuthError on 401.
│   └── content_calendar.py       Separate "OffGrid Content Calendar" DB (Draft/Ready/Published).
├── brands/
│   ├── askgauravai/              Primary brand. Hinglish. Live build journey.
│   ├── offgrid-creatives-ai/
│   └── dropvolt/                 Test brand.
├── dashboard/                    React 19 + Vite + Tailwind v4. v0-ported pages + The Brain.
├── managed_agents/               Anthropic Managed Sessions (registry + setup + session_runner).
├── scripts/                      strategic_compact, daily pipeline, GH secrets pusher.
├── .github/workflows/            daily-pipeline.yml, carousel-on-demand.yml.
└── docs/                         CLAUDE_HISTORY, EVAL_HARNESS, AGENT_INTROSPECTION, TOKEN_OPTIMIZATION + slim refs.
```
