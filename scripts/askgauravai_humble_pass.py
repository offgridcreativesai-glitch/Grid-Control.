"""
ASKGauravAI — humble-positive transformation pass on Week 1 scripts.
Pure deterministic string edits. No Claude calls. No spending.

5 rules:
  1. Drop line-item cost reveals (rupee figures, tool-by-tool bills)
  2. Soften attacking hooks → humble pain-aware
  3. Soften gotcha closes → principle (light)
  4. Strip "I will tell you" promises in CTAs
  5. Reframe self-as-fool → self-as-experienced-practitioner
"""
import json
import re
from pathlib import Path

SCRIPTS_PATH = Path("brands/askgauravai/outputs/pending_approval/script-writer/20260430_170642_scripts_week1to1.json")

# ── Rule 1 — Drop cost line-items ─────────────────────────────────────
RULE_1 = [
    # Rupee-figure invoice framings
    ("had a ₹4,200 invoice on the inside. Here is what was on it",
     "had a quiet cost on the inside that nobody warned me about. Here's what I learned from it"),
    ("₹4,200 invoice", "real cost"),
    ("a ₹4,200 invoice", "a real cost"),
    # Standalone large figures on slides
    ("'₹4,200.\n\nOne build.\nOne week.\nThree tools.'",
     "'More rupees and more weeks than the tutorials suggested.\n\nOne build.\nOne week.\nThree tools.\nSeveral lessons.'"),
    ("₹4,200.\n\nOne build.\nOne week.\nThree tools.",
     "More rupees and more weeks than the tutorials suggested.\n\nOne build.\nOne week.\nThree tools.\nSeveral lessons."),
    # Hook variations
    ("One AI build. One billing dashboard. ₹4,200. Here is the full breakdown nobody shows you",
     "One AI build. One quiet lesson about what it actually takes to make AI work in real life"),
    ("One AI build. One billing dashboard. ₹4,200",
     "One AI build. One quiet lesson"),
    # Drop bare rupee figures with their context
    ("₹4,200 in tooling and three tools", "more than I planned across three tools"),
    ("the ₹4,200 figure", "the real cost figure"),
    ("the ₹4,200 build", "the build"),
    ("₹4,200 on the inside", "a quiet cost on the inside"),
    ("₹4,200 in tooling", "real cost in tooling"),
    ("the ₹4,200 number", "the cost"),
    ("the ₹4,200", "the real-build cost"),
    ("₹4,200", "real-build cost"),
    # Tool-by-tool itemized bill phrasing
    ("billing dashboard", "build process"),
    ("Anthropic console billing screenshot", "Anthropic console screenshot"),
    ("FAL.ai billing page", "FAL.ai usage page"),
    ("every line item — what I ran, what failed, what it cost",
     "every step — what I ran, what taught me what"),
    ("Full breakdown of every line item",
     "Full walkthrough of every step"),
    # Caption-level mentions
    ("one AI build actually cost in rupees",
     "one AI build actually requires"),
    ("Real API cost breakdown",
     "Real build walkthrough"),
]

# ── Rule 2 — Soften attacking hooks ────────────────────────────────────
RULE_2 = [
    ("AI creators show you the magic. I am showing you the back-end they hide",
     "AI creators show the magic. I'm walking through the slow part — the build behind it — in case it's useful"),
    ("AI creators show the magic. Gaurav shows the back-end they hide",
     "AI creators show the magic. Gaurav walks through the slow part the explainers can't fit"),
    ("This video is everything they did not show",
     "I'm walking through the slow part most build videos can't fit"),
    ("everything they did not show", "the slow part most build videos can't fit"),
    ("they did not show", "most build videos skip"),
    ("they hide", "most build videos skip"),
    ("Here is the full breakdown nobody shows you",
     "Here's the walk-through most build videos skip"),
    ("Here is what was on it",
     "Here's what I learned from it"),
    ("Nobody tells you what they are",
     "Most short clips don't have time to spell them out"),
    ("nobody tells you", "most short clips don't say upfront"),
    ("Nobody tells you", "Most short clips don't say upfront —"),
    ("nobody shows you", "most build videos don't show"),
    ("Nobody shows you", "Most build videos don't show"),
    # Specific pain-attack hooks → humble pain-aware
    ("I paused a viral AI reel at 0:30 and checked the real math behind it. What I found took 40 hours to build",
     "I paused a viral AI reel at 0:30 and ran the actual math behind it. The build it points to takes 40 hours to do for real"),
    ("That is what the '5-minute build' actually cost me",
     "That is what the '5-minute build' actually takes when you do it for real"),
]

# ── Rule 3 — Soften gotcha closes (light) ──────────────────────────────
RULE_3 = [
    ("Here is what the finished build actually needed. It is not what the tutorial showed",
     "Here is what a finished build actually needs in real life — most of it is the part tutorials don't have time for"),
    ("It is not what the tutorial showed", "Most tutorials skip the slow parts that matter"),
    ("the tutorial claimed", "most tutorials show"),
]

