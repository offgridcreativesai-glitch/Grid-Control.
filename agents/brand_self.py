"""
brand_self.py — GRID CONTROL · Brand-Book v7 · brand-side data layer.

Pulls the BRAND's OWN real data (the hero of an onboarding audit) via the
Instagram Login API (graph.instagram.com — token type IGAA...). This is the
client's connected account, so these are REAL private metrics, not scrapes:
account stats, account-level reach/views, and per-post insights (reach, saved,
shares, total_interactions). Audience demographics unlock only at 100+ followers
— below that we record the honest absence, never fake it.

Writes brands/<slug>/brand_self_v7.json (gitignored).
Reads token + IG_USER_ID from the brand's private .env (brand_env).

Usage: python3 agents/brand_self.py [slug]
"""
from __future__ import annotations

import json
import os
import ssl
import sys
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_HOST = "https://graph.instagram.com/v21.0"

try:
    import certifi
    _CTX = ssl.create_default_context(cafile=certifi.where())
except Exception:                                    # pragma: no cover
    _CTX = ssl._create_unverified_context()


def _load_env(slug: str):
    """Overlay the brand's private .env (token lives there, not global)."""
    path = os.path.join(_ROOT, "brands", slug, ".env")
    env = {}
    if os.path.exists(path):
        for line in open(path, encoding="utf-8"):
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, v = line.split("=", 1)
            env[k.strip()] = v.strip()
    return env


def _get(path: str, params: dict, token: str):
    params = dict(params, access_token=token)
    url = f"{_HOST}/{path}?" + urllib.parse.urlencode(params)
    try:
        with urllib.request.urlopen(url, timeout=25, context=_CTX) as r:
            return json.load(r)
    except urllib.error.HTTPError as e:
        return {"_error": e.code, "body": e.read().decode()[:300]}
    except Exception as e:                            # pragma: no cover
        return {"_error": "exc", "body": str(e)[:200]}


def _ok(d) -> bool:
    return isinstance(d, dict) and "_error" not in d


def _account(uid: str, token: str) -> dict:
    fields = "user_id,username,account_type,media_count,followers_count,follows_count,name,biography"
    d = _get("me", {"fields": fields}, token)
    return d if _ok(d) else {"_error": d.get("body", "account fetch failed")}


def _account_insights(uid: str, token: str) -> dict:
    """Account-level reach/views. Small accounts expose a thin set; skip what errors."""
    out = {}
    # total_value metrics (newer API shape)
    for metric in ("reach", "views", "profile_views", "accounts_engaged", "total_interactions"):
        d = _get(f"{uid}/insights", {"metric": metric, "period": "days_28",
                                     "metric_type": "total_value"}, token)
        if _ok(d) and d.get("data"):
            tv = d["data"][0].get("total_value", {})
            if "value" in tv:
                out[metric] = tv["value"]
                continue
        # fallback to time-series shape
        d2 = _get(f"{uid}/insights", {"metric": metric, "period": "days_28"}, token)
        if _ok(d2) and d2.get("data") and d2["data"][0].get("values"):
            out[metric] = d2["data"][0]["values"][-1].get("value")
    return out


def _demographics(uid: str, token: str) -> dict:
    """REAL audience demographics — unlocks at 100+ followers. Honest-empty below."""
    out = {}
    for breakdown in ("age", "gender", "city", "country"):
        d = _get(f"{uid}/insights", {"metric": "follower_demographics", "period": "lifetime",
                                     "metric_type": "total_value", "breakdown": breakdown}, token)
        if _ok(d) and d.get("data"):
            tv = d["data"][0].get("total_value", {})
            breakdowns = tv.get("breakdowns", [])
            if breakdowns and breakdowns[0].get("results"):
                out[breakdown] = {
                    "/".join(r.get("dimension_values", [])): r.get("value")
                    for r in breakdowns[0]["results"]
                }
    return out


_POST_INSIGHTS = "reach,saved,shares,total_interactions,likes,comments,views"


