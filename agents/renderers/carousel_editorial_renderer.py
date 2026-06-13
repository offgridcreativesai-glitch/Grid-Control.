"""
Carousel Editorial Renderer — "Founder Journal" theme.

A premium editorial carousel style: warm cream paper, heavy serif display type,
brick-red accent, handwritten eyebrow labels, a faint botanical accent, and a
brush-style CTA button. Rendered HTML/CSS → PNG via Playwright (1080x1350, IG 4:5).

Drop-in compatible with carousel_html_renderer.render_slides_to_png(slides, palette, handle, out_dir).
The palette arg is ignored — this renderer owns the Founder-Journal palette so the look is locked.

Slide spec fields (per slide dict):
  number   : int (1-based)
  type     : "hook" | "point" | "insight" | "cta"
  eyebrow  : small label, e.g. "Mistake #1" / "What changed" (optional)
  headline : the slide headline
  body     : supporting paragraph (optional)
  emphasis : a short italic line under the hook (hook slides, optional)
  cta_line : the follow/save line (cta slides)
"""
from pathlib import Path
from playwright.sync_api import sync_playwright

CANVAS_W = 1080
CANVAS_H = 1350

# ── Founder-Journal palette ───────────────────────────────────────────────
PAPER   = "#f4efe3"   # warm cream
PAPER2  = "#efe8d8"   # slightly deeper cream (cta panel tint)
INK     = "#211d18"   # warm near-black
MUTE    = "#6f675a"   # muted brown-grey body
RED     = "#b23a2e"   # brick red accent
RED_DK  = "#8f2c22"
LINE    = "#d8cdb8"   # hairline


def _esc(s) -> str:
    if s is None:
        return ""
    return (str(s).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace("\n", "<br>"))


_FONTS = ("@import url('https://fonts.googleapis.com/css2?"
          "family=Fraunces:ital,opsz,wght@0,9..144,400;0,9..144,600;0,9..144,800;0,9..144,900;1,9..144,500;1,9..144,600"
          "&family=Newsreader:ital,opsz,wght@0,6..72,400;0,6..72,500;1,6..72,400"
          "&family=Caveat:wght@600;700&display=swap');")

# Faint botanical sprig (corner accent), drawn as inline SVG at low opacity.
_BOTANICAL = (
    "<svg class='botanical' width='420' height='420' viewBox='0 0 200 200' fill='none'>"
    "<path d='M100 195 C100 150 100 90 100 30' stroke='%s' stroke-width='2'/>"
    "<path d='M100 70 C70 60 55 40 52 18 C80 24 96 44 100 70Z' fill='%s'/>"
    "<path d='M100 95 C130 86 146 66 150 44 C122 50 105 70 100 95Z' fill='%s'/>"
    "<path d='M100 120 C72 112 58 94 55 74 C81 80 96 98 100 120Z' fill='%s'/>"
    "<path d='M100 145 C128 137 143 119 147 99 C120 105 104 123 100 145Z' fill='%s'/>"
    "</svg>"
) % (RED, RED, RED, RED, RED)


