# Creative Engine Rebuild — Higgsfield + Creative-Director Brain

> Decided Jun 15 2026 (revised same day).
> (1) Replace FAL with Higgsfield as the generation engine.
> (2) Upgrade the *thinking* of every creative agent so our output stops looking
> like generic AI — the brand's whole pitch ("real intelligence, not the AI crowd")
> is false if our feed looks like everyone else's. Visual POV = **Claude proposes, Gaurav reacts**.
> PRO plan comes LATER → build the wiring now (gated off), creative work later.
>
> **SEQUENCING (Gaurav, revised): NOT parallel. Finish the current build first
> (Railway worker + Wave 2 F1–F4), THEN do the creative work AGENT-BY-AGENT** —
> feed each creative agent real references and correct its pipeline hands-on, one
> at a time. The Higgsfield swap rides along with that per-agent work.
>
> **NO RIGID CREATIVE RESTRICTIONS (Gaurav).** A hard reject-list/ban-cage is its
> own kind of generic. Direction is POSITIVE and generative — POV + references +
> feel as a north-star to FEED each agent, never a gate that blocks output. Taste
> develops by feeding + iterating per agent, not by enforcing rules.

## 1. Higgsfield — what we actually get (deep study, Jun 15 — installs DONE)

**Three integration surfaces (CLI + skills installed Jun 15):**
- **Python SDK `higgsfield-client`** — `pip install higgsfield-client`. **THIS is the agent path** (our backend is
  Python; cleaner than hand-rolling REST). Pattern: `higgsfield_client.subscribe(model, arguments={...})` (submit+wait)
  or submit → `poll_request_status()` (Queued/InProgress/Completed) → `controller.get()`. Sync + `_async` variants.
  **Auth = `HF_KEY="key:secret"`** (or split `HF_API_KEY`+`HF_API_SECRET`), keys from cloud.higgsfield.ai —
  NOT a plain Bearer token. This replaces FAL inside `creative_director.py` / reel + carousel image gen.
- **CLI `higgsfield`** (aliases `higgs`/`hf`) — installed via Homebrew tap (`/opt/homebrew/bin/higgsfield`, v0.2.1, MIT).
  `auth login` · `generate create <model> --prompt … [--image/--start-image] --wait` · `model list/get` ·
  `marketing-studio` · `product-photoshoot` · `soul-id` · `account` (credits) · `workspace`. `--json` for machine output.
  A fallback the agents can shell to; SDK preferred.
- **Skills (4, installed via `npx skills add higgsfield-ai/skills` → `.agents/skills/`, symlinked to Claude Code):**
  `higgsfield-generate`, `higgsfield-soul-id`, `higgsfield-product-photoshoot`, `higgsfield-marketplace-cards`.
  Pure-markdown (no executable payload — installer's "High/Critical Risk" flags were heuristic noise off the
  official `curl|sh` CLI-installer fallback line; verified clean). **These are what I (Claude Code) use interactively**
  during art-direction (`/higgsfield:generate` etc.). Also a hosted MCP connector (already connected this session).

