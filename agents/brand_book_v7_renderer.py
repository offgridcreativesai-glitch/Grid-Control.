"""
agents/brand_book_v7_renderer.py — Brand-Book v7 HTML→PDF (GTM intelligence).

Renders the multi-platform "WHERE + HOW to promote" report from the deterministic
channel-score output (+ raw competitor intel + a narrative dict) into a visual-first
A4 PDF via Playwright. Spec: BRAND_BOOK_REPORT_SPEC.md §7.7–7.8.

Visual system (kills the boring text wall): verdict stat cards · channel verdict grid ·
ad-longevity timeline · format-mix + comment-funnel charts (hand-built inline SVG) ·
REAL creative thumbnails (fetched + base64-embedded so they survive CDN expiry) ·
brand-color theme on a forced-white page (the dark-mode bug, §5).

Public:
  render_v7(scores: dict, intel: dict, narrative: dict, palette: dict, out_pdf) -> Path

`narrative` contract (B-5 Opus fills richer prose; B-4 dry-run synthesizes from scores):
  {
    "headline": str,                       # one-line thesis for the cover
    "subhead": str,
    "snapshot": [ {verdict, channel, line}, ... ],
    "intros": { "channel_map":.., "ad":.., "content":.., "gap":.., "route":.. },
    "route_steps": [ {channel, verdict, action, why}, ... ],
  }
"""
from __future__ import annotations

import base64
import urllib.request
from pathlib import Path

from playwright.sync_api import sync_playwright

_FONTS = ("@import url('https://fonts.googleapis.com/css2?"
          "family=Fraunces:opsz,wght@9..144,500;9..144,700;9..144,900"
          "&family=Newsreader:opsz,wght@6..72,400;6..72,500;6..72,600"
          "&display=swap');")

# Verdict → colour token (semantic, brand-independent).
_VERDICT = {
    "RIDE": ("#1f7a3f", "#e6f2e9", "Ride"),
    "GAP":  ("#b23a2e", "#fbeae8", "Own the gap"),
    "TEST": ("#9a6a16", "#f7efe0", "Test"),
    "SKIP": ("#6f675a", "#efece6", "Skip"),
    "NO_DATA": ("#a9a094", "#f3f1ed", "Not scraped"),
}


# ───────────────────────────────────────── image embedding (survives CDN expiry)
def _data_uri(url: str, timeout: float = 8.0):
    """Fetch an image and return a base64 data URI, or None on any failure
    (expired IG CDN token, 404, timeout). The report degrades to a text card."""
    if not url:
        return None
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=timeout) as r:
            if r.status != 200:
                return None
            blob = r.read()
        if len(blob) < 512:                       # tiny = error placeholder, not a real image
            return None
        ctype = "image/jpeg"
        if blob[:4] == b"\x89PNG":
            ctype = "image/png"
        return f"data:{ctype};base64," + base64.b64encode(blob).decode()
    except Exception:
        return None


def _esc(s) -> str:
    if s is None:
        return ""
    return (str(s).replace("&", "&amp;").replace("<", "&lt;")
            .replace(">", "&gt;").replace("\n", "<br>"))


# ───────────────────────────────────────── inline-SVG charts (no network dep)
def _donut(segments, size=120, accent="#b23a2e"):
    """segments = [(label, value, colour)]. Returns an SVG donut + legend."""
    total = sum(v for _, v, _ in segments) or 1
    r, cx, cy, sw = size / 2 - 12, size / 2, size / 2, 18
    import math
    circ = 2 * math.pi * r
    off = 0.0
    arcs = []
    for _lbl, val, col in segments:
        frac = val / total
        dash = frac * circ
        arcs.append(
            f"<circle cx='{cx}' cy='{cy}' r='{r}' fill='none' stroke='{col}' "
            f"stroke-width='{sw}' stroke-dasharray='{dash:.2f} {circ - dash:.2f}' "
            f"stroke-dashoffset='{-off:.2f}' transform='rotate(-90 {cx} {cy})'/>")
        off += dash
    legend = "".join(
        f"<div class='lg'><span class='sw' style='background:{col}'></span>"
        f"{_esc(lbl)} · {int(val)}</div>" for lbl, val, col in segments)
    return (f"<div class='chartrow'><svg width='{size}' height='{size}' "
            f"viewBox='0 0 {size} {size}'>{''.join(arcs)}</svg>"
            f"<div class='legend'>{legend}</div></div>")


