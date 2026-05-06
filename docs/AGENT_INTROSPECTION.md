# Agent Introspection — 4-Phase Self-Debug

Ported from ECC's `agent-introspection-debugging` skill.
Activate when an agent loops, fails repeatedly, or burns tokens without progress.

## When to invoke
- Same tool fails 3+ times in a row
- Output repeatedly fails Rule 10 provenance validation
- Brand Guardian rejects 2+ retries
- Agent runs >5 min with no Loop Header progress
- Tool call count crosses 100 in a single agent run (signal of looping)

## Phase 1 — Failure Capture
Before retrying blindly, write down:

```markdown
## Failure Capture
- Agent: <name>
- Brand: <slug>
- Goal: <one line — what was the agent trying to do>
- Last successful step: <last good output>
- Last failed tool/call: <which tool, what args>
- Error: <message + stack tail>
- Repeated pattern: <what's looping>
- Context pressure: <oversized prompts, dup plans, runaway notes>
- Environment assumptions to verify: <cwd, env vars, file presence>
```

Save to `brands/{slug}/diagnostics/<agent>_<timestamp>.md`.

## Phase 2 — Root-Cause Diagnosis
Match against known failure patterns:

| Symptom | Likely cause | First check |
|---|---|---|
| JSON parse fails repeatedly | Claude inserting literal newlines in strings | Confirm `_safe_json_loads` is used |
| `data_provenance` validation fails 3x | Claude hallucinating sources OR source_index missing key | Print source_index keys, look for near-match |
| Brand Guardian rejects | Voice DNA drift OR forbidden phrase in output | Diff output vs `brand_profile.what_to_never_say` |
| Tool returns same error | Auth expired OR rate limit OR file moved | Check API keys, sleep+retry, verify path |
| Output truncated | `max_tokens` exceeded | Bump `max_tokens` 1.5x |
| Agent loops on same tool | Missing exit condition in agent loop | Add max-iteration cap |
| Notion 401 | Token expired | Regenerate at notion.so/my-integrations |
| Apify 403/429 | Rate limit OR proxy block | Wait, retry with different residential proxy |

## Phase 3 — Contained Recovery
Apply the SMALLEST corrective action that addresses the diagnosed cause:

- Auth expired → tell user to regenerate, STOP agent run
- Schema mismatch → log a warning, save with `provenance_validation_failed: true` flag
- Single bad tool call → retry once with corrected args, then escalate
- Repeated same failure → STOP the agent, save the failure capture, return to user

**Never apply blanket retries.** Retries without diagnosis = token burn.

## Phase 4 — Introspection Report
Write a concise report at `brands/{slug}/diagnostics/<agent>_<timestamp>_report.md`:

```markdown
## Introspection Report
- Agent: <name>
- Outcome: recovered | escalated | stopped
- Root cause: <one line>
- Fix applied: <what we changed>
- Pattern to learn: <if recurring, propose adding to known-causes table>
- Tokens spent on diagnosis: <est>
- Next safer retry strategy: <if applicable>
```

## How agents invoke this

In every agent's main `run()` function, wrap the inner loop with:

```python
try:
    result = self.run_autoresearch_loop(...)
except Exception as e:
    self.introspect(failure=e, phase="capture")
    return {"blocked": True, "diagnostic_path": "..."}
```

Build status: spec only. Wire into agents on next pass when needed.
