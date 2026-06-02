"""
Mine the scraped 142 posts (5 handles + garyvee when available) for:
- Top-engagement posts (cross-handle)
- Hook patterns (first 100 chars of high-performers)
- Topic tokens (most common content words after stopword filter)
- CTA patterns (DM / link / freebie / comment / follow)
- Hashtag usage
- Posting cadence (days between posts)
Pure deterministic. No Claude. Outputs brands/askgauravai/competitor_pattern_doc.json.
"""
import json
import re
from collections import Counter
from datetime import datetime
from pathlib import Path

ROOT = Path("/Users/gauravoffgrid/offgrid-marketing-os/brands/askgauravai")
RAW = json.loads((ROOT / "competitor_pattern_raw.json").read_text())

# Fold in garyvee if available
GARY_FILE = Path("/tmp/garyvee_posts.json")
if GARY_FILE.exists():
    try:
        gary = json.loads(GARY_FILE.read_text())
        # Reconstitute as summarize_post would
        from sys import path as _p
        _p.insert(0, str(Path(__file__).parent))
        from askgauravai_pattern_scrape import summarize_post
        RAW["references"]["garyvee"] = [summarize_post(p) for p in gary if isinstance(p, dict)]
        print(f"[analyze] garyvee folded in: {len(RAW['references']['garyvee'])} posts")
    except Exception as e:
        print(f"[analyze] garyvee fold-in failed: {e}")

STOPWORDS = set("""a an the and or but if then for of to in on at by with from this that these those it its is are was were be been being have has had do does did i you he she they we my your his her their our me us him them as not no yes so also just very more most much many few all any some what who when where why how can will would could should might may must been get got go going made make made out up down off over under into onto about who's whats it's i'm i've i'll you're you've you'll we're we've we'll they're they've they'll lets let's well now then there here""".split())
EMOJI_RE = re.compile(r"[\U0001F300-\U0001FAFF\U0001F600-\U0001F64F☀-➿]")

CTA_PATTERNS = {
    "dm_request": re.compile(r"\bdm\s*(me|us|to)?\b|\bsend.*(dm|message)\b", re.I),
    "comment_gated": re.compile(r"\bcomment\s+[\"\']?[A-Z]{3,}[\"\']?", re.I),
    "follow_request": re.compile(r"\bfollow\b.*\bfor\s+(more|the|daily)\b", re.I),
    "link_in_bio": re.compile(r"\b(link\s+in\s+bio|bio\s+link|linkinbio)\b", re.I),
    "save_share": re.compile(r"\b(save\s+this|share\s+with|tag\s+(a|someone))\b", re.I),
    "freebie_offer": re.compile(r"\b(free|freebie|template|cheatsheet|guide|playbook|toolkit|notion\s+template|prompt\s+pack)\b", re.I),
    "newsletter": re.compile(r"\b(newsletter|substack|email\s+list|weekly\s+breakdown)\b", re.I),
}


def tokenize(text: str) -> list:
    text = EMOJI_RE.sub(" ", text or "")
    text = re.sub(r"http\S+", " ", text)
    text = re.sub(r"[#@]\w+", " ", text)  # strip hashtags + mentions for topic words
    text = re.sub(r"[^a-zA-Z0-9\s']", " ", text).lower()
    words = [w for w in text.split() if len(w) >= 3 and w not in STOPWORDS and not w.isdigit()]
    return words


def score(post: dict) -> float:
    """Engagement score — likes + comments × 5 (comments worth more), normalized by views floor."""
    likes = post.get("likes") or 0
    comments = post.get("comments") or 0
    views = post.get("video_views") or 0
    return likes + comments * 5 + (views * 0.05)


def all_posts() -> list:
    out = []
    for cat, handles in RAW.items():
        for handle, posts in handles.items():
            if isinstance(posts, dict) and "error" in posts:
                continue
            for p in posts:
                p["_handle"] = handle
                p["_category"] = cat
                p["_score"] = score(p)
                out.append(p)
    return out


def hook_extract(caption: str, n: int = 100) -> str:
    if not caption:
        return ""
    first_line = caption.split("\n")[0].strip()
    return first_line[:n]


def cta_classify(caption: str) -> list:
    found = []
    for label, pat in CTA_PATTERNS.items():
        if pat.search(caption or ""):
            found.append(label)
    return found


