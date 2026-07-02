"""
agents/brand_book_v7_renderer.py — Brand-Book v7 HTML→PDF (BRAND-CENTERED onboarding audit).

Renders the brand-as-hero audit: the client's OWN real numbers up top, a "you vs the
category" benchmark as the centerpiece, the channel map, the winning mechanic (the HOW)
with the brand's specific gap, the paid money-signal, and a sequenced route — all visual.

Premium pass (the deliverable is the client's first impression):
hero stat tiles · dramatic you-vs-category bars · channel verdict grid · comment-funnel
chart with the brand's gap lit · inline-SVG charts (no network dep) · base64-embedded real
thumbnails (survive CDN expiry) · forced white bg (§5) · per-brand accent · denser flow
(sections share pages; only cards/charts are kept whole).

Public:  render_v7(report: dict, intel: dict, palette: dict, out_pdf) -> Path
`report` = output of brand_book_v7.generate (brand, benchmark, scores, narrative).
"""
from __future__ import annotations

import base64
import urllib.request
from pathlib import Path

from playwright.sync_api import sync_playwright

_FONTS = ("@import url('https://fonts.googleapis.com/css2?"
          "family=Fraunces:opsz,wght@9..144,400;9..144,500;9..144,600;9..144,700;9..144,900"
          "&family=Newsreader:opsz,wght@6..72,400;6..72,500;6..72,600"
          "&family=IBM+Plus+Mono:wght@500&display=swap');")

_VERDICT = {
    "RIDE": ("#1f7a3f", "#e8f3eb", "Ride"),
    "GAP":  ("#b23a2e", "#fbeae8", "Own the gap"),
    "TEST": ("#9a6a16", "#f7efe0", "Test"),
    "SKIP": ("#6f675a", "#efece6", "Skip"),
    "NO_DATA": ("#a9a094", "#f3f1ed", "Not scraped"),
}


# ─────────────────────────────── image embed (survives CDN expiry)
def _data_uri(url: str, timeout: float = 8.0):
    if not url:
        return None
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=timeout) as r:
            if r.status != 200:
                return None
            blob = r.read()
        if len(blob) < 512:
            return None
        ctype = "image/png" if blob[:4] == b"\x89PNG" else "image/jpeg"
        return f"data:{ctype};base64," + base64.b64encode(blob).decode()
    except Exception:
        return None


def _esc(s) -> str:
    if s is None:
        return ""
    return (str(s).replace("&", "&amp;").replace("<", "&lt;")
            .replace(">", "&gt;").replace("\n", "<br>"))


def _num(n) -> str:
    if n is None:
        return "—"
    if isinstance(n, float) and n.is_integer():
        n = int(n)
    return f"{n:,}" if isinstance(n, (int,)) else (f"{n:,.1f}" if isinstance(n, float) else _esc(n))


# ─────────────────────────────── inline-SVG charts
def _donut(segments, size=104, accent="#b23a2e"):
    import math
    total = sum(v for _, v, _ in segments) or 1
    r, cx, cy, sw = size / 2 - 11, size / 2, size / 2, 16
    circ = 2 * math.pi * r
    off, arcs = 0.0, []
    for _l, val, col in segments:
        dash = (val / total) * circ
        arcs.append(f"<circle cx='{cx}' cy='{cy}' r='{r}' fill='none' stroke='{col}' "
                    f"stroke-width='{sw}' stroke-dasharray='{dash:.2f} {circ-dash:.2f}' "
                    f"stroke-dashoffset='{-off:.2f}' transform='rotate(-90 {cx} {cy})'/>")
        off += dash
    legend = "".join(f"<div class='lg'><span class='sw' style='background:{col}'></span>"
                     f"{_esc(l)} · {int(v)}</div>" for l, v, col in segments)
    return (f"<div class='chartrow'><svg width='{size}' height='{size}' viewBox='0 0 {size} {size}'>"
            f"{''.join(arcs)}</svg><div class='legend'>{legend}</div></div>")


def _hbars(rows, accent="#b23a2e", highlight_brand=False):
    """rows = [(label, value, is_brand)] or [(label, value)]."""
    norm = [(r[0], r[1], (r[2] if len(r) > 2 else False)) for r in rows]
    mx = max((v for _, v, _ in norm), default=1) or 1
    out = []
    for lbl, val, is_brand in norm:
        w = max(1.5, val / mx * 100)
        col = accent if is_brand else "#cfc8bc"
        tag = "<span class='youtag'>YOU</span>" if is_brand else ""
        lblcls = "blabel brandlabel" if is_brand else "blabel"
        out.append(f"<div class='barrow'><div class='{lblcls}'>{_esc(lbl)}{tag}</div>"
                   f"<div class='btrack'><div class='bfill' style='width:{w:.1f}%;background:{col}'></div></div>"
                   f"<div class='bval'>{_num(val)}</div></div>")
    return f"<div class='bars'>{''.join(out)}</div>"


