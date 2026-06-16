"""
Trend Researcher — OffGrid Marketing OS
Agent ID: 8 | Sequence position: 1 (always runs first)
Model: claude-sonnet-4-6
Rule 1: Zero assumptions. Real scrapes only. No scrape = no output.
Rule 9: AutoResearch Loop — Volume / Velocity / Gap variants before any output.
Writes to: brands/{slug}/trends_live.json
Pushes to: Notion via CEO Brain save_agent_output()
"""

import os
import sys
import json
import time
import requests
from datetime import datetime, timedelta
from dotenv import load_dotenv

# Add project root to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import anthropic
from ceo_brain.orchestrator import CEOBrain
from agents._lib import cost_reporter


load_dotenv(override=True)

APIFY_API_KEY = os.getenv("APIFY_API_KEY", "").strip()
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "").strip()
# Phase D — model sourced from the single-source-of-truth gateway
try:
    from agents._lib.model_gateway import model_for
    from agents._lib._untrusted import wrap as _untrusted_wrap, UNTRUSTED_POLICY as _UNTRUSTED_POLICY
except ImportError:
    from agents._lib.model_gateway import model_for
    from agents._lib._untrusted import wrap as _untrusted_wrap, UNTRUSTED_POLICY as _UNTRUSTED_POLICY
MODEL = model_for("trend-researcher")
WHISPER_CANDIDATES_CAP = 5

# ── BUILD B — DATA QUALITY GATE THRESHOLDS ──────────────────────────────────
# Tunable without code changes. All ratios are decimal fractions, not %.
QUALITY_GATE_THRESHOLDS = {
    # Engagement-pod signature: huge likes, almost no comments
    "engagement_pod_max_comment_like_ratio": 0.005,   # < 0.5%
    "engagement_pod_min_likes":              50_000,  # only flag at scale
    # Bought-views signature: huge views, anemic likes
    "bought_views_max_like_view_ratio":      0.01,    # < 1%
    "bought_views_min_views":                100_000, # only flag at scale
    # Bot-comment signature: most latestComments are extremely short (likely emoji-only)
    # Tuned Apr 25 — 60% was too aggressive (typical IG fire-emoji culture). Real bot/pod
    # patterns are ~85%+ identical-length emoji floods. Threshold raised to 0.85.
    "bot_comments_short_threshold_chars":    5,        # only count truly tiny comments (was 10)
    "bot_comments_short_share_max":          0.85,    # > 85% tiny = bot pattern (was 60%)
    "bot_comments_min_sample":               8,        # need at least 8 comments (was 5)
    # Paid-promo flag: post is wildly outsized vs account's own baseline
    "paid_promo_outlier_multiplier":         10.0,    # post engagement > 10× account avg
    # Bypass: if gate would drop > X share of posts, pass everything through
    "max_drop_share_before_bypass":          0.8,
}


def _escape_literal_newlines_in_strings(json_str: str) -> str:
    """
    Escape literal newline/tab/CR characters that appear inside JSON string
    values. Claude API sometimes emits these, breaking json.loads.
    Walks character-by-character so it only touches chars genuinely inside a string literal.
    """
    result = []
    in_string = False
    i = 0
    while i < len(json_str):
        c = json_str[i]
        if in_string:
            if c == '\\':
                result.append(c)
                i += 1
                if i < len(json_str):
                    result.append(json_str[i])
            elif c == '"':
                in_string = False
                result.append(c)
            elif c == '\n':
                result.append('\\n')
            elif c == '\r':
                result.append('\\r')
            elif c == '\t':
                result.append('\\t')
            else:
                result.append(c)
        else:
            if c == '"':
                in_string = True
            result.append(c)
        i += 1
    return ''.join(result)


def _safe_json_loads(raw: str):
    """
    Try json.loads; if it fails, attempt multiple repair strategies:
    1. Escape literal newlines inside string values
    2. Extract first complete JSON object/array (strip trailing garbage)
    3. Strip markdown code fences
    Raises original exception if all fail.
    """
    # Strategy 0: direct parse
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        pass

    # Strategy 1: strip markdown code fences
    stripped = raw.strip()
    if stripped.startswith("```"):
        lines = stripped.split("\n")
        # Remove first line (```json) and last line (```)
        if lines[-1].strip() == "```":
            stripped = "\n".join(lines[1:-1])
        else:
            stripped = "\n".join(lines[1:])
        try:
            return json.loads(stripped)
        except json.JSONDecodeError:
            pass

    # Strategy 2: escape literal newlines
    repaired = _escape_literal_newlines_in_strings(raw)
    try:
        return json.loads(repaired)
    except json.JSONDecodeError:
        pass

    # Strategy 3: extract first complete JSON object/array via decoder
    decoder = json.JSONDecoder()
    text = raw.strip()
    # Find start of JSON
    for i, c in enumerate(text):
        if c in ('{', '['):
            try:
                obj, end = decoder.raw_decode(text, i)
                return obj
            except json.JSONDecodeError:
                continue

    # Strategy 4: same as 3 but on newline-repaired text
    repaired_stripped = repaired.strip()
    for i, c in enumerate(repaired_stripped):
        if c in ('{', '['):
            try:
                obj, end = decoder.raw_decode(repaired_stripped, i)
                return obj
            except json.JSONDecodeError:
                continue

    # All strategies failed — raise with original text
    return json.loads(raw)

def _build_niche_hashtags(brand_profile: dict) -> list:
    """
    Generate relevant Instagram hashtags from brand profile fields.
    Falls back to generic D2C/brand-building hashtags if no specific category detected.
    """
    industry   = (brand_profile.get("industry") or "").lower()
    product    = (brand_profile.get("product") or brand_profile.get("product_description") or "").lower()
    audience   = (brand_profile.get("target_audience") or "").lower()
    competitor_handles = brand_profile.get("competitor_handles", [])

    hashtags = set()

    # Fashion / apparel signals
    if any(kw in product + industry for kw in ["fashion", "shirt", "tee", "apparel", "clothing",
                                                 "wear", "outfit", "ethnic", "kurta", "saree",
                                                 "streetwear", "hoodie"]):
        hashtags.update(["indianfashion", "streetwearindia", "graphictee", "indiantshirts",
                          "ootdindia", "casualwear", "youthfashion", "fashionblogger"])
        if "ethnic" in product + industry:
            hashtags.update(["ethnicwear", "indianwear", "traditionalfashion", "ethnicfashion"])
        if any(kw in product for kw in ["tee", "shirt", "graphic"]):
            hashtags.update(["graphictshirt", "tshirtdesign", "tshirtlovers", "streetstyle"])

    # SaaS / AI / tech signals
    elif any(kw in product + industry for kw in ["saas", "ai ", "software", "tool", "platform",
                                                   "marketing os", "dashboard", "automation"]):
        hashtags.update(["saas", "aimarketing", "d2cmarketing", "performancemarketing",
                          "contentmarketing", "marketingstrategy", "brandstrategy",
                          "digitalmarketing", "metacads", "facebookads"])

    # Food / beverage signals
    elif any(kw in product + industry for kw in ["food", "restaurant", "cafe", "snack",
                                                   "beverage", "drink", "eat"]):
        hashtags.update(["indianfood", "foodstagram", "homechef", "foodblogger",
                          "foodlovers", "d2cfood", "healthyfood"])

    # Beauty / skincare signals
    elif any(kw in product + industry for kw in ["skincare", "beauty", "cosmetic", "makeup",
                                                   "grooming", "hair"]):
        hashtags.update(["skincare", "beautyindia", "indianskincare", "naturalskincare",
                          "beautyproducts", "skincarelovers", "selfcare"])

    # Fitness / health
    elif any(kw in product + industry for kw in ["fitness", "gym", "health", "wellness",
                                                   "supplement", "protein", "yoga"]):
        hashtags.update(["fitnessindia", "gymlife", "healthylifestyle", "fitfam",
                          "wellness", "indiafit", "gymwear"])

    # Generic D2C fallback
    if len(hashtags) < 5:
        hashtags.update(["d2cmarketing", "brandstrategy", "contentmarketing",
                          "digitalmarketing", "socialmedia", "instagrammarketing",
                          "growthmarketing", "entrepreneurindia", "startupindia",
                          "smallbusiness"])

    # Always add competitor handles as hashtags if available
    for handle in competitor_handles[:4]:
        clean = handle.lstrip("@").lower().replace(" ", "")
        if clean:
            hashtags.add(clean)

    return sorted(hashtags)[:12]


