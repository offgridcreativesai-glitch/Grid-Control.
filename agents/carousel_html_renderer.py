"""
Carousel HTML Renderer — editorial typographic templates rendered via Playwright.
Replaces the basic Pillow renderer in carousel_designer.py.

Templates: HERO / INSIGHT / LIST / DATA_CALLOUT / PRINCIPLE_CTA
Output: 1080x1350 PNG (IG 4:5 portrait)
Fonts: Manrope (Google Fonts, embedded via @import)
"""

from pathlib import Path
from playwright.sync_api import sync_playwright

CANVAS_W = 1080
CANVAS_H = 1350


def _base_css(palette: dict, handle: str) -> str:
    """Brand-palette aware base styles. Geist would be ideal but Manrope is more reliable from Google."""
    return f"""
    @import url('https://fonts.googleapis.com/css2?family=Manrope:wght@400;500;600;700;800&family=JetBrains+Mono:wght@400;500&display=swap');

    * {{ box-sizing: border-box; margin: 0; padding: 0; }}
    html, body {{
        width: {CANVAS_W}px; height: {CANVAS_H}px;
        font-family: 'Manrope', -apple-system, sans-serif;
        background: {palette.get('primary_bg', '#FFFFFF')};
        color: {palette.get('text_primary', '#1A1A1A')};
        overflow: hidden;
        -webkit-font-smoothing: antialiased;
        text-rendering: geometricPrecision;
    }}
    .slide {{
        position: relative;
        width: {CANVAS_W}px; height: {CANVAS_H}px;
        padding: 96px 90px 72px 90px;
        display: flex; flex-direction: column;
    }}
    .top-rule {{
        position: absolute; top: 0; left: 0;
        width: 100%; height: 6px;
        background: {palette.get('accent', '#0F4C5C')};
    }}
    .slide-tag {{
        position: absolute; top: 56px; right: 90px;
        font-family: 'JetBrains Mono', monospace;
        font-size: 18px; font-weight: 500;
        color: {palette.get('accent', '#0F4C5C')};
        letter-spacing: 0.15em;
    }}
    .footer {{
        position: absolute; bottom: 64px; left: 90px; right: 90px;
        display: flex; justify-content: space-between; align-items: center;
        font-size: 22px; font-weight: 600;
    }}
    .footer .handle {{ color: {palette.get('accent', '#0F4C5C')}; }}
    .footer .counter {{
        font-family: 'JetBrains Mono', monospace;
        color: {palette.get('text_primary', '#1A1A1A')};
        font-weight: 500; font-size: 18px;
    }}
    """


# ── TEMPLATE: HERO (slide 1, the hook) ────────────────────────────────────
def _tmpl_hero(slide: dict, n: int, total: int, palette: dict, handle: str) -> str:
    headline = slide.get("headline", "")
    return f"""<!doctype html><html><head><meta charset='utf-8'><style>
    {_base_css(palette, handle)}
    .slide.hero {{ justify-content: center; padding-bottom: 180px; }}
    .hero h1 {{
        font-size: 124px; font-weight: 800;
        line-height: 0.96; letter-spacing: -0.04em;
        color: {palette.get('text_primary', '#1A1A1A')};
        max-width: 920px;
    }}
    .hero .accent-block {{
        width: 96px; height: 12px;
        background: {palette.get('accent', '#0F4C5C')};
        margin-top: 56px;
    }}
    .hero .kicker {{
        font-family: 'JetBrains Mono', monospace;
        font-size: 18px; font-weight: 500;
        color: {palette.get('accent', '#0F4C5C')};
        letter-spacing: 0.2em;
        text-transform: uppercase;
        margin-bottom: 28px;
    }}
    </style></head><body>
    <div class='slide hero'>
        <div class='top-rule'></div>
        <div class='kicker'>askgaurav.ai · {n:02d} / {total:02d}</div>
        <h1>{_esc(headline)}</h1>
        <div class='accent-block'></div>
        <div class='footer'>
            <span class='handle'>{handle}</span>
            <span class='counter'>{n} / {total}</span>
        </div>
    </div>
    </body></html>"""


# ── TEMPLATE: INSIGHT (default value slide) ───────────────────────────────
def _tmpl_insight(slide: dict, n: int, total: int, palette: dict, handle: str) -> str:
    headline = slide.get("headline", "")
    body = slide.get("body", "")
    return f"""<!doctype html><html><head><meta charset='utf-8'><style>
    {_base_css(palette, handle)}
    .slide.insight {{ padding-top: 180px; }}
    .insight h2 {{
        font-size: 76px; font-weight: 800;
        line-height: 1.04; letter-spacing: -0.025em;
        color: {palette.get('text_primary', '#1A1A1A')};
        margin-bottom: 36px;
    }}
    .insight .divider {{
        width: 80px; height: 6px;
        background: {palette.get('accent', '#0F4C5C')};
        margin-bottom: 44px;
    }}
    .insight p {{
        font-size: 36px; font-weight: 500;
        line-height: 1.45; letter-spacing: -0.005em;
        color: {palette.get('text_primary', '#1A1A1A')};
        max-width: 880px;
    }}
    </style></head><body>
    <div class='slide insight'>
        <div class='top-rule'></div>
        <div class='slide-tag'>{n:02d}</div>
        <h2>{_esc(headline)}</h2>
        <div class='divider'></div>
        <p>{_esc(body)}</p>
        <div class='footer'>
            <span class='handle'>{handle}</span>
            <span class='counter'>{n} / {total}</span>
        </div>
    </div>
    </body></html>"""