def _longevity(rows, accent="#b23a2e"):
    mx = max((d for _, d, _ in rows), default=1) or 1
    out = []
    for handle, days, adv in rows:
        if adv:
            w = max(3, days / mx * 100)
            out.append(f"<div class='barrow'><div class='blabel'>{_esc(handle)}</div>"
                       f"<div class='btrack'><div class='bfill' style='width:{w:.0f}%;background:{accent}'></div></div>"
                       f"<div class='bval'>{days}d live</div></div>")
        else:
            out.append(f"<div class='barrow'><div class='blabel'>{_esc(handle)}</div>"
                       f"<div class='btrack'><div class='bfill' style='width:2%;background:#ddd7cd'></div></div>"
                       f"<div class='bval muted'>no ads</div></div>")
    return f"<div class='bars'>{''.join(out)}</div>"


def _badge(v):
    col, bg, label = _VERDICT.get(v, _VERDICT["NO_DATA"])
    return f"<span class='vbadge' style='color:{col};background:{bg}'>{label}</span>"


# ─────────────────────────────── sections
def _hero_stats(bi):
    tiles = [
        ("Followers", _num(bi.get("followers")), "the audience today"),
        ("Posts shipped", _num(bi.get("media_count")), "content live"),
        ("Avg reach / post", _num(bi.get("avg_reach")), "real, last posts"),
        ("Avg engagement", _num(round((bi.get("avg_likes") or 0) + (bi.get("avg_comments") or 0), 1)),
         "likes + comments"),
    ]
    return "<div class='herostats'>" + "".join(
        f"<div class='htile'><div class='hn'>{v}</div><div class='hl'>{_esc(l)}</div>"
        f"<div class='hs'>{_esc(s)}</div></div>" for l, v, s in tiles) + "</div>"


def _you_vs_category(benchmark, accent):
    # label the role model distinctly from competitors in the bar list
    rm = benchmark.get("role_model") or {}
    rm_handle = rm.get("handle")
    rows = []
    for r in benchmark["rows"]:
        label = r["handle"]
        if r["handle"] == rm_handle:
            label = f"{r['handle']} (role model)"
        rows.append((label, r["engagement"], r["is_brand"]))
    bars = _hbars(rows, accent=accent, highlight_brand=True)
    med = benchmark.get("category_median")
    cc = benchmark.get("competitor_ceiling") or {}
    note = (f"<div class='callout'>Category median is <b>{_num(med)}</b>. Your near-term target is your top "
            f"competitor <b>{_esc(cc.get('handle'))}</b> at <b>{_num(cc.get('engagement'))}</b>; your long-term "
            f"role model <b>{_esc(rm_handle)}</b> at <b>{_num(rm.get('engagement'))}</b> shows the destination. "
            f"The gap is the runway — the rest of this audit is the route.</div>"
            if cc else "")
    return bars + note


def _channel_grid(scores):
    out = []
    for c in scores.get("channels", []):
        col, bg, _ = _VERDICT.get(c["verdict"], _VERDICT["NO_DATA"])
        gap = "<span class='wedge'>WEDGE</span>" if c.get("is_gap") else ""
        money = (f"<div class='cg-meta'>Money signal: {c['money_signal_days']}d sustained spend</div>"
                 if c.get("money_signal_days") else "")
        out.append(f"<div class='cgrow' style='border-left:5px solid {col}'>"
                   f"<div class='cg-head'>{_badge(c['verdict'])}<span class='cg-name'>{_esc(c['channel'])}</span>{gap}</div>"
                   f"<div class='cg-line'>{_esc(c['headline'])}</div>{money}</div>")
    for c in scores.get("channels_absent", []):
        col, _, _ = _VERDICT["NO_DATA"]
        out.append(f"<div class='cgrow' style='border-left:5px solid {col}'>"
                   f"<div class='cg-head'>{_badge('NO_DATA')}<span class='cg-name'>{_esc(c['channel'])}</span></div>"
                   f"<div class='cg-line muted'>{_esc(c['headline'])}</div></div>")
    return "".join(out)