def _base_css() -> str:
    return _FONTS + """
    * { box-sizing: border-box; margin: 0; padding: 0; }
    html, body {
        width: %(W)dpx; height: %(H)dpx;
        background: %(PAPER)s; color: %(INK)s;
        overflow: hidden; -webkit-font-smoothing: antialiased; text-rendering: geometricPrecision;
    }
    .slide {
        position: relative; width: %(W)dpx; height: %(H)dpx;
        padding: 96px 92px 96px 92px; display: flex; flex-direction: column;
        background:
          radial-gradient(120%% 90%% at 100%% 0%%, rgba(178,58,46,0.04), transparent 55%%),
          %(PAPER)s;
    }
    .frame { position:absolute; inset:34px; border:1.5px solid %(LINE)s; pointer-events:none; }
    .botanical { position:absolute; right:30px; bottom:26px; opacity:0.10; }
    .counter {
        position:absolute; top:60px; right:92px;
        font-family:'Newsreader',serif; font-size:24px; color:%(RED)s; letter-spacing:.04em;
    }
    .wordmark {
        position:absolute; top:62px; left:92px;
        font-family:'Newsreader',serif; font-size:22px; font-weight:500;
        letter-spacing:.20em; text-transform:uppercase; color:%(MUTE)s;
    }
    .eyebrow {
        font-family:'Caveat',cursive; font-size:46px; font-weight:700;
        color:%(RED)s; margin-bottom:14px; line-height:1;
    }
    .eyebrow .u { display:inline-block; border-bottom:3px solid %(RED)s; padding-bottom:2px; }
    h1 { font-family:'Fraunces',serif; font-weight:900; color:%(INK)s; letter-spacing:-0.01em; }
    h2 { font-family:'Fraunces',serif; font-weight:800; color:%(INK)s; letter-spacing:-0.01em; }
    p  { font-family:'Newsreader',serif; color:%(MUTE)s; }
    .emph { font-family:'Fraunces',serif; font-style:italic; font-weight:600; color:%(RED)s; }
    .rule { width:96px; height:4px; background:%(RED)s; border-radius:2px; }
    .foot {
        position:absolute; left:92px; right:92px; bottom:60px;
        display:flex; justify-content:space-between; align-items:center;
        font-family:'Newsreader',serif; font-size:24px; color:%(MUTE)s;
    }
    .foot .h { color:%(RED)s; font-weight:500; }
    """ % {"W": CANVAS_W, "H": CANVAS_H, "PAPER": PAPER, "INK": INK, "MUTE": MUTE,
           "RED": RED, "LINE": LINE}


def _doc(inner: str, extra_css: str = "") -> str:
    return ("<!doctype html><html><head><meta charset='utf-8'><style>"
            + _base_css() + extra_css + "</style></head><body>" + inner + "</body></html>")


def _foot(handle: str, n: int, total: int) -> str:
    return ("<div class='foot'><span class='h'>" + _esc(handle) + "</span>"
            "<span>" + str(n) + " / " + str(total) + "</span></div>")


def _tmpl_hook(s, n, total, handle):
    css = """
    .slide.hook { justify-content:center; padding-bottom:160px; }
    .hook .kick { font-family:'Caveat',cursive; font-size:42px; color:%(RED)s; margin-bottom:18px; }
    .hook h1 { font-size:108px; line-height:0.98; max-width:900px; }
    .hook .emph { font-size:40px; margin-top:40px; display:block; }
    .hook .rule { margin-top:34px; }
    """ % {"RED": RED}
    kick = ("<div class='kick'>" + _esc(s.get("eyebrow", "")) + "</div>") if s.get("eyebrow") else ""
    emph = ("<span class='emph'>" + _esc(s.get("emphasis", "")) + "</span>") if s.get("emphasis") else ""
    inner = ("<div class='slide hook'><div class='frame'></div>"
             "<div class='wordmark'>ASKGAURAV.AI</div>"
             "<div class='counter'>" + f"{n:02d}/{total:02d}" + "</div>"
             + kick + "<h1>" + _esc(s.get("headline", "")) + "</h1>"
             + "<div class='rule'></div>" + emph
             + _botanical_if(n) + _foot(handle, n, total) + "</div>")
    return _doc(inner, css)


