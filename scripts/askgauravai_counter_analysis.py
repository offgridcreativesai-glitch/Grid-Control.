"""
Counter-analysis: test ASKGauravAI new direction claims against real IG data.
Pure deterministic — uses already-scraped 142 posts. No Claude. No new Apify cost.

Tests each claim in the new direction:
  C1: "Most AI builds start with one tutorial. Mine started with multi-platform research"
  C2: "Live build journey" / build-in-public framing
  C3: "Non-coder building with AI" positioning
  C4: "Two creators gave me opposite advice" / cross-creator synthesis
  C5: "I researched X creators before starting" framing

For each: how many existing posts use this angle? Saturation = bad. White space = good.
"""
import json
import re
from pathlib import Path
from collections import Counter

ROOT = Path("brands/askgauravai")
RAW = json.loads((ROOT / "competitor_pattern_raw.json").read_text())

# Flatten all posts
all_posts = []
for cat, handles in RAW.items():
    for handle, posts in handles.items():
        if isinstance(posts, dict) and "error" in posts:
            continue
        for p in posts:
            p["_handle"] = handle
            p["_category"] = cat
            all_posts.append(p)

total = len(all_posts)
print(f"=== Counter-analysis on {total} real IG posts from 5 handles ===\n")

# Test claim hits
CLAIMS = {
    "C1_multi_platform_research": [
        r"researched? (across|many|multiple|several|\d+)",
        r"\d+ (creators?|tutorials?|videos?|platforms?)",
        r"cross[- ]?(check|reference|verif)",
        r"(many|multiple|several) (creators?|sources?|tutorials?|playbooks?)",
        r"(stacked?|stacking) (creators?|sources?|insights?)",
        r"(synthesis|synthesi[sz]ing) across",
    ],
    "C2_live_build_journey": [
        r"build(ing)? in public",
        r"(live |currently )?build(ing)? journey",
        r"build with me",
        r"day \d+ of building",
        r"i'?m (currently )?building",
        r"(live|real[- ]time) build",
        r"#buildinpublic",
    ],
    "C3_non_coder_positioning": [
        r"non[- ]?cod(er|ing)",
        r"without (writing )?(a (single )?line of )?code",
        r"never (written|wrote) (a line of )?code",
        r"no[- ]code (build|founder|maker)",
        r"can'?t code",
    ],
    "C4_cross_creator_synthesis": [
        r"two (top |different )?creators? (told|gave|said)",
        r"creator a .{0,40}creator b",
        r"opposite (advice|takes?|playbooks?)",
        r"(contradictory|conflicting) advice",
        r"creators? disagree",
    ],
    "C5_creator_count_framing": [
        r"i (followed|watched|studied) \d+ (creators?|videos?|tutorials?)",
        r"\d+ creators? before",
        r"(after|across) \d+ (creators?|videos?|tutorials?)",
    ],
    "BG_pain_attack_baseline": [
        r"they (don'?t|won'?t|never) (tell|show)",
        r"nobody (tells?|shows?)",
        r"what they hide",
        r"the truth (they|nobody)",
    ],
    "BG_freebie_baseline": [
        r"free (template|guide|playbook|toolkit|cheatsheet|prompt pack)",
        r"comment [\"']?[A-Z]{3,}[\"']?",
    ],
}

def all_text(p):
    return ((p.get("caption") or "") + " " + " ".join(p.get("hashtags") or [])).lower()

results = {}
for claim, patterns in CLAIMS.items():
    hits = []
    for p in all_posts:
        text = all_text(p)
        for pat in patterns:
            if re.search(pat, text, re.I):
                hits.append({"handle": p["_handle"], "caption_snippet": (p.get("caption") or "")[:160], "matched": pat})
                break
    results[claim] = {"count": len(hits), "pct": round(len(hits) / total * 100, 1), "examples": hits[:3]}

# Print results
verdict = {}
for claim, r in results.items():
    pct = r["pct"]
    if pct == 0:
        v = "🟢 WHITE SPACE — no creator uses this angle"
    elif pct < 5:
        v = "🟢 LOW SATURATION — strong differentiator"
    elif pct < 15:
        v = "🟡 MODERATE — used by some, still differentiable with execution"
    elif pct < 30:
        v = "🟠 HIGH SATURATION — common angle"
    else:
        v = "🔴 SATURATED — everyone does this"
    verdict[claim] = v
    print(f"\n{claim}")
    print(f"  Hits: {r['count']}/{total} ({pct}%)  {v}")
    for ex in r["examples"]:
        print(f"  • {ex['handle']}: {ex['caption_snippet'][:120]}")

# Top topic tokens for white space hunt
print("\n\n=== TOP TOPIC TOKENS in 142 posts (what's already saturated) ===")
STOPWORDS = set("a an the and or but if then for of to in on at by with from this that these those it its is are was were be been being have has had do does did i you he she they we my your his her their our me us him them as not no yes so also just very more most much many few all any some what who when where why how can will would could should might may must been get got go going made make made out up down off over under into onto about whats lets letts well now then there here just like just need really when where which".split())
words = []
for p in all_posts:
    t = re.sub(r'[^a-zA-Z\s]', ' ', (p.get("caption") or "")).lower()
    words.extend(w for w in t.split() if len(w) >= 4 and w not in STOPWORDS)
top = Counter(words).most_common(25)
for word, count in top:
    print(f"  {word}: {count}")

# Save report
report = {
    "generated_at": "now",
    "total_posts_analyzed": total,
    "handles": list(set(p["_handle"] for p in all_posts)),
    "claim_results": results,
    "verdicts": verdict,
    "top_topic_tokens": [{"token": w, "count": c} for w, c in top],
}
out = ROOT / "counter_analysis_v2.json"
out.write_text(json.dumps(report, indent=2, ensure_ascii=False))
print(f"\n\nFull report → {out}")