def _snapshot(narrative):
    cards = []
    for s in narrative.get("snapshot", []):
        col, _, _ = _VERDICT.get(s.get("verdict", "TEST"), _VERDICT["NO_DATA"])
        cards.append(f"<div class='statcard' style='border-top:4px solid {col}'>{_badge(s.get('verdict','TEST'))}"
                     f"<div class='sc-channel'>{_esc(s.get('channel'))}</div>"
                     f"<div class='sc-line'>{_esc(s.get('line'))}</div></div>")
    return f"<div class='statgrid'>{''.join(cards)}</div>"


def _exec_summary(narrative):
    items = narrative.get("exec_summary") or []
    cards = "".join(f"<div class='execitem'><div class='execn'>{i}</div>"
                    f"<div class='exectext'>{_esc(t)}</div></div>" for i, t in enumerate(items, 1))
    return f"<div class='execlist'>{cards}</div>"


def _identity(report):
    n = report["narrative"].get("identity") or {}
    gaps = (report.get("signals", {}).get("identity", {}) or {}).get("identity_gaps", [])
    gap_list = "".join(f"<li class='gapitem'>{_esc(g)}</li>" for g in gaps)
    return (f"<p class='lead'>{_esc(n.get('summary'))}</p>"
            f"<h3>The gap — who you say you are vs what your account shows</h3>"
            f"<div class='callout'>{_esc(n.get('external_image_gap'))}</div>"
            + (f"<ul class='gaps'>{gap_list}</ul>" if gap_list else ""))


def _audience(report):
    return f"<p class='lead'>{_esc(report['narrative'].get('audience'))}</p>"


def _how_winners(report, intel, accent):
    pb = report.get("signals", {}).get("playbook", {})
    bi = report["brand"]["instagram"]
    n = report["narrative"]
    # the comment funnel chart: competitors' comments vs likes + the brand row (the gap)
    cs = report["scores"].get("content_signals", {})
    cf = []
    for r in cs.get("rows", []):
        cf.append((f"{r['handle']} · comments", r["avg_comments"], False))
        cf.append((f"{r['handle']} · likes", r["avg_likes"], False))
    cf.append((f"@{bi.get('username')} · comments", bi.get("avg_comments") or 0, True))
    cf.append((f"@{bi.get('username')} · likes", bi.get("avg_likes") or 0, True))
    funnel = _hbars(cf, accent=accent, highlight_brand=True)
    # real keyword-CTA examples (the exact mechanic)
    kw = "".join(f"<tr><td class='mv'>{_esc(k['handle'])}</td>"
                 f"<td><span class='kw'>comment “{_esc(k['keyword'])}”</span></td>"
                 f"<td class='ml'>{_num(k['comments'])} comments</td></tr>"
                 for k in pb.get("keyword_cta_examples", [])[:5])
    kw_table = (f"<h3>The mechanic, with receipts — “comment a word → I DM you”</h3>"
                f"<table>{kw}</table>") if kw else ""
    # real winning hooks
    hooks = "".join(f"<li class='hookitem'><span class='hookc'>{_num(h['comments'])}c</span> "
                    f"“{_esc(h['hook'])}”</li>" for h in pb.get("top_category_hooks", [])[:4])
    hook_list = f"<h3>The hooks that pulled those comments</h3><ul class='hooks'>{hooks}</ul>" if hooks else ""
    return (f"<div class='intro2'>{_esc(n.get('how_winners_win'))}</div>"
            f"<h3>Comments beat likes — and you're not in the game yet</h3>{funnel}"
            f"{kw_table}{hook_list}")


def _role_model(report):
    rm = report["benchmark"].get("role_model") or {}
    bi_rows = []
    rm_handle = rm.get("handle", "").lstrip("@")
    comp = report.get("_intel", {}).get("competitors", {}).get(rm_handle, {})
    yt = (comp.get("youtube") or {})
    if yt.get("status") == "ok":
        bi_rows.append(("YouTube", f"{_num(yt.get('subscribers'))} subs · {_num(yt.get('avg_views'))} avg views"))
    ma = (comp.get("meta_ads") or {})
    if ma.get("status") == "advertising":
        bi_rows.append(("Meta Ads", f"{_num(ma.get('active_ads'))} live · up to {_num(ma.get('max_days_running'))}d"))
    stats = "".join(f"<div class='rmstat'><div class='rml'>{_esc(l)}</div><div class='rmv'>{_esc(v)}</div></div>"
                    for l, v in bi_rows)
    return (f"<p class='lead'>{_esc(report['narrative'].get('role_model'))}</p>"
            + (f"<div class='rmstats'>{stats}</div>" if stats else ""))


