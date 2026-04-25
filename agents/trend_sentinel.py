"""
Trend Sentinel — OffGrid Marketing OS
Agent ID: 16 (NEW) | Sequence position: runs DAILY after Trend Researcher
Model: NONE — PURE DETERMINISTIC. No Claude in decision loop.
Rule 1: Zero assumptions. Operates on real trends_live.json + content_calendar.json only.
Rule 10: This is a DECISION agent — uses math, not Claude. Every STAY/TRACK/PIVOT decision
         is a code-readable expression. Zero hallucination risk by design.

Reads:
  brands/{slug}/trends_live.json         (today's trends — refreshed by Trend Researcher)
  brands/{slug}/content_calendar.json    (current 30-day calendar — written by Content Planner)
  brands/{slug}/trend_sentinel_watchlist.json   (persistence of TRACK signals)
  brands/{slug}/brand_profile.json

Writes:
  brands/{slug}/pivot_decision.json
  brands/{slug}/pivot_impact.json        (only if decision = PIVOT)
  brands/{slug}/trend_sentinel_watchlist.json   (updated)
  outputs/pending_approval/trend-sentinel/   (decision summary for human review + Notion push)

If decision = PIVOT, OPTIONALLY (env-controlled) triggers Content Planner subprocess.
By default (SENTINEL_AUTO_PIVOT not set), only writes the decision and waits for human approval.
"""

import os
import re
import sys
import json
import subprocess
from datetime import datetime, timezone, timedelta
from pathlib import Path
from dotenv import load_dotenv

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from ceo_brain.orchestrator import CEOBrain

load_dotenv(override=True)

BRAND_SLUG = os.getenv("ACTIVE_BRAND", "offgrid-creatives-ai")

# ── DETERMINISTIC THRESHOLDS (Rule 10 — no AI judgment) ────────────────────
# How many days a TRACK signal must persist before auto-escalating to PIVOT
TRACK_PERSISTENCE_DAYS_TO_PIVOT = 3
# Lookahead window for "calendar slots that matter today" (next N days)
CALENDAR_LOOKAHEAD_DAYS = 7
# Calendar overlap: Jaccard similarity above this = "already covered" → STAY
CALENDAR_OVERLAP_JACCARD_MIN = 0.4
# Strength: new signal score must beat weakest calendar slot by this multiplier → PIVOT
PIVOT_STRENGTH_MULTIPLIER = 1.5
# Strength: new signal score below this multiplier of weakest slot → STAY (too weak)
STAY_WEAKNESS_MULTIPLIER = 0.8
# Brand-lane match: signal must contain ≥1 token from this list to count as on-brand
BRAND_LANE_TOKEN_FIELDS = ("industry", "product", "target_audience", "audience", "brand_brief")
# Common stopwords for tokenization (English + minimal)
_STOPWORDS = {
    "a","an","the","and","or","but","is","are","was","were","be","been","being",
    "in","on","at","to","for","with","by","of","from","as","into","about","this",
    "that","these","those","it","its","you","your","i","we","our","they","their",
    "what","which","who","whom","when","where","why","how","not","no","do","does",
    "did","done","doing","have","has","had","having","will","would","should","could",
    "can","may","might","must","shall","ought","need","one","two","three","first",
    "next","last","more","most","less","least","very","just","than","then","also",
    "if","else","only","own","same","so","such","too","s","t","ll","re","ve","m","d",
}

# Auto-pivot toggle (default OFF — sentinel writes decision but doesn't trigger Content Planner
# until human approves). Set SENTINEL_AUTO_PIVOT=true in .env to enable autonomous pivots.
SENTINEL_AUTO_PIVOT = os.getenv("SENTINEL_AUTO_PIVOT", "").strip().lower() in ("true", "1", "yes")


def _tokenize(text: str) -> set:
    """Lowercase, split on non-word, drop stopwords + tokens < 3 chars. Pure deterministic."""
    if not text:
        return set()
    tokens = re.split(r"[^a-z0-9]+", text.lower())
    return {t for t in tokens if len(t) >= 3 and t not in _STOPWORDS}


def _jaccard(a: set, b: set) -> float:
    """Jaccard similarity = |intersection| / |union|. Pure math."""
    if not a or not b:
        return 0.0
    inter = len(a & b)
    union = len(a | b)
    return inter / union if union else 0.0


