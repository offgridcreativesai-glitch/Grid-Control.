"""
publish_runner — fires the approved posts to every platform on schedule.

Drives the real publishers (instagram/linkedin/twitter/youtube). Maps each
calendar post → its platforms → the right asset + per-platform caption, then
publishes. Idempotent: a per-(post,platform) log prevents double-posting.

Usage:
  python publishing/publish_runner.py --post P1 --dry        # show plan, post nothing
  python publishing/publish_runner.py --post P1              # publish all P1 platforms
  python publishing/publish_runner.py --post P1 --platform instagram
  python publishing/publish_runner.py --post P2 --force      # ignore the 'already posted' log

Zero fabrication: every result is a real API response; failures are surfaced, not masked.
"""
from __future__ import annotations
import os, sys, json, argparse
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE))

BRAND = os.getenv("ACTIVE_BRAND", "askgauravai")
BRAND_DIR = BASE / "brands" / BRAND
LOG = BRAND_DIR / "outputs" / "publish_log.json"


def _load_env():
    for p in (BASE / ".env", BRAND_DIR / ".env"):   # brand overlays global
        if p.exists():
            for ln in p.read_text().splitlines():
                ln = ln.strip()
                if ln and not ln.startswith("#") and "=" in ln:
                    k, v = ln.split("=", 1)
                    os.environ[k.strip()] = v.strip().strip('"').strip("'")


def _log_read() -> dict:
    if LOG.exists():
        try: return json.loads(LOG.read_text())
        except Exception: return {}
    return {}


def _log_write(d: dict):
    LOG.parent.mkdir(parents=True, exist_ok=True)
    LOG.write_text(json.dumps(d, indent=2, ensure_ascii=False))


def _abs(rel: str) -> str:
    p = (BRAND_DIR / rel) if not os.path.isabs(rel) else Path(rel)
    return str(p)


def _slides(carousel_rel: str) -> list[str]:
    d = BRAND_DIR / carousel_rel
    return [str(p.relative_to(BASE)) for p in sorted(d.glob("slide_*.png"))]


def build_jobs(post_id: str):
    cal = json.loads((BRAND_DIR / "content_calendar.json").read_text())
    content = json.loads((BRAND_DIR / "outputs" / "first3_final_content.json").read_text())
    post = next((p for p in cal["week_1"]["posts"] if p.get("post_id") == post_id), None)
    if not post:
        raise SystemExit(f"{post_id} not found in calendar")
    key = post_id[-1]  # P1->"1"
    cap = content["captions"][key]; cta = content["ctas"][key]
    tags = content["hashtags"]
    ig_caption = f"{cap}\n\n{cta}\n\n{tags}"
    li_text = content["linkedin"][key]
    x_text = content["x"][key]
    fmt = "reel" if "reel" in (post.get("format", "").lower()) else "carousel"

    jobs = {}
    if fmt == "carousel":
        slides = _slides(post["carousel_dir"])
        jobs["instagram"] = {"kind": "carousel", "slides": slides, "caption": ig_caption}
        jobs["linkedin"]  = {"kind": "images",   "slides": slides, "text": li_text}
        jobs["twitter"]   = {"kind": "images",   "slides": slides[:4], "text": x_text}
    else:
        reel = post.get("reel_asset")
        jobs["instagram"] = {"kind": "reel",  "video": reel, "caption": ig_caption}
        jobs["linkedin"]  = {"kind": "video", "video": reel, "text": li_text}
        jobs["twitter"]   = {"kind": "video", "video": reel, "text": x_text}
        first_line = cap.split("\n")[0].strip()
        jobs["youtube"]   = {"kind": "short", "video": reel,
                             "title": (first_line[:90] + " #Shorts"),
                             "description": f"{cap}\n\n{cta}\n\n{tags}",
                             "tags": [t.lstrip('#') for t in tags.split()]}
    return post, fmt, jobs