def _build_trend_keywords(brand_profile: dict) -> list:
    """
    Build Google Trends seed keywords from brand profile.
    Returns 5 relevant keywords for the brand's niche.
    """
    industry   = (brand_profile.get("industry") or "").lower()
    product    = (brand_profile.get("product") or brand_profile.get("product_description") or "").lower()
    brand_name = brand_profile.get("brand_name", "")

    # Fashion / apparel
    if any(kw in product + industry for kw in ["fashion", "shirt", "tee", "apparel",
                                                 "clothing", "wear", "ethnic", "streetwear"]):
        if any(kw in product for kw in ["tee", "shirt", "graphic"]):
            return ["graphic tshirts India", "streetwear brand India",
                    "Gen Z fashion India", "affordable t shirts online",
                    "Indian streetwear"]
        return ["Indian fashion brand", "ethnic wear online India",
                "women fashion India", "D2C fashion brand India",
                "fast fashion India"]

    # SaaS / AI / marketing
    elif any(kw in product + industry for kw in ["saas", "ai ", "software",
                                                   "marketing", "automation"]):
        return ["Meta ads", "Facebook ads ROI", "D2C brand",
                "ad intelligence", "ecommerce ads India"]

    # Food
    elif any(kw in product + industry for kw in ["food", "restaurant", "snack", "beverage"]):
        return ["Indian food brand", "D2C food India",
                "healthy snacks India", "food startup India",
                "gourmet food online India"]

    # Beauty / skincare
    elif any(kw in product + industry for kw in ["skincare", "beauty", "cosmetic", "makeup"]):
        return ["Indian skincare brand", "clean beauty India",
                "skincare routine India", "D2C beauty brand",
                "organic skincare India"]

    # Generic fallback
    return ["D2C brand India", "Indian startup", "ecommerce India",
            "social media marketing India", "content marketing India"]


def competitor_metrics_from_profiles(competitors: dict) -> list[dict]:
    """G3/G5 — deterministic REAL competitor engagement metrics from scraped
    competitor profiles (apify~instagram-scraper output, as built by
    scrape_competitor_profiles). Single source of truth so run() and the pilot
    competitor-scrape driver emit the identical competitor_metrics shape.
    avg_engagement = avg likes + avg comments per post (a real measured number)."""
    out: list[dict] = []
    for handle, c in (competitors or {}).items():
        if not isinstance(c, dict) or c.get("status") != "OK":
            continue
        al = c.get("avg_likes", 0) or 0
        ac = c.get("avg_comments", 0) or 0
        out.append({
            "handle": handle,
            "avg_likes": al,
            "avg_comments": ac,
            "avg_engagement": round(al + ac, 1),
            "posts_scraped": c.get("posts_scraped", 0),
        })
    return out


