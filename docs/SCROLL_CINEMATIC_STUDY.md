# scroll-cinematic-claude — Study (Jun 23 2026)

Source: https://github.com/zubair-trabzada/scroll-cinematic-claude (Zubair — same author as brain-map).
A **Claude Code skill** that builds "3D scroll" cinematic websites from ONE prompt via the
**Higgsfield MCP**. Installed at `~/.claude/skills/scroll-cinematic/` (skill `scroll-cinematic`).

## The core insight
The viral Apple/Awwwards "3D scroll" effect is **NOT Three.js** — it's a **canvas image-sequence
scrub**: a short cinematic clip is sliced into ~180 numbered JPGs, all preloaded, and the frame
drawn to `<canvas>` is chosen by scroll progress. Lenis smooth scroll + scroll-synced overlay copy
makes it read as premium 3D. The "3D" comes entirely from the source video. Stack: plain
HTML/CSS/JS + Lenis, zero build.

## Pipeline (one prompt → live site)
1. **Higgsfield `generate_image`** (`nano_banana_pro`) → crisp 16:9 hero keyframe.
2. **Higgsfield `generate_video`** (`seedance_2_0`, 1080p, 6s, keyframe as `start_image`) → 1–2
   clips: turntable (360°), fly-through, reveal/explode, abstract liquid-metal. Generated in
   parallel; ~54 credits/clip; built-in nsfw-refund-retry (fall back to `grok_video_v15` 720p).
3. **ffmpeg** slices → ~180 JPGs, compress to 1600px/q88 (auto-installs ffmpeg).
4. **`SCRUB_SECTIONS` config** + branded multi-section site + Lenis → launch on localhost.

## The engine (reusable ~90-line IP, `scroll-cinematic.js`)
Preload all frames → sticky stage (`height:420–600vh`, inner `sticky;top:0;height:100vh`) →
`progress = -rect.top/(height-innerH)` → `frameIndex = floor(p·frameCount)` → redraw only on index
change → cover-fit + HiDPI → driven from the Lenis rAF loop. Plus IntersectionObserver reveals +
count-up stats.

## Relevance to Grid Control (double)
1. **The landing** — this is the proven technique for the helloelva-grade premium scroll we want.
   Atlas doing a 360° turntable as the scroll hero, then the crew assembling > the constellation.
2. **Creative-engine rebuild** ([[project_creative_engine_rebuild]]) — it's a working Higgsfield MCP
   pipeline; reference for our creative agents' `generate_image`/`generate_video` calls, model
   choices, cost preflight, nsfw-retry.
3. **Product wedge** — website-agent / creative-director could ship scroll-cinematic landing pages
   for client brands.

## Status / gating
Skill installed. Live use is **gated on Higgsfield MCP** connection (PRO plan — build now, fire
later, per the creative-rebuild note). Robot cast → Atlas turntable becomes the landing scroll hero
once Higgsfield is live.

Clone studied at `/tmp/scroll-cinematic` (ephemeral).