def run_platform(platform: str, job: dict, post_id: str):
    g = os.getenv
    if platform == "instagram":
        import publishing.instagram_publisher as ig
        tok = g("META_GRAPH_API_TOKEN", "")
        if job["kind"] == "carousel":
            urls = ig.upload_slides_to_storage(BRAND, job["slides"], post_id)
            return ig.publish_carousel(urls, job["caption"], tok)
        url = ig.upload_video_to_storage(BRAND, _abs(job["video"]), post_id)
        return ig.publish_reel(url, job["caption"], tok)
    if platform == "linkedin":
        import publishing.linkedin_publisher as li
        tok, urn = g("LINKEDIN_ACCESS_TOKEN", ""), g("LINKEDIN_URN", "")
        if job["kind"] == "images":
            return li.publish_images(tok, urn, job["text"], job["slides"])
        return li.publish_video(tok, urn, job["text"], _abs(job["video"]))
    if platform == "twitter":
        import publishing.twitter_publisher as tw
        a = (g("TWITTER_API_KEY",""), g("TWITTER_API_SECRET",""),
             g("TWITTER_ACCESS_TOKEN",""), g("TWITTER_ACCESS_SECRET",""))
        if job["kind"] == "images":
            return tw.publish_images(*a, job["text"], job["slides"])
        return tw.publish_video(*a, job["text"], _abs(job["video"]))
    if platform == "youtube":
        import publishing.youtube_publisher as yt
        return yt.upload_video(g("YOUTUBE_CLIENT_ID",""), g("YOUTUBE_CLIENT_SECRET",""),
            g("YOUTUBE_REFRESH_TOKEN",""), _abs(job["video"]),
            job["title"], job["description"], job["tags"], "public")
    return {"published": False, "error": f"unknown platform {platform}"}


SCHED_TO_PLATFORM = {"x": "twitter", "twitter": "twitter", "linkedin": "linkedin",
                     "instagram": "instagram", "youtube": "youtube"}


def auto_dispatch():
    """Sleep-resilient: fire any platform whose scheduled IST time has passed and
    isn't already in the log. One cron every ~15 min drives this; idempotent."""
    from datetime import datetime
    from zoneinfo import ZoneInfo
    now = datetime.now(ZoneInfo("Asia/Kolkata"))
    cal = json.loads((BRAND_DIR / "content_calendar.json").read_text())
    log = _log_read()
    print(f"[auto] {now:%Y-%m-%d %H:%M IST}")
    for post in cal["week_1"]["posts"]:
        pid = post.get("post_id"); sched = post.get("schedule", {})
        date = post.get("publish_date"); times = sched.get("times", {})
        if not (pid and date and times):
            continue
        _, _, jobs = build_jobs(pid)
        for skey, hhmm in times.items():
            plat = SCHED_TO_PLATFORM.get(skey)
            if not plat or plat not in jobs:
                continue
            due = datetime.fromisoformat(f"{date}T{hhmm}:00").replace(tzinfo=ZoneInfo("Asia/Kolkata"))
            lk = f"{pid}:{plat}"
            if now < due:
                continue
            if log.get(lk, {}).get("published"):
                continue
            print(f"  → due {pid}:{plat} (scheduled {date} {hhmm})")
            res = run_platform(plat, jobs[plat], pid)
            ok = res.get("published")
            print(f"    {'✅' if ok else '❌'} {res.get('permalink') or res.get('error') or res}")
            log[lk] = {**res, "post": pid, "platform": plat, "fired_at": now.isoformat()}
            _log_write(log)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--post", default=None)
    ap.add_argument("--platform", default=None)
    ap.add_argument("--dry", action="store_true")
    ap.add_argument("--force", action="store_true")
    ap.add_argument("--auto", action="store_true")
    args = ap.parse_args()
    _load_env()

    if args.auto:
        auto_dispatch()
        return
    if not args.post:
        raise SystemExit("--post required (or use --auto)")

    post, fmt, jobs = build_jobs(args.post)
    targets = [args.platform] if args.platform else list(jobs.keys())
    print(f"== {args.post} ({fmt}) → {targets} ==")
    log = _log_read()

    for plat in targets:
        job = jobs.get(plat)
        if not job:
            print(f"  {plat}: no job"); continue
        lk = f"{args.post}:{plat}"
        if log.get(lk, {}).get("published") and not args.force:
            print(f"  {plat}: ⏭ already published ({log[lk].get('permalink','')})"); continue
        if args.dry:
            preview = (job.get("caption") or job.get("text") or job.get("title") or "")[:80]
            asset = job.get("video") or f"{len(job.get('slides',[]))} slides"
            print(f"  {plat}: [{job['kind']}] asset={asset} | “{preview}…”")
            continue
        print(f"  {plat}: publishing [{job['kind']}] …")
        res = run_platform(plat, job, args.post)
        ok = res.get("published")
        print(f"    {'✅' if ok else '❌'} {res.get('permalink') or res.get('error') or res}")
        log[lk] = {**res, "post": args.post, "platform": plat}
        _log_write(log)


if __name__ == "__main__":
    main()
