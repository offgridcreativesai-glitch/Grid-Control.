# Flask API Routes — `dashboard_api.py`

Port 5001. All `/api/*` paths.

| Method | Path | Purpose |
|--------|------|---------|
| GET | `/api/health` | Health check |
| GET | `/api/agents` | List all agents with config |
| GET | `/api/agents/status` | Live status of all agents |
| POST | `/api/agents/run` | Run an agent (managed sessions or subprocess) |
| POST | `/api/agents/chat` | Agent chat (calls Claude with agent context) |
| POST | `/api/agents/train` | Agent training input |
| GET | `/api/brands` | List all brands |
| POST | `/api/brands/create` | Create new brand folder + default JSON files |
| GET | `/api/outputs/pending?brand_slug=` | Pending approval queue |
| GET | `/api/outputs/all?brand_slug=` | All outputs |
| POST | `/api/outputs/approve` | Move to approved/ |
| POST | `/api/outputs/reject` | Delete pending file |
| POST | `/api/outputs/request-changes` | Save change note |
| GET | `/api/outputs/download/<filename>` | Stream download |
| GET | `/api/outputs/media/<filepath>` | MIME-aware inline media |
| GET | `/api/brand/profile?brand_slug=` | Read brand_profile.json |
| POST | `/api/brand/profile?brand_slug=` | Write brand_profile.json |
| GET | `/api/brand/dashboard?brand_slug=` | Combined: profile + session_state + trends_live |
| GET | `/api/brand/file?brand_slug=&file=` | Whitelisted brand-output file reader |
| POST | `/api/pipeline/daily-run` | Chain Trend → Sentinel → Data Analyst → Contradictions |
| POST | `/api/carousel/generate` | Carousel Designer subprocess |
| POST | `/api/contradictions/check?brand_slug=` | Run contradiction detector live |
| GET | `/api/contradictions/latest?brand_slug=` | Most recent persisted report |
| POST | `/api/performance/log-post` | Append metrics to performance_inbox.json |
| GET | `/api/performance/history` | Computed performance_history.json |
| GET | `/api/performance/inbox` | Queued not-yet-ingested entries |
| POST | `/api/jarvis/query` | Voice answer + edge-tts audio |
| POST | `/api/voice/extract-profile` | Extract voice DNA from raw scripts |
| GET | `/api/voice/profile` | Read voice_profile.json |
| GET | `/api/connections/check` | Validate all API tokens |
| GET | `/api/config/keys` | Show which API keys are set |
| POST | `/api/brain/chat` | The Brain — embedded Claude chat (Sonnet 4.6 default, opt `use_opus`) |
| POST | `/api/brain/execute` | Execute approved Brain proposal (edit / bash) |
