"""
Performance Tracker — OffGrid Marketing OS
Agent ID: 17 (NEW Apr 26) | Sequence: runs after content publishes (manual or scheduled)
Model: NONE — PURE DETERMINISTIC. No Claude. Class-1 decision agent per Rule 10.

Purpose: Close the feedback loop. Take real published-post metrics (from Meta Graph API
when token unblocks, OR from manual-paste endpoint) → compute performance_history.json
with rolling baselines + winning patterns + dead patterns. Downstream agents read this:
  - Trend Researcher boosts trends matching past winners
  - Script Writer prefers hook patterns that hit >X save rate
  - Trend Sentinel adds dead-pattern penalty (won't pivot to topics that flopped)

Reads:
  brands/{slug}/performance_history.json  (existing — preserves history across runs)
  brands/{slug}/performance_inbox.json    (NEW — manual paste queue from /api/performance/log-post)
  brands/{slug}/brand_profile.json        (for IG handle → Meta Graph API path when ready)

Writes:
  brands/{slug}/performance_history.json  (full updated history with computed baselines)
  outputs/pending_approval/performance-tracker/  (decision summary for human review)

Modes:
  - "manual"   — read performance_inbox.json (user-pasted metrics)
  - "meta_api" — call Meta Graph API for published posts (BLOCKED until token unblocks)
  - "auto"    — try meta_api first, fall back to manual
"""

import os
import sys
import json
import statistics
from collections import defaultdict
from datetime import datetime, timezone, timedelta
from pathlib import Path
from dotenv import load_dotenv

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from ceo_brain.orchestrator import CEOBrain

load_dotenv(override=True)

BRAND_SLUG = os.getenv("ACTIVE_BRAND", "offgrid-creatives-ai")
META_GRAPH_API_TOKEN = os.getenv("META_GRAPH_API_TOKEN", "").strip()

# ── DETERMINISTIC SCORING + BASELINES (Rule 10 — no AI judgment) ───────────
# performance_score formula: weighted blend of save_rate, ER, DM inquiries, normalized 0-100
SCORE_WEIGHTS = {
    "save_rate_pct":       30.0,   # saves / impressions × 100 (most predictive of long-term value)
    "engagement_rate_pct": 20.0,   # (likes + comments + shares) / reach × 100
    "dm_inquiries_norm":   25.0,   # min(dm_inquiries, 20) / 20 × 25  (caps at 20 DMs = max signal)
    "shares_norm":         15.0,   # min(shares, 50) / 50 × 15
    "comments_norm":       10.0,   # min(comments, 30) / 30 × 10
}

# Lookback window for rolling baselines
ROLLING_WINDOW_DAYS = 30

# Top winning patterns to surface (per category)
TOP_PATTERNS_N = 3

# A pattern is "dead" if its median performance_score is below this percentile of all posts
DEAD_PATTERN_PERCENTILE = 25
# AND it has at least N posts to be statistically meaningful
DEAD_PATTERN_MIN_POSTS = 3


def _compute_performance_score(metrics: dict) -> float:
    """
    Pure-math compound score (0-100). Every weight + cap is in SCORE_WEIGHTS.
    Inputs that are missing default to 0 — score drops naturally.
    """
    save_rate = float(metrics.get("save_rate_pct", 0) or 0)
    er        = float(metrics.get("engagement_rate_pct", 0) or 0)
    dms       = float(metrics.get("dm_inquiries", 0) or 0)
    shares    = float(metrics.get("shares", 0) or 0)
    comments  = float(metrics.get("comments", 0) or 0)

    # Normalize each component to 0-1 range, then multiply by weight
    score = 0.0
    score += min(save_rate / 2.0,    1.0) * SCORE_WEIGHTS["save_rate_pct"]      # save_rate of 2%+ = max
    score += min(er / 5.0,           1.0) * SCORE_WEIGHTS["engagement_rate_pct"] # ER of 5%+ = max
    score += min(dms / 20.0,         1.0) * SCORE_WEIGHTS["dm_inquiries_norm"]   # 20+ DMs = max
    score += min(shares / 50.0,      1.0) * SCORE_WEIGHTS["shares_norm"]         # 50+ shares = max
    score += min(comments / 30.0,    1.0) * SCORE_WEIGHTS["comments_norm"]       # 30+ comments = max

    return round(score, 1)