class TrendSentinel:
    """
    Pure-deterministic decision agent. NO Claude. NO LLM. NO synthesis.
    Every STAY/TRACK/PIVOT decision is a math expression over real input data.
    Audit any decision by reading the `reason` field — it cites the exact numbers/strings used.
    """

    def __init__(self, brand_slug: str = BRAND_SLUG):
        self.brand_slug = brand_slug
        self.run_at = datetime.now(timezone.utc).isoformat()
        self.log(f"Initialising Trend Sentinel for brand: {self.brand_slug}")

        self.ceo = CEOBrain()
        self.brand_profile = self.ceo.brand_profile
        self.brand_name = self.brand_profile.get("brand_name") or self.brand_slug

        # Pre-compute brand-lane token set ONCE (used in every signal eval)
        brand_lane_text = " ".join(
            str(self.brand_profile.get(f, "")) for f in BRAND_LANE_TOKEN_FIELDS
        )
        self.brand_lane_tokens = _tokenize(brand_lane_text)

        # Path helpers
        project_root = Path(__file__).resolve().parent.parent
        self.brand_dir = project_root / "brands" / self.brand_slug
        self.trends_path     = self.brand_dir / "trends_live.json"
        self.calendar_path   = self.brand_dir / "content_calendar.json"
        self.watchlist_path  = self.brand_dir / "trend_sentinel_watchlist.json"
        self.decision_path   = self.brand_dir / "pivot_decision.json"
        self.impact_path     = self.brand_dir / "pivot_impact.json"
        self.history_path    = self.brand_dir / "performance_history.json"

        # BUILD C — Pre-compute dead-pattern token set from performance history
        # If a signal's tokens overlap with dead-pattern tokens → block PIVOT (force STAY/TRACK)
        self.dead_pattern_tokens: set = set()
        if self.history_path.exists():
            try:
                with open(self.history_path) as f:
                    history = json.load(f)
                for d in history.get("dead_patterns", []) or []:
                    if d.get("category") in ("topic", "hook_pattern"):
                        v = d.get("value", "")
                        self.dead_pattern_tokens.update(_tokenize(v))
            except Exception:
                pass

    def log(self, msg: str):
        print(f"[Trend Sentinel | {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] {msg}")

    # -------------------------------------------------------------------------
    # INPUT LOADING
    # -------------------------------------------------------------------------

    def _load_trends(self) -> dict:
        if not self.trends_path.exists():
            self.log("HALT — trends_live.json not found. Run Trend Researcher first.")
            return {}
        with open(self.trends_path) as f:
            return json.load(f)

    def _load_calendar(self) -> dict:
        """Returns calendar dict OR empty dict if no calendar exists yet."""
        if not self.calendar_path.exists():
            self.log("No content_calendar.json yet — sentinel will recommend FIRST_PLAN (synthetic PIVOT).")
            return {}
        with open(self.calendar_path) as f:
            return json.load(f)

    def _load_watchlist(self) -> dict:
        """Returns watchlist dict. Auto-create if missing."""
        if not self.watchlist_path.exists():
            return {"signals": {}, "last_updated": None}
        try:
            with open(self.watchlist_path) as f:
                return json.load(f)
        except Exception as e:
            self.log(f"WARNING: Could not read watchlist — {e}. Resetting.")
            return {"signals": {}, "last_updated": None}

    def _save_watchlist(self, wl: dict):
        wl["last_updated"] = self.run_at
        with open(self.watchlist_path, "w") as f:
            json.dump(wl, f, indent=2)

    # -------------------------------------------------------------------------
    # NORMALIZATION — extract comparable signals from trends_live + calendar
    # -------------------------------------------------------------------------

    def _extract_today_signals(self, trends: dict) -> list:
        """
        Pull today's strongest comparable signals from trends_live.json.
        Each signal = {id, label, evidence, source}.
        """
        signals = []

        # Build a score lookup from scored_posts (real engagement metrics) — so signal strength is REAL
        score_lookup_by_handle: dict[str, float] = {}
        score_lookup_by_keyword: dict[str, float] = {}
        # If trends_live.json has the raw scored_posts, use them. Otherwise score = 0 (signal still valid but unscored).
        # NOTE: scored_posts isn't currently saved into trends_live.json — it's only in scraped_data internal.
        # We approximate per-signal score from competitor_intel + cluster size.
        ci = trends.get("competitor_intel", {})

        # Source 1: topic_clusters (named + may have a count or score)
        # Each cluster gets score = cluster post_count if available, else default 50
        for c in trends.get("topic_clusters", []):
            label = (c.get("name") or c.get("topic") or "").strip()
            if not label:
                continue
            # Real metric from clustering pass: count of posts in this cluster
            score = float(c.get("post_count") or c.get("count") or len(c.get("posts", [])) or 50)
            signals.append({
                "id": f"cluster::{label.lower()[:60]}",
                "label": label,
                "evidence": c.get("description") or c.get("reason") or str(c)[:200],
                "source": "topic_clusters",
                "score": score,
            })

        # Source 2: content_angles_to_pursue — these are AutoResearch winners; assigned default score 70
        for a in trends.get("content_angles_to_pursue", []):
            if isinstance(a, dict):
                label = (a.get("angle") or a.get("topic") or "").strip()
                evidence = a.get("reason") or a.get("evidence") or str(a)[:200]
            else:
                label = str(a).strip()
                evidence = ""
            if not label:
                continue
            signals.append({
                "id": f"angle::{label.lower()[:60]}",
                "label": label,
                "evidence": evidence,
                "source": "content_angles_to_pursue",
                "score": 70.0,
            })

        # Source 3: competitor gaps_identified — high-value (competitors not doing them); score 80
        for g in ci.get("gaps_identified", []):
            if isinstance(g, dict):
                label = (g.get("opportunity_for_brand") or g.get("gap") or "").strip()
                evidence = g.get("evidence") or ""
            else:
                continue
            if not label:
                continue
            signals.append({
                "id": f"gap::{label.lower()[:60]}",
                "label": label,
                "evidence": evidence,
                "source": "competitor_gaps",
                "score": 80.0,
            })

        # Dedupe by id, keep highest-score occurrence
        seen: dict[str, dict] = {}
        for s in signals:
            existing = seen.get(s["id"])
            if not existing or s.get("score", 0) > existing.get("score", 0):
                seen[s["id"]] = s
        deduped = list(seen.values())
        # Sort by score descending, cap to 12
        deduped.sort(key=lambda s: s.get("score", 0), reverse=True)
        return deduped[:12]

    def _extract_calendar_topics(self, calendar: dict) -> list:
        """
        Pull topics from calendar slots in the next CALENDAR_LOOKAHEAD_DAYS days.
        Returns list of dicts: {week, day, topic, hook, content_pillar}.
        """
        if not calendar:
            return []

        # Calendar can be at top level OR nested under content_calendar
        cal = calendar.get("content_calendar", calendar)

        topics = []
        for week_key in ("week_1", "week_2", "week_3", "week_4"):
            wk = cal.get(week_key, {})
            for post in wk.get("posts", []):
                if not isinstance(post, dict):
                    continue
                topics.append({
                    "week": week_key,
                    "day": post.get("day"),
                    "topic": post.get("topic", ""),
                    "hook": post.get("hook", ""),
                    "content_pillar": post.get("content_pillar", ""),
                    # Calendar slots from Content Planner have a baseline score of 60
                    # (deterministic baseline — we don't know per-slot performance yet)
                    "score": float(post.get("score", 60.0)),
                })
        # Lookahead: take first N posts (since calendar uses day numbers, not absolute dates,
        # the first N in week_1 are "next 7 days")
        return topics[:CALENDAR_LOOKAHEAD_DAYS]

    # -------------------------------------------------------------------------
    # CORE DECISION — PURE MATH STAY / TRACK / PIVOT per signal
    # NO Claude. NO LLM. Every decision is a code-readable expression.
    # -------------------------------------------------------------------------

    def _decide(self, signals: list, calendar_topics: list, watchlist: dict, calendar_exists: bool) -> dict:
        """
        Pure-math decision per signal. Each decision cites the exact numbers it used.

        Decision tree (in order):
          1. Synthetic PIVOT if no calendar exists → trigger first-plan
          2. STAY if signal token-overlap with any calendar slot >= CALENDAR_OVERLAP_JACCARD_MIN
          3. STAY if signal has no brand-lane keyword match
          4. PIVOT if signal_score > PIVOT_STRENGTH_MULTIPLIER × weakest calendar slot score
          5. STAY if signal_score < STAY_WEAKNESS_MULTIPLIER × weakest calendar slot score
          6. TRACK otherwise (mid-strength signals)
          7. Watchlist auto-escalation (handled in _update_watchlist)

        Every per_signal.reason field includes the exact math expression that drove the decision.
        """
        if not signals:
            return {
                "overall_decision": "STAY",
                "per_signal": [],
                "pivot_signals": [],
                "decision_engine": "pure_math",
                "thresholds_used": {
                    "calendar_overlap_jaccard_min": CALENDAR_OVERLAP_JACCARD_MIN,
                    "pivot_strength_multiplier":    PIVOT_STRENGTH_MULTIPLIER,
                    "stay_weakness_multiplier":     STAY_WEAKNESS_MULTIPLIER,
                    "track_persistence_days":       TRACK_PERSISTENCE_DAYS_TO_PIVOT,
                },
                "loop_header": {
                    "goal":   "Decide whether to pivot the content calendar based on today's trends",
                    "metric": "better = higher precision (no false PIVOTs, no missed real signals)",
                    "variants_tested": 0,
                    "winner": "No signals to evaluate — STAY by default",
                },
            }

        # --- Synthetic PIVOT case: no calendar exists at all ---
        if not calendar_exists:
            return {
                "overall_decision": "PIVOT",
                "per_signal": [{
                    "signal_id": s["id"],
                    "label":     s["label"],
                    "score":     s.get("score", 0),
                    "decision":  "PIVOT",
                    "reason":    "No content_calendar.json exists — first plan must be built",
                } for s in signals],
                "pivot_signals": [s["id"] for s in signals],
                "decision_engine": "pure_math",
                "thresholds_used": {
                    "calendar_overlap_jaccard_min": CALENDAR_OVERLAP_JACCARD_MIN,
                    "pivot_strength_multiplier":    PIVOT_STRENGTH_MULTIPLIER,
                    "stay_weakness_multiplier":     STAY_WEAKNESS_MULTIPLIER,
                    "track_persistence_days":       TRACK_PERSISTENCE_DAYS_TO_PIVOT,
                },
                "loop_header": {
                    "goal":   "Decide whether to pivot the content calendar based on today's trends",
                    "metric": "better = first calendar built from today's strongest signals",
                    "variants_tested": 0,
                    "winner": "calendar_exists == False → all signals PIVOT (build first plan)",
                },
            }

        # --- Pre-compute calendar token sets + weakest score ---
        calendar_token_sets: list[tuple[dict, set]] = []
        calendar_scores: list[float] = []
        for slot in calendar_topics:
            slot_text = " ".join(str(slot.get(f, "")) for f in ("topic", "hook", "content_pillar"))
            slot_tokens = _tokenize(slot_text)
            calendar_token_sets.append((slot, slot_tokens))
            calendar_scores.append(slot.get("score", 60.0))

        weakest_calendar_score = min(calendar_scores) if calendar_scores else 0.0
        per_signal: list[dict] = []

        # --- Per-signal math evaluation ---
        for s in signals:
            sig_tokens = _tokenize(f"{s['label']} {s.get('evidence', '')}")
            sig_score  = float(s.get("score", 0))

            # GATE 1: calendar overlap check
            best_overlap = 0.0
            best_match_topic = ""
            for slot, slot_tokens in calendar_token_sets:
                j = _jaccard(sig_tokens, slot_tokens)
                if j > best_overlap:
                    best_overlap = j
                    best_match_topic = slot.get("topic", "")[:60]
            if best_overlap >= CALENDAR_OVERLAP_JACCARD_MIN:
                per_signal.append({
                    "signal_id": s["id"],
                    "label":     s["label"],
                    "score":     sig_score,
                    "decision":  "STAY",
                    "reason":    f"jaccard_overlap={best_overlap:.2f} >= {CALENDAR_OVERLAP_JACCARD_MIN} with calendar topic '{best_match_topic}' — already covered",
                })
                continue

            # GATE 2: brand-lane match (signal must share at least 1 token with brand profile)
            brand_match = sig_tokens & self.brand_lane_tokens
            if not brand_match:
                per_signal.append({
                    "signal_id": s["id"],
                    "label":     s["label"],
                    "score":     sig_score,
                    "decision":  "STAY",
                    "reason":    f"zero token-overlap with brand profile (industry/product/audience) — off-brand",
                })
                continue

            # GATE 2B: BUILD C — dead-pattern penalty (signal matches a historically-flopped pattern)
            dead_match = sig_tokens & self.dead_pattern_tokens
            if dead_match:
                per_signal.append({
                    "signal_id": s["id"],
                    "label":     s["label"],
                    "score":     sig_score,
                    "decision":  "STAY",
                    "reason":    f"signal matches dead-pattern tokens={sorted(dead_match)[:5]} — flagged by Performance Tracker as historically flopped for this brand; blocked from PIVOT",
                })
                continue

            # GATE 3: strength check vs weakest calendar slot
            ratio = (sig_score / weakest_calendar_score) if weakest_calendar_score > 0 else 999.0
            if ratio > PIVOT_STRENGTH_MULTIPLIER:
                per_signal.append({
                    "signal_id": s["id"],
                    "label":     s["label"],
                    "score":     sig_score,
                    "decision":  "PIVOT",
                    "reason":    f"signal_score={sig_score:.1f} / weakest_calendar_score={weakest_calendar_score:.1f} = {ratio:.2f}× > {PIVOT_STRENGTH_MULTIPLIER}× threshold; brand-match tokens={sorted(brand_match)[:5]}",
                })
            elif ratio < STAY_WEAKNESS_MULTIPLIER:
                per_signal.append({
                    "signal_id": s["id"],
                    "label":     s["label"],
                    "score":     sig_score,
                    "decision":  "STAY",
                    "reason":    f"signal_score={sig_score:.1f} / weakest_calendar_score={weakest_calendar_score:.1f} = {ratio:.2f}× < {STAY_WEAKNESS_MULTIPLIER}× threshold — too weak",
                })
            else:
                per_signal.append({
                    "signal_id": s["id"],
                    "label":     s["label"],
                    "score":     sig_score,
                    "decision":  "TRACK",
                    "reason":    f"signal_score={sig_score:.1f} / weakest_calendar_score={weakest_calendar_score:.1f} = {ratio:.2f}× — mid-strength, watch for {TRACK_PERSISTENCE_DAYS_TO_PIVOT} days",
                })

        # Aggregate overall_decision
        any_pivot = any(p["decision"] == "PIVOT" for p in per_signal)
        any_track = any(p["decision"] == "TRACK" for p in per_signal)
        if any_pivot:
            overall = "PIVOT"
            winner_line = f"≥1 signal scored above {PIVOT_STRENGTH_MULTIPLIER}× weakest calendar slot AND brand-matched → PIVOT"
        elif any_track:
            overall = "TRACK"
            winner_line = f"All signals either covered/off-brand or mid-strength — no PIVOT triggered, watching mid-strength signals"
        else:
            overall = "STAY"
            winner_line = f"All signals either already covered, off-brand, or below strength threshold — no action"

        return {
            "overall_decision": overall,
            "per_signal":       per_signal,
            "pivot_signals":    [p["signal_id"] for p in per_signal if p["decision"] == "PIVOT"],
            "decision_engine":  "pure_math",
            "thresholds_used": {
                "calendar_overlap_jaccard_min": CALENDAR_OVERLAP_JACCARD_MIN,
                "pivot_strength_multiplier":    PIVOT_STRENGTH_MULTIPLIER,
                "stay_weakness_multiplier":     STAY_WEAKNESS_MULTIPLIER,
                "track_persistence_days":       TRACK_PERSISTENCE_DAYS_TO_PIVOT,
                "weakest_calendar_score":       weakest_calendar_score,
                "dead_pattern_tokens_loaded":   len(self.dead_pattern_tokens),
            },
            "loop_header": {
                "goal":   "Decide whether to pivot the content calendar based on today's trends",
                "metric": "better = higher precision (no false PIVOTs, no missed real signals)",
                "variants_tested": 1,
                "winner": winner_line,
            },
        }

    # -------------------------------------------------------------------------
    # WATCHLIST — TRACK persistence + auto-escalation
    # -------------------------------------------------------------------------

    def _update_watchlist(self, decision: dict, watchlist: dict) -> tuple[dict, list]:
        """
        Update watchlist based on per_signal decisions.
        - TRACK signals: increment day_count (or create with day_count=1)
        - STAY signals: remove from watchlist (no longer relevant)
        - PIVOT signals: remove from watchlist (will be addressed by Content Planner re-run)

        Auto-escalation: if a TRACK signal has day_count >= TRACK_PERSISTENCE_DAYS_TO_PIVOT,
        upgrade it to PIVOT and add to escalated_signals.

        Returns (updated_watchlist, escalated_signals).
        """
        signals_dict = watchlist.get("signals", {})
        escalated = []

        for ps in decision.get("per_signal", []):
            sid = ps.get("signal_id")
            d   = ps.get("decision", "STAY")

            if d == "TRACK":
                if sid in signals_dict:
                    signals_dict[sid]["day_count"] += 1
                    signals_dict[sid]["last_seen"] = self.run_at
                    if signals_dict[sid]["day_count"] >= TRACK_PERSISTENCE_DAYS_TO_PIVOT:
                        # Auto-escalate
                        ps["decision"] = "PIVOT"
                        ps["reason"]   = f"AUTO-ESCALATED — TRACKed for {signals_dict[sid]['day_count']} days (>={TRACK_PERSISTENCE_DAYS_TO_PIVOT})"
                        escalated.append(sid)
                        del signals_dict[sid]
                else:
                    signals_dict[sid] = {
                        "label": ps.get("label", ""),
                        "first_seen": self.run_at,
                        "last_seen":  self.run_at,
                        "day_count":  1,
                        "reason":     ps.get("reason", ""),
                    }
            elif d in ("STAY", "PIVOT"):
                if sid in signals_dict:
                    del signals_dict[sid]

        # Recompute overall_decision after escalation
        any_pivot = any(p.get("decision") == "PIVOT" for p in decision.get("per_signal", []))
        any_track = any(p.get("decision") == "TRACK" for p in decision.get("per_signal", []))
        if any_pivot:
            decision["overall_decision"] = "PIVOT"
            decision["pivot_signals"] = [
                p["signal_id"] for p in decision.get("per_signal", []) if p.get("decision") == "PIVOT"
            ]
        elif any_track:
            decision["overall_decision"] = "TRACK"
        else:
            decision["overall_decision"] = "STAY"

        watchlist["signals"] = signals_dict
        return watchlist, escalated

    # -------------------------------------------------------------------------
    # PIVOT IMPACT — what calendar slots / produced content gets killed?
    # -------------------------------------------------------------------------

    def _compute_pivot_impact(self, calendar_topics: list) -> dict:
        """
        On PIVOT decision, list which already-planned content slots would be invalidated.
        Conservative: only future slots (which haven't yet been produced) are killed.
        Already-scripted/visualized content in pending_approval is NEVER auto-killed.
        """
        # Look for already-produced content for each calendar slot
        produced = []
        sw_dir = self.brand_dir / "outputs" / "pending_approval" / "script-writer"
        cd_dir = self.brand_dir / "outputs" / "pending_approval" / "creative-director"

        if sw_dir.exists():
            for f in sw_dir.glob("*.json"):
                produced.append({"agent": "script-writer", "file": f.name})
        if cd_dir.exists():
            for f in cd_dir.iterdir():
                if f.is_file():
                    produced.append({"agent": "creative-director", "file": f.name})

        return {
            "computed_at": self.run_at,
            "calendar_slots_to_be_replaced": len(calendar_topics),
            "slot_summaries": [
                {"week": t.get("week"), "day": t.get("day"), "topic": t.get("topic", "")[:80]}
                for t in calendar_topics
            ],
            "already_produced_content_in_pending_approval": produced,
            "human_action_required": "Review pivot_decision.json. If approved, Content Planner will re-run. Already-produced content in pending_approval will NOT be auto-deleted — review manually.",
        }

    # -------------------------------------------------------------------------
    # PIVOT TRIGGER — optionally call Content Planner subprocess
    # -------------------------------------------------------------------------

    def _trigger_content_planner(self):
        """If SENTINEL_AUTO_PIVOT enabled, fire Content Planner as background subprocess."""
        if not SENTINEL_AUTO_PIVOT:
            self.log("SENTINEL_AUTO_PIVOT not enabled — skipping auto-trigger. Human must approve pivot_decision.json manually.")
            return None

        cp_path = Path(__file__).resolve().parent / "content_planner.py"
        if not cp_path.exists():
            self.log(f"WARNING: Content Planner script not found at {cp_path}")
            return None

        env = os.environ.copy()
        env["ACTIVE_BRAND"] = self.brand_slug
        env["GRID_BRAND_SLUG"] = self.brand_slug

        self.log(f"AUTO-PIVOT: triggering Content Planner subprocess for {self.brand_slug}...")
        proc = subprocess.Popen(
            [sys.executable, str(cp_path)],
            cwd=str(Path(__file__).resolve().parent.parent),
            env=env,
            stdout=subprocess.DEVNULL,  # don't block — Content Planner has its own logging
            stderr=subprocess.DEVNULL,
        )
        return proc.pid

    # -------------------------------------------------------------------------
    # MAIN RUN
    # -------------------------------------------------------------------------

    def run(self) -> dict:
        self.log("=" * 60)
        self.log("TREND SENTINEL — DAILY RUN STARTING")
        self.log("=" * 60)

        # --- STEP 1: LOAD INPUTS ---
        trends = self._load_trends()
        if not trends:
            self.log("HALT — no trends_live.json. Run Trend Researcher first.")
            return {"status": "HALTED", "reason": "no_trends_live"}

        calendar = self._load_calendar()
        calendar_exists = bool(calendar)
        watchlist = self._load_watchlist()

        # --- STEP 2: EXTRACT COMPARABLE SIGNALS ---
        signals = self._extract_today_signals(trends)
        calendar_topics = self._extract_calendar_topics(calendar)
        self.log(f"Today: {len(signals)} signals | Calendar (next {CALENDAR_LOOKAHEAD_DAYS} slots): {len(calendar_topics)}")

        # --- STEP 3: CLAUDE-JUDGED DECISION ---
        decision = self._decide(signals, calendar_topics, watchlist, calendar_exists)

        # --- STEP 4: UPDATE WATCHLIST + AUTO-ESCALATION ---
        watchlist, escalated = self._update_watchlist(decision, watchlist)
        self._save_watchlist(watchlist)
        if escalated:
            self.log(f"AUTO-ESCALATED to PIVOT: {escalated}")

        decision["computed_at"] = self.run_at
        decision["brand_slug"] = self.brand_slug
        decision["calendar_existed"] = calendar_exists
        decision["watchlist_size"] = len(watchlist.get("signals", {}))
        decision["auto_escalated_signals"] = escalated

        # --- STEP 5: SAVE DECISION ---
        with open(self.decision_path, "w") as f:
            json.dump(decision, f, indent=2)
        self.log(f"pivot_decision.json saved → {self.decision_path}")

        # --- STEP 6: PIVOT IMPACT + OPTIONAL TRIGGER ---
        triggered_pid = None
        if decision["overall_decision"] == "PIVOT":
            impact = self._compute_pivot_impact(calendar_topics)
            with open(self.impact_path, "w") as f:
                json.dump(impact, f, indent=2)
            self.log(f"pivot_impact.json saved — {impact['calendar_slots_to_be_replaced']} slots affected, "
                     f"{len(impact['already_produced_content_in_pending_approval'])} already-produced files flagged for human review")

            triggered_pid = self._trigger_content_planner()
            if triggered_pid:
                decision["content_planner_subprocess_pid"] = triggered_pid

        # --- STEP 7: PUSH TO PENDING APPROVAL + NOTION ---
        loop_header = decision.get("loop_header", {})
        save_result = self.ceo.save_agent_output(
            agent_name="Trend Sentinel",
            output_type="Daily Pivot Decision",
            loop_header={
                "goal":            loop_header.get("goal", ""),
                "metric":          loop_header.get("metric", ""),
                "variants_tested": loop_header.get("variants_tested", 3),
                "winner":          loop_header.get("winner", ""),
            },
            content=json.dumps(decision, indent=2),
            filename="pivot_decision.json",
        )

        # --- STEP 8: COMPLETE (no cost — pure math, zero Claude calls) ---

        self.log("=" * 60)
        self.log(f"TREND SENTINEL — RUN COMPLETE | Decision: {decision['overall_decision']}")
        self.log(f"Per-signal breakdown:")
        for ps in decision.get("per_signal", []):
            self.log(f"  [{ps.get('decision')}] {ps.get('label', '')[:80]}")
        if triggered_pid:
            self.log(f"Content Planner subprocess started — PID {triggered_pid}")
        self.log("=" * 60)

        return decision


if __name__ == "__main__":
    sentinel = TrendSentinel()
    sentinel.run()
