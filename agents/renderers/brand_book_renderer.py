"""
agents/brand_book_renderer.py — Brand-Book v6 HTML→PDF (Phase G).

Renders the structured 8-part report dict (from brand_book.BrandBook) to a
multi-page PDF via Playwright `page.pdf()`. Distinct from the IG-slide
screenshot renderer: this is a paginated A4 document.

Spec §5: FORCE WHITE BACKGROUND (the dark-mode bug). We hard-set white on
html/body/@page and pass print_background=True so accent fills still render.

Public:
  render_brand_book(report: dict, palette: dict, out_pdf: Path) -> Path
palette = {"accent": "#rrggbb", "ink": "#rrggbb", "paper": "#ffffff"}
"""
from pathlib import Path
from playwright.sync_api import sync_playwright

_FONTS = ("@import url('https://fonts.googleapis.com/css2?"
          "family=Fraunces:opsz,wght@9..144,500;9..144,700;9..144,900"
          "&family=Newsreader:opsz,wght@6..72,400;6..72,500;6..72,600"
          "&display=swap');")


def _esc(s) -> str:
    if s is None:
        return ""
    return (str(s).replace("&", "&amp;").replace("<", "&lt;")
            .replace(">", "&gt;").replace("\n", "<br>"))


def _chip(basis: str) -> str:
    real = basis == "REAL"
    label = "REAL" if real else "EST"
    cls = "chip real" if real else "chip est"
    return f"<span class='{cls}'>{label}</span>"


def _metric_row(label: str, m: dict) -> str:
    val = _esc(m.get("value"))
    note = m.get("note")
    note_html = f"<div class='note'>{_esc(note)}</div>" if note else ""
    return (f"<tr><td class='ml'>{_esc(label)}</td>"
            f"<td class='mv'>{val} {_chip(m.get('basis','AI_ESTIMATED'))}{note_html}</td></tr>")


def _css(palette: dict) -> str:
    accent = palette.get("accent", "#b23a2e")
    ink = palette.get("ink", "#211d18")
    return _FONTS + """
    @page { size: A4; margin: 18mm 16mm 20mm 16mm; background: #ffffff; }
    * { box-sizing: border-box; }
    html, body { background: #ffffff !important; color: %(INK)s; margin: 0; padding: 0;
        font-family: 'Newsreader', serif; -webkit-print-color-adjust: exact; print-color-adjust: exact; }
    h1,h2,h3 { font-family: 'Fraunces', serif; color: %(INK)s; letter-spacing: -0.01em; }
    .part { page-break-before: always; padding-top: 6mm; }
    .part:first-of-type { page-break-before: avoid; }
    .eyebrow { font-size: 11px; letter-spacing: .22em; text-transform: uppercase;
        color: %(ACCENT)s; font-weight: 600; margin-bottom: 6px; }
    h1.cover { font-size: 46px; font-weight: 900; line-height: 1.02; margin: 0 0 8px; }
    h2 { font-size: 26px; font-weight: 700; margin: 0 0 10px; }
    h3 { font-size: 16px; font-weight: 700; margin: 16px 0 6px; }
    p, li, td { font-size: 13px; line-height: 1.5; color: #2a2620; }
    .rule { height: 4px; width: 70px; background: %(ACCENT)s; border-radius: 2px; margin: 10px 0 18px; }
    .basis-line { font-size: 12px; color: #6f675a; margin-top: 4px; }
    table { width: 100%%; border-collapse: collapse; margin: 8px 0 14px; }
    td { padding: 7px 8px; border-bottom: 1px solid #ece6da; vertical-align: top; }
    .ml { width: 38%%; color: #6f675a; font-weight: 500; }
    .mv { font-weight: 600; color: %(INK)s; }
    .note { font-size: 11px; color: #8a8270; font-weight: 400; margin-top: 2px; }
    .chip { display: inline-block; font-family: 'Newsreader',serif; font-size: 10px;
        font-weight: 600; padding: 1px 6px; border-radius: 8px; margin-left: 6px; vertical-align: middle; }
    .chip.real { background: #e6f2e9; color: #1f7a3f; }
    .chip.est  { background: #f3ece0; color: #9a6a16; }
    .card { border: 1px solid #ece6da; border-radius: 8px; padding: 12px 14px; margin: 8px 0; }
    .pos { font-family:'Fraunces',serif; font-size: 18px; font-weight: 500; font-style: italic;
        color: %(INK)s; line-height: 1.35; }
    .pill { display:inline-block; background:%(ACCENT)s; color:#fff; font-size:11px; font-weight:600;
        padding: 2px 9px; border-radius: 10px; margin: 0 4px 4px 0; }
    .do { color:#1f7a3f; } .dont { color:#b23a2e; }
    .bench-grid { display:flex; flex-wrap:wrap; gap:10px; margin:10px 0; }
    .bench-grid .b { flex:1 1 28%%; border:1px solid #ece6da; border-radius:8px; padding:10px; text-align:center; }
    .bench-grid .b .n { font-family:'Fraunces',serif; font-weight:900; font-size:22px; color:%(ACCENT)s; }
    .bench-grid .b .l { font-size:10px; letter-spacing:.08em; text-transform:uppercase; color:#6f675a; }
    .pending { background:#fff8ee; border:1px solid #f0e2c8; color:#8a6a1a; padding:10px 12px;
        border-radius:8px; font-size:12px; }
    .narr { white-space: normal; }
    .foot { position: fixed; bottom: 6mm; left: 0; right: 0; text-align: center;
        font-size: 10px; color: #b3ab9b; }
    """ % {"ACCENT": accent, "INK": ink}


