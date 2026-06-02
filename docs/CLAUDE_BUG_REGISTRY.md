# Bug Registry — Tracked Fixes (DO NOT REPEAT)

Read this when debugging similar-looking issues — the fix is likely here.

| # | File | Bug | Fix | Status |
|---|------|-----|-----|--------|
| 1 | `dashboard_api.py` | `_bootstrap_brand_memory` called before `profile` dict was defined — brand creation crashed | Moved call to after `profile` is built and written | ✅ Fixed Apr 14 |
| 2 | `agents/cost_reporter.py` | `import supabase.db as _db` fails — pip `supabase` package shadows local `supabase/db.py` | Use `importlib.util.spec_from_file_location` to load local file directly | ✅ Fixed Apr 14 |
| 3 | `agents/trend_researcher.py` | `__init__` had hardcoded default `brand_slug = "offgrid-creatives-ai"` — always ran for wrong brand | Reads from `os.getenv("ACTIVE_BRAND", "offgrid-creatives-ai")` | ✅ Fixed Apr 14 |
| 4 | `agents/trend_researcher.py` | Hardcoded `NICHE_HASHTAGS` was D2C/Meta content — wrong for fashion brands | Replaced with `_build_niche_hashtags(brand_profile)` — dynamic from brand profile | ✅ Fixed Apr 14 |
| 5 | `ceo_brain/orchestrator.py` | `save_agent_output` used display name as folder ("Trend Researcher" not "trend-researcher") | Slugify: `re.sub(r"[^a-z0-9-]", "", agent_name.lower().replace(" ", "-"))` | ✅ Fixed Apr 14 |
| 6 | `dashboard/src/screens/MeetingRoom.tsx` | `clearIndividualHistory` called on every agent click — wiped in-memory history | Removed the call from `handleSelectAgent` | ✅ Fixed Apr 14 |
| 7 | `dashboard/src/store/brandStore.ts` | No localStorage persistence — chat history lost on page refresh | Added `persist` middleware, `partialize` chat histories + active brand | ✅ Fixed Apr 14 |
| 8 | `agents/trend_researcher.py`, `agents/data_analyst.py`, `agents/script_writer.py` | `json.loads(claude_response)` failed with `Unterminated string` (literal newlines in JSON values) | Added `_safe_json_loads()` + `_escape_literal_newlines_in_strings()` helper | ✅ Fixed Apr 25 |
| 9 | `agents/trend_researcher.py` | AutoResearch loop `max_tokens=4000` truncated at ~15.5K chars, JSON parse fails | Bumped to `max_tokens=16000` + `stop_reason == "max_tokens"` truncation log | ✅ Fixed Apr 25 |
| 10 | `dashboard_api.py` connections check | Twitter `/2/users/me` returns 403 on Free tier App-Only Bearer (needs OAuth user-context) | 401 → invalid; 403/429 → "Token set (Free tier — read via Apify)", marked connected | ✅ Fixed Apr 25 |
| 11 | `agents/carousel_designer.py` | Brand palette hex contained descriptive text (e.g. `"#0F4C5C (deep teal)"`) — Pillow rejected | `_clean_hex()` static helper extracts pure hex via regex | ✅ Fixed May 2 |
| 12 | `ceo_brain/orchestrator.py` | Build H auto-block was overzealous — quarantined ANY save when ANY CRITICAL contradiction existed | Quarantine only if saving agent is named in a CRITICAL finding's `agents_involved` | ✅ Fixed May 2 |
| 13 | `agents/carousel_designer.py` | HelveticaNeue.ttc font index 3 = BoldItalic, 5 = UltraLight (slides rendered italic + thin) | Index 0 = Regular, index 1 = Bold | ✅ Fixed May 2 |