def _hbars(rows, accent="#b23a2e", unit=""):
    """rows = [(label, value)]. Horizontal proportional bars."""
    mx = max((v for _, v in rows), default=1) or 1
    out = []
    for lbl, val in rows:
        w = max(2, round(val / mx * 100))
        out.append(
            f"<div class='barrow'><div class='blabel'>{_esc(lbl)}</div>"
            f"<div class='btrack'><div class='bfill' style='width:{w}%;background:{accent}'></div></div>"
            f"<div class='bval'>{_esc(f'{val:,.0f}{unit}')}</div></div>")
    return f"<div class='bars'>{''.join(out)}</div>"


def _longevity_timeline(rows, accent="#b23a2e"):
    """rows = [(handle, days, advertising)]. Bars scaled to the longest runner."""
    mx = max((d for _, d, _ in rows), default=1) or 1
    out = []
    for handle, days, adv in rows:
        if adv:
            w = max(3, round(days / mx * 100))
            out.append(
                f"<div class='barrow'><div class='blabel'>{_esc(handle)}</div>"
                f"<div class='btrack'><div class='bfill' style='width:{w}%;background:{accent}'></div></div>"
                f"<div class='bval'>{days}d live</div></div>")
        else:
            out.append(
                f"<div class='barrow'><div class='blabel'>{_esc(handle)}</div>"
                f"<div class='btrack'><div class='bfill' style='width:2%;background:#d8d2c8'></div></div>"
                f"<div class='bval muted'>no ads</div></div>")
    return f"<div class='bars'>{''.join(out)}</div>"


# ───────────────────────────────────────── section builders
def _verdict_badge(v):
    col, bg, label = _VERDICT.get(v, _VERDICT["NO_DATA"])
    return f"<span class='vbadge' style='color:{col};background:{bg}'>{label}</span>"


def _snapshot(narrative):
    cards = []
    for s in narrative.get("snapshot", []):
        v = s.get("verdict", "TEST")
        col, bg, _ = _VERDICT.get(v, _VERDICT["NO_DATA"])
        cards.append(
            f"<div class='statcard' style='border-top:4px solid {col}'>"
            f"{_verdict_badge(v)}"
            f"<div class='sc-channel'>{_esc(s.get('channel'))}</div>"
            f"<div class='sc-line'>{_esc(s.get('line'))}</div></div>")
    return f"<div class='statgrid'>{''.join(cards)}</div>"


def _channel_grid(scores):
    out = []
    for c in scores.get("channels", []):
        v = c["verdict"]
        col, bg, label = _VERDICT.get(v, _VERDICT["NO_DATA"])
        gap = "<span class='wedge'>WEDGE</span>" if c.get("is_gap") else ""
        money = (f"<div class='cg-meta'>Money signal: {c['money_signal_days']}d sustained spend</div>"
                 if c.get("money_signal_days") else "")
        out.append(
            f"<div class='cgrow' style='border-left:5px solid {col}'>"
            f"<div class='cg-head'>{_verdict_badge(v)}"
            f"<span class='cg-name'>{_esc(c['channel'])}</span>{gap}</div>"
            f"<div class='cg-line'>{_esc(c['headline'])}</div>{money}</div>")
    for c in scores.get("channels_absent", []):
        col, bg, label = _VERDICT["NO_DATA"]
        out.append(
            f"<div class='cgrow' style='border-left:5px solid {col}'>"
            f"<div class='cg-head'>{_verdict_badge('NO_DATA')}"
            f"<span class='cg-name'>{_esc(c['channel'])}</span></div>"
            f"<div class='cg-line muted'>{_esc(c['headline'])}</div></div>")
    return "".join(out)


def _ad_section(scores, intel, accent):
    ads = next((c for c in scores["channels"] if c["channel"].startswith("Meta Ads")), {})
    rows = [(r["handle"], r.get("max_days_running", 0), r.get("advertising"))
            for r in ads.get("rows", [])]
    timeline = _longevity_timeline(rows, accent)
    # creative cards — image if it survives, else text card with the ad body
    owner = ads.get("money_signal_owner")
    comp = intel.get("competitors", {}).get(owner, {}) if owner else {}
    top_ads = (comp.get("meta_ads", {}) or {}).get("top_ads", [])[:4]
    cards = []
    for a in top_ads:
        img = _data_uri(a.get("image"))
        media = (f"<img class='adimg' src='{img}'/>" if img
                 else f"<div class='adimg ph'>{_esc(a.get('media_type','AD'))}</div>")
        cards.append(
            f"<div class='adcard'>{media}"
            f"<div class='ad-days'>{a.get('days_running','?')}d live</div>"
            f"<div class='ad-body'>{_esc((a.get('body') or '')[:140])}</div>"
            f"<div class='ad-cta'>{_esc(a.get('cta',''))}</div></div>")
    cards_html = f"<div class='adcards'>{''.join(cards)}</div>" if cards else ""
    return f"<h3>Ad-longevity — who keeps paying (and for how long)</h3>{timeline}{cards_html}"