def _foundation_html(f: dict) -> str:
    if not f or f.get("_unparsed"):
        return ("<div class='pending'>Foundation block could not be structured this run — "
                "raw analyst output retained in the JSON; re-run before sign-off.</div>")
    out = []
    if f.get("positioning_statement"):
        out.append(f"<div class='card pos'>{_esc(f['positioning_statement'])}</div>")
    vp = f.get("value_prop") or {}
    if vp:
        out.append("<h3>Value proposition</h3>"
                   f"<p><b>Functional:</b> {_esc(vp.get('functional'))}<br>"
                   f"<b>Emotional:</b> {_esc(vp.get('emotional'))}</p>")
    pillars = f.get("pillars") or []
    if pillars:
        out.append("<h3>Messaging pillars</h3>")
        for p in pillars:
            if isinstance(p, dict):
                out.append(f"<div class='card'><b>{_esc(p.get('name'))}</b>"
                           f"<p>{_esc(p.get('proof'))}</p></div>")
    voice = f.get("voice") or {}
    if voice:
        do = "".join(f"<li class='do'>✓ {_esc(x)}</li>" for x in (voice.get("do") or []))
        dont = "".join(f"<li class='dont'>✕ {_esc(x)}</li>" for x in (voice.get("dont") or []))
        use = " ".join(f"<span class='pill'>{_esc(x)}</span>" for x in (voice.get("vocab_use") or []))
        avoid = ", ".join(_esc(x) for x in (voice.get("vocab_avoid") or []))
        out.append("<h3>Voice &amp; tone</h3>"
                   f"<p>{_esc(voice.get('personality'))}</p>"
                   f"<ul>{do}{dont}</ul>"
                   + (f"<p><b>Words we use:</b> {use}</p>" if use else "")
                   + (f"<p><b>Words we avoid:</b> {avoid}</p>" if avoid else ""))
    icp = f.get("icp") or []
    if icp:
        out.append("<h3>ICP / personas</h3><ul>"
                   + "".join(f"<li>{_esc(x)}</li>" for x in icp) + "</ul>")
    ns = f.get("north_star") or {}
    if ns:
        out.append("<h3>90-day north-star</h3>"
                   f"<div class='card'><b>{_esc(ns.get('metric'))}</b> — target {_esc(ns.get('target'))}</div>")
    return "".join(out)


def _benchmark_html(b: dict) -> str:
    if not b or not b.get("available"):
        reason = (b or {}).get("reason", "competitor numerics unavailable")
        return f"<div class='pending'><b>Full-category benchmark pending.</b> {_esc(reason)}.</div>"
    cells = [
        ("Category avg", b["category_avg"]),
        ("Category median", b["category_median"]),
        ("Your value", b["brand_value"]),
        ("Percentile", f"{b['percentile_rank']} · {b['percentile_band']}"),
        ("Share of Voice", f"{b['share_of_voice_pct']}%"),
        ("Rank", f"#{b['leaderboard_rank']} of {b['n']}"),
    ]
    inner = "".join(f"<div class='b'><div class='n'>{_esc(v)}</div><div class='l'>{_esc(l)}</div></div>"
                    for l, v in cells)
    return f"<div class='bench-grid'>{inner}</div>"


def _part(eyebrow: str, title: str, inner: str) -> str:
    return (f"<section class='part'><div class='eyebrow'>{_esc(eyebrow)}</div>"
            f"<h2>{_esc(title)}</h2><div class='rule'></div>{inner}</section>")


def _narr(part: dict) -> str:
    return f"<div class='narr'><p>{_esc((part or {}).get('narrative',''))}</p></div>"