def _posts(token: str, limit: int = 25) -> list:
    fields = "id,caption,media_type,media_product_type,like_count,comments_count,timestamp,permalink,thumbnail_url,media_url"
    d = _get("me/media", {"fields": fields, "limit": limit}, token)
    if not (_ok(d) and d.get("data")):
        return []
    posts = []
    for m in d["data"]:
        ins = _get(f"{m['id']}/insights", {"metric": _POST_INSIGHTS}, token)
        metrics = {}
        if _ok(ins) and ins.get("data"):
            for row in ins["data"]:
                vals = row.get("values") or []
                if vals:
                    metrics[row["name"]] = vals[0].get("value")
        posts.append({
            "id": m["id"],
            "caption": (m.get("caption") or "")[:240],
            "media_type": m.get("media_type"),
            "product_type": m.get("media_product_type"),
            "likes": m.get("like_count", 0),
            "comments": m.get("comments_count", 0),
            "timestamp": m.get("timestamp"),
            "permalink": m.get("permalink"),
            "thumbnail": m.get("thumbnail_url") or m.get("media_url"),
            "insights": metrics,
        })
    return posts


def collect(slug: str) -> dict:
    env = _load_env(slug)
    token = env.get("META_GRAPH_API_TOKEN", "")
    uid = env.get("IG_USER_ID", "")
    if not token or not uid:
        return {"_error": "no IG token / IG_USER_ID in brand .env"}

    acct = _account(uid, token)
    posts = _posts(token)
    # derived: real averages over the brand's OWN posts
    n = len(posts)
    avg_likes = round(sum(p["likes"] for p in posts) / n, 1) if n else 0
    avg_comments = round(sum(p["comments"] for p in posts) / n, 1) if n else 0
    reaches = [p["insights"].get("reach") for p in posts if isinstance(p["insights"].get("reach"), (int, float))]
    avg_reach = round(sum(reaches) / len(reaches), 1) if reaches else None
    saves = [p["insights"].get("saved") for p in posts if isinstance(p["insights"].get("saved"), (int, float))]
    total_saves = sum(saves) if saves else None

    fmt = {}
    for p in posts:
        fmt[p["media_type"]] = fmt.get(p["media_type"], 0) + 1

    return {
        "brand_slug": slug,
        "collected_at": datetime.now(timezone.utc).isoformat(),
        "source": "Instagram Login API (graph.instagram.com) — REAL connected-account data",
        "instagram": {
            "status": "ok" if _ok(acct) else "error",
            "username": acct.get("username"),
            "name": acct.get("name"),
            "biography": acct.get("biography"),
            "account_type": acct.get("account_type"),
            "followers": acct.get("followers_count"),
            "follows": acct.get("follows_count"),
            "media_count": acct.get("media_count"),
            "account_insights_28d": _account_insights(uid, token),
            "demographics": _demographics(uid, token),
            "demographics_status": "locked_under_100_followers"
            if (acct.get("followers_count") or 0) < 100 else "available",
            "posts_pulled": n,
            "avg_likes": avg_likes,
            "avg_comments": avg_comments,
            "avg_reach": avg_reach,
            "total_saves": total_saves,
            "format_mix": fmt,
            "posts": posts,
        },
        "other_channels": {
            # brand_profile says askgauravai is IG-only today; tokens for LI/YT/X are
            # post-capable but the brand isn't active there yet. Honest absence.
            "linkedin": "not_active",
            "youtube": "not_active",
            "x": "not_active",
            "website": "none",
        },
    }


def main():
    slug = sys.argv[1] if len(sys.argv) > 1 else os.getenv("ACTIVE_BRAND", "askgauravai")
    data = collect(slug)
    if data.get("_error"):
        sys.exit(f"[brand_self] {data['_error']}")
    path = os.path.join(_ROOT, "brands", slug, "brand_self_v7.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    ig = data["instagram"]
    print(f"[brand_self] {slug} @{ig['username']} — {ig['followers']} followers · "
          f"{ig['posts_pulled']} posts · avg {ig['avg_likes']} likes / {ig['avg_comments']} comments · "
          f"avg reach {ig['avg_reach']} · saves {ig['total_saves']}")
    print(f"  account insights: {ig['account_insights_28d']}")
    print(f"  demographics: {ig['demographics_status']} ({len(ig['demographics'])} breakdowns)")
    print(f"  format mix: {ig['format_mix']}")
    print(f"  → brands/{slug}/brand_self_v7.json")


if __name__ == "__main__":
    main()