def main():
    posts = all_posts()
    posts.sort(key=lambda p: p["_score"], reverse=True)
    print(f"[analyze] {len(posts)} total posts across {len(set(p['_handle'] for p in posts))} handles")

    # Top 20 across all
    top20 = posts[:20]

    # Topic tokens — global, top 40
    all_tokens = []
    for p in posts:
        all_tokens.extend(tokenize(p.get("caption") or ""))
    topic_counter = Counter(all_tokens)
    top_topics = topic_counter.most_common(40)

    # Hashtag usage
    all_hashtags = []
    for p in posts:
        all_hashtags.extend([h.lower() for h in (p.get("hashtags") or [])])
    top_hashtags = Counter(all_hashtags).most_common(30)

    # CTA distribution
    cta_counter = Counter()
    cta_examples = {}
    for p in posts:
        ctas = cta_classify(p.get("caption") or "")
        for c in ctas:
            cta_counter[c] += 1
            if c not in cta_examples:
                cta_examples[c] = {"handle": p["_handle"], "caption_snippet": (p.get("caption") or "")[:200]}

    # Hook patterns from top 30
    top30_hooks = [
        {
            "handle": p["_handle"],
            "category": p["_category"],
            "score": int(p["_score"]),
            "type": "carousel" if p.get("is_carousel") else ("video" if p.get("is_video") else "image"),
            "video_duration": p.get("video_duration"),
            "hook": hook_extract(p.get("caption") or ""),
            "ctas": cta_classify(p.get("caption") or ""),
            "url": p.get("url"),
        }
        for p in posts[:30]
    ]

    # Per-handle CTA + freebie analysis
    per_handle = {}
    for handle in set(p["_handle"] for p in posts):
        hp = [p for p in posts if p["_handle"] == handle]
        ctas_h = Counter()
        freebie_count = 0
        for p in hp:
            for c in cta_classify(p.get("caption") or ""):
                ctas_h[c] += 1
                if c == "freebie_offer":
                    freebie_count += 1
        per_handle[handle] = {
            "post_count": len(hp),
            "cta_distribution": dict(ctas_h),
            "freebie_offer_posts": freebie_count,
            "avg_caption_length": int(sum(len(p.get("caption") or "") for p in hp) / max(len(hp), 1)),
        }

    # Long-form-cut signal — handles with high % of >60s videos
    long_form_signal = {}
    for handle in set(p["_handle"] for p in posts):
        hp = [p for p in posts if p["_handle"] == handle]
        videos = [p for p in hp if p.get("is_video") and p.get("video_duration")]
        long_videos = [p for p in videos if (p.get("video_duration") or 0) > 60]
        long_form_signal[handle] = {
            "video_count": len(videos),
            "long_form_count": len(long_videos),
            "long_form_pct": round(len(long_videos) / max(len(videos), 1) * 100, 1),
        }

    # Timestamp cadence
    cadence = {}
    for handle in set(p["_handle"] for p in posts):
        hp = sorted([p for p in posts if p["_handle"] == handle], key=lambda x: x.get("timestamp") or "")
        timestamps = [p.get("timestamp") for p in hp if p.get("timestamp")]
        if len(timestamps) >= 2:
            try:
                dts = [datetime.fromisoformat(t.replace("Z", "+00:00")) for t in timestamps]
                gaps = [(dts[i + 1] - dts[i]).total_seconds() / 86400 for i in range(len(dts) - 1)]
                cadence[handle] = {
                    "posts_in_window": len(timestamps),
                    "median_days_between_posts": round(sorted(gaps)[len(gaps) // 2], 2) if gaps else None,
                    "posts_per_week_estimate": round(7 / max(sorted(gaps)[len(gaps) // 2], 0.1), 1) if gaps else None,
                }
            except Exception:
                cadence[handle] = {"error": "timestamp parse failed"}

    doc = {
        "generated_at": datetime.utcnow().isoformat(),
        "data_source": "apify/instagram-scraper, live IG fetch, no assumption",
        "total_posts_analyzed": len(posts),
        "handles_in_set": list(set(p["_handle"] for p in posts)),
        "top_30_engagement_hooks": top30_hooks,
        "top_topic_tokens": [{"token": t, "count": c} for t, c in top_topics],
        "top_hashtags": [{"tag": t, "count": c} for t, c in top_hashtags],
        "cta_distribution_global": dict(cta_counter),
        "cta_examples": cta_examples,
        "per_handle_analysis": per_handle,
        "long_form_video_signal": long_form_signal,
        "posting_cadence": cadence,
    }
    out_path = ROOT / "competitor_pattern_doc.json"
    out_path.write_text(json.dumps(doc, indent=2, ensure_ascii=False))
    print(f"[analyze] DONE → {out_path}")
    print(f"[analyze] top topics: {[t for t, _ in top_topics[:10]]}")
    print(f"[analyze] CTAs: {dict(cta_counter)}")
    print(f"[analyze] long-form signal: {long_form_signal}")


if __name__ == "__main__":
    main()
