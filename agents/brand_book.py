"""
agents/brand_book.py — Brand-Book / Brand-Intelligence Report v6 (Phase G).

Builds the 8-part report per docs/BRAND_BOOK_REPORT_SPEC.md. ONE artifact, two
uses (G7):
  - cold_sellable        — scrape-only, inferred audience, "recommended" foundation.
  - onboarding_connected — OAuth real IG Insights + client sign-off → writes
                           brand_profile.json + voice_profile.json (the Step-3.5 gate).

Real data only; every metric carries Rule-10 provenance (REAL vs AI_ESTIMATED).
Narrative sections run on Opus via the model gateway with an AutoResearch 3-variant
loop; deterministic sections (scorecard, full-category benchmark, eval) are pure math.
Renders to PDF via brand_book_renderer (forced white bg — dark-mode bug, spec §5).

──────────────────────────────────────────────────────────────────────────────
RUN-COST BOUNDARY (standing rule — no unattended paid runs):
  generate() makes Opus calls (+ onboarding: live IG Insights) → this is a PAID run.
  It is invoked ONLY in the supervised pilot (§4.5), never unattended.
  The deterministic core (benchmark(), _scorecard(), _eval(), metric()) and the
  renderer are import-safe and unit-testable at ZERO API cost — that is what
  Phase G verifies during the build.
──────────────────────────────────────────────────────────────────────────────
"""
import os
import sys
import json
import statistics
from datetime import datetime, timezone
from pathlib import Path

_HERE = Path(__file__).resolve().parent
_ROOT = _HERE.parent

try:
    from model_gateway import complete, model_for
    from _untrusted import wrap as _untrusted_wrap, UNTRUSTED_POLICY
except ImportError:
    from agents.model_gateway import complete, model_for
    from agents._untrusted import wrap as _untrusted_wrap, UNTRUSTED_POLICY

# ── config ────────────────────────────────────────────────────────────────────
MODE_COLD = "cold_sellable"
MODE_ONBOARDING = "onboarding_connected"
VALID_MODES = (MODE_COLD, MODE_ONBOARDING)

REAL = "REAL"            # scraped / IG Insights — a real measured number
ESTIMATED = "AI_ESTIMATED"  # inferred / modeled — tagged, never presented as measured

VERSION = "v6"
AGENT_SLUG = "brand-book"


# ── provenance-tagged metric (Rule 10) ─────────────────────────────────────────
def metric(value, basis: str, source_file: str | None = None,
           path: str | None = None, note: str | None = None) -> dict:
    """A single figure with its provenance. basis ∈ {REAL, AI_ESTIMATED}.
    REAL requires a source_file+path the number traces to; ESTIMATED carries a note."""
    assert basis in (REAL, ESTIMATED), f"bad basis {basis!r}"
    m = {"value": value, "basis": basis}
    if source_file:
        m["source_file"] = source_file
    if path:
        m["path"] = path
    if note:
        m["note"] = note
    return m


def _is_real(m) -> bool:
    return isinstance(m, dict) and m.get("basis") == REAL


# ── G3: full-category benchmark (pure math, deterministic, testable) ────────────
def _percentile_band(p: float) -> str:
    if p < 25:   return "bottom-quartile"
    if p < 50:   return "below-median"
    if p < 75:   return "solid (50–75)"
    if p < 90:   return "top-quartile (75–90)"
    if p < 95:   return "exceptional (90–95)"
    return "category-leading (>95)"


def benchmark(brand_value: float, competitor_values: list[float]) -> dict:
    """Benchmark a brand metric against the full category (spec §2.3 / G3).

    Returns category avg + median, the brand's percentile rank + band, Share of
    Voice %, and leaderboard rank (out of N including the brand). If there are not
    enough REAL competitor numbers it returns {available: False, reason} — the
    report then renders an honest "benchmark pending — competitor scrape" block
    instead of fabricating a category average (zero-assumption rule; the live
    competitor scrape happens in the supervised pilot).
    """
    vals = [float(v) for v in competitor_values if isinstance(v, (int, float))]
    if brand_value is None or len(vals) < 2:
        return {"available": False,
                "reason": "needs a real numeric metric for the brand + ≥2 competitors "
                          "(competitor scrape runs in the pilot)"}
    brand_value = float(brand_value)
    universe = vals + [brand_value]
    n = len(universe)
    # percentile rank of the brand within the full universe
    below = sum(1 for v in universe if v < brand_value)
    equal = sum(1 for v in universe if v == brand_value)
    pct = (below + 0.5 * equal) / n * 100.0
    total = sum(universe)
    sov = (brand_value / total * 100.0) if total > 0 else 0.0
    rank = sorted(universe, reverse=True).index(brand_value) + 1
    return {
        "available": True,
        "n": n,
        "category_avg": round(statistics.mean(vals), 2),
        "category_median": round(statistics.median(vals), 2),
        "brand_value": round(brand_value, 2),
        "percentile_rank": round(pct, 1),
        "percentile_band": _percentile_band(pct),
        "share_of_voice_pct": round(sov, 1),
        "leaderboard_rank": rank,
    }


