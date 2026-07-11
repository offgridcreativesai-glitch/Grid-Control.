# Repo Reference Shelf (Jul 11 2026)

All reference repos cloned to `~/GC-ref-repos/` (OUTSIDE the GC repo — so AGPL/GPL code never
enters GC's licensed tree). Verdicts: 🟢 adopt into GC · 🔵 install for Claude Code · ⚪ reference-only
· ⚫ skip. **License rule: MIT/BSD/Apache = may vendor snippets; AGPL/GPL = read-only, never vendor.**

## New repos (Jul 11 batch)

| Repo | License | Verdict | Use |
|------|---------|---------|-----|
| [msitarzewski/agency-agents](https://github.com/msitarzewski/agency-agents) | MIT | ⚪ | 230+ agent personas. Roster is locked — mine for prompt patterns only. |
| [jamiepine/voicebox](https://github.com/jamiepine/voicebox) | MIT | 🟢 | Local Whisper STT + Kokoro/Qwen3 TTS. Borrow engines to replace ElevenLabs cost (creative voiceovers, trend-researcher STT). App → take the engine layer. |
| [blader/humanizer](https://github.com/blader/humanizer) | MIT | 🟢🔵 | Anti-AI-slop skill (33 patterns). **Top quick win** — serves our anti-filler mandate. Vendor into content agents + install for me. |
| [DietrichGebert/ponytail](https://github.com/DietrichGebert/ponytail) | MIT | 🔵 | YAGNI token-saver ruleset. For my build discipline. |
| [AgriciDaniel/claude-ads](https://github.com/AgriciDaniel/claude-ads) | MIT | ✅ already in GC | It's our `ads`/`ads-*` skills. Verify `ad-strategist` invokes it. |
| [11cafe/jaaz](https://github.com/11cafe/jaaz) | open | 🟢 ref | Multimodal creative assistant (canvas, character coherence, multi-provider). Reference for **#1 Creative Library** + creative-engine rebuild. |
| [obra/superpowers](https://github.com/obra/superpowers) | MIT | 🔵 | Dev-methodology skills (brainstorm→worktree→TDD→review). Install for me. |
| [mattpocock/skills](https://github.com/mattpocock/skills) | MIT | 🔵 (cherry-pick) | Engineering skills; overlaps superpowers. Take specific ones. |
| [ColeMurray/background-agents](https://github.com/ColeMurray/background-agents) | MIT | ⚫ | Off-domain (hosted coding-agent platform). Skip. |
| [davila7/claude-code-templates](https://github.com/davila7/claude-code-templates) | MIT | ⚪ | Catalog of CC agents/commands/MCPs/hooks. Shopping list. |

## Gap repos (from GAP_BUILD_PLAN_11JUL) — reference for the build sequence

| Gap | Repo | License | Verdict |
|-----|------|---------|---------|
| #1 Reputation | [MantisClone/awesome-reputation-systems](https://github.com/MantisClone/awesome-reputation-systems) | MIT | ⚪ data-model ref |
| #1 / #4 | [openstream/open-social-media-monitoring](https://github.com/openstream/open-social-media-monitoring) | AGPL | ⚪ ref-only |
| #2 White-label | [ixartz/SaaS-Boilerplate](https://github.com/ixartz/SaaS-Boilerplate) | (check) | ⚪ pattern ref (Next.js; GC is React+Flask) |
| #2 | nextjs/saas-starter, LastSaaS | — | ⚪ pattern ref (URLs unconfirmed — resolve at build time) |
| #3 Creative library | [atrocore/atrodam](https://github.com/atrocore/atrodam) | GPL | ⚪ asset-model ref |
| #3 | [resourcespace/resourcespace](https://github.com/resourcespace/resourcespace) | BSD | ⚪ some code reusable |
| #3 | [unopim/unopim-digital-asset-management](https://github.com/unopim/unopim-digital-asset-management) | (Laravel) | ⚪ asset-model ref |
| #4 Social listening | GitHub topic `brand-monitoring` (SERP+LLM tracker) | varies | ⚪ pattern ref |
| #5 Analytics | [plausible/analytics](https://github.com/plausible/analytics) | AGPL | ⚪ UX ref-only |
| #5 | [NafisRayan/Social-Media-Dashboard](https://github.com/NafisRayan/Social-Media-Dashboard) | (check) | ⚪ component ref |
| #5 | [socioboard/Socioboard-5.0](https://github.com/socioboard/Socioboard-5.0) | GPL/AGPL | ⚪ ref-only |

## Build sequence (unchanged, from GAP_BUILD_PLAN_11JUL)
1. **Creative Library** (#3) — refs: atrodam, resourcespace, unopim, jaaz · voicebox for voice assets
2. Analytics Cockpit (#5) — refs: plausible (UX), NafisRayan, socioboard
3. Social Listening (#4) — refs: open-social-media-monitoring, brand-monitoring
4. White-label SaaS Mode (#2) — refs: ixartz/SaaS-Boilerplate
5. Reputation (#1, optional) — refs: awesome-reputation-systems, open-social-media-monitoring

## Cross-cutting adopts (not gap-specific)
- **humanizer** → content agents (anti-slop) — do alongside #1.
- **voicebox engines** → creative voice (Kokoro/Qwen TTS local, Whisper) — folds into #1 / creative-engine rebuild.
- **superpowers + ponytail** → my Claude Code setup (install via `/plugin`, needs interactive terminal).
