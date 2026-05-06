# Token Optimization — OffGrid Marketing OS

Ported patterns from Everything Claude Code. Operating rules to keep token usage low and sessions long.

## The 7 leaks (where tokens go to die)

1. **Bloated CLAUDE.md** — loaded every turn. Keep it ≤200 lines. Move history to `docs/CLAUDE_HISTORY.md`.
2. **Re-reading the same file** — read once, reference by path/line.
3. **Tailing long backgrounds** — let `nohup` run; check file output later, don't stream.
4. **No sub-agent delegation** — when reading >3 files, use Explore agent.
5. **Running Opus when Haiku would work** — match model to task class.
6. **Auto-compact at random points** — use `/compact` strategically.
7. **Carrying dead context** — drop intermediate analysis once you've decided.

## Model selection rules

| Task class | Model | Cost ratio |
|---|---|---|
| Yes/no checks, schema validation, classification | Haiku 4.5 | 1× |
| Content generation, scripts, captions, summaries | Sonnet 4.6 | 5× |
| Strategy, multi-input synthesis, brand-defining outputs | Opus 4.6 | 25× |

Rule: default to Sonnet. Drop to Haiku when output is small + structured. Promote to Opus only when you can show why Sonnet failed.

In `agents/_token_optimization.py` (when built):
```python
def pick_model(task_class: str, task_size_tokens: int) -> str:
    if task_class in ("classify", "validate", "yes_no"):
        return "claude-haiku-4-5"
    if task_class == "strategy" and task_size_tokens > 8000:
        return "claude-opus-4-6"
    return "claude-sonnet-4-6"
```

## When to /compact

✅ DO compact:
- Research → Planning transition (research bulky, plan distilled)
- Planning → Implementation (plan in TodoWrite, free up code context)
- After milestone (clean slate for next phase)
- After failed approach (clear dead-end reasoning)

❌ DON'T compact:
- Mid-implementation (lose variable names, file paths, partial state)
- Right before a multi-file edit (lose the path map)

The strategic_compact hook (`scripts/strategic_compact.py`) suggests after 50 tool calls. Then every 25.

## Sub-agent delegation rule

For >3 file reads OR >2 web fetches, use sub-agents:
- `Explore` — code search, file location, "where is X defined"
- `general-purpose` — open-ended research with tool variety
- Specialized agents (`Plan`, `code-reviewer`, etc.) — when fits

Why: sub-agent results return as a single summary. Main context stays light.

## Background process rule

Long jobs (Whisper, Apify scrapes, builds, FAL renders):
- Use `run_in_background: true` on Bash
- Don't tail their stdout
- Read output file when done (or use the completion notification)

Saves: ~5K tokens per long-running job that you'd otherwise stream.

## CLAUDE.md slimming

Original `.claude/CLAUDE.md` was 925 lines. Slimmed at `.claude/CLAUDE_SLIM.md` to 113 lines (88% reduction).

Once approved by Gaurav:
```bash
mkdir -p docs
mv .claude/CLAUDE.md docs/CLAUDE_HISTORY.md
mv .claude/CLAUDE_SLIM.md .claude/CLAUDE.md
```

Estimated savings: ~50-70% of "always-on" tokens per turn.

## Per-agent prompt slimming

Each `.claude/agents/*.md` persona is loaded when agent invoked. Audit them:
- Remove redundant prose
- Use tables/bullets over paragraphs
- Move examples to a referenced file, not inline

Target: ≤150 lines per persona. Bigger = each agent run starts heavier.

## Hook setup (one-time)

Add to `~/.claude/settings.json`:
```json
{
  "hooks": {
    "PreToolUse": [
      {"matcher": "Edit|Write|Bash",
       "hooks": [{"type": "command",
                  "command": "python3 /Users/gauravoffgrid/offgrid-marketing-os/scripts/strategic_compact.py"}]}
    ]
  }
}
```

Or run: `bash scripts/install_strategic_compact.sh` (TODO — convenience installer).

## Measuring impact

Want to know if these are working? Track:
- Average tokens per turn (in Anthropic console / your billing)
- Session length before forced compaction
- Number of `/compact` invocations per session
- Sub-agent vs main-context read ratio

Aim for: session length 2x longer, tokens per turn 40-60% lower.