# ── the generator ───────────────────────────────────────────────────────────────
class BrandBook:
    def __init__(self, brand_slug: str, mode: str = MODE_COLD, benv: dict | None = None):
        if mode not in VALID_MODES:
            raise ValueError(f"mode must be one of {VALID_MODES}, got {mode!r}")
        self.slug = brand_slug
        self.mode = mode
        self.benv = benv or {}
        self.brand_dir = _ROOT / "brands" / brand_slug
        self.data: dict = {}
        self.insights: dict = {}
        self._provenance: list[dict] = []

    # —— data load (real files only; honest-empty on absence) ——
    def _load_json(self, name: str) -> dict:
        p = self.brand_dir / name
        if not p.exists():
            return {}
        try:
            raw = p.read_text(encoding="utf-8")
            body = raw.split("\n---\n", 1)[1] if "\n---\n" in raw else raw
            return json.loads(body)
        except Exception:
            return {}

    def load(self) -> "BrandBook":
        self.data = {
            "brand_profile": self._load_json("brand_profile.json"),
            "voice_profile": self._load_json("voice_profile.json"),
            "trends_live": self._load_json("trends_live.json"),
            "strategy_90day": self._load_json("strategy_90day.json"),
            "content_calendar": self._load_json("content_calendar.json"),
        }
        # onboarding mode pulls REAL demographics; cold mode stays inferred
        if self.mode == MODE_ONBOARDING:
            try:
                try:
                    from meta_insights import fetch_instagram_insights
                except ImportError:
                    from agents.meta_insights import fetch_instagram_insights
                self.insights = fetch_instagram_insights(self.benv) or {}
            except Exception as e:
                self.insights = {"connected": False, "errors": [f"insights load failed: {e}"]}
        return self

    def _record(self, m: dict) -> dict:
        """Track a metric in the flat provenance list (appendix table) and return it."""
        self._provenance.append(m)
        return m

    # —— PART 0: scorecard (deterministic from real profile/calendar) ——
    def _scorecard(self) -> dict:
        bp = self.data["brand_profile"]
        cal = self.data["content_calendar"]
        acct = self.insights.get("account", {}) if self.mode == MODE_ONBOARDING else {}

        metrics = []
        # followers: REAL from IG Insights (onboarding) else inferred range (cold)
        if acct.get("followers_count") is not None:
            metrics.append(("Followers", self._record(metric(
                acct["followers_count"], REAL, "ig_insights", "account.followers_count"))))
        elif bp.get("follower_range"):
            metrics.append(("Follower range", self._record(metric(
                bp["follower_range"], ESTIMATED, "brand_profile.json", "follower_range",
                note="inferred range — connect IG for exact count"))))

        # posting cadence: REAL from the produced calendar
        posts = cal.get("posts") or cal.get("calendar") or []
        if isinstance(posts, list) and posts:
            metrics.append(("Planned cadence", self._record(metric(
                f"{len(posts)} posts / 30d", REAL, "content_calendar.json", "posts[]"))))

        # reach 28d: REAL when connected
        if acct.get("reach_28d") is not None:
            metrics.append(("Reach (28d)", self._record(metric(
                acct["reach_28d"], REAL, "ig_insights", "account.reach_28d"))))

        return {"title": "Executive Scorecard", "metrics": metrics}

    # —— external data, LAW-wrapped before any model call ——
    def _scraped_block(self, label: str, obj) -> str:
        return _untrusted_wrap(label, obj)

    # —— narrative section prompt builders (PAID: run in pilot only) ——
    def _section(self, agent_role: str, instruction: str, *, scraped: dict | None = None,
                 max_tokens: int = 2000) -> str:
        """One Opus call for a narrative section. All scraped/external content is
        LAW-wrapped. Returns the model text. PAID — only reached via generate()."""
        bp = self.data["brand_profile"]
        parts = [
            f"You are the Brand-Book analyst for {bp.get('name', self.slug)} "
            f"({bp.get('industry','')} · {bp.get('market','')}).",
            UNTRUSTED_POLICY,
            "BRAND PROFILE:\n" + json.dumps(bp, ensure_ascii=False, indent=2),
        ]
        if scraped:
            parts.append("REAL SCRAPED DATA:\n" + self._scraped_block("scraped_brand_data", scraped))
        parts.append(instruction)
        # G6 — the eval auto-rejects AI-filler phrases; ban them at generation time
        # so we never pay to regenerate over a stray cliché.
        parts.append(
            "HARD STYLE RULE — never use these phrases or close variants "
            "(the report is auto-rejected if any appear): " + "; ".join(_FILLER) + "."
        )
        prompt = "\n\n".join(parts)
        res = complete(AGENT_SLUG, [{"role": "user", "content": prompt}], max_tokens=max_tokens)
        return (res.get("text") or "").strip()

    # —— G6: eval rubric (deterministic pass/fail over the built report) ——
    def _eval(self, report: dict) -> dict:
        parts = report.get("parts", {})
        prov = report.get("provenance", [])
        checks = {
            # (a) at least one REAL scraped/Insights number anywhere
            "has_real_number": any(_is_real(m) for m in prov),
            # (b) competitor + full-category benchmark present (available OR honestly-pending)
            "benchmark_present": "benchmark" in parts.get("part2_where_you_stand", {}),
            # (d) Part-1 foundation block complete
            "foundation_complete": all(
                k in (parts.get("part1_foundation") or {})
                for k in ("positioning_statement", "pillars", "voice", "north_star")
            ),
            # (e) no AI-filler flag language in any narrative
            "no_ai_filler": not _has_filler(report),
            # template contract: all 8 parts + appendix emitted
            "all_parts_present": all(
                k in parts for k in (
                    "part0_scorecard", "part1_foundation", "part2_where_you_stand",
                    "part3_market", "part4_content_intel", "part5_audience",
                    "part6_growth_playbook", "part7_horizon", "appendix")
            ),
        }
        return {"passed": all(checks.values()), "checks": checks}

    # —— orchestration (PAID — pilot only) ——
    def generate(self, render_pdf: bool = True) -> dict:
        """Build the full 8-part report. PAID (Opus + IG Insights). Returns the
        structured report dict; writes JSON (+ optional PDF) to pending_approval."""
        if not self.data:
            self.load()
        bp = self.data["brand_profile"]
        trends = self.data["trends_live"]
        comp = trends.get("competitor_intel", {})

        scorecard = self._scorecard()
        n_real = sum(1 for m in self._provenance if _is_real(m))

        parts = {
            "part0_scorecard": scorecard,
            "part1_foundation": self._foundation(),
            "part2_where_you_stand": self._where_you_stand(comp),
            "part3_market": {"narrative": self._section(
                "market", "PART 3 — THE MARKET: who is winning in this category and why "
                "(competitor deep-dive), then a blunt Brand-vs-Market reality check. "
                "Use only the scraped competitor data; cite specifics.",
                scraped=comp)},
            "part4_content_intel": {"narrative": self._section(
                "content", "PART 4 — CONTENT INTELLIGENCE: what stops the scroll in this "
                "category (hooks + formats), proven hook formulas from the data, and the "
                "format gaps this brand can own.",
                scraped={"instagram_trends": trends.get("instagram_trends", {})})},
            "part5_audience": self._audience(),
            "part6_growth_playbook": {"narrative": self._section(
                "growth", "PART 6 — GROWTH PLAYBOOK: ad-ready content angles + a 30-day "
                "content playbook + a 'Stop These Immediately' list + 5 priority actions "
                "ranked by impact. Be specific and sequenced.",
                scraped={"strategy": self.data["strategy_90day"]})},
            "part7_horizon": {"narrative": self._section(
                "horizon", "PART 7 — HORIZON: trends to ride before they peak and new "
                "channels to expand onto. Ground every call in the scraped signals.",
                scraped={"trends": trends})},
            "appendix": self._appendix(),
        }

        report = {
            "meta": {
                "brand": bp.get("name", self.slug),
                "slug": self.slug,
                "category": bp.get("industry", ""),
                "market": bp.get("market", ""),
                "date": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
                "version": VERSION,
                "mode": self.mode,
                "model": model_for(AGENT_SLUG),
                "data_basis": f"built from {n_real} real measured figures "
                              f"({'live IG Insights + ' if self.mode == MODE_ONBOARDING else ''}"
                              f"scraped category data)",
            },
            "parts": parts,
            "provenance": self._provenance,
        }
        report["eval"] = self._eval(report)

        out = self._write(report)
        report["_output_path"] = str(out)
        if render_pdf:
            try:
                report["_pdf_path"] = str(self._render(report))
            except Exception as e:
                report["_pdf_error"] = str(e)
        return report

    def _foundation(self) -> dict:
        """PART 1 — the sign-off block. Synthesized from brand_profile + voice_profile
        + strategy. Returned as STRUCTURED fields so onboarding can write them to
        brand_profile.json + voice_profile.json on approval (Phase H)."""
        instruction = (
            "PART 1 — BRAND FOUNDATION (the sign-off block). Return STRICT JSON with keys: "
            "positioning_statement (one line: 'For [ICP], [brand] is the [category] that "
            "[unique value], unlike [alt].'), value_prop {functional, emotional}, "
            "pillars (3–5 items, each {name, proof}), voice {personality, do[], dont[], "
            "vocab_use[], vocab_avoid[]}, icp (2–3 persona strings), "
            "north_star {metric, target}. No prose outside the JSON."
        )
        raw = self._section("foundation", instruction,
                            scraped={"voice_profile": self.data["voice_profile"],
                                     "strategy": self.data["strategy_90day"]},
                            max_tokens=2500)
        return _coerce_json(raw, fallback_keys=(
            "positioning_statement", "value_prop", "pillars", "voice", "icp", "north_star"))

    def _where_you_stand(self, comp: dict) -> dict:
        """PART 2 — honest position + competitor head-to-head + full-category benchmark.
        The benchmark uses real numeric competitor metrics when present; absent them
        it renders an honest 'pending' block (scrape happens in the pilot)."""
        # numeric competitor metrics are not in cache today (qualitative competitor_intel
        # only) → benchmark() returns available:False until the pilot scrape populates them.
        comp_numbers = comp.get("competitor_metrics") or []
        brand_metric_val = None  # populated by the pilot scrape (brand avg engagement)
        bench = benchmark(brand_metric_val, [c.get("avg_engagement") for c in comp_numbers
                                             if isinstance(c, dict)])
        # G5 — each scraped competitor engagement figure is a REAL measured number;
        # record it as provenance so the report cites real data (Rule 10, eval G6).
        for c in comp_numbers:
            if isinstance(c, dict) and isinstance(c.get("avg_engagement"), (int, float)) \
                    and c["avg_engagement"] > 0:
                self._record(metric(
                    c["avg_engagement"], REAL, "apify_competitor_scrape",
                    f"competitor_intel.competitor_metrics[{c.get('handle','?')}].avg_engagement",
                    note="avg likes+comments per post from scraped competitor profile"))
        hard_truth = self._section(
            "assessment", "PART 2 — WHERE YOU STAND: the single hardest truth about this "
            "brand's current position vs the category, in 2–3 blunt sentences. No hedging.",
            scraped=comp)
        return {"hard_truth": hard_truth,
                "competitors_scraped": comp.get("handles_scraped", []),
                "benchmark": bench}

    def _audience(self) -> dict:
        """PART 5 — REAL Insights demographics (onboarding) or inferred (cold)."""
        if self.mode == MODE_ONBOARDING and self.insights.get("connected"):
            aud = self.insights.get("audience", {})
            for dim in ("age", "gender", "country"):
                if aud.get(dim):
                    self._record(metric(aud[dim], REAL, "ig_insights", f"audience.{dim}"))
            return {"basis": REAL, "demographics": aud,
                    "note": "Real Instagram Insights (authenticated account)."}
        inferred = self._section(
            "audience", "PART 5 — AUDIENCE INTELLIGENCE: infer who is actually engaging "
            "(age range, interests, the language they use) from the scraped engagement "
            "signals. Mark this explicitly as INFERRED, not measured.",
            scraped={"audience_language": self.data["trends_live"].get("audience_language", {})})
        return {"basis": ESTIMATED, "inferred": inferred,
                "note": "Inferred from engagement — connect IG for real demographics."}

    def _appendix(self) -> dict:
        trends = self.data["trends_live"]
        real = [m for m in self._provenance if _is_real(m)]
        est = [m for m in self._provenance if not _is_real(m)]
        return {
            "top_posts": trends.get("instagram_trends", {}).get("top_hooks", [])[:10],
            "provenance": self._provenance,
            "methodology": (
                f"{len(real)} figures are REAL (scraped IG data / live Insights); "
                f"{len(est)} are AI-ESTIMATED (inferred, tagged in-line). "
                f"Category set: the brand's scraped competitor handles. "
                f"Scrape date: {trends.get('scraped_at', 'n/a')}. "
                f"Mode: {self.mode}."),
        }

    # —— IO ——
    def _write(self, report: dict) -> Path:
        out_dir = self.brand_dir / "outputs" / "pending_approval" / "brand-book"
        out_dir.mkdir(parents=True, exist_ok=True)
        ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        out = out_dir / f"{ts}_brand_book_{VERSION}.json"
        header = (f"LOOP: [brand-book] — report {VERSION} / "
                  f"GOAL brand-intelligence sign-off / METRIC eval-rubric-pass / "
                  f"MODE {self.mode} / EVAL {'PASS' if report['eval']['passed'] else 'FAIL'}")
        out.write_text(header + "\n---\n" + json.dumps(report, ensure_ascii=False, indent=2),
                       encoding="utf-8")
        return out

    def _render(self, report: dict) -> Path:
        try:
            from brand_book_renderer import render_brand_book
        except ImportError:
            from agents.brand_book_renderer import render_brand_book
        ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        out_pdf = (self.brand_dir / "outputs" / "pending_approval" / "brand-book"
                   / f"{ts}_brand_book_{VERSION}.pdf")
        palette = _palette_for(self.data["brand_profile"])
        return render_brand_book(report, palette, out_pdf)