def _your_playbook(narrative):
    items = narrative.get("your_playbook") or []
    return "<ol class='playbook'>" + "".join(f"<li>{_esc(t)}</li>" for t in items) + "</ol>"


def _roadmap(narrative):
    rm = narrative.get("roadmap") or {}
    cols = []
    for i, key in enumerate(("month_1", "month_2", "month_3"), 1):
        m = rm.get(key) or {}
        moves = "".join(f"<li>{_esc(x)}</li>" for x in (m.get("moves") or []))
        cols.append(f"<div class='rmcol'><div class='rmmonth'>Month {i}</div>"
                    f"<div class='rmtitle'>{_esc(m.get('title'))}</div><ul>{moves}</ul></div>")
    return f"<div class='roadmapgrid'>{''.join(cols)}</div>"


def _money_section(report, intel, accent):
    scores = report["scores"]
    ads = next((c for c in scores["channels"] if c["channel"].startswith("Meta Ads")), {})
    rows = [(r["handle"], r.get("max_days_running", 0), r.get("advertising")) for r in ads.get("rows", [])]
    timeline = _longevity(rows, accent)
    owner = ads.get("money_signal_owner")
    comp = intel.get("competitors", {}).get(owner, {}) if owner else {}
    top = (comp.get("meta_ads", {}) or {}).get("top_ads", [])[:3]
    cards = []
    for a in top:
        img = _data_uri(a.get("image"))
        media = f"<img class='adimg' src='{img}'/>" if img else f"<div class='adimg ph'>{_esc(a.get('media_type','AD'))}</div>"
        cards.append(f"<div class='adcard'>{media}<div class='ad-days'>{a.get('days_running','?')}d live</div>"
                     f"<div class='ad-body'>{_esc((a.get('body') or '')[:120])}</div></div>")
    return f"<div class='intro2'>{_esc(report['narrative'].get('intros',{}).get('money'))}</div>" \
           f"<h3>Ad-longevity — who keeps paying</h3>{timeline}" \
           + (f"<div class='adcards'>{''.join(cards)}</div>" if cards else "")


def _route(narrative):
    out = []
    for i, s in enumerate(narrative.get("route_steps", []), 1):
        out.append(f"<div class='step'><div class='step-n'>{i}</div><div class='step-body'>"
                   f"<div class='step-h'>{_badge(s.get('verdict','TEST'))}<b>{_esc(s.get('channel'))}</b> — {_esc(s.get('action'))}</div>"
                   f"<div class='step-why'>{_esc(s.get('why'))}</div></div></div>")
    return f"<div class='roadmap'>{''.join(out)}</div>"


def _foundation(narrative):
    """Phase H sign-off payload — the prescriptive Foundation. Empty string if absent."""
    f = narrative.get("foundation") or {}
    if not f:
        return ""
    voice = f.get("voice") or {}
    chips = lambda items: "".join(f"<span class='fchip'>{_esc(x)}</span>" for x in (items or []))
    # Pillars with a one-line proof when available; fall back to plain pillar names.
    pe = f.get("pillars_explained") or []
    if pe:
        pillars = "".join(f"<li><b>{_esc(p.get('pillar'))}</b> — {_esc(p.get('proof'))}</li>" for p in pe)
    else:
        pillars = "".join(f"<li>{_esc(p)}</li>" for p in (f.get("pillars") or []))
    do = "".join(f"<li>{_esc(x)}</li>" for x in (voice.get("do") or []))
    dont = "".join(f"<li>{_esc(x)}</li>" for x in (voice.get("dont") or []))
    purpose_html = (f"<div class='callout'><b>Why you exist.</b> {_esc(f.get('purpose'))}</div>"
                    if f.get("purpose") else "")
    return (purpose_html
            + f"<div class='callout'><b>Positioning.</b> {_esc(f.get('positioning_statement'))}</div>"
            f"<p class='lead'><b>Value proposition.</b> {_esc(f.get('value_prop'))}</p>"
            f"<h3>Content pillars to own</h3><ol class='playbook'>{pillars}</ol>"
            f"<h3>Ideal audience</h3><p class='lead'>{_esc(f.get('icp'))}</p>"
            f"<h3>90-day north star</h3><p class='lead'>{_esc(f.get('north_star'))}</p>"
            f"<h3>Voice</h3><p class='lead'>{_esc(voice.get('personality'))}</p>"
            f"<div class='vgrid'><div><div class='vh'>Do</div><ul>{do}</ul></div>"
            f"<div><div class='vh'>Don't</div><ul>{dont}</ul></div></div>"
            f"<div class='vvocab'><b>Use:</b> {chips(voice.get('vocab_use'))}<br><b>Avoid:</b> {chips(voice.get('vocab_avoid'))}</div>")