class TrendResearcher:

    def __init__(self, brand_slug: str = None):
        # Read brand slug from env var first, then fall back to argument, then to default
        self.brand_slug = brand_slug or os.getenv("ACTIVE_BRAND", "offgrid-creatives-ai")
        self.scraped_at = datetime.utcnow().isoformat()
        self.log(f"Initialising Trend Researcher for brand: {self.brand_slug}")

        # Boot CEO Brain — loads brand profile, verifies Notion
        self.ceo = CEOBrain()
        self.brand_profile = self.ceo.brand_profile
        self.brand_name = self.brand_profile.get("brand_name") or self.brand_slug

        # Build brand-specific hashtags and trend keywords from profile
        self.niche_hashtags   = _build_niche_hashtags(self.brand_profile)
        self.trend_keywords   = _build_trend_keywords(self.brand_profile)

        # Anthropic client — explicit key with strip() to remove trailing whitespace
        if not ANTHROPIC_API_KEY:
            raise ValueError("ANTHROPIC_API_KEY not found in .env — cannot run AutoResearch Loop")
        self.client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

        self.log(f"Ready. Brand: {self.brand_name}")
        self.log(f"Hashtags: {self.niche_hashtags}")
        self.log(f"Trend keywords: {self.trend_keywords}")
        self._total_input_tokens = 0
        self._total_output_tokens = 0
        self._apify_runs = 0

    def log(self, message: str):
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        print(f"[Trend Researcher | {timestamp}] {message}")

    # -------------------------------------------------------------------------
    # APIFY HELPERS
    # -------------------------------------------------------------------------

    def apify_start_run(self, actor_id: str, input_body: dict) -> str | None:
        """Start an Apify actor run. Returns run ID or None on failure."""
        # Cost circuit-breaker: refuse paid Apify spend when the kill-switch is off
        # or the daily cap is hit. Fail-closed (block) if the breaker can't load.
        try:
            from agents._lib import paid_ops
            _ok, _reason = paid_ops.check(f"apify:{actor_id}")
        except Exception as _e:
            _ok, _reason = False, f"paid_ops unavailable ({_e})"
        if not _ok:
            self.log(f"⛔ paid-ops: Apify run blocked [{actor_id}] — {_reason}")
            return None
        url = f"https://api.apify.com/v2/acts/{actor_id}/runs?token={APIFY_API_KEY}"
        try:
            response = requests.post(url, json=input_body, timeout=30)
            if response.status_code == 201:
                run_id = response.json()["data"]["id"]
                self.log(f"Apify run started [{actor_id}] → run ID: {run_id}")
                self._apify_runs += 1
                return run_id
            else:
                self.log(f"ERROR: Apify start failed [{actor_id}] — {response.status_code}: {response.text[:200]}")
                return None
        except Exception as e:
            self.log(f"ERROR: Apify request exception — {e}")
            return None

    def apify_fetch_results(self, run_id: str, limit: int = 50) -> list:
        """Fetch dataset items from a completed Apify run."""
        url = (
            f"https://api.apify.com/v2/actor-runs/{run_id}/dataset/items"
            f"?token={APIFY_API_KEY}&limit={limit}"
        )
        try:
            response = requests.get(url, timeout=30)
            if response.status_code == 200:
                items = response.json()
                self.log(f"Apify results fetched — {len(items)} items")
                return items
            else:
                self.log(f"ERROR: Apify fetch failed — {response.status_code}")
                return []
        except Exception as e:
            self.log(f"ERROR: Apify fetch exception — {e}")
            return []

    # -------------------------------------------------------------------------
    # DATA SOURCE: Instagram Hashtags (Apify)
    # -------------------------------------------------------------------------

    def scrape_instagram_hashtags(self) -> dict:
        """
        Scrape Instagram posts by hashtag for the brand's niche.
        Uses apify/instagram-hashtag-scraper.
        Waits 120 seconds (same as Make.com pipeline).
        """
        self.log(f"Scraping Instagram hashtags for niche: {self.niche_hashtags}...")

        tags = self.niche_hashtags[:5]

        # ── Phase E2: scrape cache — skip Apify cost + 120s wait on a fresh hit ──
        try:
            from utils import scrape_cache as _cache
            cached = _cache.get(self.brand_slug, "ig_hashtags", tags, ttl_hours=24.0)
            if cached:
                self.log("Using cached IG hashtag scrape (<24h old) — no Apify call")
                return cached
        except Exception as _ce:
            self.log(f"scrape_cache check skipped: {_ce}")

        # ── Phase E3: official IG Hashtag Search API (off by default; Apify fallback) ──
        try:
            from agents import ig_hashtag_search as _ighs
        except ImportError:
            import agents.intel.ig_hashtag_search as _ighs  # script-context
        if _ighs.enabled():
            api_res = _ighs.scrape_hashtags(tags)
            if api_res.get("status") == "OK":
                self.log(f"IG Hashtag API returned {api_res['posts_scraped']} posts (no Apify, no ban risk)")
                try:
                    from utils import scrape_cache as _cache
                    _cache.put(self.brand_slug, "ig_hashtags", tags, api_res, ttl_hours=24.0)
                except Exception:
                    pass
                return api_res
            self.log(f"IG Hashtag API unavailable ({api_res.get('error')}) — falling back to Apify")

        if not APIFY_API_KEY:
            return {"status": "FAILED", "error": "APIFY_API_KEY not set"}

        run_id = self.apify_start_run(
            actor_id="apify~instagram-hashtag-scraper",
            input_body={
                "hashtags": tags,
                "resultsLimit": 30
            }
        )

        if not run_id:
            return {"status": "FAILED", "error": "Apify run could not be started"}

        self.log("Waiting 120s for hashtag scraper...")
        time.sleep(120)

        items = self.apify_fetch_results(run_id, limit=50)

        if not items:
            return {"status": "FAILED", "error": "No items returned from hashtag scraper"}

        # Extract top hooks and post data
        top_posts = []
        for post in items[:20]:
            caption = (post.get("caption") or "")[:300]
            # Preserve latestComments (Build B — bot-comment signature check)
            latest_comments = []
            for c in (post.get("latestComments") or [])[:12]:
                if isinstance(c, dict):
                    latest_comments.append({
                        "text": (c.get("text") or "")[:200],
                        "ownerUsername": c.get("ownerUsername", "")
                    })
            top_posts.append({
                "caption_snippet": caption,
                "likes": post.get("likesCount", 0),
                "comments": post.get("commentsCount", 0),
                "videoViewCount": post.get("videoViewCount", 0) or 0,
                "type": post.get("type", "unknown"),
                "hashtags": (post.get("hashtags") or [])[:5],
                "owner_username": post.get("ownerUsername", ""),
                "url": post.get("url", ""),
                "timestamp": post.get("timestamp", ""),
                "latestComments": latest_comments,
            })

        # Sort by engagement
        top_posts.sort(key=lambda x: x["likes"] + x["comments"], reverse=True)

        result = {
            "status": "OK",
            "posts_scraped": len(items),
            "top_posts": top_posts[:10],
            "hashtags_scraped": tags,
            "source": "apify",
        }

        # Phase E2: cache the fresh Apify scrape so the next run (within 24h) is free.
        try:
            from utils import scrape_cache as _cache
            _cache.put(self.brand_slug, "ig_hashtags", tags, result, ttl_hours=24.0)
        except Exception:
            pass

        return result

    # -------------------------------------------------------------------------
    # DATA SOURCE: Brand's Own Instagram Posts (Apify)
    # -------------------------------------------------------------------------

    def scrape_brand_instagram(self) -> dict:
        """
        Scrape the brand's own Instagram profile to understand baseline performance.
        Uses apify/instagram-scraper with directUrls (instagram-post-scraper is deprecated — returns 0 posts).
        Waits 90 seconds per apify-strategy skill rules.
        """
        # Support both top-level instagram_handle and nested accounts.instagram_handle
        handle = (
            self.brand_profile.get("instagram_handle")
            or self.brand_profile.get("accounts", {}).get("instagram_handle", "")
        )
        if not handle:
            return {"status": "SKIPPED", "reason": "No Instagram handle in brand_profile.json"}

        handle_clean = handle.replace("@", "").strip()
        self.log(f"Scraping brand Instagram: @{handle_clean}")

        if not APIFY_API_KEY:
            return {"status": "FAILED", "error": "APIFY_API_KEY not set"}

        run_id = self.apify_start_run(
            actor_id="apify~instagram-scraper",
            input_body={
                "directUrls": [f"https://www.instagram.com/{handle_clean}/"],
                "resultsType": "posts",
                "resultsLimit": 20
            }
        )

        if not run_id:
            return {"status": "FAILED", "error": "Apify run could not be started"}

        self.log("Waiting 90s for brand profile scraper...")
        time.sleep(90)

        items = self.apify_fetch_results(run_id, limit=20)

        if not items:
            return {
                "status": "OK",
                "posts_scraped": 0,
                "posts": [],
                "note": "Brand account may have no posts yet or is private"
            }

        posts = []
        for post in items:
            posts.append({
                "caption_snippet": (post.get("caption") or "")[:300],
                "likes": post.get("likesCount", 0),
                "comments": post.get("commentsCount", 0),
                "timestamp": post.get("timestamp", ""),
                "type": post.get("type", "unknown")
            })

        avg_likes = sum(p["likes"] for p in posts) / len(posts) if posts else 0
        avg_comments = sum(p["comments"] for p in posts) / len(posts) if posts else 0

        return {
            "status": "OK",
            "posts_scraped": len(items),
            "avg_likes": round(avg_likes, 1),
            "avg_comments": round(avg_comments, 1),
            "posts": posts
        }

    # -------------------------------------------------------------------------
    # DATA SOURCE: Competitor Instagram Profiles (Apify)
    # -------------------------------------------------------------------------

    def _load_competitor_handles(self) -> list[str]:
        """
        Collect competitor handles from two sources (deduplicated):
          1. brand_profile.json competitor_handles list
          2. brands/{slug}/competitors_db.json (written by Strategy Agent) — reads
             top-level list OR list of objects with an "instagram_handle" / "handle" key
        Returns clean handles (no @ prefix, lowercase).
        """
        handles: list[str] = []

        # Source 1 — brand_profile
        for h in self.brand_profile.get("competitor_handles", []):
            clean = h.replace("@", "").strip().lower()
            if clean and clean not in handles:
                handles.append(clean)

        # Source 2 — competitors_db.json (Strategy Agent output)
        project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        db_path = os.path.join(project_root, "brands", self.brand_slug, "competitors_db.json")
        if os.path.exists(db_path):
            try:
                with open(db_path) as f:
                    db = json.load(f)
                entries = db if isinstance(db, list) else db.get("competitors", [])
                for entry in entries:
                    if isinstance(entry, str):
                        h = entry.replace("@", "").strip().lower()
                    elif isinstance(entry, dict):
                        h = (
                            entry.get("instagram_handle")
                            or entry.get("handle")
                            or entry.get("instagram")
                            or ""
                        ).replace("@", "").strip().lower()
                    else:
                        continue
                    if h and h not in handles:
                        handles.append(h)
            except Exception as e:
                self.log(f"WARNING: Could not read competitors_db.json — {e}")

        return handles

    def scrape_competitor_profiles(self) -> dict:
        """
        Scrape top posts from each competitor's Instagram profile.
        Uses apify/instagram-scraper with directUrls — the only actor that returns real posts.
        Runs one Apify job per competitor handle (max 5 handles).
        Waits 90s per run per apify-strategy skill rules.

        Returns:
          {
            "status": "OK" | "SKIPPED" | "PARTIAL" | "FAILED",
            "handles_attempted": [...],
            "competitors": {
              "handle": {
                "status": "OK" | "FAILED",
                "posts_scraped": N,
                "top_posts": [...],
                "avg_likes": N,
                "avg_comments": N,
                "formats_used": [...],
                "top_hashtags": [...]
              }
            }
          }
        """
        handles = self._load_competitor_handles()

        if not handles:
            return {
                "status": "SKIPPED",
                "reason": "No competitor handles found in brand_profile.json or competitors_db.json"
            }

        if not APIFY_API_KEY:
            return {"status": "FAILED", "error": "APIFY_API_KEY not set"}

        # Cap at 5 competitors to keep runtime reasonable
        handles = handles[:5]
        self.log(f"Scraping {len(handles)} competitor profiles: {handles}")

        # Start all runs first, then wait once, then fetch all
        run_ids: dict[str, str] = {}  # handle → run_id
        for handle in handles:
            run_id = self.apify_start_run(
                actor_id="apify~instagram-scraper",
                input_body={
                    "directUrls": [f"https://www.instagram.com/{handle}/"],
                    "resultsType": "posts",
                    "resultsLimit": 20
                }
            )
            if run_id:
                run_ids[handle] = run_id
            else:
                self.log(f"WARNING: Could not start Apify run for @{handle} — skipping")

        if not run_ids:
            return {"status": "FAILED", "error": "All competitor Apify runs failed to start"}

        # Single 90s wait covers all parallel runs
        self.log(f"Waiting 90s for {len(run_ids)} competitor scraper(s) to complete...")
        time.sleep(90)

        competitors: dict[str, dict] = {}
        ok_count = 0

        for handle, run_id in run_ids.items():
            items = self.apify_fetch_results(run_id, limit=20)

            if not items:
                competitors[handle] = {
                    "status": "FAILED",
                    "posts_scraped": 0,
                    "top_posts": [],
                    "note": "No data returned — account may be private or rate-limited"
                }
                continue

            posts = []
            formats: set[str] = set()
            hashtags_seen: list[str] = []

            for post in items:
                likes    = post.get("likesCount", 0) or 0
                comments = post.get("commentsCount", 0) or 0
                views    = post.get("videoViewCount", 0) or 0
                ptype    = post.get("type", "unknown")
                formats.add(ptype)
                for tag in (post.get("hashtags") or [])[:5]:
                    if tag and tag not in hashtags_seen:
                        hashtags_seen.append(tag)
                # Preserve latestComments (Build B — bot-comment signature check)
                latest_comments = []
                for c in (post.get("latestComments") or [])[:12]:
                    if isinstance(c, dict):
                        latest_comments.append({
                            "text": (c.get("text") or "")[:200],
                            "ownerUsername": c.get("ownerUsername", "")
                        })
                posts.append({
                    "caption_snippet": (post.get("caption") or "")[:300],
                    "likes": likes,
                    "comments": comments,
                    "videoViewCount": views,
                    "type": ptype,
                    "timestamp": post.get("timestamp", ""),
                    "hashtags": (post.get("hashtags") or [])[:5],
                    "url": post.get("url", ""),
                    "owner_username": handle,
                    "latestComments": latest_comments,
                })

            # Sort by engagement descending
            posts.sort(key=lambda p: p["likes"] + p["comments"], reverse=True)

            avg_likes    = sum(p["likes"] for p in posts) / len(posts) if posts else 0
            avg_comments = sum(p["comments"] for p in posts) / len(posts) if posts else 0

            # Top hashtags by frequency
            from collections import Counter
            hashtag_counts = Counter(
                tag
                for p in posts
                for tag in p["hashtags"]
            )
            top_hashtags = [tag for tag, _ in hashtag_counts.most_common(8)]

            competitors[handle] = {
                "status": "OK",
                "posts_scraped": len(items),
                "avg_likes": round(avg_likes, 1),
                "avg_comments": round(avg_comments, 1),
                "formats_used": sorted(formats),
                "top_hashtags": top_hashtags,
                "top_posts": posts[:5]  # top 5 by engagement sent to Claude
            }
            ok_count += 1
            self.log(f"  @{handle}: {len(items)} posts, avg {avg_likes:.0f} likes, formats: {sorted(formats)}")

        overall_status = (
            "OK" if ok_count == len(handles)
            else "PARTIAL" if ok_count > 0
            else "FAILED"
        )

        return {
            "status": overall_status,
            "handles_attempted": handles,
            "handles_ok": ok_count,
            "competitors": competitors
        }

    # -------------------------------------------------------------------------
    # DATA SOURCE: Google Trends (PyTrends — no API key needed)
    # -------------------------------------------------------------------------

    def scrape_google_trends(self) -> dict:
        """
        Scrape Google Trends for keywords relevant to this brand's niche.
        Uses pytrends (no API key required).
        Fails gracefully if pytrends not installed.
        """
        self.log("Scraping Google Trends (pytrends)...")

        try:
            from pytrends.request import TrendReq
        except ImportError:
            return {
                "status": "FAILED",
                "error": "pytrends not installed. Fix: pip install pytrends"
            }

        try:
            pytrends = TrendReq(hl="en-US", tz=330)  # IST timezone

            keywords = self.trend_keywords

            pytrends.build_payload(keywords, timeframe="now 7-d", geo="IN")

            # Rising keywords
            related = pytrends.related_queries()
            rising_keywords = []
            for kw in keywords:
                if kw in related and related[kw].get("rising") is not None:
                    rising_df = related[kw]["rising"]
                    if not rising_df.empty:
                        for _, row in rising_df.head(3).iterrows():
                            rising_keywords.append({
                                "seed_keyword": kw,
                                "rising_query": row.get("query", ""),
                                "value": int(row.get("value", 0))
                            })

            # Current interest levels
            interest_df = pytrends.interest_over_time()
            top_keywords = []
            if not interest_df.empty:
                last_row = interest_df.iloc[-1]
                for kw in keywords:
                    if kw in last_row:
                        top_keywords.append({
                            "keyword": kw,
                            "interest_score": int(last_row[kw])
                        })
                top_keywords.sort(key=lambda x: x["interest_score"], reverse=True)

            return {
                "status": "OK",
                "rising_keywords": rising_keywords[:10],
                "top_keywords": top_keywords
            }

        except Exception as e:
            return {"status": "FAILED", "error": str(e)}

    # -------------------------------------------------------------------------
    # DATA SOURCE: YouTube Shorts (Apify)
    # -------------------------------------------------------------------------

    def scrape_youtube_shorts(self) -> list:
        """
        Scrape YouTube Shorts for brand niche keywords.
        Uses apify/youtube-scraper. Graceful skip on any failure.
        Returns list of post dicts or [] on failure.
        """
        if not APIFY_API_KEY:
            self.log("YouTube Shorts: SKIPPED — no APIFY_API_KEY")
            return []

        keywords = self.trend_keywords[:3]
        self.log(f"Scraping YouTube Shorts for: {keywords}")

        try:
            run_id = self.apify_start_run(
                actor_id="apify~youtube-scraper",
                input_body={
                    "searchKeywords": keywords,
                    "type": "shorts",
                    "datePublishedAfter": (datetime.utcnow() - timedelta(days=7)).strftime("%Y-%m-%d"),
                    "maxItems": 30,
                }
            )
            if not run_id:
                self.log("YouTube Shorts: Apify run failed to start — SKIPPED")
                return []

            self.log("Waiting 90s for YouTube Shorts scraper...")
            time.sleep(90)
            items = self.apify_fetch_results(run_id, limit=30)

            posts = []
            for item in items:
                posts.append({
                    "caption_snippet": (item.get("title") or "")[:300],
                    "likes": int(item.get("likes", 0) or 0),
                    "comments": int(item.get("commentsCount", 0) or 0),
                    "videoViewCount": int(item.get("viewCount", 0) or 0),
                    "platform": "youtube",
                    "url": item.get("url", ""),
                    "timestamp": item.get("publishedAt", ""),
                })

            self.log(f"YouTube Shorts: {len(posts)} shorts scraped")
            return posts

        except Exception as e:
            self.log(f"YouTube Shorts: SKIPPED — exception: {e}")
            return []

    # -------------------------------------------------------------------------
    # DATA SOURCE: Twitter/X (Apify)
    # -------------------------------------------------------------------------

    def scrape_twitter(self) -> list:
        """
        Scrape Twitter/X for brand niche keywords.
        Uses apify/twitter-scraper. Graceful skip on any failure.
        Returns list of post dicts or [] on failure.
        """
        if not APIFY_API_KEY:
            self.log("Twitter/X: SKIPPED — no APIFY_API_KEY")
            return []

        keywords = self.trend_keywords[:3]
        self.log(f"Scraping Twitter/X for: {keywords}")

        try:
            run_id = self.apify_start_run(
                actor_id="apify~twitter-scraper",
                input_body={
                    "searchTerms": keywords,
                    "maxTweets": 30,
                    "since": (datetime.utcnow() - timedelta(days=7)).strftime("%Y-%m-%d"),
                    "lang": "en",
                }
            )
            if not run_id:
                self.log("Twitter/X: Apify run failed to start — SKIPPED")
                return []

            self.log("Waiting 60s for Twitter scraper...")
            time.sleep(60)
            items = self.apify_fetch_results(run_id, limit=30)

            posts = []
            for item in items:
                posts.append({
                    "caption_snippet": (item.get("text") or item.get("full_text") or "")[:300],
                    "likes": int(item.get("favorite_count", 0) or 0),
                    "comments": int(item.get("reply_count", 0) or 0),
                    "platform": "twitter",
                    "url": item.get("url", ""),
                    "timestamp": item.get("created_at", ""),
                    "hashtags": item.get("hashtags", []),
                })

            self.log(f"Twitter/X: {len(posts)} tweets scraped")
            return posts

        except Exception as e:
            self.log(f"Twitter/X: SKIPPED — exception: {e}")
            return []

    # -------------------------------------------------------------------------
    # WHISPER TRANSCRIPT EXTRACTION
    # -------------------------------------------------------------------------

    def _extract_whisper_transcripts(self) -> None:
        """
        Extract audio transcripts from top video posts using Whisper.
        Requires: pip install openai-whisper yt-dlp
        Fully graceful skip if not installed or any post fails.
        Mutates self._whisper_candidates in-place — adds 'whisper_transcript' field.
        """
        if not self._whisper_candidates:
            return

        try:
            import whisper  # type: ignore
        except ImportError:
            self.log("Whisper: SKIPPED — openai-whisper not installed (pip install openai-whisper)")
            return

        try:
            import yt_dlp  # type: ignore
        except ImportError:
            self.log("Whisper: SKIPPED — yt-dlp not installed (pip install yt-dlp)")
            return

        import tempfile

        self.log(f"Whisper: Loading base model... (first run downloads ~140MB)")
        try:
            model = whisper.load_model("base")
        except Exception as e:
            self.log(f"Whisper: SKIPPED — could not load model: {e}")
            return

        for i, post in enumerate(self._whisper_candidates):
            url = post.get("url", "")
            if not url:
                continue

            self.log(f"Whisper [{i+1}/{len(self._whisper_candidates)}]: Transcribing {url[:60]}...")

            try:
                with tempfile.TemporaryDirectory() as tmpdir:
                    ydl_opts = {
                        "format": "bestaudio/best",
                        "outtmpl": f"{tmpdir}/audio.%(ext)s",
                        "quiet": True,
                        "no_warnings": True,
                        "extract_flat": False,
                    }
                    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                        ydl.download([url])

                    # Find the downloaded file
                    import os as _os
                    audio_files = [f for f in _os.listdir(tmpdir) if f.startswith("audio.")]
                    if not audio_files:
                        self.log(f"  Whisper: no audio file found for {url[:40]}")
                        continue

                    audio_path = f"{tmpdir}/{audio_files[0]}"
                    result = model.transcribe(audio_path, language="en", fp16=False)
                    transcript = result.get("text", "").strip()[:500]
                    post["whisper_transcript"] = transcript
                    self.log(f"  Whisper: transcript extracted ({len(transcript)} chars)")

            except Exception as e:
                self.log(f"  Whisper: FAILED for {url[:40]} — {e}")
                continue

        self.log("Whisper extraction complete.")

    # -------------------------------------------------------------------------
    # POST SCORING
    # -------------------------------------------------------------------------

    def _score_posts(self, scraped_data: dict) -> list:
        """
        Score all scraped posts across Instagram, YouTube, Twitter.
        Formula: Views×0.4 + ER×0.35 + Comments×0.25 (for video posts)
                 Likes×0.6 + Comments×0.4 (for photo posts)
        Hard filters: drop if (likes+comments) < 10K OR ER < 2% (where calculable) OR age > 30 days
        Flags: HIGH_SIGNAL if views > 100K, VIRAL if ER > 5%
        Builds self._whisper_candidates (max 5) — HIGH_SIGNAL/VIRAL posts with videoUrl
        """
        all_posts = []
        now = datetime.utcnow()
        cutoff = now - timedelta(days=30)

        def _parse_ts(ts_str):
            if not ts_str:
                return None
            for fmt in ("%Y-%m-%dT%H:%M:%S.%fZ", "%Y-%m-%dT%H:%M:%SZ", "%Y-%m-%d"):
                try:
                    return datetime.strptime(ts_str[:19], fmt[:len(ts_str[:19])])
                except Exception:
                    pass
            return None

        # BUILD C — Load this brand's winning-topic tokens ONCE for boost lookup
        winning_tokens = self._load_winning_topics()
        if winning_tokens:
            self.log(f"Performance feedback ACTIVE — {len(winning_tokens)} winning-topic tokens will boost matching trends")
        else:
            self.log("Performance feedback: no history yet (first run on this brand) — no boosts applied")

        def _collect(posts, platform):
            for p in (posts or []):
                if not isinstance(p, dict):
                    continue
                likes    = int(p.get("likes", 0) or 0)
                comments = int(p.get("comments", 0) or 0)
                views    = int(p.get("videoViewCount", p.get("views", 0)) or 0)
                url      = p.get("url", "")
                ts       = _parse_ts(p.get("timestamp", ""))

                # Age filter
                if ts and ts < cutoff:
                    continue

                # Engagement filter
                engagement = likes + comments
                if engagement < 10000 and platform == "instagram":
                    continue  # Instagram posts below 10K total are noise

                # ER calculation
                er = 0.0
                if views > 0:
                    er = (likes + comments) / views * 100
                elif likes > 0:
                    er = 100.0  # photo with no views — assume 100% ER (likes/likes)

                # Hard ER filter (only apply when views are available)
                if views > 0 and er < 2.0:
                    continue

                # Score
                if views > 0:
                    score = views * 0.4 + er * 0.35 + comments * 0.25
                else:
                    score = likes * 0.6 + comments * 0.4

                # BUILD C — historical_winner_boost (+20 if post text matches past winning topics)
                historical_winner_boost = 0
                history_match_tokens: list = []
                if winning_tokens:
                    import re as _re
                    post_text = " ".join([
                        str(p.get("caption_snippet", "")),
                        str(p.get("topic", "")),
                    ]).lower()
                    post_tokens = set(t for t in _re.split(r"[^a-z0-9]+", post_text) if len(t) >= 3)
                    history_match_tokens = sorted(post_tokens & winning_tokens)
                    if history_match_tokens:
                        historical_winner_boost = 20  # flat boost — calibrated, deterministic
                        score += historical_winner_boost

                # Flags
                flags = []
                if views > 100000:
                    flags.append("HIGH_SIGNAL")
                if er > 5.0:
                    flags.append("VIRAL")
                if historical_winner_boost:
                    flags.append("HISTORICAL_WINNER")

                all_posts.append({
                    **p,
                    "platform": platform,
                    "score": round(score, 2),
                    "er": round(er, 2),
                    "flags": flags,
                    "historical_winner_boost": historical_winner_boost,
                    "history_match_tokens": history_match_tokens[:5],  # cap for output size
                })

        # Collect Instagram hashtag posts
        ig_hashtags = scraped_data.get("instagram_hashtag_scrape", {})
        _collect(ig_hashtags.get("top_posts", []), "instagram")

        # Collect competitor posts
        ig_comp = scraped_data.get("instagram_competitor_profiles", {})
        for handle_data in ig_comp.get("competitors", {}).values():
            _collect(handle_data.get("top_posts", []), "instagram")

        # Collect YouTube Shorts
        _collect(scraped_data.get("youtube_shorts_raw", []), "youtube")

        # Collect Twitter
        _collect(scraped_data.get("twitter_raw", []), "twitter")

        # Sort by score descending
        all_posts.sort(key=lambda x: x["score"], reverse=True)

        # Build whisper candidates (video posts with HIGH_SIGNAL or VIRAL flag, max 5)
        self._whisper_candidates = [
            p for p in all_posts
            if p.get("url") and ("HIGH_SIGNAL" in p["flags"] or "VIRAL" in p["flags"])
        ][:WHISPER_CANDIDATES_CAP]

        self.log(f"_score_posts: {len(all_posts)} posts survived filters. {len(self._whisper_candidates)} whisper candidates.")
        return all_posts

    # -------------------------------------------------------------------------
    # BUILD B — DATA QUALITY GATE
    # -------------------------------------------------------------------------

    # -------------------------------------------------------------------------
    # BUILD C — PERFORMANCE FEEDBACK LOOP (historical winner boost)
    # -------------------------------------------------------------------------

    def _load_winning_topics(self) -> set:
        """
        Pure deterministic. Reads performance_history.json and returns a flat set of
        token-strings from the brand's PROVEN winning topics + hook_patterns.
        Used by _score_posts() to BOOST trends that match past winners (+20 score).
        Returns empty set if no history exists yet (first run on new brand).
        """
        project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        history_path = os.path.join(project_root, "brands", self.brand_slug, "performance_history.json")
        if not os.path.exists(history_path):
            return set()
        try:
            with open(history_path) as f:
                history = json.load(f)
        except Exception:
            return set()

        winning = history.get("winning_patterns", {}) or {}
        token_pool: set = set()
        # Pull tokens from top topics + top hook patterns
        for category in ("topic_clusters_top_3", "hook_patterns_top_3"):
            for entry in winning.get(category, []) or []:
                v = entry.get("value", "") if isinstance(entry, dict) else str(entry)
                # Tokenize: lowercase, split on non-word, keep tokens ≥3 chars
                import re as _re
                tokens = _re.split(r"[^a-z0-9]+", v.lower())
                token_pool.update(t for t in tokens if len(t) >= 3)
        return token_pool

    def _quality_gate(self, scored_posts: list, scraped_data: dict) -> tuple[list, dict]:
        """
        Filter out posts that look like engagement pods, bought views, or bot-comment-flooded.
        Flag (don't drop) posts that look like paid promos relative to the account's baseline.

        Each surviving post gets a `trust_score` (0-100) and `trust_signals` array.

        Returns:
          (clean_posts, gate_report)
            clean_posts: list of posts that passed (or all if bypass triggered)
            gate_report: dict with counts + drop reasons + flagged urls (saved into trends_live.json)
        """
        T = QUALITY_GATE_THRESHOLDS

        # Build account baseline lookup: handle → avg engagement (likes + comments)
        account_baseline: dict[str, float] = {}
        ig_comp = scraped_data.get("instagram_competitor_profiles", {})
        for handle, data in ig_comp.get("competitors", {}).items():
            if data.get("status") == "OK":
                avg_eng = float(data.get("avg_likes", 0) or 0) + float(data.get("avg_comments", 0) or 0)
                if avg_eng > 0:
                    account_baseline[handle.lower()] = avg_eng

        # Brand's own posts baseline
        ig_brand = scraped_data.get("instagram_brand_posts", {})
        brand_handle = (
            self.brand_profile.get("instagram_handle", "")
            .replace("@", "").strip().lower()
        )
        if brand_handle and ig_brand.get("status") == "OK":
            avg_eng = float(ig_brand.get("avg_likes", 0) or 0) + float(ig_brand.get("avg_comments", 0) or 0)
            if avg_eng > 0:
                account_baseline[brand_handle] = avg_eng

        clean: list = []
        drop_reasons: dict[str, int] = {
            "engagement_pod_signature": 0,
            "bought_views": 0,
            "bot_comments": 0,
        }
        dropped_urls: list[dict] = []
        flagged_paid_promo: list[str] = []

        for post in scored_posts:
            likes    = int(post.get("likes", 0) or 0)
            comments = int(post.get("comments", 0) or 0)
            views    = int(post.get("videoViewCount", 0) or 0)
            url      = post.get("url", "") or ""
            owner    = (post.get("owner_username", "") or "").lower()
            latest_comments = post.get("latestComments", []) or []

            # ── CHECK 1: Engagement-pod signature ────────────────────────────
            # Huge likes, almost no comments → bought likes / pod activity
            if likes >= T["engagement_pod_min_likes"] and comments > 0:
                clr = comments / likes
                if clr < T["engagement_pod_max_comment_like_ratio"]:
                    drop_reasons["engagement_pod_signature"] += 1
                    dropped_urls.append({"url": url, "reason": "engagement_pod_signature",
                                         "comment_like_ratio": round(clr, 5)})
                    continue
            # Edge case: huge likes, ZERO comments → harder pod signal
            if likes >= T["engagement_pod_min_likes"] and comments == 0:
                drop_reasons["engagement_pod_signature"] += 1
                dropped_urls.append({"url": url, "reason": "engagement_pod_signature",
                                     "comment_like_ratio": 0})
                continue

            # ── CHECK 2: Bought-views signature ──────────────────────────────
            # Huge views, anemic likes → likely bought views (real virality has 4-8% LVR)
            if views >= T["bought_views_min_views"]:
                lvr = likes / views if views > 0 else 0
                if lvr < T["bought_views_max_like_view_ratio"]:
                    drop_reasons["bought_views"] += 1
                    dropped_urls.append({"url": url, "reason": "bought_views",
                                         "like_view_ratio": round(lvr, 5)})
                    continue

            # ── CHECK 3: Bot-comment signature ───────────────────────────────
            # Most latestComments are emoji-only or under N chars → bot reply pattern
            if len(latest_comments) >= T["bot_comments_min_sample"]:
                short_count = sum(
                    1 for c in latest_comments
                    if len((c.get("text") or "").strip()) <= T["bot_comments_short_threshold_chars"]
                )
                short_share = short_count / len(latest_comments)
                if short_share > T["bot_comments_short_share_max"]:
                    drop_reasons["bot_comments"] += 1
                    dropped_urls.append({"url": url, "reason": "bot_comments",
                                         "short_comment_share": round(short_share, 3)})
                    continue

            # ── CHECK 4: Paid-promo outlier flag (DON'T drop, just flag) ─────
            # Real organic virality CAN be 10× baseline — flag for review, don't filter out
            baseline = account_baseline.get(owner)
            this_engagement = likes + comments
            paid_promo_suspect = False
            if baseline and this_engagement > T["paid_promo_outlier_multiplier"] * baseline:
                paid_promo_suspect = True
                flagged_paid_promo.append(url)

            # ── Compute per-post trust_score (0-100) ─────────────────────────
            trust_signals: list[str] = []
            trust_score = 100

            # Healthy comment-like ratio (1-5%)
            if likes >= 1000 and comments > 0:
                clr = comments / likes
                if 0.01 <= clr <= 0.05:
                    trust_signals.append("healthy_comment_like_ratio")
                elif clr < 0.005:
                    trust_score -= 15
                elif clr > 0.20:
                    trust_score -= 10  # comment-bait engagement (low quality)

            # Healthy like-view ratio (4-12%)
            if views >= 1000:
                lvr = likes / views if views > 0 else 0
                if 0.04 <= lvr <= 0.12:
                    trust_signals.append("healthy_like_view_ratio")
                elif lvr < 0.02:
                    trust_score -= 10

            # Comment quality
            if len(latest_comments) >= T["bot_comments_min_sample"]:
                long_count = sum(
                    1 for c in latest_comments
                    if len((c.get("text") or "").strip()) > T["bot_comments_short_threshold_chars"]
                )
                if long_count / len(latest_comments) >= 0.5:
                    trust_signals.append("substantive_comments")

            # Paid-promo penalty
            if paid_promo_suspect:
                trust_score -= 15
                trust_signals.append("paid_promo_suspect")

            trust_score = max(0, min(100, trust_score))
            post["trust_score"] = trust_score
            post["trust_signals"] = trust_signals
            clean.append(post)

        evaluated = len(scored_posts)
        passed    = len(clean)
        dropped   = evaluated - passed
        drop_share = (dropped / evaluated) if evaluated > 0 else 0

        # ── Bypass guard: if gate would kill > 80% of posts, pass them through ──
        bypass = False
        if drop_share > T["max_drop_share_before_bypass"] and evaluated > 0:
            bypass = True
            self.log(
                f"WARNING: Quality gate would drop {drop_share*100:.0f}% of posts "
                f"(>{T['max_drop_share_before_bypass']*100:.0f}% threshold). Bypassing — passing all posts through."
            )
            # Pass everything through but mark as bypass
            clean = scored_posts
            for p in clean:
                p.setdefault("trust_score", 50)  # neutral score
                p.setdefault("trust_signals", ["quality_gate_bypassed"])

        gate_report = {
            "evaluated": evaluated,
            "passed": passed if not bypass else evaluated,
            "dropped": dropped if not bypass else 0,
            "bypass_triggered": bypass,
            "drop_reasons": drop_reasons,
            "dropped_samples": dropped_urls[:10],  # sample for human audit
            "flagged_paid_promo_suspect_count": len(flagged_paid_promo),
            "flagged_paid_promo_suspect_urls": flagged_paid_promo[:10],
            "thresholds_used": T,
        }

        self.log(
            f"_quality_gate: {evaluated} evaluated → {gate_report['passed']} passed, "
            f"{gate_report['dropped']} dropped "
            f"(pod={drop_reasons['engagement_pod_signature']}, "
            f"views={drop_reasons['bought_views']}, "
            f"bots={drop_reasons['bot_comments']}). "
            f"Paid-promo flags: {len(flagged_paid_promo)}. "
            f"Bypass: {bypass}"
        )

        return clean, gate_report

    # -------------------------------------------------------------------------
    # TOPIC CLUSTERING
    # -------------------------------------------------------------------------

    def _run_topic_clustering(self, scored_posts: list) -> dict:
        """
        Group top scored posts into named topic clusters using Claude.
        Returns dict with topic_clusters[], recommended_topic, recommendation_reason.
        """
        if not scored_posts:
            return {"topic_clusters": [], "recommended_topic": "", "recommendation_reason": "No posts to cluster"}

        # Send top 30 posts (by score) to Claude
        top_posts_summary = []
        for p in scored_posts[:30]:
            top_posts_summary.append({
                "platform": p.get("platform", ""),
                "caption": p.get("caption_snippet", "")[:200],
                "score": p.get("score", 0),
                "flags": p.get("flags", []),
                "er": p.get("er", 0),
                "whisper": p.get("whisper_transcript", ""),
            })

        prompt = f"""You are analyzing the top-performing content posts for {self.brand_name} across platforms.

{_UNTRUSTED_POLICY}

Group these {len(top_posts_summary)} posts into 3-7 named topic clusters based on what they're about.

TOP POSTS:
{_untrusted_wrap("scraped_post_captions", top_posts_summary)}

BRAND CONTEXT:
- Brand: {self.brand_name}
- Product: {self.brand_profile.get("product", "")}
- Target audience: {self.brand_profile.get("target_audience", "")}

Return valid JSON only. No markdown.

{{
  "topic_clusters": [
    {{
      "name": "cluster name (3-5 words)",
      "post_count": 0,
      "avg_engagement": 0,
      "repeat_viral_signal": true,
      "sustained_trend": false,
      "description": "one sentence"
    }}
  ],
  "recommended_topic": "name of the cluster {self.brand_name} should focus on this week",
  "recommendation_reason": "one sentence — why this cluster over others"
}}"""

        try:
            self.log("Running topic clustering (single Claude call)...")
            response = self.client.messages.create(
                model=MODEL,
                max_tokens=1500,
                messages=[{"role": "user", "content": prompt}]
            )
            self._total_input_tokens += response.usage.input_tokens
            self._total_output_tokens += response.usage.output_tokens

            raw = response.content[0].text.strip()
            if "```" in raw:
                for part in raw.split("```"):
                    part = part.strip()
                    if part.startswith("json"):
                        part = part[4:].strip()
                    if part.startswith("{"):
                        raw = part
                        break

            result = _safe_json_loads(raw)
            self.log(f"Topic clustering done. Recommended: {result.get('recommended_topic', '')}")
            return result

        except Exception as e:
            self.log(f"Topic clustering FAILED — {e}")
            return {"topic_clusters": [], "recommended_topic": "", "recommendation_reason": f"Clustering failed: {e}"}

    # -------------------------------------------------------------------------
    # AUTORESEARCH LOOP (Rule 9)
    # -------------------------------------------------------------------------

    def run_autoresearch_loop(self, scraped_data: dict) -> dict:
        """
        Rule 9 — AutoResearch Loop.

        Runs 3 internal variants through Claude:
          Variant A — Volume angle (what has most engagement/search volume)
          Variant B — Velocity angle (what is growing fastest right now)
          Variant C — Gap angle (what competitors are ignoring — brand can own)

        Selects winner based on metric:
          better = highest probability of driving awareness + trust for this brand in 7 days

        Returns dict with loop_header + winning trend_report.
        """
        self.log("Running AutoResearch Loop — 3 variants (Volume / Velocity / Gap)...")

        brand_context = {
            "brand_name": self.brand_profile.get("brand_name"),
            "product": self.brand_profile.get("product"),
            "product_description": self.brand_profile.get("product_description"),
            "target_audience": self.brand_profile.get("target_audience"),
            "platforms": self.brand_profile.get("platforms"),
            "bottlenecks": self.brand_profile.get("bottlenecks"),
            "tone": self.brand_profile.get("tone"),
            "phase": self.brand_profile.get("phase"),
            "goal": self.brand_profile.get("goal")
        }

        # Truncate scraped data to avoid token overflow
        scraped_summary = json.dumps(scraped_data, indent=2)
        if len(scraped_summary) > 8000:
            scraped_summary = scraped_summary[:8000] + "\n... [truncated for token limit]"

        # Build competitor intel summary for the Gap variant
        competitor_summary = ""
        ig_comp = scraped_data.get("instagram_competitor_profiles", {})
        if ig_comp.get("status") in ("OK", "PARTIAL") and ig_comp.get("competitors"):
            lines = []
            for handle, data in ig_comp["competitors"].items():
                if data.get("status") != "OK":
                    continue
                top_captions = [p["caption_snippet"][:150] for p in data.get("top_posts", [])[:3]]
                lines.append(
                    f"@{handle}: avg {data.get('avg_likes',0)} likes, "
                    f"formats={data.get('formats_used',[])},"
                    f" top hashtags={data.get('top_hashtags',[])[:5]}\n"
                    f"  Top post captions: {top_captions}"
                )
            competitor_summary = "\n\n".join(lines)
        else:
            competitor_summary = "No competitor data scraped — skip Gap variant or note this in output."

        prompt = f"""You are the Trend Researcher for {self.brand_name}.
Your job: identify the highest-leverage content angle for this brand this week based on real scraped data.

{_UNTRUSTED_POLICY}

BRAND CONTEXT:
{json.dumps(brand_context, indent=2)}

REAL SCRAPED DATA (timestamped {self.scraped_at}):
{_untrusted_wrap("scraped_trend_data", scraped_summary)}

COMPETITOR INSTAGRAM DATA (real scrape — use this for Gap variant):
{_untrusted_wrap("competitor_profiles", competitor_summary)}

---

Run the AutoResearch Loop. You must evaluate 3 distinct variants before producing output.

VARIANT A — VOLUME ANGLE
Analyze what has the most engagement volume or search volume right now.
What content format or topic is already proven to work at scale in this niche?
What should {self.brand_name} post to ride existing demand?

VARIANT B — VELOCITY ANGLE
Analyze what is growing fastest right now — emerging trends, rising keywords,
formats gaining momentum. What is early enough to own but already showing signal?

VARIANT C — GAP ANGLE
Use the real competitor data above. What topics, formats, or audience emotions are the
competitors NOT addressing in their top posts? What hashtag territory are they ignoring?
What is the audience craving that no brand is giving them?
What can {self.brand_name} own by being first?

---

SELECTION METRIC:
better = which variant gives {self.brand_name} the highest probability of content that drives
awareness AND trust among the target audience in the next 7 days

Select the winner. State the reason in one line.

---

OUTPUT: Return valid JSON only. No markdown fences. No commentary outside the JSON.

{{
  "loop_header": {{
    "agent": "Trend Researcher",
    "output_type": "Weekly Trend Report",
    "goal": "Identify the highest-leverage content angle for {self.brand_name} this week",
    "metric": "highest probability of driving awareness + trust among target audience in 7 days",
    "variants_tested": 3,
    "winner": "Variant [A/B/C] — [one line reason]"
  }},
  "winning_variant": "A",
  "trend_report": {{
    "scraped_at": "{self.scraped_at}",
    "scrape_status_per_source": {{}},
    "instagram_trends": {{
      "top_hooks": [
        {{"hook": "", "why_it_works": "", "relevance_score": 0, "trend_type": "FAD|MICRO_TREND|STRUCTURAL_SHIFT"}}
      ],
      "trending_formats": [],
      "sentiment": ""
    }},
    "competitor_intel": {{
      "handles_scraped": [],
      "what_competitors_are_posting": "",
      "formats_competitors_dominate": [],
      "hashtag_territory_they_own": [],
      "gaps_identified": [
        {{"gap": "", "evidence": "", "opportunity_for_brand": ""}}
      ]
    }},
    "google_trends": {{
      "rising_keywords": [],
      "top_keywords": [],
      "opportunity": ""
    }},
    "audience_language": {{
      "phrases_heard_this_week": [],
      "fears_expressed": [],
      "desires_expressed": []
    }},
    "summary": "One paragraph — what is trending this week and what content angles {self.brand_name} should pursue",
    "contrarian_opportunities": "What is NOT being talked about that {self.brand_name} should own",
    "content_angles_to_pursue": [
      {{"angle": "", "format": "", "why": "", "urgency": "HIGH|MEDIUM|LOW"}}
    ],
    "content_angles_to_avoid": [
      {{"angle": "", "why": ""}}
    ]
  }}
}}"""

        # ── Rule 10: build source_index from REAL scraped_data + brand_profile ──
        # Note: trend_researcher's "source" is the live Apify scrapes (in scraped_data dict).
        # We pass it as a virtual source so the validator can check Claude's claims against it.
        try:
            from agents._lib._provenance import build_source_index, validate_citations, build_violation_message, MAX_RERUN_ATTEMPTS as _MAX
        except ImportError:
            import sys as _sys
            _sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
            from agents._lib._provenance import build_source_index, validate_citations, build_violation_message, MAX_RERUN_ATTEMPTS as _MAX
        project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        source_files = [
            os.path.join(project_root, "brands", self.brand_slug, "brand_profile.json"),
        ]
        source_index = build_source_index(
            source_files,
            virtual_sources={"scraped_data.json": scraped_data}
        )
        self.log(f"Rule 10: Source index built — {len(source_index)} citable keys (file + virtual scraped_data)")

        # Append Rule 10 enforcement block to the prompt
        prompt += """

⚠️ RULE 10 — SOURCE CITATION ENFORCEMENT (HARD REQUIREMENT) ⚠️

Every claim in your trend_report (audience_language phrases, competitor patterns,
content_angles_to_pursue, contrarian_opportunities, summary) MUST trace back to a real
source data point in either:
  - brand_profile.json (brand context)
  - scraped_data.json (the live Apify scrape data shown above)

Add a top-level "data_provenance" array to your output with entries:
  - "claim": short text of the claim
  - "source_file": "brand_profile.json" OR "scraped_data.json"
  - "source_path": dot.notation path (e.g. "instagram_competitor_profiles.competitors.manthanjethwani.top_posts[0].caption_snippet")
  - "source_value": verbatim ≥30-char snippet

Aim for 8–12 provenance entries. Validation will reject claims that don't trace.
"""

        messages = [{"role": "user", "content": self.ceo.story_so_far_block() + prompt}]
        result = None
        validation_report = None
        attempt = 0
        max_attempts = _MAX + 1

        while attempt < max_attempts:
            attempt += 1
            self.log(f"Calling Claude claude-sonnet-4-6 for AutoResearch Loop (attempt {attempt}/{max_attempts})...")
            response = self.client.messages.create(
                model=MODEL,
                max_tokens=16000,
                messages=messages
            )
            self._total_input_tokens += response.usage.input_tokens
            self._total_output_tokens += response.usage.output_tokens

            if response.stop_reason == "max_tokens":
                self.log(f"WARNING: Claude hit max_tokens cap ({response.usage.output_tokens} out). Response truncated.")

            raw = response.content[0].text.strip()
            if "```" in raw:
                for part in raw.split("```"):
                    part = part.strip()
                    if part.startswith("json"):
                        part = part[4:].strip()
                    if part.startswith("{"):
                        raw = part
                        break

            try:
                result = _safe_json_loads(raw)
            except json.JSONDecodeError as e:
                self.log(f"ERROR: invalid JSON — {e}")
                raise

            is_valid, missing, validation_report = validate_citations(result, source_index)
            self.log(f"Rule 10 validation (attempt {attempt}): {validation_report['claims_validated']}/{validation_report['claims_total']} passed")

            if is_valid or attempt >= max_attempts:
                break

            messages.append({"role": "assistant", "content": json.dumps(result)})
            messages.append({"role": "user", "content": (
                f"Your previous output failed Rule 10 validation.\n\n"
                f"{build_violation_message(missing)}\n\n"
                f"Re-emit COMPLETE corrected JSON. Strict JSON only."
            )})

        if result is not None:
            result["provenance_validation"] = validation_report

        self.log(f"AutoResearch Loop complete.")
        self.log(f"Winner: {result['loop_header']['winner']}")
        return result

    # -------------------------------------------------------------------------
    # SAVE TRENDS LIVE
    # -------------------------------------------------------------------------

    def save_trends_live(self, trend_report: dict):
        """
        Write trends_live.json to brands/{slug}/.
        This file is read by all downstream agents.
        """
        path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "brands", self.brand_slug, "trends_live.json"
        )
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w") as f:
            json.dump(trend_report, f, indent=2)
        self.log(f"trends_live.json saved → {path}")

    # -------------------------------------------------------------------------
    # MAIN RUN
    # -------------------------------------------------------------------------

    def run(self):
        """
        Full agent run sequence:
        1. Scrape all available data sources
        2. Run AutoResearch Loop (3 variants → winner)
        3. Save trends_live.json for downstream agents
        4. Push to pending_approval/ + Notion via CEO Brain
        5. Mark agent complete
        """
        self.log("=" * 60)
        self.log("TREND RESEARCHER — WEEKLY RUN STARTING")
        self.log("=" * 60)

        # --- STEP 1: SCRAPE ---
        self.log("STEP 1 — Scraping data sources...")
        scraped_data = {
            "scraped_at": self.scraped_at,
            "scrape_status_per_source": {}
        }

        # Instagram hashtags (120s wait)
        ig_hashtags = self.scrape_instagram_hashtags()
        scraped_data["instagram_hashtag_scrape"] = ig_hashtags
        scraped_data["scrape_status_per_source"]["instagram_hashtags"] = ig_hashtags.get("status")

        # Brand's own posts (90s wait — uses instagram-scraper with directUrls)
        ig_brand = self.scrape_brand_instagram()
        scraped_data["instagram_brand_posts"] = ig_brand
        scraped_data["scrape_status_per_source"]["instagram_brand"] = ig_brand.get("status")

        # Competitor profiles (90s wait — parallel Apify runs, one wait covers all)
        ig_competitors = self.scrape_competitor_profiles()
        scraped_data["instagram_competitor_profiles"] = ig_competitors
        scraped_data["scrape_status_per_source"]["instagram_competitors"] = ig_competitors.get("status")

        # Google Trends (no wait — synchronous)
        google = self.scrape_google_trends()
        scraped_data["google_trends_raw"] = google
        scraped_data["scrape_status_per_source"]["google_trends"] = google.get("status")

        # YouTube Shorts (90s wait — graceful skip if Apify credits insufficient)
        youtube_shorts = self.scrape_youtube_shorts()
        scraped_data["youtube_shorts_raw"] = youtube_shorts
        scraped_data["scrape_status_per_source"]["youtube_shorts"] = "OK" if youtube_shorts else "SKIPPED"

        # Twitter/X (60s wait — graceful skip)
        twitter_posts = self.scrape_twitter()
        scraped_data["twitter_raw"] = twitter_posts
        scraped_data["scrape_status_per_source"]["twitter"] = "OK" if twitter_posts else "SKIPPED"

        # Rule 1 gate — if ALL scrapes failed, stop
        ok_sources = [k for k, v in scraped_data["scrape_status_per_source"].items() if v == "OK"]
        failed_sources = [k for k, v in scraped_data["scrape_status_per_source"].items() if v == "FAILED"]

        self.log(f"Scrape complete — {len(ok_sources)} OK, {len(failed_sources)} failed")
        for src, status in scraped_data["scrape_status_per_source"].items():
            self.log(f"  {src}: {status}")

        if not ok_sources:
            self.log("CRITICAL — Rule 1 HALT: All data sources failed.")
            self.log("Cannot produce output without real data.")
            self.log("ACTION REQUIRED: Check APIFY_API_KEY and internet connectivity.")
            return None

        # --- STEP 1B: SCORING + QUALITY GATE + WHISPER + TOPIC CLUSTERING ---
        self.log("STEP 1B — Scoring posts, running quality gate, extracting whisper transcripts, clustering topics...")
        self._whisper_candidates = []
        scored_posts = self._score_posts(scraped_data)
        scraped_data["scored_posts_count"] = len(scored_posts)

        # BUILD B — Quality gate: drop pods/bought-views/bot-comment posts before clustering
        clean_posts, quality_gate_report = self._quality_gate(scored_posts, scraped_data)
        scraped_data["quality_gate"] = quality_gate_report

        # Whisper transcript extraction (graceful skip if not installed)
        # Re-derive whisper candidates from CLEAN posts only
        self._whisper_candidates = [
            p for p in clean_posts
            if p.get("url") and ("HIGH_SIGNAL" in p.get("flags", []) or "VIRAL" in p.get("flags", []))
        ][:WHISPER_CANDIDATES_CAP]
        self._extract_whisper_transcripts()
        # Inject whisper transcripts back into clean_posts
        for wp in self._whisper_candidates:
            for sp in clean_posts:
                if sp.get("url") == wp.get("url") and wp.get("whisper_transcript"):
                    sp["whisper_transcript"] = wp["whisper_transcript"]

        # Topic clustering — uses CLEAN posts only (build B effect)
        clustering = self._run_topic_clustering(clean_posts)
        scraped_data["topic_clustering"] = clustering

        # --- STEP 2: AUTORESEARCH LOOP ---
        self.log("STEP 2 — AutoResearch Loop (3 variants)...")
        loop_result = self.run_autoresearch_loop(scraped_data)

        trend_report = loop_result["trend_report"]
        # Inject real scrape statuses into the report
        trend_report["scrape_status_per_source"] = scraped_data["scrape_status_per_source"]

        # Inject topic clustering into trend_report
        trend_report["topic_clusters"] = clustering.get("topic_clusters", [])
        trend_report["recommended_topic"] = clustering.get("recommended_topic", "")
        trend_report["recommendation_reason"] = clustering.get("recommendation_reason", "")

        # BUILD B — Inject quality gate report (so downstream agents can audit data trust)
        trend_report["quality_gate"] = scraped_data.get("quality_gate", {})

        # G3/G5 — inject REAL competitor engagement metrics (deterministic, computed from
        # the competitor profile scrape) into competitor_intel. The AutoResearch synthesis
        # only produces QUALITATIVE competitor_intel; without this the Brand-Book benchmark
        # has no real category numbers. Additive — qualitative fields are preserved.
        _comp_profiles = (scraped_data.get("instagram_competitor_profiles") or {}).get("competitors", {})
        _comp_metrics = competitor_metrics_from_profiles(_comp_profiles)
        if _comp_metrics:
            trend_report.setdefault("competitor_intel", {})
            trend_report["competitor_intel"]["competitor_metrics"] = _comp_metrics
            trend_report["competitor_intel"].setdefault(
                "metrics_source",
                "apify~instagram-scraper — deterministic avg of scraped competitor posts")
            self.log(f"  Injected REAL competitor_metrics for {len(_comp_metrics)} handles")

        # Rule 10 — Inject provenance + validation into trend_report
        trend_report["data_provenance"] = loop_result.get("data_provenance", [])
        trend_report["provenance_validation"] = loop_result.get("provenance_validation", {})

        loop_header = loop_result["loop_header"]

        # --- STEP 3: SAVE TRENDS LIVE ---
        self.log("STEP 3 — Saving trends_live.json for downstream agents...")
        self.save_trends_live(trend_report)

        # --- STEP 4: PUSH TO PENDING APPROVAL + NOTION ---
        self.log("STEP 4 — Pushing output to pending_approval/ and Notion...")
        save_result = self.ceo.save_agent_output(
            agent_name="Trend Researcher",
            output_type="Weekly Trend Report",
            loop_header={
                "goal": loop_header["goal"],
                "metric": loop_header["metric"],
                "variants_tested": loop_header["variants_tested"],
                "winner": loop_header["winner"]
            },
            content=json.dumps(trend_report, indent=2),
            filename="trend_report.json"
        )

        if save_result["notion_result"]["success"]:
            self.log(f"Notion card created: {save_result['notion_result']['notion_url']}")
        else:
            self.log(f"WARNING: Notion push failed — {save_result['notion_result'].get('error')}")

        # --- STEP 5: MARK COMPLETE ---
        self.log("STEP 5 — Marking trend-researcher complete in CEO Brain...")
        self.ceo.mark_agent_complete("trend-researcher")

        self.log("=" * 60)
        self.log("TREND RESEARCHER — RUN COMPLETE")
        self.log(f"Winner variant : {loop_result['winning_variant']}")
        self.log(f"Reason         : {loop_header['winner']}")
        self.log(f"Local output   : {save_result['local_path']}")
        self.log("Pending approval in Notion. Approve to unlock: strategy-agent")
        self.log("=" * 60)
        cost_reporter.record(MODEL, self._total_input_tokens, self._total_output_tokens, apify_runs=self._apify_runs)

        return save_result


if __name__ == "__main__":
    agent = TrendResearcher()
    agent.run()