def _content_section(scores, intel, peers, accent):
    cs = scores.get("content_signals", {})
    # format-mix donut aggregated across peers
    fmt = {}
    for h in peers:
        for k, v in ((intel["competitors"].get(h, {}).get("instagram", {}) or {})
                     .get("format_mix", {}) or {}).items():
            fmt[k] = fmt.get(k, 0) + v
    palette_seq = [accent, "#d98a1f", "#1f7a3f", "#6f675a"]
    donut = _donut([(k, v, palette_seq[i % len(palette_seq)]) for i, (k, v) in enumerate(fmt.items())],
                   accent=accent) if fmt else ""
    # comment-funnel bars: comments vs likes per peer
    cf_rows = []
    for r in cs.get("rows", []):
        cf_rows.append((f"{r['handle']} · comments", r["avg_comments"]))
        cf_rows.append((f"{r['handle']} · likes", r["avg_likes"]))
    funnel = _hbars(cf_rows, accent=accent) if cf_rows else ""
    # real example posts — top post per peer, image-embedded
    thumbs = []
    for h in peers:
        posts = ((intel["competitors"].get(h, {}).get("instagram", {}) or {})
                 .get("top_posts", []))
        if not posts:
            continue
        p = posts[0]
        img = _data_uri(p.get("thumbnail"))
        media = (f"<img class='pimg' src='{img}'/>" if img
                 else f"<div class='pimg ph'>IG</div>")
        thumbs.append(
            f"<div class='pcard'>{media}"
            f"<div class='p-meta'>{_esc(h)} · {int(p.get('comments',0)):,} comments</div>"
            f"<div class='p-cap'>{_esc((p.get('caption') or '')[:90])}</div></div>")
    thumb_html = f"<div class='pcards'>{''.join(thumbs)}</div>" if thumbs else ""
    funnel_note = (f"<div class='callout'>{_esc(cs.get('headline'))}</div>"
                   if cs.get("headline") else "")
    return (f"<h3>Format mix — what the category posts</h3>{donut}"
            f"<h3>The comment-to-DM funnel — comments beat likes</h3>{funnel_note}{funnel}"
            f"<h3>What the posts actually look like</h3>{thumb_html}")


def _route(narrative):
    steps = narrative.get("route_steps", [])
    out = []
    for i, s in enumerate(steps, 1):
        out.append(
            f"<div class='step'><div class='step-n'>{i}</div>"
            f"<div class='step-body'><div class='step-h'>{_verdict_badge(s.get('verdict','TEST'))}"
            f"<b>{_esc(s.get('channel'))}</b> — {_esc(s.get('action'))}</div>"
            f"<div class='step-why'>{_esc(s.get('why'))}</div></div></div>")
    return f"<div class='roadmap'>{''.join(out)}</div>"


def _provenance(scores):
    rows = []
    for c in scores.get("channels", []):
        p = c.get("provenance", {})
        rows.append(f"<tr><td class='mv'>{_esc(c['channel'])}</td>"
                    f"<td><span class='chip real'>{_esc(p.get('tag','REAL'))}</span></td>"
                    f"<td class='ml'>{_esc(p.get('source'))}</td>"
                    f"<td>{_esc(p.get('note'))}</td></tr>")
    return (f"<table><tr><td class='ml'>Channel</td><td>Basis</td>"
            f"<td class='ml'>Source</td><td class='ml'>Derivation</td></tr>{''.join(rows)}</table>")


