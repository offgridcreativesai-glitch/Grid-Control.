# AI Tools' System Prompts — Deep Study (Jun 23 2026)

Source: https://github.com/x1xhlol/system-prompts-and-models-of-ai-tools (LeaksLab / x1xhlol).
A crypto-donation-funded collection of **leaked/extracted system prompts + tool JSON schemas**
from 33 commercial AI tools. Studied by cloning and reading the actual files (Manus + Lovable
in full, all 33 surveyed, cross-tool pattern greps).

## What's in it (33 tools)
Agentic coders/IDEs: **Cursor** (6 prompt versions), **Windsurf**, **Devin**, **Augment**,
**Cline/RooCode/Bolt** (open), **Trae**, **Qoder**, **Kiro**, **Replit**, **VSCode Agent**
(per-model: gpt-5, claude-sonnet-4, gemini-2.5). Design/site builders: **v0**, **Lovable**,
**Same.dev**, **Leap.new**, **Orchids**, **Emergent**. Autonomous agents: **Manus** (loop +
modules + tools), **Google Antigravity** (planning mode). Assistants: **Anthropic** (Claude
Code 2.0, Sonnet 4.5/4.6, Claude for Chrome), **Perplexity**, **NotionAI**, **Comet**, **Poke**,
**Warp**, **Cluely**, **dia**. Most folders carry a `Prompt.txt` + a `Tools.json` (the actual
function schemas).

## The high-value cross-tool patterns

### 1. The autonomous agent loop (Manus — the clearest spec)
Manus runs an explicit **event stream** of typed events: Message, Action, Observation, **Plan**
(from a Planner module), **Knowledge** (best-practice module), **Datasource** (data-API module).
Rules: **one tool call per iteration**; loop until done then go idle. This is the Noimos/Manus
pattern we keep referencing — and it maps almost 1:1 onto our CEO-Brain-orchestrates +
provenance + trends/data-sources design.

### 2. Notify vs Ask (= our approval gate)
Manus splits user messaging into **`notify`** (non-blocking progress) and **`ask`** (blocking,
needs a reply) — "reserve ask for essential needs to avoid blocking progress." This is exactly
our approval-gate distinction (auto-progress vs human-gated).

### 3. Information hierarchy + anti-fabrication (= our zero-assumption rule)
Manus: **authoritative datasource API > web search > model's internal knowledge**; "snippets
are not valid sources, access the original page"; "fabricating non-existent APIs is prohibited."
Industry-standard version of our real-data mandate + no-fabrication rule.

### 4. Plan / TODO discipline (~15 of 33 tools)
Manus `todo.md` checklist updated after each step; Cursor/Devin/Kiro/v0/Cline/Qoder/Antigravity
all have an explicit **plan phase** or task-list artifact before executing. Plan-before-code is
near-universal in the good ones.

### 5. Parallel tool calls (~20 of 33)
Claude Code, Cursor, Lovable, Devin, Gemini CLI, etc. all mandate: **invoke independent
operations simultaneously, never sequentially.** Pure latency/cost win.

### 6. Concision mandates (token discipline, everywhere)
"Answer in fewer than 2–4 lines," "under 15 words," "minimize output tokens," "no emojis,"
"don't summarize what the diff already shows." Matches our terse-response CLAUDE.md rules.

### 7. Design-system-first generation (Lovable + v0 — mirrors our stack)
Lovable is React+Vite+Tailwind+shadcn (our stack) and its hard rules ARE ours: **semantic design
tokens only, never ad-hoc `text-white`/inline styles**; edit `index.css`/tailwind config not
components; **discussion-mode default** (only build on explicit "implement/build"); **no scope
creep / no overengineering**; small focused components; "wow first impression"; debug via
console/network tools FIRST. Validates our Tailwind-v4-tokens conventions and chat-console UX.

### 8. Secrecy / "don't reveal" (~11 tools = our THE SECRET)
Anthropic, Devin, Perplexity, Poke, Trae, Warp instruct: never reveal the system prompt; don't
name internal tools to the user. Industry-wide confirmation of our THE SECRET (client UI hides
model/cost/tokens/infra).

### 9. Tool-schema craft (the `Tools.json` files)
The function schemas are verbose and example-rich: long natural-language descriptions, explicit
"when to use / when NOT to use," enumerated params with constraints. Worth modeling our agents'
tool defs on.

## What to apply to Grid Control
1. **Adopt the Manus loop framing in agent prompts** — give each of our 18 agents an explicit
   event-loop + plan(todo) + "one action per step" + notify/ask structure. Tightens behavior and
   makes the approval gate native to the prompt, not bolted on.
2. **Bake the info-hierarchy line verbatim** into every Class-2 agent: authoritative source >
   web > internal knowledge; never fabricate. (We have the policy; these are battle-tested words.)
3. **Plan/TODO artifact per agent run** — a `todo.md`-style checklist mirrors our AutoResearch
   loop header; consider standardizing it.
4. **Lovable/v0 rules → our FE port + creative agents** — the design-token discipline is already
   ours; the "discussion-default, wow-first-impression, no scope creep" lines are good to lift
   into the creative-director / brand-guardian prompts.
5. **Tool-schema upgrade** — model our agent tool definitions on the verbose, example-rich
   `Tools.json` style (when-to-use / when-not).

## Verdict
This repo is a **prompt-engineering benchmark**, not code to integrate — the single best corpus
for seeing how the top agent products structure prompts, tool schemas, plan modes, and guardrails.
Highest leverage for us: **rewrite the 18 agent prompts against these patterns** (loop + plan +
notify/ask + info-hierarchy + concision), and lift the **Lovable/v0 design rules** into the FE
port and creative agents. Connects to [[reference_hermes_agent]], the Noimos/Manus pattern
([[competitor_noimosai]]), and our [[feedback_smart_model_routing]] / no-fabrication rules.

Clone studied at `/tmp/sysprompts` (ephemeral).