def _tmpl_point(s, n, total, handle):
    # eyebrow (handwritten) + serif headline + body — the "Mistake #N" / "What changed" slides
    css = """
    .slide.point { justify-content:flex-start; padding-top:150px; }
    .point .eyebrow { font-size:50px; margin-bottom:22px; }
    .point h2 { font-size:78px; line-height:1.02; max-width:880px; margin-bottom:30px; }
    .point .rule { margin-bottom:40px; }
    .point p { font-size:38px; line-height:1.5; max-width:860px; }
    """
    eb = ""
    if s.get("eyebrow"):
        eb = "<div class='eyebrow'><span class='u'>" + _esc(s.get("eyebrow")) + "</span></div>"
    body = ("<p>" + _esc(s.get("body", "")) + "</p>") if s.get("body") else ""
    inner = ("<div class='slide point'><div class='frame'></div>"
             "<div class='wordmark'>ASKGAURAV.AI</div>"
             "<div class='counter'>" + f"{n:02d}/{total:02d}" + "</div>"
             + eb + "<h2>" + _esc(s.get("headline", "")) + "</h2>"
             + "<div class='rule'></div>" + body
             + _botanical_if(n) + _foot(handle, n, total) + "</div>")
    return _doc(inner, css)


def _tmpl_cta(s, n, total, handle):
    css = """
    .slide.cta { justify-content:center; padding-bottom:150px; background:
        radial-gradient(120%% 90%% at 0%% 100%%, rgba(178,58,46,0.06), transparent 55%%), %(PAPER2)s; }
    .cta .eyebrow { font-size:48px; margin-bottom:18px; }
    .cta h2 { font-size:84px; line-height:1.0; max-width:880px; margin-bottom:30px; }
    .cta p { font-size:38px; line-height:1.45; max-width:840px; margin-bottom:54px; }
    .cta .btn {
        display:inline-block; align-self:flex-start;
        background:%(RED)s; color:%(PAPER)s; font-family:'Fraunces',serif; font-weight:800;
        font-size:38px; letter-spacing:0.01em; padding:30px 46px; border-radius:6px;
        box-shadow: 10px 10px 0 rgba(143,44,34,0.28); transform: rotate(-1.2deg);
    }
    """ % {"PAPER": PAPER, "PAPER2": PAPER2, "RED": RED}
    eb = ("<div class='eyebrow'>" + _esc(s.get("eyebrow", "")) + "</div>") if s.get("eyebrow") else ""
    body = ("<p>" + _esc(s.get("body", "")) + "</p>") if s.get("body") else ""
    cta = _esc(s.get("cta_line") or "Follow to watch what I'm building.").upper()
    inner = ("<div class='slide cta'><div class='frame'></div>"
             "<div class='wordmark'>ASKGAURAV.AI</div>"
             "<div class='counter'>" + f"{n:02d}/{total:02d}" + "</div>"
             + eb + "<h2>" + _esc(s.get("headline", "")) + "</h2>" + body
             + "<span class='btn'>" + cta + "</span>"
             + _foot(handle, n, total) + "</div>")
    return _doc(inner, css)


def _botanical_if(n: int) -> str:
    # show botanical sprig on a couple of slides only, for restraint
    return _BOTANICAL if n in (1,) else ""


_ROUTE = {"hook": _tmpl_hook, "point": _tmpl_point, "insight": _tmpl_point, "cta": _tmpl_cta}


def render_slides_to_png(slides: list, palette: dict, handle: str, out_dir: Path) -> list:
    out_dir.mkdir(parents=True, exist_ok=True)
    total = len(slides)
    rendered = []
    with sync_playwright() as pw:
        browser = pw.chromium.launch()
        try:
            ctx = browser.new_context(viewport={"width": CANVAS_W, "height": CANVAS_H}, device_scale_factor=2)
            page = ctx.new_page()
            for s in slides:
                n = s.get("number", 1)
                tmpl = _ROUTE.get((s.get("type") or "point").lower(), _tmpl_point)
                page.set_content(tmpl(s, n, total, handle), wait_until="networkidle", timeout=25000)
                page.wait_for_timeout(400)
                out_path = out_dir / f"slide_{n:02d}.png"
                page.screenshot(path=str(out_path), clip={"x": 0, "y": 0, "width": CANVAS_W, "height": CANVAS_H})
                rendered.append(out_path)
        finally:
            browser.close()
    return rendered
