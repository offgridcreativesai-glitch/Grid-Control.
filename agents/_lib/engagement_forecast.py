"""
engagement_forecast.py — the cheap "neuroforecast" proxy.

WHY THIS EXISTS
----------------
We wanted facebookresearch/tribev2 to pre-test content the way a "neural focus
group" does: predict what will trend before we post it. TRIBE does that by
predicting fMRI brain responses to video/audio/text — but it needs a GPU, only
outputs raw cortical-mesh activity (not a usable score), and is unvalidated for
social virality. Cost-heavy, R&D-grade.

So we STEAL THE PURPOSE, not the model. The neuroforecasting literature
(Falk, Berns, et al.) says population-level sharing is predicted by brain
activity in regions tied to: REWARD/VALUE, EMOTIONAL AROUSAL, ATTENTION/SALIENCE,
SOCIAL/SELF-RELEVANCE, and MEMORY/DISTINCTIVENESS. Those map cleanly onto the
STEPPS framework our content agents already use. We score those dimensions with
cheap text heuristics, calibrate the weights on THIS brand's real past winners,
and emit a 0-100 Trend Forecast with full provenance.

This is a Class-1 (pure-math) helper: decision_engine = "pure_math". No LLM call,
no GPU, $0 per run. It is a PROXY, not a measurement — it ranks variants and
flags weak ones; it does not claim to read brains.
"""
from __future__ import annotations

import json
import math
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

# --- neuroforecast dimensions (brain-response drivers of sharing) -> STEPPS ---
# weight = default prior; calibrated against brand performance history when present.
DIMENSIONS = {
    "attention":   {"weight": 0.24, "stepps": "Trigger/Public",  "desc": "hook salience — does it stop the scroll in 1-2s"},
    "reward":      {"weight": 0.22, "stepps": "Practical Value", "desc": "promised payoff / value signal"},
    "arousal":     {"weight": 0.22, "stepps": "Emotion",         "desc": "high-arousal emotion (awe, surprise, conviction)"},
    "social_self": {"weight": 0.20, "stepps": "Social Currency", "desc": "identity / 'this is my tribe' relevance"},
    "memory":      {"weight": 0.12, "stepps": "Stories",         "desc": "distinctiveness + story structure (sticky)"},
}

# lightweight lexicons (signal markers, not exhaustive — heuristic by design)
_HIGH_AROUSAL = {
    "shocking", "insane", "unbelievable", "never", "secret", "brutal", "stop",
    "warning", "mistake", "fail", "wow", "stunning", "obsessed", "love", "hate",
    "fear", "proud", "finally", "breakthrough", "exposed", "truth", "nobody",
}
_VALUE_MARKERS = {
    "how", "steps", "framework", "save", "free", "guide", "tips", "hack",
    "playbook", "template", "checklist", "results", "proven", "in minutes",
    "without", "cheaper", "faster", "double", "grow", "revenue", "leads",
}
_SOCIAL_SELF = {
    "you", "your", "founders", "we", "us", "creators", "owners", "people who",
    "if you're", "for anyone", "every founder", "your brand", "your team",
}
_CURIOSITY = {"why", "what", "how", "the reason", "here's", "this is why", "nobody tells you", "?"}
_STORY = {"i ", "we ", "when ", "after ", "before ", "story", "day ", "year", "started", "lesson"}


@dataclass
class Forecast:
    score: int                       # 0-100 overall trend forecast
    dimensions: dict                 # per-dimension 0-100
    verdict: str                     # STRONG / SOLID / WEAK
    notes: list = field(default_factory=list)
    provenance: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "trend_forecast": self.score,
            "verdict": self.verdict,
            "dimensions": self.dimensions,
            "notes": self.notes,
            "data_provenance": self.provenance,
        }


def _norm(x: float) -> int:
    return max(0, min(100, round(x)))


def _hits(text: str, lexicon) -> int:
    t = text.lower()
    return sum(1 for w in lexicon if w in t)


def _hook_strength(first_line: str) -> float:
    """Attention/salience of the opening line — the scroll-stopper."""
    fl = first_line.strip().lower()
    if not fl:
        return 0.0
    s = 0.0
    if re.search(r"\d", fl):                       s += 22   # numbers anchor
    if "?" in fl:                                   s += 18   # open loop
    if _hits(fl, _CURIOSITY):                       s += 18
    if _hits(fl, _HIGH_AROUSAL):                    s += 22
    if fl.startswith(("how", "why", "what", "the", "stop", "nobody", "i ")): s += 12
    wc = len(fl.split())
    if 4 <= wc <= 12:                               s += 14   # punchy length
    elif wc > 22:                                   s -= 12   # too long to hook
    return min(100.0, s)


def _density(text: str, lexicon, cap: int = 5) -> float:
    """0-100 from marker density, saturating."""
    n = min(_hits(text, lexicon), cap)
    return 100.0 * (1 - math.exp(-0.7 * n))