# ── TEMPLATE: LIST (value slide with bullets) ─────────────────────────────
def _tmpl_list(slide: dict, n: int, total: int, palette: dict, handle: str) -> str:
    headline = slide.get("headline", "")
    bullets = slide.get("bullets") or []
    body = slide.get("body", "")
    bullet_html = "".join(
        f"<li><span class='num'>{i+1:02d}</span><span class='txt'>{_esc(b)}</span></li>"
        for i, b in enumerate(bullets[:6])
    )
    body_block = f"<p class='lead'>{_esc(body)}</p>" if body and not bullets else ""
    return f"""<!doctype html><html><head><meta charset='utf-8'><style>
    {_base_css(palette, handle)}
    .slide.list {{ padding-top: 170px; }}
    .list h2 {{
        font-size: 64px; font-weight: 800;
        line-height: 1.04; letter-spacing: -0.025em;
        margin-bottom: 28px;
    }}
    .list .divider {{
        width: 64px; height: 5px;
        background: {palette.get('accent', '#0F4C5C')};
        margin-bottom: 38px;
    }}
    .list .lead {{
        font-size: 30px; font-weight: 500; line-height: 1.4;
        margin-bottom: 36px; max-width: 880px;
    }}
    .list ul {{ list-style: none; padding: 0; }}
    .list li {{
        display: flex; align-items: baseline;
        gap: 24px; padding: 18px 0;
        border-bottom: 1px solid {palette.get('secondary_bg', '#F1F5F9')};
        font-size: 32px; font-weight: 600;
        line-height: 1.3;
    }}
    .list li:last-child {{ border-bottom: none; }}
    .list .num {{
        font-family: 'JetBrains Mono', monospace;
        font-weight: 500; font-size: 22px;
        color: {palette.get('accent', '#0F4C5C')};
        min-width: 48px;
    }}
    .list .txt {{ flex: 1; }}
    </style></head><body>
    <div class='slide list'>
        <div class='top-rule'></div>
        <div class='slide-tag'>{n:02d}</div>
        <h2>{_esc(headline)}</h2>
        <div class='divider'></div>
        {body_block}
        <ul>{bullet_html}</ul>
        <div class='footer'>
            <span class='handle'>{handle}</span>
            <span class='counter'>{n} / {total}</span>
        </div>
    </div>
    </body></html>"""


# ── TEMPLATE: DATA_CALLOUT (stat-led slide) ────────────────────────────────
def _tmpl_data(slide: dict, n: int, total: int, palette: dict, handle: str) -> str:
    headline = slide.get("headline", "")
    body = slide.get("body", "")
    # Try to extract a leading number/stat from headline
    stat = slide.get("stat") or _extract_stat(headline)
    label = slide.get("stat_label") or headline
    return f"""<!doctype html><html><head><meta charset='utf-8'><style>
    {_base_css(palette, handle)}
    .slide.data {{
        padding-top: 130px;
        align-items: center; text-align: center;
    }}
    .data .stat {{
        font-size: 220px; font-weight: 800;
        line-height: 0.92; letter-spacing: -0.06em;
        color: {palette.get('accent', '#0F4C5C')};
        margin-top: 80px; margin-bottom: 32px;
    }}
    .data .label {{
        font-size: 38px; font-weight: 700;
        line-height: 1.2; letter-spacing: -0.01em;
        max-width: 760px; margin: 0 auto 48px;
    }}
    .data .body {{
        font-size: 28px; font-weight: 500;
        line-height: 1.45; max-width: 720px; margin: 0 auto;
        color: {palette.get('text_primary', '#1A1A1A')};
        opacity: 0.78;
    }}
    </style></head><body>
    <div class='slide data'>
        <div class='top-rule'></div>
        <div class='slide-tag'>{n:02d}</div>
        <div class='stat'>{_esc(stat)}</div>
        <div class='label'>{_esc(label)}</div>
        <div class='body'>{_esc(body)}</div>
        <div class='footer'>
            <span class='handle'>{handle}</span>
            <span class='counter'>{n} / {total}</span>
        </div>
    </div>
    </body></html>"""