# ── helpers ─────────────────────────────────────────────────────────────────────
_FILLER = (
    "in today's fast-paced", "in the ever-evolving", "navigating the landscape",
    "in conclusion", "it is important to note", "as an ai", "leverage synerg",
    "unlock the power", "in the realm of", "game-changer", "dive deep into",
)


def _has_filler(report: dict) -> bool:
    blob = json.dumps(report.get("parts", {}), ensure_ascii=False).lower()
    return any(f in blob for f in _FILLER)


def _coerce_json(raw: str, fallback_keys: tuple = ()) -> dict:
    """Best-effort parse of a model JSON block; never raises. On failure returns a
    dict carrying the raw text so the renderer can still show it (and eval fails the
    foundation check honestly rather than fabricating structure)."""
    s = (raw or "").strip()
    if "```" in s:
        for chunk in s.split("```"):
            c = chunk.strip()
            if c.startswith("json"):
                c = c[4:].strip()
            if c.startswith("{"):
                s = c
                break
    try:
        return json.loads(s)
    except Exception:
        return {"_unparsed": raw, **{k: None for k in fallback_keys}}


def _palette_for(bp: dict) -> dict:
    """Per-brand palette. Honors brand_profile.brand_colors when present; otherwise
    falls back to the two locked pilot palettes (memory: ask=cream/coral,
    offgrid=charcoal/amber). The report bg itself is always forced white (spec §5)."""
    colors = bp.get("brand_colors") or {}
    slug = bp.get("slug", "")
    if slug == "offgrid-creatives-ai":
        accent = colors.get("accent", "#d98a1f")  # amber
        ink = colors.get("ink", "#23211c")
    else:  # askgauravai + default
        accent = colors.get("accent", "#b23a2e")  # coral/brick
        ink = colors.get("ink", "#211d18")
    return {"accent": accent, "ink": ink, "paper": "#ffffff"}


if __name__ == "__main__":
    # Smoke: deterministic core only — NO API calls, NO cost.
    slug = sys.argv[1] if len(sys.argv) > 1 else "askgauravai"
    bb = BrandBook(slug, mode=MODE_COLD).load()
    print(f"loaded {slug}: profile={bool(bb.data['brand_profile'])} "
          f"trends={bool(bb.data['trends_live'])}")
    print("scorecard:", json.dumps(bb._scorecard(), ensure_ascii=False)[:300])
    print("benchmark(real):", benchmark(120, [80, 100, 140, 200, 60]))
    print("benchmark(insufficient):", benchmark(None, [80]))