# ── Rule 4 — Strip "I will tell you" + soft promises ───────────────────
RULE_4 = [
    ("What AI tool are you currently paying for — drop it below and I will tell you if the cost structure makes sense for what you are getting",
     "What's an AI tool you keep hearing about but haven't tried — curious to know what's making you hesitate"),
    ("What AI tool are you currently paying for — drop it below and I will tell you if the cost structure makes sense",
     "What's an AI tool you keep hearing about but haven't tried — curious to know what's making you hesitate"),
    ("drop it below and I will tell you if the cost structure makes sense",
     "drop it below — curious about what's making you hesitate"),
    ("drop it below and I will tell you what is actually",
     "drop it below — curious about the patterns"),
    ("drop it below and I will tell you where it is most likely breaking",
     "drop it below — curious where the friction shows up most"),
    ("I will tell you where it is most likely breaking for you",
     "curious where the friction shows up most"),
    ("I will tell you what is actually",
     "curious about the patterns I see"),
    (" — I will tell you", " — curious to see"),
    ("and I will tell you", "— curious about what people are running into"),
    ("I will tell you", "I'm curious"),
]

# ── Rule 5 — Reframe self-as-fool → experienced practitioner ───────────
RULE_5 = [
    # "I wasted X hours"
    ("I wasted 40 hours so you could watch this in 30 seconds",
     "40 hours of iteration on my end. 30 seconds on yours. Here's what the build actually takes"),
    ("I wasted 40 hours", "40 hours of iteration is what the build actually takes"),
    # "version 47 worked" — drop the count
    ("Version 47 worked — but yes, and this is the part the 5-minute build videos do not show you — version 47 only works in the specific context I built it for",
     "Once the build settled — and this is the part most short videos can't fit — the working version only fires inside the specific context it was built for"),
    ("Version 47 worked", "Once the build settled"),
    ("version 47 worked", "once the build settled"),
    ("version 47", "the working version"),
    ("Version 47", "The working version"),
    # "what kept breaking"
    ("what kept breaking", "what the build kept teaching me"),
    # "I had to do by hand" / "fix manually"
    ("I had to do by hand", "the human-judgment step that still belongs in the build"),
    ("What I had to do by hand", "The human-judgment step the build still needs"),
    ("what I had to do by hand", "the human-judgment step the build still needs"),
    ("I had to fix it manually", "the build needed a human-judgment moment to settle"),
    ("had to fix manually", "needed a human-judgment moment"),
    ("AI broke and a human had to fix it manually",
     "AI handed off to human judgment — and that's where most builds stall"),
    ("AI broke and a human had to fix it",
     "AI handed off to human judgment"),
    ("Where AI broke and a human had to fix it manually — real failure log",
     "Where AI hands off to human judgment — and why most builds stall there"),
    ("AI broke here. I fixed it manually",
     "AI handed off to human judgment. Here's the moment most builds stall"),
    ("AI broke here", "AI handed off to human judgment"),
    # "I broke things" framings
    ("AI failed at step 3. Here is exactly what I had to do by hand — and how long it actually took",
     "AI handles the bulk of this kind of build. There's a human-judgment moment that most builds underestimate. Here's exactly what it looks like — and how long it actually takes"),
    ("AI failed at step 3", "There's a human-judgment step in step 3"),
    # Caption / topic level
    ("real failure log", "real build walkthrough"),
    # Self-deprecating "I wasted weeks/rebuilding things wrong"
    ("Copying Instagram reels without understanding architecture — wasted weeks rebuilding things wrong",
     "Pattern I see often: copying reels without seeing the architecture underneath — leads to weeks rebuilding from a broken starting point"),
]

ALL_RULES = [
    ("Rule 1 — drop cost line-items", RULE_1),
    ("Rule 2 — soften attacking hooks", RULE_2),
    ("Rule 3 — soften gotcha closes", RULE_3),
    ("Rule 4 — strip 'I will tell you' promises", RULE_4),
    ("Rule 5 — reframe self-as-fool", RULE_5),
]


def apply_string_rules(s: str, counters: dict) -> str:
    if not isinstance(s, str):
        return s
    out = s
    for rule_name, pairs in ALL_RULES:
        for old, new in pairs:
            if old in out:
                out = out.replace(old, new)
                counters[rule_name] = counters.get(rule_name, 0) + 1
    return out


def walk(obj, counters):
    if isinstance(obj, dict):
        for k, v in list(obj.items()):
            if isinstance(v, str):
                obj[k] = apply_string_rules(v, counters)
            elif isinstance(v, (dict, list)):
                walk(v, counters)
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            if isinstance(v, str):
                obj[i] = apply_string_rules(v, counters)
            elif isinstance(v, (dict, list)):
                walk(v, counters)


def main():
    raw = SCRIPTS_PATH.read_text()
    hdr_end = raw.find("{")
    header = raw[:hdr_end]
    d = json.loads(raw[hdr_end:])

    counters = {}
    walk(d, counters)

    # Write back
    SCRIPTS_PATH.write_text(header + json.dumps(d, indent=2, ensure_ascii=False))

    print("[humble-pass] DONE")
    total = sum(counters.values())
    print(f"  Total replacements: {total}")
    for rule_name, n in counters.items():
        print(f"  {rule_name}: {n}")


if __name__ == "__main__":
    main()