# ───────────────────────────────────────── CSS
def _css(palette):
    accent = palette.get("accent", "#b23a2e")
    ink = palette.get("ink", "#211d18")
    return _FONTS + """
    @page { size: A4; margin: 16mm 15mm 18mm 15mm; background:#fff; }
    * { box-sizing: border-box; }
    html,body { background:#fff !important; color:%(INK)s; margin:0; padding:0;
        font-family:'Newsreader',serif; -webkit-print-color-adjust:exact; print-color-adjust:exact; }
    h1,h2,h3 { font-family:'Fraunces',serif; color:%(INK)s; letter-spacing:-0.01em; }
    .part { page-break-before:always; padding-top:4mm; }
    .part:first-of-type { page-break-before:avoid; }
    .eyebrow { font-size:11px; letter-spacing:.22em; text-transform:uppercase; color:%(ACCENT)s;
        font-weight:600; margin-bottom:6px; }
    h1.cover { font-size:40px; font-weight:900; line-height:1.04; margin:0 0 10px; }
    h2 { font-size:24px; font-weight:700; margin:0 0 8px; }
    h3 { font-size:15px; font-weight:700; margin:18px 0 8px; }
    p,li,td { font-size:12.5px; line-height:1.5; color:#2a2620; }
    .rule { height:4px; width:64px; background:%(ACCENT)s; border-radius:2px; margin:10px 0 16px; }
    .sub { font-size:14px; color:#6f675a; }
    .basis-line { font-size:11px; color:#8a8270; margin-top:6px; }
    /* stat cards */
    .statgrid { display:flex; flex-wrap:wrap; gap:12px; margin:14px 0; }
    .statcard { flex:1 1 30%%; min-width:180px; border:1px solid #ece6da; border-radius:10px;
        padding:14px; background:#fff; }
    .sc-channel { font-family:'Fraunces',serif; font-weight:700; font-size:17px; margin:8px 0 4px; }
    .sc-line { font-size:12px; color:#4a463f; line-height:1.45; }
    .vbadge { display:inline-block; font-family:'Newsreader',serif; font-size:10px; font-weight:700;
        letter-spacing:.06em; text-transform:uppercase; padding:2px 8px; border-radius:8px; }
    /* channel grid */
    .cgrow { background:#fff; border:1px solid #ece6da; border-radius:8px; padding:12px 14px; margin:8px 0; }
    .cg-head { display:flex; align-items:center; gap:8px; margin-bottom:4px; }
    .cg-name { font-family:'Fraunces',serif; font-weight:700; font-size:15px; }
    .cg-line { font-size:12px; color:#3a362f; line-height:1.45; }
    .cg-meta { font-size:11px; color:%(ACCENT)s; font-weight:600; margin-top:4px; }
    .wedge { font-size:9px; font-weight:700; letter-spacing:.1em; color:#fff; background:%(ACCENT)s;
        padding:2px 7px; border-radius:7px; }
    .muted { color:#9a9286; }
    /* bars + charts */
    .bars { margin:10px 0 6px; }
    .barrow { display:flex; align-items:center; gap:10px; margin:5px 0; }
    .blabel { width:34%%; font-size:11px; color:#5a554c; text-align:right; }
    .btrack { flex:1; background:#f0ece4; border-radius:5px; height:14px; overflow:hidden; }
    .bfill { height:100%%; border-radius:5px; }
    .bval { width:74px; font-size:11px; font-weight:600; color:%(INK)s; }
    .chartrow { display:flex; align-items:center; gap:18px; margin:10px 0; }
    .legend { font-size:12px; }
    .lg { display:flex; align-items:center; gap:7px; margin:3px 0; color:#4a463f; }
    .sw { width:11px; height:11px; border-radius:3px; display:inline-block; }
    .callout { background:#fbeae8; border-left:4px solid %(ACCENT)s; padding:10px 12px; border-radius:6px;
        font-size:12.5px; color:#3a362f; margin:8px 0; line-height:1.5; }
    /* ad + post cards */
    .adcards,.pcards { display:flex; flex-wrap:wrap; gap:10px; margin:10px 0; }
    .adcard,.pcard { flex:1 1 22%%; min-width:120px; border:1px solid #ece6da; border-radius:8px;
        overflow:hidden; background:#fff; }
    .adimg,.pimg { width:100%%; height:120px; object-fit:cover; display:block; }
    .adimg.ph,.pimg.ph { display:flex; align-items:center; justify-content:center; background:#f3efe7;
        color:#b3ab9b; font-family:'Fraunces',serif; font-weight:700; font-size:13px; }
    .ad-days,.p-meta { font-size:10.5px; font-weight:700; color:%(ACCENT)s; padding:6px 8px 0; }
    .ad-body,.p-cap { font-size:10.5px; color:#5a554c; padding:2px 8px 8px; line-height:1.4; }
    .ad-cta { font-size:10px; color:#8a8270; padding:0 8px 8px; font-style:italic; }
    /* roadmap */
    .roadmap { margin:10px 0; }
    .step { display:flex; gap:12px; margin:10px 0; }
    .step-n { width:26px; height:26px; flex:0 0 26px; border-radius:50%%; background:%(ACCENT)s; color:#fff;
        font-family:'Fraunces',serif; font-weight:700; font-size:13px; display:flex; align-items:center;
        justify-content:center; }
    .step-h { font-size:13px; color:%(INK)s; }
    .step-why { font-size:12px; color:#5a554c; margin-top:3px; line-height:1.45; }
    .intro { font-family:'Fraunces',serif; font-size:15px; font-style:italic; color:#3a362f;
        line-height:1.5; margin:6px 0 12px; }
    /* table + chips */
    table { width:100%%; border-collapse:collapse; margin:8px 0 14px; }
    td { padding:6px 8px; border-bottom:1px solid #ece6da; vertical-align:top; font-size:11.5px; }
    .ml { color:#6f675a; } .mv { font-weight:600; }
    .chip { display:inline-block; font-size:10px; font-weight:600; padding:1px 6px; border-radius:8px; }
    .chip.real { background:#e6f2e9; color:#1f7a3f; }
    .foot { position:fixed; bottom:6mm; left:0; right:0; text-align:center; font-size:10px; color:#b3ab9b; }
    """ % {"ACCENT": accent, "INK": ink}


