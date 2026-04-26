
# AutoResearch Loop Skill
# Applies to: All agents, all outputs, no exceptions

## What This Skill Is
Every agent output must be the winner of an internal loop.
No single untested output ever reaches pending_approval/ or the user.
This is Rule 9. It is non-negotiable.

## The Loop Structure

### Step 1 — Define The Goal
Before generating anything, state what this output must accomplish.
Not vague. Specific.
BAD: "write a good hook"
GOOD: "write a hook that stops a D2C founder mid-scroll on Instagram"

### Step 2 — Define The Metric
State what "better" means in numbers or observable behavior.
BAD: "sounds more engaging"
GOOD: "better = more saves + shares than last post" or "better = lower CAC"
Without a metric, the loop is just noise.

### Step 3 — Run 3 Internal Variants
Every agent must internally generate a minimum of 3 approaches before selecting one.
These variants must differ in angle, not just wording.

Variant types by agent:

TREND RESEARCHER
- Variant A: Volume angle (what has most search volume)
- Variant B: Velocity angle (what is growing fastest right now)
- Variant C: Gap angle (what competitors are missing)

STRATEGY AGENT
- Variant A: Aggressive growth play
- Variant B: Trust-first slow burn
- Variant C: Hybrid with clear phase gates

CONTENT PLANNER
- Variant A: Education-heavy calendar
- Variant B: Social proof-heavy calendar
- Variant C: Curiosity/hook-heavy calendar

SCRIPT WRITER
- Variant A: Hook angle (pain-first)
- Variant B: Result angle (outcome-first)
- Variant C: Curiosity angle (pattern interrupt)

CREATIVE DIRECTOR
- Variant A: Minimal text, visual-led
- Variant B: Bold headline, image support
- Variant C: Story format, sequential

AD STRATEGIST
- Variant A: Hook angle test
- Variant B: Offer angle test
- Variant C: Audience angle test

DATA ANALYST
- Variant A: Raw metrics summary
- Variant B: Trend + pattern read
- Variant C: Actionable insight with next step recommendation

FUNNEL SPECIALIST
- Variant A: Awareness-first funnel
- Variant B: Retargeting-first funnel
- Variant C: Hybrid with split entry points

WEBSITE AGENT
- Variant A: Conversion-optimized layout
- Variant B: Trust-optimized layout
- Variant C: Story-led layout

CEO BRAIN
- Variant A: Fast path (skip low-priority agents)
- Variant B: Full sequence (all agents in order)
- Variant C: Targeted path (only agents relevant to current bottleneck)

### Step 4 — Select The Winner
Pick the variant that best satisfies the metric defined in Step 2.
State the reason in one line. Not an essay. One line.

### Step 5 — Output The Loop Header
Every output that goes to pending_approval/ must begin with this header:

LOOP: [Agent Name] — [Output Type]
GOAL: [What this output is optimizing for]
METRIC: better = [specific measurable definition]
VARIANTS TESTED: [number]
WINNER: [Variant letter] — [one line reason]

Then the actual output follows.

## What This Prevents
- Hallucinated outputs that feel right but have no basis
- Single-path thinking that misses better approaches
- Outputs with no measurable success definition
- Agent drift (producing what's easy, not what's best)

## Token Efficiency Note
The loop runs internally. The header is compact.
The user sees one clean output plus five lines of reasoning.
No token waste. No verbose explanations. Loop runs lean.

## Example — Script Writer In Action

LOOP: Script Writer — Instagram Hook
GOAL: Stop D2C founder mid-scroll, drive saves
METRIC: better = higher save rate than previous post (baseline: 2.1%)
VARIANTS TESTED: 3
WINNER: Variant C — curiosity angle matches pattern interrupt behavior of top 3 competitor posts this week

[Hook output follows here]