def _provenance(report):
    rows = [("Brand IG account", "REAL", "Instagram Login API (connected account)",
             f"@{report['brand']['instagram'].get('username')} · {_num(report['brand']['instagram'].get('followers'))} followers, "
             f"{_num(report['brand']['instagram'].get('media_count'))} posts")]
    for c in report["scores"].get("channels", []):
        p = c.get("provenance", {})
        rows.append((c["channel"], p.get("tag", "REAL"), p.get("source"), p.get("note")))
    body = "".join(f"<tr><td class='mv'>{_esc(a)}</td><td><span class='chip real'>{_esc(b)}</span></td>"
                   f"<td class='ml'>{_esc(c)}</td><td>{_esc(d)}</td></tr>" for a, b, c, d in rows)
    return (f"<table><tr><td class='ml'>What</td><td>Basis</td><td class='ml'>Source</td>"
            f"<td class='ml'>Detail</td></tr>{body}</table>")


# ─────────────────────────────── CSS (premium)
def _css(palette):
    accent = palette.get("accent", "#b23a2e")
    ink = palette.get("ink", "#211d18")
    return _FONTS + """
    @page { size:A4; margin:15mm 14mm 16mm; background:#fff; }
    *{box-sizing:border-box;}
    html,body{background:#fff!important;color:%(INK)s;margin:0;padding:0;font-family:'Newsreader',serif;
        -webkit-print-color-adjust:exact;print-color-adjust:exact;}
    h1,h2,h3{font-family:'Fraunces',serif;color:%(INK)s;letter-spacing:-0.015em;}
    .section{padding-top:7mm;}
    .section.brk{page-break-before:always;}
    .card,.cgrow,.statcard,.htile,.adcard,.step,.chartrow,.callout,.bars{page-break-inside:avoid;}
    .eyebrow{font-family:'IBM Plus Mono',monospace;font-size:10px;letter-spacing:.24em;text-transform:uppercase;
        color:%(ACCENT)s;font-weight:500;margin-bottom:8px;}
    .secnum{font-family:'Fraunces',serif;font-weight:900;font-size:13px;color:%(ACCENT)s;letter-spacing:.04em;}
    h1.cover{font-size:44px;font-weight:900;line-height:1.03;margin:2px 0 12px;max-width:90%%;}
    h2{font-size:25px;font-weight:700;margin:0 0 4px;}
    h3{font-size:14px;font-weight:700;margin:16px 0 7px;color:%(INK)s;}
    p,li,td{font-size:12.5px;line-height:1.52;color:#2c2820;}
    .rule{height:3px;width:54px;background:%(ACCENT)s;border-radius:2px;margin:9px 0 15px;}
    .sub{font-size:14px;color:#5f584d;max-width:88%%;line-height:1.5;}
    .bioline{font-family:'IBM Plus Mono',monospace;font-size:10.5px;color:#8a8270;margin-top:10px;}
    .intro2{font-family:'Fraunces',serif;font-size:15px;font-style:italic;color:#39342c;line-height:1.5;margin:4px 0 12px;}
    .lead{font-size:13.5px;color:#39342c;line-height:1.55;margin:10px 0;}
    /* hero stats */
    .herostats{display:flex;gap:11px;margin:20px 0 8px;}
    .htile{flex:1;border:1px solid #e7e0d3;border-radius:11px;padding:14px 13px;background:linear-gradient(180deg,#fff,#fcfaf6);}
    .htile .hn{font-family:'Fraunces',serif;font-weight:900;font-size:30px;color:%(INK)s;line-height:1;}
    .htile .hl{font-size:11px;font-weight:600;color:#4a463f;margin-top:7px;text-transform:uppercase;letter-spacing:.04em;}
    .htile .hs{font-size:10.5px;color:#9a9286;margin-top:2px;}
    /* stat cards */
    .verdictstrip-label{font-family:'IBM Plus Mono',monospace;font-size:10px;letter-spacing:.18em;
        text-transform:uppercase;color:#8a8270;margin:22px 0 0;}
    .statgrid{display:flex;flex-wrap:wrap;gap:11px;margin:13px 0;}
    .statcard{flex:1 1 30%%;min-width:175px;border:1px solid #e7e0d3;border-radius:10px;padding:13px;background:#fff;}
    .sc-channel{font-family:'Fraunces',serif;font-weight:700;font-size:16px;margin:8px 0 4px;}
    .sc-line{font-size:11.5px;color:#4a463f;line-height:1.42;}
    .vbadge{display:inline-block;font-family:'IBM Plus Mono',monospace;font-size:9px;font-weight:500;
        letter-spacing:.08em;text-transform:uppercase;padding:3px 8px;border-radius:7px;}
    /* channel grid */
    .cgrow{background:#fff;border:1px solid #e7e0d3;border-radius:9px;padding:11px 13px;margin:7px 0;}
    .cg-head{display:flex;align-items:center;gap:8px;margin-bottom:3px;}
    .cg-name{font-family:'Fraunces',serif;font-weight:700;font-size:14.5px;}
    .cg-line{font-size:11.5px;color:#3a362f;line-height:1.42;}
    .cg-meta{font-size:10.5px;color:%(ACCENT)s;font-weight:600;margin-top:4px;}
    .wedge{font-family:'IBM Plus Mono',monospace;font-size:8.5px;font-weight:500;letter-spacing:.1em;color:#fff;
        background:%(ACCENT)s;padding:2px 7px;border-radius:6px;}
    .muted{color:#9a9286;}
    /* bars + charts */
    .bars{margin:9px 0 4px;}
    .barrow{display:flex;align-items:center;gap:10px;margin:4px 0;}
    .blabel{width:38%%;font-size:11px;color:#5a554c;text-align:right;}
    .brandlabel{color:%(ACCENT)s;font-weight:700;}
    .youtag{display:inline-block;background:%(ACCENT)s;color:#fff;font-family:'IBM Plus Mono',monospace;
        font-size:8px;padding:1px 5px;border-radius:5px;margin-left:6px;vertical-align:middle;}
    .btrack{flex:1;background:#f1ede5;border-radius:5px;height:13px;overflow:hidden;}
    .bfill{height:100%%;border-radius:5px;}
    .bval{width:72px;font-size:11px;font-weight:600;color:%(INK)s;font-family:'IBM Plus Mono',monospace;}
    .chartrow{display:flex;align-items:center;gap:18px;margin:9px 0;}
    .legend{font-size:12px;}.lg{display:flex;align-items:center;gap:7px;margin:3px 0;color:#4a463f;}
    .sw{width:11px;height:11px;border-radius:3px;display:inline-block;}
    .callout{background:#fbeae8;border-left:4px solid %(ACCENT)s;padding:11px 13px;border-radius:7px;
        font-size:12.5px;color:#39342c;margin:9px 0;line-height:1.5;}
    /* foundation (sign-off) */
    .vgrid{display:flex;gap:18px;margin:6px 0;}
    .vgrid>div{flex:1;}
    .vh{font-family:'IBM Plus Mono',monospace;font-size:10px;letter-spacing:.12em;text-transform:uppercase;
        color:%(ACCENT)s;font-weight:600;margin-bottom:4px;}
    .vvocab{font-size:11.5px;color:#39342c;margin-top:10px;line-height:2;}
    .fchip{display:inline-block;font-family:'IBM Plus Mono',monospace;font-size:10px;background:#f1ede5;
        color:#4a463f;padding:2px 8px;border-radius:6px;margin:2px 4px 2px 0;}
    /* ad + post cards */
    .adcards{display:flex;flex-wrap:wrap;gap:9px;margin:9px 0;}
    .adcard{flex:1 1 30%%;min-width:130px;border:1px solid #e7e0d3;border-radius:8px;overflow:hidden;background:#fff;}
    .adimg{width:100%%;height:118px;object-fit:cover;display:block;}
    .adimg.ph{display:flex;align-items:center;justify-content:center;background:#f3efe7;color:#b3ab9b;
        font-family:'Fraunces',serif;font-weight:700;font-size:13px;height:118px;}
    .ad-days{font-family:'IBM Plus Mono',monospace;font-size:10px;font-weight:600;color:%(ACCENT)s;padding:6px 9px 0;}
    .ad-body{font-size:10.5px;color:#5a554c;padding:2px 9px 9px;line-height:1.4;}
    /* roadmap */
    .roadmap{margin:9px 0;}
    .step{display:flex;gap:13px;margin:11px 0;}
    .step-n{width:27px;height:27px;flex:0 0 27px;border-radius:50%%;background:%(ACCENT)s;color:#fff;
        font-family:'Fraunces',serif;font-weight:700;font-size:13px;display:flex;align-items:center;justify-content:center;}
    .step-h{font-size:13px;color:%(INK)s;}.step-h b{font-family:'Fraunces',serif;}
    .step-why{font-size:12px;color:#5a554c;margin-top:3px;line-height:1.45;}
    /* table */
    table{width:100%%;border-collapse:collapse;margin:8px 0 12px;page-break-inside:avoid;}
    td{padding:6px 8px;border-bottom:1px solid #ece6da;vertical-align:top;font-size:11px;}
    .ml{color:#6f675a;}.mv{font-weight:600;}
    .chip{display:inline-block;font-family:'IBM Plus Mono',monospace;font-size:9px;font-weight:500;padding:2px 6px;border-radius:6px;}
    .chip.real{background:#e8f3eb;color:#1f7a3f;}
    /* exec summary */
    .execlist{margin:10px 0;}
    .execitem{display:flex;gap:12px;align-items:flex-start;margin:9px 0;page-break-inside:avoid;}
    .execn{flex:0 0 24px;width:24px;height:24px;border-radius:6px;background:%(ACCENT)s;color:#fff;
        font-family:'Fraunces',serif;font-weight:700;font-size:12px;display:flex;align-items:center;justify-content:center;}
    .exectext{font-size:13px;color:#2c2820;line-height:1.5;padding-top:2px;}
    /* identity gaps */
    .gaps{margin:8px 0;padding-left:0;list-style:none;}
    .gapitem{font-size:12px;color:#3a362f;padding:6px 0 6px 22px;position:relative;border-bottom:1px solid #f1ede5;}
    .gapitem:before{content:"✕";position:absolute;left:0;color:%(ACCENT)s;font-weight:700;}
    /* how-winners */
    .kw{font-family:'IBM Plus Mono',monospace;font-size:11px;background:#fbeae8;color:%(ACCENT)s;
        padding:2px 7px;border-radius:6px;font-weight:500;}
    .hooks{margin:6px 0;padding-left:0;list-style:none;}
    .hookitem{font-size:12px;color:#3a362f;padding:5px 0;line-height:1.45;font-style:italic;}
    .hookc{font-family:'IBM Plus Mono',monospace;font-style:normal;font-size:10px;font-weight:600;
        color:#fff;background:%(ACCENT)s;padding:1px 6px;border-radius:5px;margin-right:6px;}
    /* role model */
    .rmstats{display:flex;gap:11px;margin:10px 0;}
    .rmstat{flex:1;border:1px solid #e7e0d3;border-radius:9px;padding:11px 13px;background:#fcfaf6;}
    .rml{font-family:'IBM Plus Mono',monospace;font-size:10px;text-transform:uppercase;letter-spacing:.06em;color:#8a8270;}
    .rmv{font-family:'Fraunces',serif;font-weight:700;font-size:15px;color:%(INK)s;margin-top:3px;}
    /* playbook */
    .playbook{margin:8px 0;padding-left:0;counter-reset:pb;list-style:none;}
    .playbook li{position:relative;padding:8px 0 8px 30px;font-size:12.5px;color:#2c2820;line-height:1.5;
        border-bottom:1px solid #f1ede5;page-break-inside:avoid;}
    .playbook li:before{counter-increment:pb;content:counter(pb);position:absolute;left:0;top:7px;width:20px;height:20px;
        background:%(ACCENT)s;color:#fff;border-radius:50%%;font-family:'Fraunces',serif;font-weight:700;font-size:11px;
        display:flex;align-items:center;justify-content:center;}
    /* roadmap */
    .roadmapgrid{display:flex;gap:11px;margin:12px 0;}
    .rmcol{flex:1;border:1px solid #e7e0d3;border-radius:10px;padding:13px;background:#fff;page-break-inside:avoid;}
    .rmmonth{font-family:'IBM Plus Mono',monospace;font-size:10px;letter-spacing:.1em;text-transform:uppercase;color:%(ACCENT)s;}
    .rmtitle{font-family:'Fraunces',serif;font-weight:700;font-size:14px;margin:4px 0 7px;color:%(INK)s;}
    .rmcol ul{margin:0;padding-left:15px;}
    .rmcol li{font-size:11px;color:#3a362f;line-height:1.4;margin:4px 0;}
    .foot{margin-top:9mm;padding-top:5mm;border-top:1px solid #ece6da;text-align:center;
        font-family:'IBM Plus Mono',monospace;font-size:9px;color:#bcb4a4;letter-spacing:.06em;
        page-break-before:avoid;}
    """ % {"ACCENT": accent, "INK": ink}


