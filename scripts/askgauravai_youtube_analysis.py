"""
YouTube counter-analysis: test the new direction claims against 82 YouTube videos.
Same claim battery as IG counter-analysis.
"""
import json
import re
from pathlib import Path
from collections import Counter

ROOT = Path("brands/askgauravai")
data = json.load(open(ROOT / "youtube_scrape_raw.json"))

# Flatten + dedupe by URL
seen, all_vids = set(), []
for q, vids in data.items():
    for v in vids:
        url = v.get("url")
        if url and url not in seen:
            seen.add(url)
            v["_query"] = q
            all_vids.append(v)

total = len(all_vids)
print(f"=== YouTube counter-analysis on {total} unique videos (deduped from 82) ===\n")

CLAIMS = {
    "C1_multi_platform_research": [
        r"researched? (across|many|multiple|several|\d+)",
        r"\d+ (creators?|tutorials?|videos?|platforms?)",
        r"(many|multiple|several) (platforms?|sources?|tutorials?|playbooks?)",
        r"cross[- ]?(check|reference)",
    ],
    "C2_live_build_journey": [
        r"build(ing)? in public",
        r"(live |currently )?build(ing)? journey",
        r"build with me",
        r"day \d+ of building",
        r"i'?m (currently )?building",
    ],
    "C3_non_coder_positioning": [
        r"non[- ]?cod(er|ing)",
        r"without (writing )?(a (single )?line of )?code",
        r"never (written|wrote) (a line of )?code",
        r"no[- ]code",
        r"can'?t code",
    ],
    "C4_cross_creator_synthesis": [
        r"two (top |different )?creators?",
        r"opposite (advice|takes?|playbooks?)",
        r"creators? disagree",
        r"contradictory",
    ],
    "C5_creator_count_framing": [
        r"i (followed|watched|studied) \d+ creators?",
        r"\d+ creators? before",
        r"after \d+ (creators?|videos?|tutorials?)",
    ],
    "MONETIZATION_long_form_signal": [
        r"(\d{1,2}:\d{2}:\d{2}|\d{1,2}:\d{2})",  # duration in title sometimes
    ],
}

def text_blob(v):
    return ((v.get("title") or "") + " " + (v.get("description") or "")).lower()

results = {}
for claim, patterns in CLAIMS.items():
    if claim == "MONETIZATION_long_form_signal":
        continue
    hits = []
    for v in all_vids:
        text = text_blob(v)
        for pat in patterns:
            if re.search(pat, text, re.I):
                hits.append({
                    "channel": v.get("channel"),
                    "title": (v.get("title") or "")[:120],
                    "duration_sec": v.get("duration_seconds"),
                    "views": v.get("views"),
                    "matched": pat,
                })
                break
    results[claim] = {"count": len(hits), "pct": round(len(hits) / total * 100, 1), "examples": hits[:3]}

# Parse duration from HH:MM:SS string when duration_seconds is null
def parse_duration(v):
    secs = v.get("duration_seconds")
    if secs:
        return int(secs)
    dur = v.get("duration") or ""
    parts = dur.split(":")
    try:
        if len(parts) == 3:
            return int(parts[0]) * 3600 + int(parts[1]) * 60 + int(parts[2])
        if len(parts) == 2:
            return int(parts[0]) * 60 + int(parts[1])
    except (ValueError, IndexError):
        pass
    return 0

# Length distribution for monetization analysis
durations = [parse_duration(v) for v in all_vids]
durations = [d for d in durations if d > 0]
def med(arr):
    if not arr: return 0
    s = sorted(arr); return s[len(s)//2]
shorts = sum(1 for d in durations if d <= 60)
medium = sum(1 for d in durations if 60 < d <= 600)  # 1-10 min
long_form = sum(1 for d in durations if d > 600)     # 10+ min — monetization-eligible
mid_roll = sum(1 for d in durations if d >= 480)     # 8 min+ — mid-roll ad eligible

print("=== Length distribution (monetization signal) ===")
print(f"  Total videos with duration data: {len(durations)}")
if durations:
    print(f"  Shorts (≤60s): {shorts}  ({round(shorts/len(durations)*100,1)}%)")
    print(f"  Medium (1-10 min): {medium}  ({round(medium/len(durations)*100,1)}%)")
    print(f"  Long-form (10+ min, AdSense-eligible): {long_form}  ({round(long_form/len(durations)*100,1)}%)")
    print(f"  Mid-roll eligible (8+ min): {mid_roll}  ({round(mid_roll/len(durations)*100,1)}%)")
    print(f"  Median duration: {med(durations)}s")
else:
    print("  No duration data available")

print("\n=== View patterns by length ===")
for label, lo, hi in [("Shorts ≤60s", 0, 60), ("1-10min", 60, 600), ("10min+", 600, 99999)]:
    bucket = [v for v in all_vids if (v.get("duration_seconds") or 0) > lo and (v.get("duration_seconds") or 0) <= hi]
    if bucket:
        views = [v.get("views") or 0 for v in bucket]
        likes = [v.get("likes") or 0 for v in bucket]
        print(f"  {label}: count={len(bucket)}, median_views={med(views)}, median_likes={med(likes)}")

print("\n=== Claim verdicts ===")
for claim, r in results.items():
    pct = r["pct"]
    if pct == 0: v = "🟢 WHITE SPACE"
    elif pct < 5: v = "🟢 LOW SATURATION"
    elif pct < 15: v = "🟡 MODERATE"
    elif pct < 30: v = "🟠 HIGH"
    else: v = "🔴 SATURATED"
    print(f"\n{claim} — {pct}% ({r['count']}/{total})  {v}")
    for ex in r["examples"][:2]:
        print(f"  • {ex['channel']}: {ex['title'][:90]}  [{ex['duration_sec']}s, {ex['views']} views]")

# Top tokens in titles (saturation map for hook design)
print("\n=== Top hook-keyword tokens in 82 video titles ===")
STOPWORDS = set("a an the and or but if then for of to in on at by with from this that these those it its is are was were be been being have has had do does did i you he she they we my your his her their our me us him them as not no yes so also just very more most much many few all any some what who when where why how can will would could should might may must been get got go going made make made out up down off over under into onto about whats lets letts well now then there here just like just need really when where which".split())
words = []
for v in all_vids:
    t = re.sub(r'[^a-zA-Z\s]', ' ', (v.get("title") or "")).lower()
    words.extend(w for w in t.split() if len(w) >= 4 and w not in STOPWORDS)
top = Counter(words).most_common(20)
for word, count in top:
    print(f"  {word}: {count}")

report = {
    "total_unique_videos": total,
    "claim_results": results,
    "length_distribution": {
        "shorts_le_60s": shorts, "medium_1_10min": medium,
        "longform_10plus_min_adsense": long_form,
        "midroll_8plus_min": mid_roll,
        "median_duration_sec": med(durations),
    },
    "top_tokens": [{"token": w, "count": c} for w, c in top],
}
out = ROOT / "youtube_counter_analysis.json"
out.write_text(json.dumps(report, indent=2, ensure_ascii=False))
print(f"\nFull report → {out}")
