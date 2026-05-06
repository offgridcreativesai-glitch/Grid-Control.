# OffGrid Eval Harness — Rule 9 Formalized

Ported from ECC's `eval-harness` skill. Formalizes Rule 9 (AutoResearch Standard) with measurable evals + pass@k metrics.

## Why this exists
Rule 9 says every output is the winner of an internal loop with measurable "better." This doc gives that loop teeth — explicit grader types, eval categories, regression tracking.

## Eval Types

### 1. Capability Eval — does this agent CAN do X?
Use when: launching a new agent, adding a new task type to existing agent.

```markdown
[CAPABILITY EVAL: <agent>-<feature>]
Task: Specific task description
Success Criteria:
  - [ ] Output is valid JSON conforming to expected schema
  - [ ] Output passes Rule 10 provenance validation
  - [ ] Output passes Brand Guardian soul check
  - [ ] (Agent-specific criterion)
Expected Output: Description of expected result
```

### 2. Regression Eval — did we break what worked?
Run on every meaningful agent change (prompt edit, schema bump, dependency upgrade).

```markdown
[REGRESSION EVAL: <agent>]
Baseline: <git SHA or date checkpoint>
Tests:
  - voice-match: PASS/FAIL
  - hook-strength: PASS/FAIL
  - data-provenance: PASS/FAIL
Result: X/Y passed (previously Y/Y)
Action: <none | re-run | rollback prompt change>
```

## Grader Types

### A. Code-based grader (deterministic)
For schema, format, presence checks. No Claude needed.
- "Does output JSON have all required fields?" → grep / json.dumps
- "Does provenance_validation.passed equal True?" → boolean check
- "Does headline length ≤ 80 chars?" → `len(headline) <= 80`

### B. Model-based grader (LLM judge)
For quality, voice match, brand fit. Use Haiku for cost.
```python
prompt = f"""Score this {agent}'s output on these dimensions (1-5 each):
- Voice match to brand_profile.tone_of_voice
- Hook strength (scroll-stop in 2 sec)
- Audience fit (matches audience_primary)

Output JSON: {{"voice": 1-5, "hook": 1-5, "fit": 1-5, "reasoning": "..."}}

Output to grade:
{output_json}
"""
```

### C. Human grader (flag for review)
Required for: brand-defining outputs, first-time agent runs, when CRITICAL contradictions surface.

## Metrics

- **pass@1** — first attempt success rate. Target: ≥70% for stable agents.
- **pass@3** — success within 3 attempts (with retries). Target: ≥90%.
- **pass^k** — all k trials succeed. Use for: brand-critical outputs (target pass^3 ≥ 80%).

## Where evals live

- `tests/evals/<agent>/capability_*.md` — capability eval specs
- `tests/evals/<agent>/regression_*.md` — regression test specs
- `tests/evals/runner.py` — runs all evals, reports pass@k per agent
- Wired into GitHub Actions: runs on PR + nightly

## Hook into Rule 9 Loop Header

Every agent output already has:
```
LOOP: [agent] — [output type]
GOAL: [...]
METRIC: better = [...]
VARIANTS TESTED: [N]
WINNER: [...]
```

NEW: every output also gets:
```
EVAL: <pass/fail counts vs baseline>
GRADER: code|model|human
PASS@K: pass@1=N% pass@3=N%
```

## Build status

- Spec: this doc
- Runner: `tests/evals/runner.py` — TODO
- First eval suite: Strategy Agent capability + regression — TODO
- CI integration: `.github/workflows/evals.yml` — TODO

When you say "build the eval runner," I'll wire it up against existing agents.
