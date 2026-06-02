# File Structure

```
/Users/gauravoffgrid/offgrid-marketing-os/
├── dashboard_api.py              Flask REST API (multi-brand, all endpoints, port 5001)
├── agents/
│   ├── trend_researcher.py       Reads ACTIVE_BRAND env. Apify + Whisper + clustering.
│   ├── strategy_agent.py         Rule 10 wired. Opus.
│   ├── content_planner.py        Rule 10 wired. Sonnet.
│   ├── script_writer.py          Rule 10 wired. Voice DNA. Performance feedback injection.
│   ├── creative_director.py     Rule 10 wired. FAL.ai (flux/dev + ideogram/v2 + recraft-v3).
│   ├── data_analyst.py
│   ├── funnel_specialist.py
│   ├── website_agent.py
│   ├── brand_guardian.py         Rule 10 wired. Soul check.
│   ├── trend_sentinel.py         Pure math (Rule 10 Class-1).
│   ├── performance_tracker.py    Pure math (Rule 10 Class-1).
│   ├── carousel_designer.py      Sonnet content + Pillow OR Playwright HTML render. Multi-brand.
│   ├── carousel_html_renderer.py 5 editorial templates: HERO/INSIGHT/LIST/DATA_CALLOUT/PRINCIPLE_CTA.
│   ├── _provenance.py            Rule 10 helpers (build_source_index, validate_citations).
│   ├── _token_optimization.py    Token-saving utilities (planned: model selector, prompt slimmer).
│   ├── references/
│   │   └── meta_ads_framework.json   10-pillar Meta Ads framework — read by Ad Strategist.
│   └── cost_reporter.py          Uses importlib.util to load local supabase/db.py.
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