# ── TEMPLATE: PRINCIPLE_CTA (last slide) ───────────────────────────────────
def _tmpl_cta(slide: dict, n: int, total: int, palette: dict, handle: str) -> str:
    headline = slide.get("headline", "")
    body = slide.get("body", "")
    return f"""<!doctype html><html><head><meta charset='utf-8'><style>
    {_base_css(palette, handle)}
    .slide.cta {{
        background: {palette.get('accent', '#0F4C5C')};
        color: #FFFFFF;
        padding-top: 200px;
    }}
    .cta .top-rule {{ background: {palette.get('highlight_sparing', '#E07A5F')}; }}
    .cta .kicker {{
        font-family: 'JetBrains Mono', monospace;
        font-size: 18px; font-weight: 500;
        color: {palette.get('highlight_sparing', '#E07A5F')};
        letter-spacing: 0.2em;
        text-transform: uppercase;
        margin-bottom: 32px;
    }}
    .cta h2 {{
        font-size: 84px; font-weight: 800;
        line-height: 1.02; letter-spacing: -0.03em;
        color: #FFFFFF;
        margin-bottom: 56px;
        max-width: 880px;
    }}
    .cta p {{
        font-size: 32px; font-weight: 500;
        line-height: 1.5; color: #FFFFFF;
        opacity: 0.86; max-width: 800px;
    }}
    .cta .handle-prom {{
        position: absolute; bottom: 130px; left: 90px;
        font-size: 56px; font-weight: 800;
        color: {palette.get('highlight_sparing', '#E07A5F')};
        letter-spacing: -0.02em;
    }}
    .cta .footer {{ color: rgba(255,255,255,0.7); }}
    .cta .footer .handle, .cta .footer .counter {{ color: rgba(255,255,255,0.7); }}
    </style></head><body>
    <div class='slide cta'>
        <div class='top-rule'></div>
        <div class='kicker'>The principle</div>
        <h2>{_esc(headline)}</h2>
        <p>{_esc(body)}</p>
        <div class='handle-prom'>{handle}</div>
        <div class='footer'>
            <span class='handle'>follow for the build journey</span>
            <span class='counter'>{n} / {total}</span>
        </div>
    </div>
    </body></html>"""


def _esc(s) -> str:
    if s is None:
        return ""
    return (str(s)
            .replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
            .replace("\n", "<br>"))


def _extract_stat(text: str) -> str:
    """Extract a leading stat from headline. e.g. '40 hours of building' → '40'."""
    import re
    m = re.search(r"(\d+(?:\.\d+)?[%×x]?|₹\d+(?:[KMLkmlcr]+)?|\$\d+(?:[KMB]+)?)", text or "")
    return m.group(1) if m else text[:6] if text else "?"


_TEMPLATES = {
    "HERO":          _tmpl_hero,
    "INSIGHT":       _tmpl_insight,
    "LIST":          _tmpl_list,
    "DATA_CALLOUT":  _tmpl_data,
    "PRINCIPLE_CTA": _tmpl_cta,
}


def pick_layout(slide: dict, n: int, total: int) -> str:
    """If the spec has a layout field, use it. Else auto-pick by position + content."""
    layout = (slide.get("layout") or "").upper().strip()
    if layout in _TEMPLATES:
        return layout

    slide_type = (slide.get("type") or "").lower()
    bullets = slide.get("bullets") or []
    headline = slide.get("headline", "")

    if slide_type == "hook" or n == 1:
        return "HERO"
    if slide_type == "cta" or n == total:
        return "PRINCIPLE_CTA"
    if bullets and len(bullets) >= 2:
        return "LIST"
    # If headline starts with a clear stat (number, ₹, %), use DATA_CALLOUT
    import re
    if re.match(r"^[₹$]?\d", headline.strip()):
        return "DATA_CALLOUT"
    return "INSIGHT"


def render_slide_html(slide: dict, n: int, total: int, palette: dict, handle: str) -> str:
    layout = pick_layout(slide, n, total)
    tmpl = _TEMPLATES[layout]
    return tmpl(slide, n, total, palette, handle)


def render_slides_to_png(slides: list[dict], palette: dict, handle: str, out_dir: Path) -> list[Path]:
    """Render every slide to PNG using a single Chromium instance."""
    out_dir.mkdir(parents=True, exist_ok=True)
    rendered: list[Path] = []
    total = len(slides)

    with sync_playwright() as pw:
        browser = pw.chromium.launch()
        try:
            ctx = browser.new_context(viewport={"width": CANVAS_W, "height": CANVAS_H},
                                       device_scale_factor=2)
            page = ctx.new_page()
            for slide in slides:
                n = slide.get("number", 1)
                html = render_slide_html(slide, n, total, palette, handle)
                page.set_content(html, wait_until="networkidle", timeout=20000)
                # Allow webfonts to settle
                page.wait_for_timeout(300)
                out_path = out_dir / f"slide_{n:02d}.png"
                page.screenshot(path=str(out_path), full_page=False, omit_background=False,
                                clip={"x": 0, "y": 0, "width": CANVAS_W, "height": CANVAS_H})
                rendered.append(out_path)
        finally:
            browser.close()
    return rendered