def _sec(num, eyebrow, title, inner, brk=True):
    cls = "section brk" if brk else "section"
    return (f"<section class='{cls}'><div class='eyebrow'><span class='secnum'>{_esc(num)}</span> &nbsp; {_esc(eyebrow)}</div>"
            f"<h2>{_esc(title)}</h2><div class='rule'></div>{inner}</section>")


def _build_html(report, intel, palette):
    report["_intel"] = intel                       # for _role_model lookups
    n = report["narrative"]
    bi = report["brand"]["instagram"]
    accent = palette.get("accent", "#b23a2e")
    name = report["meta"].get("brand")
    intros = n.get("intros", {})

    cover = (f"<section class='section'>"
             f"<div class='eyebrow'>Onboarding Brand Audit · prepared for @{_esc(bi.get('username'))}</div>"
             f"<h1 class='cover'>{_esc(n.get('headline','Your starting line, and the route from it'))}</h1>"
             f"<div class='rule'></div>"
             f"<p class='sub'>{_esc(n.get('subhead',''))}</p>"
             f"<div class='bioline'>{_esc(name)} · “{_esc((bi.get('biography') or '').splitlines()[0] if bi.get('biography') else '')}” · {_esc(report['meta'].get('date'))}</div>"
             f"{_hero_stats(bi)}"
             f"<p class='lead'>{_esc(n.get('starting_line'))}</p></section>")

    summary = _sec("00", "Executive summary", "What this audit found",
                   _exec_summary(n) + f"<div class='verdictstrip-label'>The channel verdict, in one screen</div>{_snapshot(n)}",
                   brk=False)

    sov_html = (f"<div class='callout'><b>Share of voice.</b> {_esc(n.get('share_of_voice'))}</div>"
                if n.get("share_of_voice") else "")
    ws_html = (f"<div class='callout'><b>Your open lane.</b> {_esc(n.get('white_space'))}</div>"
               if n.get("white_space") else "")
    where = _sec("01", "Where you stand", "You vs the category",
                 f"<p class='lead'>{_esc(n.get('where_you_stand'))}</p>"
                 f"{sov_html}"
                 f"<h3>Engagement per post — you against your category</h3>{_you_vs_category(report['benchmark'], accent)}"
                 f"{ws_html}")

    identity = _sec("02", "Brand identity", "Who you are — and the gap", _identity(report), brk=False)

    chan = _sec("03", "The map", "The channel map",
                f"<div class='intro2'>{_esc(intros.get('channel_map'))}</div>"
                f"{_channel_grid(report['scores'])}")

    aud = _sec("04", "Audience", "Who you're for", _audience(report), brk=False)

    how = _sec("05", "The mechanic", "How the competitors win",
               _how_winners(report, intel, accent))

    money = _sec("06", "The money signal", "Who's paying to win", _money_section(report, intel, accent), brk=False)

    rolemodel = _sec("07", "The destination", "Your role model", _role_model(report), brk=False)

    playbook = _sec("08", "Your move", "Your playbook",
                    f"<div class='intro2'>{_esc(intros.get('how'))}</div>{_your_playbook(n)}")

    roadmap = _sec("09", "The plan", "Your 90-day roadmap", _roadmap(n), brk=False)

    found_inner = _foundation(n)
    foundation = _sec("10", "Sign-off", "Your brand foundation", found_inner, brk=True) if found_inner else ""

    appendix = _sec("11", "Receipts", "Provenance & methodology", _provenance(report), brk=True)

    body = (cover + summary + where + identity + chan + aud + how + money + rolemodel + playbook + roadmap
            + foundation + appendix
            + f"<div class='foot'>GRID CONTROL · real-data brand audit · prepared for @{_esc(bi.get('username'))}</div>")
    return ("<!doctype html><html><head><meta charset='utf-8'><style>"
            + _css(palette) + "</style></head><body>" + body + "</body></html>")


def render_v7(report: dict, intel: dict, palette: dict, out_pdf) -> Path:
    out_pdf = Path(out_pdf)
    out_pdf.parent.mkdir(parents=True, exist_ok=True)
    html = _build_html(report, intel, palette)
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