def _section(eyebrow, title, intro, inner):
    intro_html = f"<div class='intro'>{_esc(intro)}</div>" if intro else ""
    return (f"<section class='part'><div class='eyebrow'>{_esc(eyebrow)}</div>"
            f"<h2>{_esc(title)}</h2><div class='rule'></div>{intro_html}{inner}</section>")


def _build_html(scores, intel, narrative, palette):
    peers = scores.get("tiers", {}).get("peers", [])
    accent = palette.get("accent", "#b23a2e")
    intros = narrative.get("intros", {})
    brand = scores.get("brand_slug", "").replace("-", " ").title()

    cover = (f"<section class='part'>"
             f"<div class='eyebrow'>Go-to-Market Intelligence · v7</div>"
             f"<h1 class='cover'>{_esc(narrative.get('headline','Where to promote, and how'))}</h1>"
             f"<div class='rule'></div>"
             f"<p class='sub'>{_esc(narrative.get('subhead',''))}</p>"
             f"<p class='basis-line'>{_esc(brand)} · built from real multi-platform competitor scrapes "
             f"({', '.join(_esc(p) for p in peers)} + category leader) · "
             f"scraped {_esc((intel.get('scraped_at') or '')[:10])}</p>"
             f"<h3>The verdict, in one screen</h3>{_snapshot(narrative)}</section>")

    channel_map = _section("Section 2 · WHERE", "The Channel Map",
                           intros.get("channel_map"), _channel_grid(scores))
    ad = _section("Section 3 · MARKETING", "Ad Intelligence — the money signal",
                  intros.get("ad"), _ad_section(scores, intel, accent))
    content = _section("Section 4 · SOCIAL", "What Content Is Working",
                       intros.get("content"), _content_section(scores, intel, peers, accent))
    gaps_inner = "".join(
        f"<div class='callout'><b>{_esc(g['channel'])}</b> — {_esc(g['headline'])}</div>"
        for g in scores.get("gaps", [])) or "<p class='muted'>No uncontested wedge detected this pass.</p>"
    gap = _section("Section 6 · THE OPENING", "The Gap to Own", intros.get("gap"), gaps_inner)
    route = _section("Section 7 · PAYOFF", "The Route Forward", intros.get("route"), _route(narrative))
    appendix = _section("Appendix", "Provenance & Methodology", None, _provenance(scores))

    body = (cover + channel_map + ad + content + gap + route + appendix
            + "<div class='foot'>GRID CONTROL · real-data GTM intelligence · v7</div>")
    return ("<!doctype html><html><head><meta charset='utf-8'><style>"
            + _css(palette) + "</style></head><body>" + body + "</body></html>")


def render_v7(scores: dict, intel: dict, narrative: dict, palette: dict, out_pdf) -> Path:
    out_pdf = Path(out_pdf)
    out_pdf.parent.mkdir(parents=True, exist_ok=True)
    html = _build_html(scores, intel, narrative, palette)
    with sync_playwright() as pw:
        browser = pw.chromium.launch()
        try:
            page = browser.new_page()
            page.set_content(html, wait_until="networkidle", timeout=45000)
            page.wait_for_timeout(400)
            page.pdf(path=str(out_pdf), format="A4", print_background=True,
                     prefer_css_page_size=True,
                     margin={"top": "0", "bottom": "0", "left": "0", "right": "0"})
        finally:
            browser.close()
    return out_pdf