def _calibrate(history_path: Optional[Path]) -> dict:
    """
    Adjust dimension weights toward whatever correlated with THIS brand's
    past high performers. Falls back to priors when no usable history.
    Returns (weights, provenance_note).
    """
    weights = {k: v["weight"] for k, v in DIMENSIONS.items()}
    note = "default priors (no calibration data)"
    if not history_path or not history_path.exists():
        return weights, note
    try:
        data = json.loads(history_path.read_text())
        posts = data if isinstance(data, list) else data.get("posts", data.get("history", []))
        winners = [p for p in posts if isinstance(p, dict) and _engagement_of(p) is not None]
        if len(winners) >= 5:
            # rank by engagement, take top third as "winners", nudge weights
            winners.sort(key=_engagement_of, reverse=True)
            top = winners[: max(3, len(winners) // 3)]
            boost = _dimension_bias(top)
            for k in weights:
                weights[k] = weights[k] * (0.7 + 0.6 * boost.get(k, 0.5))
            tot = sum(weights.values()) or 1.0
            weights = {k: v / tot for k, v in weights.items()}
            note = f"calibrated on {len(top)} top performers of {len(winners)} scored posts"
    except Exception as e:  # never let calibration break a forecast
        note = f"calibration skipped ({type(e).__name__})"
    return weights, note


def _engagement_of(post: dict):
    likes = post.get("likesCount", post.get("likes"))
    comments = post.get("commentsCount", post.get("comments"))
    saves = post.get("saves", post.get("savesCount", 0))
    if likes is None and comments is None:
        return None
    return (likes or 0) + 2 * (comments or 0) + 3 * (saves or 0)


def _dimension_bias(top_posts) -> dict:
    """Which dimensions the brand's winners over-index on (0-1 each)."""
    agg = {k: 0.0 for k in DIMENSIONS}
    for p in top_posts:
        text = " ".join(str(p.get(f, "")) for f in ("caption", "hook", "text", "title"))
        fc = forecast(text, calibrate_path=None, _raw=True)
        for k, v in fc.dimensions.items():
            agg[k] += v / 100.0
    n = max(1, len(top_posts))
    return {k: v / n for k, v in agg.items()}


def forecast(text: str, *, format_hint: str = "reel", calibrate_path: Optional[Path] = None, _raw: bool = False) -> Forecast:
    """Score one content draft. Pure math, $0, no network."""
    text = (text or "").strip()
    first_line = text.splitlines()[0] if text else ""

    dims = {
        "attention":   _hook_strength(first_line),
        "reward":      _density(text, _VALUE_MARKERS),
        "arousal":     _density(text, _HIGH_AROUSAL),
        "social_self": _density(text, _SOCIAL_SELF),
        "memory":      _density(text, _STORY),
    }
    dims = {k: _norm(v) for k, v in dims.items()}

    weights, cal_note = ({k: v["weight"] for k, v in DIMENSIONS.items()}, "raw") if _raw else _calibrate(calibrate_path)
    score = _norm(sum(dims[k] * weights[k] for k in dims))

    verdict = "STRONG" if score >= 70 else "SOLID" if score >= 50 else "WEAK"
    notes = []
    weak = sorted(dims, key=dims.get)[:2]
    for k in weak:
        if dims[k] < 45:
            notes.append(f"low {k} ({dims[k]}) — {DIMENSIONS[k]['desc']}")

    return Forecast(
        score=score, dimensions=dims, verdict=verdict, notes=notes,
        provenance={
            "decision_engine": "pure_math",
            "method": "neuroforecast-proxy (TRIBE purpose, STEPPS dimensions, heuristic)",
            "weights": {k: round(v, 3) for k, v in weights.items()},
            "calibration": cal_note,
        },
    )


def rank_variants(variants: list[dict], *, text_key: str = "text", calibrate_path: Optional[Path] = None) -> list[dict]:
    """
    Score + rank AutoResearch variants by predicted trend. Returns variants
    sorted best-first, each annotated with its forecast. Use as a selection
    signal alongside the agent's own metric.
    """
    out = []
    for v in variants:
        fc = forecast(v.get(text_key, ""), calibrate_path=calibrate_path)
        out.append({**v, "forecast": fc.to_dict()})
    out.sort(key=lambda x: x["forecast"]["trend_forecast"], reverse=True)
    if out:
        out[0]["forecast_winner"] = True
    return out


if __name__ == "__main__":
    samples = [
        "I spent 40 hours building what AI creators do in 4 minutes. Here's the brutal truth nobody tells founders.",
        "Check out our new product update, now available for everyone to use today.",
        "Why your marketing feels stuck — and the 3-step framework we used to double our leads without ads.",
    ]
    for s in samples:
        fc = forecast(s)
        print(f"\n[{fc.verdict} · {fc.score}] {s[:60]}…")
        print("   dims:", fc.dimensions)
        if fc.notes:
            print("   fix :", "; ".join(fc.notes))
