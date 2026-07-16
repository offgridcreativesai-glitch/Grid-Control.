# GRID CONTROL — ACTIVE GROUND RULES (surfaced every session by SessionStart hook)

These are ENFORCED expectations, not suggestions. Machinery backs several of them
(hooks/tests/CI); the rest are the standing rules that have burned this project when
forgotten. Treat every one as in effect from turn 1.

1. **Non-technical founder.** Gaurav does not read code. Never say "done", "fixed",
   "works", or "yes" about behavior you did not verify THIS SESSION with a tool.
   State what you verified and how. Before any done-claim, run the `gc-verify` skill.
2. **No raw JSON reaches Gaurav — ever.** Not in chat, not in the dashboard. Every
   agent output renders through `utils/output_formatter.format_for_notion()` as human
   markdown. A new agent output type ships its formatter branch + test in the same
   commit (`utils/test_formatter_coverage.py` enforces the roster).
3. **RULE ZERO — ASK, never guess** on infra / OAuth / connections / deploys /
   accounts / anything external. `docs/CONNECTIONS_SETUP.md` is the authority; if
   it's silent, say "I don't know, tell me" and WAIT. Never reconstruct from inference.
4. **Never self-trigger user-facing GC actions** (run agents, generate reports,
   publish, approve) from the CLI or backend. Gaurav clicks them in the GC UI.
   Fix the FE path instead of routing around it.
5. **Every bug fix ships with a test** — fail-on-old, pass-on-fix, wired into the
   REAL code path (never a copy). The commit guard (`.claude/hooks/test_guard.py`)
   blocks app-code commits with no test staged. CI is the door guard.
6. **One repo, main branch only.** Commit ONLY files you created/changed, by explicit
   path. NEVER `git add -A` / `git add .` — run `git status` first (a broad commit
   once swept up other sessions' work).
7. **Pre-flight before paid runs.** Check credit balances, API keys, and the cost
   gate before any run that spends money. One scheduler, in-flight lock, budget caps.
8. **Zero fabrication.** Every data point traces to a real scrape, API call, or user
   input. Missing data → say "no data", stop, ask. Never plausible-looking numbers.
