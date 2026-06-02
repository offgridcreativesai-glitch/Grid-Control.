---
type: community
cohesion: 0.12
members: 32
---

# Agent System — Creative, Brand

**Cohesion:** 0.12 - loosely connected
**Members:** 32 nodes

## Members
- [[.__init__()_4]] - code - agents/creative_director.py
- [[._build_caption_clips()]] - code - agents/creative_director.py
- [[._edit_video()]] - code - agents/creative_director.py
- [[._transcribe_video()]] - code - agents/creative_director.py
- [[.generate_image()]] - code - agents/creative_director.py
- [[.generate_narration()]] - code - agents/creative_director.py
- [[.load_competitors()]] - code - agents/creative_director.py
- [[.load_scripts()]] - code - agents/creative_director.py
- [[.log()_2]] - code - agents/creative_director.py
- [[.process_raw_footage()]] - code - agents/creative_director.py
- [[.run()_2]] - code - agents/creative_director.py
- [[.run_autoresearch_loop()]] - code - agents/creative_director.py
- [[.run_brand_safety_check()]] - code - agents/creative_director.py
- [[3 creative variants         A — Minimal text, visual-led         B — Bold headl]] - rationale - agents/creative_director.py
- [[4-point brand safety check per spec. Returns {passed bool, flags }.]] - rationale - agents/creative_director.py
- [[Brand Safety Check]] - rationale - .claude/agents/creative-director.md
- [[Build word-grouped caption TextClips from Whisper segments.]] - rationale - agents/creative_director.py
- [[Creative Director Agent]] - document - .claude/agents/creative-director.md
- [[Creative Director — OffGrid Marketing OS Agent ID 4  Runs after Script Writer]] - rationale - agents/creative_director.py
- [[Edit raw footage         - Crop to 916, resize to 1080×1920         - Add Whis]] - rationale - agents/creative_director.py
- [[Generate audio narration via ElevenLabs. Returns file path or None.]] - rationale - agents/creative_director.py
- [[Generate image via FAL.ai.         text_heavy=True  → fal-aiideogramv2  (bette]] - rationale - agents/creative_director.py
- [[Load competitors_db.json — graceful fallback if missing or empty.]] - rationale - agents/creative_director.py
- [[Load most recent Script Writer output from pending_approval (slug-cased path).]] - rationale - agents/creative_director.py
- [[Scan brands{slug}raw_footage for new video files.         For each transcrib]] - rationale - agents/creative_director.py
- [[Transcribe videoaudio via FAL.ai Whisper.         Returns {text str, segmen]] - rationale - agents/creative_director.py
- [[Visual Psychology Rules]] - rationale - .claude/agents/creative-director.md
- [[_escape_literal_newlines_in_strings()]] - code - agents/creative_director.py
- [[_safe_json_loads()]] - code - agents/creative_director.py
- [[bool_2]] - code - agents/creative_director.py
- [[float_2]] - code - agents/creative_director.py
- [[str_7]] - code - agents/creative_director.py

## Live Query (requires Dataview plugin)

```dataview
TABLE source_file, type FROM #community/Agent_System__Creative_Brand
SORT file.name ASC
```

## Connections to other communities
- 5 edges to [[_COMMUNITY_Claude Agent Definitions — Community, Content]]
- 4 edges to [[_COMMUNITY_Managed Agent Prompts — Pipeline]]
- 3 edges to [[_COMMUNITY_Agent System — Ui, Trend]]
- 2 edges to [[_COMMUNITY_Ceo_Brain — Agent]]
- 1 edge to [[_COMMUNITY_Agent System — Funnel, Prompt]]
- 1 edge to [[_COMMUNITY_Claude Skills — Brand, Content]]

## Top bridge nodes
- [[Creative Director Agent]] - degree 30, connects to 5 communities
- [[.run_autoresearch_loop()]] - degree 8, connects to 1 community
- [[.__init__()_4]] - degree 4, connects to 1 community