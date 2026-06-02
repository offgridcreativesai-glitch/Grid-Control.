# PILLAR-FORGE-29MAY — AskGauravAI YouTube Long-Form Edit

> Safe word: **PILLAR-FORGE-29MAY**
> Status: IN PROGRESS — 1080p assembly running
> Created: May 29, 2026
> Updated: May 29, 2026 (session 2)

## Recordings Location

`brands/askgauravai/Raw_recordings/Week 1/Youtube long form/`

## File → Script Section Mapping (confirmed by Gaurav)

All files named per script sections. No "Section 3" file exists — both are "Section 4" (.mov + .m4a).

| File | Script Section | Duration |
|------|---------------|----------|
| Clip maker 1 (.mov + .m4a) | Hook Open + Intro | ~69s |
| Failure pattern 1 (.mov + .m4a) | Failure Pattern 1: The Assumption Campaign | ~146s |
| Failure pattern 2 (.mov + .m4a) | Failure Pattern 2: The Borrowed Framework | ~146s |
| Failure pattern 3 (.MOV + .m4a) | Failure Pattern 3: The Timing Blind Spot | ~123s |
| Section 4 (.mov + .m4a) | What Pre-Advertising Intelligence Means | ~144s |
| Clip maker 2 (.MOV + .m4a) | Diagnostic Line — The Pattern | ~94s |
| Clip maker 3 (.mov + .m4a) | Principle Close | ~112s |
| CTA (.mov + .m4a) | CTA + Close | ~58s |

## Audio Decision

Using embedded video audio (camera mic), NOT separate .m4a wireless mic files. Gaurav will fix mic sync for next video.

## Pillar Script Reference

`brands/askgauravai/outputs/week1_shooting_scripts.html` — Script 2 of 12 (YouTube Long-form)

## Key Editing Instructions (from shooting script)

1. **Zoom-out on Clip Marker 3**: Principle close + CTA get 90% scale (mid-shot feel)
2. **End card**: 5s branded card — "AskGauravAI / Build the intelligence first. / Subscribe"
3. **Chapter timestamps**: Generated from assembly for YouTube description
4. **Clip Markers** (for derivative cuts):
   - CLIP MARKER 1 — Hook open → IG Reel
   - CLIP MARKER 2 — Diagnostic line ("Past performance data vs market intelligence") → IG Reel
   - CLIP MARKER 3 — Principle close ("Build the intelligence first") → IG Reel
5. **Derivatives cut FROM final assembled video** (GaryVee pillar model), NOT from raw clips

## Completed Steps

1. ✅ Whisper transcription of all 8 audio clips (saved in `Raw_recordings/transcripts/`)
2. ✅ Mic sync attempted — abandoned, using video audio instead
3. ✅ Audio cleanup: FFT noise reduction, 80Hz-14kHz bandpass, compression, EBU R128 normalization
4. ✅ Trimming: False starts, slates, retakes removed from all clips
5. ✅ Cleaned clips saved to `brands/askgauravai/Raw_recordings/cleaned/`
6. ✅ End card generated (1080p PNG → 5s MP4)
7. 🔄 Direct assembly at 1080p — RUNNING (background task bpyar93v7)
8. ⏳ Agent assembly with FAL.ai B-roll — NOT STARTED (run after direct completes)
9. ⏳ Derivative cutting from final video — script ready at `scripts/pillar_cut_derivatives.py`

## Scripts

| Script | Purpose |
|--------|---------|
| `scripts/pillar_video_sync.py` | Mic-to-video sync (not used — audio decision changed) |
| `scripts/pillar_video_cleanup.py` | Noise reduction + trim false starts |
| `scripts/pillar_assemble_direct.py` | Direct ffmpeg assembly (1080p) |
| `scripts/pillar_assemble_agent.py` | Agent path with FAL.ai B-roll (1080p) |
| `scripts/pillar_cut_derivatives.py` | Cut reels/shorts FROM final pillar video |

## Cleaned Clips (ready for assembly)

`brands/askgauravai/Raw_recordings/cleaned/`
- 01_hook.mov (69s)
- 02_failure_pattern_1.mov (146s)
- 03_failure_pattern_2.mov (146s)
- 04_failure_pattern_3.mov (123s)
- 05_market_intelligence.mov (144s)
- 06_the_pattern.mov (94s)
- 07_build_intelligence_first.mov (112s)
- 08_cta.mov (58s)
- 09_end_card.mp4 (5s)
Total: ~14.9 min + 5s end card

## Remaining Blockers

1. ~~Anthropic credits~~ ✅ Recharged
2. **Key rotation** — .env exposed on prod. Rotate tonight.
3. **Decorator fix** — 54 Flask routes auth bypass. Fix tonight.

## How to Resume

Tell Claude: **"PILLAR-FORGE-29MAY"** — read this file, check background task status, continue.