def _build_html(report: dict, palette: dict) -> str:
    meta = report.get("meta", {})
    parts = report.get("parts", {})
    prov = report.get("provenance", [])

    # Cover + scorecard
    sc = parts.get("part0_scorecard", {})
    sc_rows = "".join(_metric_row(lbl, m) for lbl, m in sc.get("metrics", []))
    cover = (f"<section class='part'>"
             f"<div class='eyebrow'>Brand Intelligence Report · {_esc(meta.get('version'))}</div>"
             f"<h1 class='cover'>{_esc(meta.get('brand'))}</h1>"
             f"<div class='rule'></div>"
             f"<p>{_esc(meta.get('category'))} · {_esc(meta.get('market'))} · {_esc(meta.get('date'))}</p>"
             f"<p class='basis-line'>{_esc(meta.get('data_basis'))} · mode: {_esc(meta.get('mode'))}</p>"
             f"<h3>{_esc(sc.get('title','Executive Scorecard'))}</h3>"
             f"<table>{sc_rows or '<tr><td>No scorecard metrics available.</td></tr>'}</table>"
             f"</section>")

    foundation = _part("Part 1", "Brand Foundation",
                       _foundation_html(parts.get("part1_foundation", {})))

    p2 = parts.get("part2_where_you_stand", {})
    where = _part("Part 2", "Where You Stand",
                  f"<p class='pos'>{_esc(p2.get('hard_truth'))}</p>"
                  f"<h3>Full-category benchmark</h3>{_benchmark_html(p2.get('benchmark', {}))}"
                  + (f"<p class='basis-line'>Competitors scraped: "
                     f"{_esc(', '.join(p2.get('competitors_scraped', [])))}</p>"
                     if p2.get('competitors_scraped') else ""))

    market = _part("Part 3", "The Market", _narr(parts.get("part3_market")))
    content = _part("Part 4", "Content Intelligence", _narr(parts.get("part4_content_intel")))

    aud = parts.get("part5_audience", {})
    if aud.get("basis") == "REAL":
        demo = aud.get("demographics", {})
        blocks = []
        for dim in ("age", "gender", "country"):
            if demo.get(dim):
                rows = "".join(f"<tr><td class='ml'>{_esc(k)}</td><td class='mv'>{_esc(v)}</td></tr>"
                               for k, v in list(demo[dim].items())[:8])
                blocks.append(f"<h3>{dim.title()} <span class='chip real'>REAL</span></h3><table>{rows}</table>")
        audience = _part("Part 5", "Audience Intelligence",
                         "".join(blocks) + f"<p class='basis-line'>{_esc(aud.get('note'))}</p>")
    else:
        audience = _part("Part 5", "Audience Intelligence",
                         f"<p class='narr'>{_esc(aud.get('inferred'))}</p>"
                         f"<p class='basis-line'>{_esc(aud.get('note'))} "
                         f"<span class='chip est'>EST</span></p>")

    growth = _part("Part 6", "Growth Playbook", _narr(parts.get("part6_growth_playbook")))
    horizon = _part("Part 7", "Horizon", _narr(parts.get("part7_horizon")))

    # Appendix — provenance table
    apx = parts.get("appendix", {})
    prov_rows = "".join(
        f"<tr><td class='mv'>{_esc(m.get('value'))}</td>"
        f"<td>{_chip(m.get('basis','AI_ESTIMATED'))}</td>"
        f"<td class='ml'>{_esc(m.get('source_file') or m.get('note') or '')}</td></tr>"
        for m in prov)
    appendix = _part("Appendix", "Data Provenance &amp; Methodology",
                     f"<p>{_esc(apx.get('methodology'))}</p>"
                     f"<table><tr><td class='ml'>Figure</td><td>Basis</td><td class='ml'>Source</td></tr>"
                     f"{prov_rows or '<tr><td>No metrics recorded.</td></tr>'}</table>")

    body = (cover + foundation + where + market + content + audience + growth + horizon + appendix
            + "<div class='foot'>Generated by GRID CONTROL · real-data brand intelligence · "
            + _esc(meta.get("model", "")) + "</div>")
    return ("<!doctype html><html><head><meta charset='utf-8'><style>"
            + _css(palette) + "</style></head><body>" + body + "</body></html>")


def render_brand_book(report: dict, palette: dict, out_pdf) -> Path:
    out_pdf = Path(out_pdf)
    out_pdf.parent.mkdir(parents=True, exist_ok=True)
    html = _build_html(report, palette)
    with sync_playwright() as pw:
        browser = pw.chromium.launch()
        try:
            page = browser.new_page()
            page.set_content(html, wait_until="networkidle", timeout=30000)
            page.wait_for_timeout(300)
            page.pdf(
                path=str(out_pdf),
                format="A4",
                print_background=True,           # render accent fills + chips
                prefer_css_page_size=True,
                margin={"top": "0", "bottom": "0", "left": "0", "right": "0"},
            )
        finally:
            browser.close()
    return out_pdf