**Model routing (catalog studied — match by intent, run `higgsfield model list` to confirm IDs):**
- **`gpt_image_2`** — high-fidelity design / banners / **on-image TEXT** → our **carousels + PDF/report visuals**. (Default for design.)
- **Soul 2.0 (`text2image_soul_v2`)** — aesthetic UGC / fashion-editorial / lifestyle character → askgauravai **founder-documentary stills**. "Feels shot, not generated" = our anti-generic weapon. Soul-aware (accepts a Soul ref).
- **Soul Cinema** — cinematic film-grade stills. **Soul Location** — best-in-class no-people environments.
- **Seedance 2.0 (`seedance_2_0`)** — SOTA all-purpose **video** (multi-shot, 4–15s, image-to-video) → our **reels**. Kling 3.0 = cheaper substitute.
- **Marketing Studio (`marketing_studio_image`/`_video`)** — product URL + avatar → publish-ready **ads** (RAG over the brand's own assets).
- **Soul ID** — train a consistent face from real photos → on-identity images. (Founder likeness at scale — flag against "no AI clone Month 1"; opt-in, Gaurav decides per brand. Note: catalog rejects *real public figures* in plain prompts.)
- **Virality Predictor (`brain_activity`)** — scores a finished clip's hook/attention/retention → **feeds our performance/eval loop** (Performance Tracker, AutoResearch).

**Prompt grammar Higgsfield rewards (feed this to Script Writer / CD — confirms our thesis):** concrete + sensory —
*subject + setting + style*, *camera* (lens 35/85mm, angle, motion: dolly/track/push), *lighting* (rim, neon, backlight),
*medium* (photo/film/oil/anime). Keep **under ~200 tokens** (long prompts distort). Phrase **positively** (no neg-prompt on most models: "tack sharp" not "no blur"). Image-to-image → describe only what *changes*. Image-to-video → describe *motion*, don't redescribe the frame.

**Cost:** credit-based (PRO later; account currently shows credits exhausted). → gate on `HF_KEY`/`HIGGSFIELD_API_KEY` presence; absent = "prepared, not generated" (same honest pattern as the IG publisher).

**Org repos triaged:** USE → `higgsfield-client` (Python SDK, agent path) · `cli` · `skills`. IGNORE → `higgsfield` (a GPU/LLM *training* framework, unrelated) · `juice-shop` (OWASP security-training fork) · `higgsfield-js` (Node SDK — backend is Python).

## 2. Replace FAL — architecture

Today FAL is called directly inside agents → engine is hardcoded, no taste layer. Fix:

- **`agents/_lib/media_gateway.py`** (new) — single source of truth for media gen, mirroring `model_gateway.py`.
  `generate_image(brief)` / `generate_video(brief)` / `animate(image, motion_brief)`. Wraps the **`higgsfield-client`
  Python SDK** (`subscribe`/poll). A `MEDIA_ROUTING` map picks the model by asset intent (carousel/PDF→`gpt_image_2`,
  lifestyle still→Soul 2.0, reel→`seedance_2_0`, ad→Marketing Studio) the same way `model_gateway` routes LLMs.
  **default engine → higgsfield**, FAL kept only as a fallback constant (not used). Engine-swappable, agents never hardcode.
- Rewire `creative_director.py` (+ any reel/carousel image gen) to call the gateway, not FAL.
- Credit-gate: no `HIGGSFIELD_API_KEY` → return a "prepared" package (brief + prompt + chosen preset), never a fake asset (zero-assumption rule).
- Keep it behind the **`cd_guard`** rule — generation only via the Creative Director agent; I never hand-author.

## 3. The Creative-Director BRAIN (the real fix — kills sameness)

Swapping engines alone does nothing if the *brief* is generic. New pipeline inside the CD agent:

**Step A — Art-Direction Brief (before any pixel):** concept → references → composition → palette →
lighting → typography → motion. Structured, per asset. This is the "thinking" that's missing today.

**Step B — Per-brand Visual POV (the anti-sameness anchor):** each brand gets a locked `visual_pov.json`
(palette, type system, framing rules, texture, motion signature, do/don't). The CD brief MUST conform.
Claude proposes it; Gaurav reacts/locks. (Section 4 = first cut.)

**Step C — Coach, don't cage (NO hard restrictions):** instead of an auto-reject ban-list, each creative agent is
*fed* — strong references, worked examples, the brand POV — and its pipeline is corrected hands-on through
iteration. A self-critique pass may *flag* "does this read as generic AI?" as guidance, but it never hard-blocks
output. Taste develops by feeding + iterating per agent, not by enforcing rules (a ban-cage is its own generic).

**Step D — Prompt upgrade:** replace thin one-line prompts with POV-derived, reference-grounded, Soul-aware prompts
(Soul rewards photographic language: lens, film stock, lighting, grain — not "4k hyperrealistic trending").

This same brain upgrades **PDF reports** too (use the `canvas-design` design-philosophy skill + a real design
system, not the current generic template) and **editing** (Higgsfield Viral Clip Generator + `adobe-for-creativity`).

## 4. First-cut Visual POV per brand (REACT TO THIS)

**askgauravai** — *anti-AI-gloss, founder-documentary.*
Voice is "feel shot not generated, show the work, slightly contrarian, anti-hype" → visuals must look **real and
tactile**, not rendered. Palette cream + coral (locked earlier). Editorial bold-type carousels (not centered
template text). Textures: real desk/screen/whiteboard/phone-shot. Motion: handheld/documentary DoP, never floaty
drift. Soul (smartphone-real) is the default image model. NO glossy 3D, NO gradient glow, NO stock smiles.

**offgrid-creatives-ai** (Reporting SaaS) — *intelligence-brief as craft.*
Palette charcoal + amber (locked). Aesthetic = "Bloomberg terminal meets design studio" — precise, dark, editorial
data-viz, monospaced accents, real chart craft. NOT generic SaaS-blue, NOT 3D blobs. Motion: precise, mechanical,
data-reveal. Conveys rigor and real numbers (matches the brand-audit product).

→ Gaurav reacts; on lock these become `brands/<slug>/visual_pov.json`, read by the CD brain.

## 5. Build order — AFTER the current build, then agent-by-agent
**First finish the current build:** Railway scheduler worker + Wave 2 F1–F4. THEN, per creative agent (one at a
time, hands-on feeding + pipeline correction):
1. `media_gateway.py` + Higgsfield API client (gated off until PRO) — swap FAL as we touch each agent. — code, $0
2. Rewire that agent's gen → gateway; feed it references; correct its prompt/pipeline; iterate with Gaurav.
3. Lock `visual_pov.json` per brand as the positive north-star (Gaurav already likes the §4 directions).
4. PDF-report design upgrade via `canvas-design` + design system (its own pass).
5. When PRO lands: connect Higgsfield MCP to Claude Code (interactive art-direction) + set `HIGGSFIELD_API_KEY` (agents). — ops

Agent pass order (suggested): Creative Director → Carousel Designer → Script-Writer hooks → Brand-book/PDF design.

### 5a. Open Design — mine as a REFERENCE CORPUS (study, $0, NOT a runtime dep)
`nexu-io/open-design` is rejected as an engine (it orchestrates Claude to build design-in-code = the sameness trap; Higgsfield stays the engine). But its bundled ~150 brand design systems + ~100 skills are worked examples of real art direction. Task (part of the per-agent creative work, before/with the CD pass):
1. Shallow-clone the repo to a scratch dir (NOT vendored into our tree); read only `design-systems/` + `skills/`.
2. Distill recurring patterns (composition, type systems, palette logic, layout grammar, "design-system as prompt" structure) into: (a) upgraded prompt templates for Creative Director / Script-Writer / Carousel agents, (b) each brand's `visual_pov.json`.
3. Write the distilled patterns into a short `docs/CREATIVE_PROMPTING_NOTES.md`; discard the clone. No dependency added.

Sources: higgsfield.ai/mcp · higgsfield.ai/soul-intro · higgsfield.ai/marketing-studio-intro · apidog.com/blog/higgsfield-api