def _derive_save_rate_and_er(metrics: dict) -> dict:
    """
    Compute save_rate_pct and engagement_rate_pct from raw counts if not provided.
    Returns enriched metrics dict.
    """
    out = dict(metrics)
    impressions = float(metrics.get("impressions", 0) or 0)
    reach       = float(metrics.get("reach", 0) or 0)
    saves       = float(metrics.get("saves", 0) or 0)
    likes       = float(metrics.get("likes", 0) or 0)
    comments    = float(metrics.get("comments", 0) or 0)
    shares      = float(metrics.get("shares", 0) or 0)

    # save_rate = saves / impressions × 100
    if "save_rate_pct" not in out and impressions > 0:
        out["save_rate_pct"] = round(saves / impressions * 100, 3)

    # engagement_rate = (likes + comments + shares) / reach × 100
    if "engagement_rate_pct" not in out and reach > 0:
        out["engagement_rate_pct"] = round((likes + comments + shares) / reach * 100, 3)

    return out


class PerformanceTracker:
    """
    Pure-deterministic performance feedback agent. NO Claude. NO LLM.
    Every output value is a math expression over real published-post metrics.
    """

    def __init__(self, brand_slug: str = BRAND_SLUG, mode: str = "auto"):
        self.brand_slug = brand_slug
        self.mode       = mode
        self.run_at     = datetime.now(timezone.utc).isoformat()
        self.log(f"Initialising Performance Tracker for brand: {self.brand_slug} (mode={mode})")

        self.ceo = CEOBrain()
        self.brand_profile = self.ceo.brand_profile

        project_root             = Path(__file__).resolve().parent.parent
        self.brand_dir           = project_root / "brands" / self.brand_slug
        self.history_path        = self.brand_dir / "performance_history.json"
        self.inbox_path          = self.brand_dir / "performance_inbox.json"

    def log(self, msg: str):
        print(f"[Performance Tracker | {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] {msg}")

    # -------------------------------------------------------------------------
    # INPUT — load existing history + new entries from inbox or Meta API
    # -------------------------------------------------------------------------

    def _load_existing_history(self) -> dict:
        """Returns existing performance_history.json or empty skeleton."""
        if not self.history_path.exists():
            return {
                "posts": [],
                "rolling_baselines": {},
                "winning_patterns": {},
                "dead_patterns": [],
                "last_updated": None,
            }
        try:
            with open(self.history_path) as f:
                return json.load(f)
        except Exception as e:
            self.log(f"WARNING: Could not parse existing history — {e}. Starting fresh.")
            return {"posts": [], "rolling_baselines": {}, "winning_patterns": {}, "dead_patterns": []}

    def _load_inbox(self) -> list:
        """Read manual-paste inbox queue. Each entry should match the post schema."""
        if not self.inbox_path.exists():
            return []
        try:
            with open(self.inbox_path) as f:
                data = json.load(f)
            return data.get("queue", []) if isinstance(data, dict) else (data if isinstance(data, list) else [])
        except Exception as e:
            self.log(f"WARNING: Could not parse inbox — {e}.")
            return []

    def _clear_inbox(self):
        """After ingesting inbox entries, clear it so they don't get re-ingested."""
        with open(self.inbox_path, "w") as f:
            json.dump({"queue": [], "last_cleared": self.run_at}, f, indent=2)

    def _fetch_meta_api(self) -> list:
        """
        Pull recent post metrics from Meta Graph API.
        BLOCKED — META_GRAPH_API_TOKEN pending Meta App review (per CLAUDE.md).
        Returns empty list if token not set; logs the reason.
        """
        if not META_GRAPH_API_TOKEN:
            self.log("Meta Graph API path SKIPPED — META_GRAPH_API_TOKEN not set (still pending Meta approval)")
            return []

        # When unblocked, this will:
        # 1. Read brand_profile.instagram_handle
        # 2. Resolve IG business account ID via /me/accounts
        # 3. Call /{ig_user_id}/media?fields=id,permalink,timestamp,media_type
        # 4. For each media: /{media_id}/insights?metric=impressions,reach,saved,...
        # 5. Return list of post dicts matching our schema
        self.log("Meta Graph API path NOT YET IMPLEMENTED — token present but fetch logic deferred")
        return []

    def _ingest_new_entries(self) -> list:
        """
        Combine entries from inbox (manual) + Meta API (auto). Returns merged list of new posts.
        Each entry gets normalized: save_rate/ER computed if missing, performance_score added.
        """
        new_entries: list = []

        if self.mode in ("manual", "auto"):
            inbox = self._load_inbox()
            if inbox:
                self.log(f"Inbox: {len(inbox)} new entries from manual paste")
                new_entries.extend(inbox)

        if self.mode in ("meta_api", "auto"):
            api_entries = self._fetch_meta_api()
            if api_entries:
                self.log(f"Meta API: {len(api_entries)} new entries")
                new_entries.extend(api_entries)

        # Normalize + score every new entry
        normalized = []
        for entry in new_entries:
            if not isinstance(entry, dict):
                continue
            metrics = _derive_save_rate_and_er(entry.get("metrics", {}))
            entry["metrics"] = metrics
            entry["performance_score"] = _compute_performance_score(metrics)
            entry["ingested_at"] = self.run_at
            normalized.append(entry)

        return normalized

    def _merge_into_history(self, history: dict, new_entries: list) -> dict:
        """
        Merge new entries into history.posts, deduping by post_id (last-write-wins for same id).
        """
        existing_by_id = {p.get("post_id"): p for p in history.get("posts", []) if p.get("post_id")}
        for entry in new_entries:
            pid = entry.get("post_id")
            if not pid:
                # No post_id — append unconditionally
                history.setdefault("posts", []).append(entry)
                continue
            existing_by_id[pid] = entry  # overwrite

        # Re-write posts list from updated dict (preserves order roughly)
        non_id_posts = [p for p in history.get("posts", []) if not p.get("post_id")]
        history["posts"] = non_id_posts + list(existing_by_id.values())
        return history

    # -------------------------------------------------------------------------
    # COMPUTATION — rolling baselines + winning patterns + dead patterns
    # -------------------------------------------------------------------------

    def _compute_rolling_baselines(self, posts: list) -> dict:
        """
        Pure math. Median of save_rate / ER / performance_score across last ROLLING_WINDOW_DAYS.
        """
        cutoff = datetime.now(timezone.utc) - timedelta(days=ROLLING_WINDOW_DAYS)
        cutoff_iso = cutoff.isoformat()

        recent = [p for p in posts if p.get("published_at", "") >= cutoff_iso]
        if not recent:
            return {
                "window_days": ROLLING_WINDOW_DAYS,
                "post_count": 0,
                "note": "No posts within rolling window — no baselines yet",
            }

        save_rates = [float(p.get("metrics", {}).get("save_rate_pct", 0) or 0) for p in recent]
        ers        = [float(p.get("metrics", {}).get("engagement_rate_pct", 0) or 0) for p in recent]
        scores     = [float(p.get("performance_score", 0) or 0) for p in recent]

        baselines = {
            "window_days":               ROLLING_WINDOW_DAYS,
            "post_count":                len(recent),
            "median_save_rate_pct":      round(statistics.median(save_rates), 3) if save_rates else 0,
            "median_engagement_rate_pct": round(statistics.median(ers), 3) if ers else 0,
            "median_performance_score":  round(statistics.median(scores), 1) if scores else 0,
        }
        # Top quartile threshold = 75th percentile
        if len(scores) >= 4:
            sorted_scores = sorted(scores)
            q3_idx = int(len(sorted_scores) * 0.75)
            baselines["top_quartile_threshold_score"] = round(sorted_scores[q3_idx], 1)
        else:
            baselines["top_quartile_threshold_score"] = round(max(scores), 1) if scores else 0

        return baselines

    def _flag_outperformers(self, posts: list, baselines: dict) -> list:
        """Add 'outperformed_baseline' bool to every post based on top_quartile_threshold_score."""
        threshold = baselines.get("top_quartile_threshold_score", 0)
        for p in posts:
            score = float(p.get("performance_score", 0) or 0)
            p["outperformed_baseline"] = score >= threshold and threshold > 0
        return posts

    def _compute_winning_patterns(self, posts: list) -> dict:
        """
        Pure math. Group posts by hook_pattern_used / topic / format.
        For each group, compute median performance_score. Top N per category = winners.
        """
        if not posts:
            return {"hook_patterns_top_3": [], "topic_clusters_top_3": [], "formats_top_3": []}

        def _top_n_by_median_score(grouping_key: str) -> list:
            groups: dict[str, list] = defaultdict(list)
            for p in posts:
                key = p.get(grouping_key, "")
                if not key:
                    continue
                groups[str(key)].append(float(p.get("performance_score", 0) or 0))
            scored = [
                (k, round(statistics.median(scores), 1), len(scores))
                for k, scores in groups.items()
                if len(scores) >= 1  # at least 1 post (loosen if data is sparse)
            ]
            scored.sort(key=lambda x: x[1], reverse=True)
            return [
                {"value": v, "median_score": s, "post_count": n}
                for v, s, n in scored[:TOP_PATTERNS_N]
            ]

        return {
            "hook_patterns_top_3":  _top_n_by_median_score("hook_pattern_used"),
            "topic_clusters_top_3": _top_n_by_median_score("topic"),
            "formats_top_3":        _top_n_by_median_score("format"),
        }

    def _compute_dead_patterns(self, posts: list) -> list:
        """
        Pure math. Patterns whose median performance_score is below the DEAD_PATTERN_PERCENTILE
        of all posts AND have at least DEAD_PATTERN_MIN_POSTS data points = officially dead.
        Returned as list of dicts: {category, value, median_score, post_count, reason}
        """
        if len(posts) < DEAD_PATTERN_MIN_POSTS:
            return []

        all_scores = [float(p.get("performance_score", 0) or 0) for p in posts]
        sorted_scores = sorted(all_scores)
        cutoff_idx = int(len(sorted_scores) * (DEAD_PATTERN_PERCENTILE / 100))
        cutoff_score = sorted_scores[cutoff_idx] if cutoff_idx < len(sorted_scores) else sorted_scores[-1]

        dead: list = []
        for category, key in (("hook_pattern", "hook_pattern_used"),
                              ("topic", "topic"),
                              ("format", "format")):
            groups: dict[str, list] = defaultdict(list)
            for p in posts:
                v = p.get(key, "")
                if v:
                    groups[str(v)].append(float(p.get("performance_score", 0) or 0))
            for v, scores in groups.items():
                if len(scores) < DEAD_PATTERN_MIN_POSTS:
                    continue
                med = statistics.median(scores)
                if med < cutoff_score:
                    dead.append({
                        "category":     category,
                        "value":        v,
                        "median_score": round(med, 1),
                        "post_count":   len(scores),
                        "reason":       f"median_score={med:.1f} < {DEAD_PATTERN_PERCENTILE}th percentile cutoff={cutoff_score:.1f}",
                    })
        return dead

    # -------------------------------------------------------------------------
    # MAIN RUN
    # -------------------------------------------------------------------------

    def run(self) -> dict:
        self.log("=" * 60)
        self.log("PERFORMANCE TRACKER — RUN STARTING")
        self.log("=" * 60)

        # STEP 1: Load existing history
        history = self._load_existing_history()
        before_count = len(history.get("posts", []))
        self.log(f"Existing history: {before_count} posts")

        # STEP 2: Ingest new entries (inbox + Meta API)
        new_entries = self._ingest_new_entries()
        self.log(f"New entries to ingest: {len(new_entries)}")

        # STEP 3: Merge + dedupe
        history = self._merge_into_history(history, new_entries)
        after_count = len(history.get("posts", []))
        added = after_count - before_count
        self.log(f"After merge: {after_count} posts ({added:+d})")

        # STEP 4: Compute rolling baselines
        baselines = self._compute_rolling_baselines(history["posts"])
        history["rolling_baselines"] = baselines
        self.log(f"Baselines: median_score={baselines.get('median_performance_score')}, top_quartile={baselines.get('top_quartile_threshold_score')}")

        # STEP 5: Flag outperformers
        history["posts"] = self._flag_outperformers(history["posts"], baselines)

        # STEP 6: Compute winning + dead patterns
        history["winning_patterns"] = self._compute_winning_patterns(history["posts"])
        history["dead_patterns"]    = self._compute_dead_patterns(history["posts"])
        history["last_updated"]     = self.run_at
        history["decision_engine"]  = "pure_math"
        history["computation_thresholds"] = {
            "score_weights":             SCORE_WEIGHTS,
            "rolling_window_days":       ROLLING_WINDOW_DAYS,
            "top_patterns_n":            TOP_PATTERNS_N,
            "dead_pattern_percentile":   DEAD_PATTERN_PERCENTILE,
            "dead_pattern_min_posts":    DEAD_PATTERN_MIN_POSTS,
        }

        winning_hooks = history["winning_patterns"].get("hook_patterns_top_3", [])
        if winning_hooks:
            self.log(f"Top hook patterns: {[w['value'] for w in winning_hooks]}")
        dead = history["dead_patterns"]
        if dead:
            self.log(f"Dead patterns flagged: {len(dead)}")

        # STEP 7: Save history
        with open(self.history_path, "w") as f:
            json.dump(history, f, indent=2)
        self.log(f"performance_history.json saved → {self.history_path}")

        # STEP 8: Clear inbox (only if we had inbox entries)
        if self.mode in ("manual", "auto") and self._load_inbox():
            self._clear_inbox()
            self.log("performance_inbox.json cleared")

        # STEP 9: Push summary to pending_approval + Notion via CEO Brain
        summary = {
            "run_at":                self.run_at,
            "brand_slug":            self.brand_slug,
            "mode":                  self.mode,
            "posts_total":           after_count,
            "posts_added_this_run":  added,
            "rolling_baselines":     baselines,
            "winning_patterns":      history["winning_patterns"],
            "dead_patterns":         history["dead_patterns"],
            "decision_engine":       "pure_math",
        }
        try:
            self.ceo.save_agent_output(
                agent_name="Performance Tracker",
                output_type="Performance Feedback Snapshot",
                loop_header={
                    "goal":            "Compute rolling baselines + winning/dead patterns from real published-post metrics",
                    "metric":          "better = downstream agents (Trend Researcher / Script Writer / Sentinel) get accurate audience-specific signal",
                    "variants_tested": 0,
                    "winner":          f"Pure math over {after_count} posts ({added:+d} this run)",
                },
                content=json.dumps(summary, indent=2),
                filename="performance_snapshot.json",
            )
        except Exception as e:
            self.log(f"WARNING: CEO Brain save_agent_output skipped — {e}")

        self.log("=" * 60)
        self.log(f"PERFORMANCE TRACKER — RUN COMPLETE")
        self.log(f"Total posts in history: {after_count} | Added this run: {added:+d}")
        self.log(f"Winning hook patterns: {[w.get('value') for w in winning_hooks]}")
        self.log(f"Dead patterns: {len(dead)}")
        self.log("=" * 60)

        return summary


if __name__ == "__main__":
    tracker = PerformanceTracker(mode="auto")
    tracker.run()
