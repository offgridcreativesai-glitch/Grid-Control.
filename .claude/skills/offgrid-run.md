---
name: offgrid-run
description: Runs the full OffGrid Marketing OS pipeline. Triggers all agents in correct order. Nothing runs without approval at each gate.
---

# OffGrid Marketing OS — Full Pipeline Run

## Execution Order
1. Run trend-researcher — scrape real trends
2. Run strategy-agent — scrape competitors, build roadmap
3. WAIT for brand owner approval on strategy
4. Run content-planner — build 30-day calendar
5. Run funnel-specialist — build conversion journey
6. WAIT for brand owner approval on content plan and funnel
7. Run script-writer — write all scripts and hooks
8. WAIT for brand owner approval on scripts
9. Run creative-director — produce all assets
10. WAIT for brand owner approval on creatives
11. Run data-analyst — weekly performance check
12. Run website-agent — research and build website

## Rules
- Nothing skips an approval gate
- Nothing is posted or published directly
- All outputs go to outputs/pending_approval/ first
- CEO Brain manages session state throughout
