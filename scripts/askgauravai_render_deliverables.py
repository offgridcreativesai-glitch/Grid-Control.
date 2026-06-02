"""
Render ASKGauravAI deliverables (Strategy, Calendar, Scripts, Brand Book) → HTML → PDF.
Uses Chrome headless for PDF conversion.

Outputs:
  brands/askgauravai/deliverables/{date}/strategy_90day.{html,pdf}
  brands/askgauravai/deliverables/{date}/content_calendar.{html,pdf}
  brands/askgauravai/deliverables/{date}/scripts_week1.{html,pdf}
  brands/askgauravai/deliverables/{date}/brand_book_v2.{html,pdf}

Brand palette baked in:
  primary_bg #FFFFFF | accent #0F4C5C (deep teal) | text #1A1A1A | highlight #E07A5F
"""
import json
import subprocess
from datetime import datetime
from pathlib import Path

BRAND_DIR = Path("/Users/gauravoffgrid/offgrid-marketing-os/brands/askgauravai")
DATESTAMP = datetime.now().strftime("%Y%m%d")
OUT_DIR = BRAND_DIR / "deliverables" / DATESTAMP
OUT_DIR.mkdir(parents=True, exist_ok=True)
CHROME = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"

CSS = """
@page { size: A4; margin: 18mm 16mm 18mm 16mm; }
* { box-sizing: border-box; }
body {
  font-family: -apple-system, 'SF Pro Text', 'Helvetica Neue', Helvetica, Arial, sans-serif;
  color: #1A1A1A;
  background: #FFFFFF;
  font-size: 10.5pt;
  line-height: 1.55;
  margin: 0;
}
h1 { font-size: 24pt; color: #0F4C5C; margin: 0 0 4pt 0; letter-spacing: -0.4pt; font-weight: 700; }
h2 { font-size: 15pt; color: #0F4C5C; margin: 22pt 0 6pt 0; font-weight: 600; border-bottom: 1pt solid #0F4C5C; padding-bottom: 2pt; }
h3 { font-size: 12pt; color: #1A1A1A; margin: 14pt 0 4pt 0; font-weight: 600; }
h4 { font-size: 10.5pt; color: #0F4C5C; margin: 10pt 0 3pt 0; font-weight: 600; text-transform: uppercase; letter-spacing: 0.5pt; }
p { margin: 0 0 6pt 0; }
.muted { color: #6B7280; font-size: 9pt; }
.kicker { color: #0F4C5C; font-size: 9pt; text-transform: uppercase; letter-spacing: 1pt; font-weight: 600; margin-bottom: 2pt; }
.cover { padding: 60pt 0 40pt 0; border-bottom: 2pt solid #0F4C5C; margin-bottom: 24pt; }
.cover h1 { font-size: 38pt; }
.cover .meta { color: #6B7280; font-size: 10pt; margin-top: 14pt; }
.callout { background: #FAFAFA; border-left: 3pt solid #0F4C5C; padding: 10pt 14pt; margin: 8pt 0; border-radius: 2pt; page-break-inside: avoid; }
.highlight { background: #E07A5F; color: #FFFFFF; padding: 1pt 5pt; border-radius: 2pt; font-weight: 600; }
table { width: 100%; border-collapse: collapse; margin: 8pt 0; font-size: 9.5pt; }
th { text-align: left; padding: 6pt 8pt; background: #0F4C5C; color: #FFFFFF; font-weight: 600; }
td { padding: 6pt 8pt; border-bottom: 1pt solid #E5E7EB; vertical-align: top; }
ul, ol { margin: 4pt 0 8pt 18pt; padding: 0; }
li { margin-bottom: 3pt; }
code, pre { font-family: 'SF Mono', Menlo, Monaco, Consolas, monospace; font-size: 9pt; background: #F3F4F6; padding: 1pt 4pt; border-radius: 2pt; color: #0F4C5C; }
.script-card { border: 1pt solid #E5E7EB; border-radius: 4pt; padding: 14pt 16pt; margin: 12pt 0; page-break-inside: avoid; }
.script-card .day-tag { display: inline-block; background: #0F4C5C; color: #FFFFFF; padding: 3pt 9pt; border-radius: 12pt; font-size: 9pt; font-weight: 600; margin-bottom: 6pt; }
.beat { background: #FAFAFA; padding: 8pt 12pt; border-radius: 3pt; margin: 5pt 0; }
.beat .label { font-size: 8.5pt; color: #6B7280; text-transform: uppercase; letter-spacing: 0.7pt; font-weight: 600; }
.gauravbox { background: #0F4C5C; color: #FFFFFF; padding: 12pt 16pt; border-radius: 4pt; margin: 10pt 0; page-break-inside: avoid; }
.gauravbox h4 { color: #FFFFFF; margin-top: 0; }
.gauravbox ul { margin: 4pt 0 0 18pt; }
.gear-grid { display: grid; grid-template-columns: 130pt 1fr; gap: 4pt 12pt; font-size: 9.5pt; margin: 6pt 0; }
.gear-grid dt { font-weight: 600; color: #0F4C5C; }
hr { border: 0; border-top: 1pt dashed #D1D5DB; margin: 20pt 0; }
.footer-note { color: #9CA3AF; font-size: 8.5pt; margin-top: 30pt; text-align: center; }
"""

HTML_SHELL = """<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">
<title>{title}</title>
<style>{css}</style>
</head>
<body>
<div class="cover">
  <div class="kicker">ASKGauravAI · Brand Manager Deliverable</div>
  <h1>{title}</h1>
  <div class="meta">Generated {datestamp} · For founder review</div>
</div>
{body}
<div class="footer-note">ASKGauravAI · {filename}</div>
</body>
</html>
"""


def html_escape(s):
    if s is None:
        return ""
    return (
        str(s)
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


def render_value(v):
    """Render any value (str/list/dict) as readable HTML — never raw Python dict strings."""
    if v is None or v == "":
        return ""
    if isinstance(v, str):
        return html_escape(v)
    if isinstance(v, (int, float, bool)):
        return html_escape(str(v))
    if isinstance(v, list):
        if not v:
            return ""
        if all(isinstance(x, (str, int, float, bool)) for x in v):
            return "<ul>" + "".join(f"<li>{html_escape(str(x))}</li>" for x in v) + "</ul>"
        return "<ul>" + "".join(f"<li>{render_value(x)}</li>" for x in v) + "</ul>"
    if isinstance(v, dict):
        rows = []
        for k, val in v.items():
            label = html_escape(str(k).replace("_", " ").title())
            rows.append(f"<tr><td style='font-weight:600;color:#0F4C5C;width:35%;'>{label}</td><td>{render_value(val)}</td></tr>")
        return f"<table style='margin:4pt 0;'>{''.join(rows)}</table>"
    return html_escape(str(v))


def render_strategy(data):
    s = data.get("strategy_90day", data)
    parts = []
    parts.append(f"<h2>Strategic Angle</h2><p>{html_escape(s.get('strategic_angle', ''))}</p>")

    if s.get("competitive_positioning"):
        parts.append(f"<h2>Competitive Positioning</h2><p>{html_escape(s['competitive_positioning'])}</p>")

    pillars = s.get("content_pillars", [])
    if pillars:
        parts.append("<h2>Content Pillars</h2><ul>")
        for p in pillars:
            if isinstance(p, dict):
                pname = p.get("pillar") or p.get("name") or "Pillar"
                parts.append(f"<li><strong>{html_escape(pname)}</strong> — {html_escape(p.get('rationale', ''))}</li>")
            else:
                parts.append(f"<li>{html_escape(p)}</li>")
        parts.append("</ul>")

    for phase_key in ("phase_1", "phase_2", "phase_3"):
        phase = s.get(phase_key)
        if not phase:
            continue
        parts.append(f"<h2>{html_escape(phase.get('name', phase_key.replace('_', ' ').title()))}</h2>")
        for k in ("days", "primary_goal", "weekly_output", "weekly_volume_target", "primary_channel", "secondary_channels", "key_metrics", "approach", "phase_gate"):
            v = phase.get(k)
            if v:
                parts.append(f"<h4>{k.replace('_', ' ').title()}</h4>{render_value(v)}")

    if s.get("90_day_north_star") or s.get("north_star"):
        ns = s.get("90_day_north_star") or s.get("north_star")
        parts.append(f"<div class='callout'><strong>90-Day North Star:</strong> {html_escape(ns)}</div>")

    return "\n".join(parts)


def render_calendar(data):
    cal = data.get("content_calendar", data)
    parts = []
    parts.append(f"<h2>Calendar Angle</h2><p>{html_escape(cal.get('calendar_angle', ''))}</p>")

    pf = cal.get("posting_frequency", {})
    if pf:
        parts.append("<h2>Posting Frequency</h2><table><tr><th>Channel</th><th>Per Week</th></tr>")
        for k, v in pf.items():
            parts.append(f"<tr><td>{html_escape(k.replace('_', ' '))}</td><td>{html_escape(v)}</td></tr>")
        parts.append("</table>")

    pillars = cal.get("content_pillars", [])
    if pillars:
        parts.append("<h2>Content Pillars</h2>")
        for p in pillars:
            if isinstance(p, dict):
                parts.append(f"<div class='callout'><strong>{html_escape(p.get('pillar') or p.get('name', ''))}</strong><br><span class='muted'>{html_escape(p.get('rationale', ''))}</span></div>")
            else:
                parts.append(f"<p>{html_escape(p)}</p>")

    for week_key in ("week_1", "week_2", "week_3", "week_4"):
        w = cal.get(week_key)
        if not w:
            continue
        parts.append(f"<h2>{week_key.replace('_', ' ').title()} — {html_escape(w.get('theme', ''))}</h2>")
        posts = w.get("posts", [])
        if posts:
            parts.append("<table><tr><th>Day</th><th>Platform</th><th>Format</th><th>Topic</th><th>Hook</th><th>CTA</th></tr>")
            for p in posts:
                parts.append(
                    f"<tr><td>{html_escape(p.get('day', ''))}</td>"
                    f"<td>{html_escape(p.get('platform', ''))}</td>"
                    f"<td>{html_escape(p.get('format', ''))}</td>"
                    f"<td>{html_escape((p.get('topic') or '')[:90])}</td>"
                    f"<td>{html_escape((p.get('hook') or '')[:80])}</td>"
                    f"<td>{html_escape((p.get('cta') or '')[:80])}</td></tr>"
                )
            parts.append("</table>")
        compliance = w.get(f"{week_key}_compliance_check")
        if compliance:
            parts.append("<h4>Compliance Check</h4><div class='callout'>")
            for k, v in compliance.items():
                parts.append(f"<div><strong>{html_escape(k.replace('_', ' '))}:</strong> {html_escape(v)}</div>")
            parts.append("</div>")

    rules = cal.get("posting_rules", [])
    if rules:
        parts.append("<h2>Posting Rules</h2><ul>")
        for r in rules:
            parts.append(f"<li>{html_escape(r)}</li>")
        parts.append("</ul>")

    return "\n".join(parts)


def render_scripts(data):
    scripts = data.get("scripts") if isinstance(data, dict) else data
    if not scripts:
        scripts = [data] if isinstance(data, dict) and data.get("script") else []
    parts = []
    parts.append("<h2>Week 1 Recording Plan — All scripts to be recorded by Gaurav</h2>")
    parts.append("<div class='callout'><strong>Production rule:</strong> Every script below is recorded by Gaurav using iPhone 13 Pro Max + GoPro Hero 7 Black + wireless mic. NO ElevenLabs, NO synthetic voice. Real voice = brand DNA.</div>")

    for i, item in enumerate(scripts, 1):
        scr = item.get("script", item)
        prod = item.get("production_instructions_for_gaurav", {})
        op = item.get("original_post", {})
        # new format fields
        title_yt = item.get("title_for_youtube", "")
        hook_text = item.get("hook_text", "")
        reel_cut = item.get("reel_cut", "")
        psych = item.get("psychological_framework", "")
        # legacy hook_block support
        hook_block = item.get("hook_block", {})
        recommended_hook_id = hook_block.get("recommended_hook")
        hooks = hook_block.get("hooks", [])
        rec_hook = next((h for h in hooks if h.get("id") == recommended_hook_id), hooks[0] if hooks else {})

        display_title = title_yt or scr.get("topic", op.get("topic", f"Script {i}"))
        platform_tag = item.get("platform_primary", scr.get("platform", op.get("platform", "YouTube + Reel")))
        order = item.get("order", i)

        parts.append("<div class='script-card'>")
        parts.append(f"<span class='day-tag'>Post {html_escape(str(order))} · {html_escape(platform_tag)}</span>")
        if psych:
            parts.append(f"<span class='day-tag' style='margin-left:8px;background:#1e3a4a;'>{html_escape(psych)}</span>")
        parts.append(f"<h3>{html_escape(display_title)}</h3>")

        if hook_text:
            parts.append(f"<h4>Hook (first 30-60s — also Reel/Short cut-point)</h4>")
            parts.append(f"<p><strong>«{html_escape(hook_text)}»</strong></p>")
        elif rec_hook.get("text"):
            parts.append(f"<h4>Recommended Hook ({html_escape(rec_hook.get('pattern', ''))})</h4>")
            parts.append(f"<p><strong>«{html_escape(rec_hook['text'])}»</strong></p>")

        for beat_key in ("beat_1", "beat_2", "beat_3"):
            b = scr.get(beat_key, {})
            if isinstance(b, dict) and b.get("content"):
                parts.append(f"<div class='beat'><div class='label'>{beat_key.replace('_', ' ').title()} — {html_escape(b.get('purpose', ''))}</div>{html_escape(b.get('content', ''))}</div>")
            elif isinstance(b, str) and b:
                parts.append(f"<div class='beat'><div class='label'>{beat_key.replace('_', ' ').title()}</div>{html_escape(b)}</div>")

        if scr.get("cta"):
            parts.append(f"<p><strong>CTA:</strong> {html_escape(scr['cta'])}</p>")
        if scr.get("caption"):
            parts.append(f"<p><strong>Caption:</strong> {html_escape(scr['caption'])}</p>")
        if scr.get("hashtags"):
            parts.append(f"<p class='muted'>{html_escape(' '.join('#' + h.lstrip('#') for h in scr.get('hashtags', [])))}</p>")

        if reel_cut:
            parts.append(f"<div class='beat' style='background:#0f2d3d;border-left:3px solid #0F4C5C;'><div class='label'>📱 Reel / Short Cut (60s version)</div>{html_escape(reel_cut)}</div>")

        if prod:
            parts.append("<div class='gauravbox'>")
            parts.append("<h4>📹 Production Instructions for Gaurav</h4>")
            if isinstance(prod, str):
                parts.append(f"<p>{html_escape(prod)}</p>")
            elif isinstance(prod, dict):
                if prod.get("who_records"):
                    parts.append(f"<p><strong>Who:</strong> {html_escape(prod['who_records'])}</p>")
                if prod.get("framing"):
                    parts.append(f"<p><strong>Framing:</strong> {html_escape(prod['framing'])}</p>")
                if prod.get("duration_target"):
                    parts.append(f"<p><strong>Duration:</strong> {html_escape(prod['duration_target'])}</p>")
                gear = prod.get("gear", {})
                if gear:
                    parts.append("<dl class='gear-grid'>")
                    for k, v in gear.items():
                        parts.append(f"<dt>{html_escape(k.replace('_', ' '))}</dt><dd>{html_escape(v)}</dd>")
                    parts.append("</dl>")
                if prod.get("beat_direction"):
                    parts.append("<p><strong>Beat direction:</strong></p><ul>")
                    for d in prod["beat_direction"]:
                        parts.append(f"<li>{html_escape(d)}</li>")
                    parts.append("</ul>")
                if prod.get("retake_rules"):
                    parts.append("<p><strong>Retake rules:</strong></p><ul>")
                    for d in prod["retake_rules"]:
                        parts.append(f"<li>{html_escape(d)}</li>")
                    parts.append("</ul>")
                if prod.get("post_production_handoff"):
                    parts.append(f"<p><strong>Handoff:</strong> {html_escape(prod['post_production_handoff'])}</p>")
            parts.append("</div>")

        parts.append("</div>")

    return "\n".join(parts)


def render_brand_book(profile):
    parts = []
    parts.append(f"<h2>Brand Identity</h2>")
    parts.append(f"<div class='callout'><strong>{html_escape(profile.get('brand_name', ''))}</strong> — {html_escape(profile.get('industry', ''))}<br><br>"
                 f"<strong>Founder:</strong> {html_escape(profile.get('founder_identity', ''))}</div>")
    parts.append(f"<p>{html_escape(profile.get('brand_brief', ''))}</p>")

    parts.append(f"<h2>Unique Tension</h2>")
    parts.append(f"<div class='callout' style='background:#0F4C5C;color:#fff;'><strong style='color:#fff;'>«{html_escape(profile.get('unique_tension', ''))}»</strong></div>")

    weapons = profile.get("back_end_weapons", [])
    if weapons:
        parts.append("<h2>Back-end Weapons</h2><ol>")
        for w in weapons:
            parts.append(f"<li>{html_escape(w)}</li>")
        parts.append("</ol>")

    parts.append("<h2>Audience Map</h2>")
    parts.append(f"<p><strong>Primary:</strong> {html_escape(profile.get('audience_primary', ''))}</p>")
    parts.append(f"<p><strong>Secondary 1:</strong> {html_escape(profile.get('audience_secondary_1', ''))}</p>")
    parts.append(f"<p><strong>Secondary 2:</strong> {html_escape(profile.get('audience_secondary_2', ''))}</p>")
    nf = profile.get("not_for_audience", [])
    if nf:
        parts.append("<h4>Not For</h4><ul>")
        for x in nf:
            parts.append(f"<li>{html_escape(x)}</li>")
        parts.append("</ul>")

    parts.append("<h2>Voice DNA</h2>")
    parts.append(f"<p>{html_escape(profile.get('tone_of_voice', ''))}</p>")
    parts.append(f"<p class='muted'>{html_escape(profile.get('tone_specifics', ''))}</p>")

    parts.append("<h2>Visual System</h2>")
    palette = profile.get("brand_palette", {})
    if palette:
        parts.append("<table><tr><th>Token</th><th>Value</th></tr>")
        for k, v in palette.items():
            parts.append(f"<tr><td>{html_escape(k)}</td><td><code>{html_escape(v)}</code></td></tr>")
        parts.append("</table>")
    if profile.get("anti_generic_ai_directive"):
        parts.append(f"<div class='callout'>{html_escape(profile['anti_generic_ai_directive'])}</div>")

    gear = profile.get("production_gear", {})
    if gear:
        parts.append("<h2>Production Gear</h2><dl class='gear-grid'>")
        for k, v in gear.items():
            parts.append(f"<dt>{html_escape(k.replace('_', ' '))}</dt><dd>{html_escape(v)}</dd>")
        parts.append("</dl>")

    parts.append("<h2>Volume Plan</h2>")
    vol = profile.get("weekly_volume_target", {})
    if vol:
        parts.append("<table><tr><th>Output</th><th>Per Week</th></tr>")
        for k, v in vol.items():
            parts.append(f"<tr><td>{html_escape(k.replace('_', ' '))}</td><td>{html_escape(v)}</td></tr>")
        parts.append("</table>")

    parts.append("<h2>Revenue Paths</h2><ol>")
    for r in profile.get("revenue_paths", []):
        parts.append(f"<li>{html_escape(r)}</li>")
    parts.append("</ol>")

    parts.append("<h2>What to Never Say</h2><ul>")
    for x in profile.get("what_to_never_say", []):
        parts.append(f"<li>{html_escape(x)}</li>")
    parts.append("</ul>")

    parts.append("<h2>Grid Control Naming Rule</h2>")
    gcr = profile.get("grid_control_naming_rule", {})
    if isinstance(gcr, dict):
        for k, v in gcr.items():
            parts.append(f"<p><strong>{html_escape(k.replace('_', ' '))}:</strong> {html_escape(v)}</p>")

    parts.append("<h2>Hire Signal Rule</h2>")
    hsr = profile.get("hire_signal_rule", {})
    if isinstance(hsr, dict):
        for k, v in hsr.items():
            parts.append(f"<p><strong>{html_escape(k.replace('_', ' '))}:</strong> {html_escape(v if not isinstance(v, list) else ', '.join(v))}</p>")

    parts.append("<h2>Freebie + DM Automation Strategy</h2>")
    fs = profile.get("freebie_strategy", {})
    if isinstance(fs, dict):
        for k, v in fs.items():
            parts.append(f"<p><strong>{html_escape(k.replace('_', ' '))}:</strong> {html_escape(v)}</p>")
    dma = profile.get("dm_automation_required", {})
    if isinstance(dma, dict):
        parts.append("<h4>DM Automation</h4>")
        for k, v in dma.items():
            parts.append(f"<p><strong>{html_escape(k.replace('_', ' '))}:</strong> {html_escape(v if not isinstance(v, list) else ', '.join(v))}</p>")

    parts.append("<h2>North-Star Metric</h2>")
    parts.append(f"<div class='callout' style='background:#E07A5F;color:#fff;'><strong style='color:#fff;'>{html_escape(profile.get('north_star_metric', ''))}</strong><br>{html_escape(profile.get('north_star_metric_definition', ''))}</div>")

    return "\n".join(parts)


def html_to_pdf(html_path: Path, pdf_path: Path):
    cmd = [
        CHROME,
        "--headless",
        "--disable-gpu",
        "--no-pdf-header-footer",
        "--virtual-time-budget=4000",
        f"--print-to-pdf={pdf_path}",
        f"file://{html_path.resolve()}",
    ]
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
    if pdf_path.exists() and pdf_path.stat().st_size > 1000:
        return True
    print(f"[pdf] FAILED for {html_path.name}: {r.stderr[:300]}")
    return False


def write_deliverable(filename: str, title: str, body_html: str):
    html_path = OUT_DIR / f"{filename}.html"
    pdf_path = OUT_DIR / f"{filename}.pdf"
    full = HTML_SHELL.format(
        title=html_escape(title),
        css=CSS,
        body=body_html,
        datestamp=datetime.now().strftime("%B %d, %Y"),
        filename=filename,
    )
    html_path.write_text(full)
    ok = html_to_pdf(html_path, pdf_path)
    print(f"[render] {'OK' if ok else 'HTML-ONLY'} {filename} → {pdf_path if ok else html_path}")
    return html_path, pdf_path


def render_recording_checklist(cal, scripts_data):
    """One-page table: Day | Title | Format | Duration | Face | Drop folder."""
    posts = cal.get("week_1", {}).get("posts", [])
    scripts = (scripts_data or {}).get("scripts", []) if isinstance(scripts_data, dict) else []
    flags = (scripts_data or {}).get("human_face_flags", []) if isinstance(scripts_data, dict) else []
    flag_idx = {(f.get("day"), f.get("format")): f.get("note", "") for f in flags}

    parts = []
    parts.append("<h2>Week 1 Recording Checklist</h2>")
    parts.append("<p>One row per post. Tick as you record. Carousel posts need NO recording — they are 100% AI-generated by Creative Director.</p>")
    parts.append("<table><tr><th>#</th><th>Day</th><th>Format</th><th>Topic</th><th>Recording?</th><th>Drop folder</th></tr>")
    for i, p in enumerate(posts, 1):
        day = p.get("day", "?")
        fmt = p.get("format", "")
        topic = (p.get("topic") or "")[:75]
        is_carousel = "carousel" in fmt.lower()
        if is_carousel:
            rec = "<strong style='color:#0F4C5C;'>NO</strong> — AI-generated"
        else:
            human = "Face on camera" if (p.get("day"), p.get("format")) in flag_idx else "Voice + screen"
            rec = f"<strong style='color:#E07A5F;'>YES</strong> — {human}"
        slug = ''.join(c.lower() if c.isalnum() else '_' for c in topic).strip('_')[:40]
        suffix = '_carousel_no_recording' if is_carousel else ''
        folder = f"post_{i:02d}_day{day}_{slug}{suffix}"
        parts.append(f"<tr><td>{i}</td><td>{html_escape(day)}</td><td>{html_escape(fmt)}</td><td>{html_escape(topic)}</td><td>{rec}</td><td><code>raw_recordings/week_1/{html_escape(folder)}/</code></td></tr>")
    parts.append("</table>")

    parts.append("<h2>Recording Workflow</h2><ol>")
    parts.append("<li>Read your script in <code>03_scripts_week1.pdf</code> — find the dark teal box labeled <strong>Production Instructions for Gaurav</strong>.</li>")
    parts.append("<li>Set up gear per the script: iPhone 13 Pro Max 4K, GoPro 7 Black for B-roll, wireless mic, natural light only.</li>")
    parts.append("<li>Record. Restart per beat if you stumble (not the whole script). Record 2 alternate hook takes.</li>")
    parts.append("<li>Drop raw .mov + audio in the folder shown above. Do NOT delete the README inside.</li>")
    parts.append("<li>Ping me when all uploads done. Creative Director Phase B runs the overlays + transitions on your footage.</li>")
    parts.append("</ol>")

    parts.append("<h2>Already Done — No Work From You</h2><ul>")
    parts.append("<li>Brand Book v2 — <code>04_brand_book_v2.pdf</code></li>")
    parts.append("<li>90-Day Strategy — <code>01_strategy_90day.pdf</code></li>")
    parts.append("<li>30-Day Calendar — <code>02_content_calendar.pdf</code></li>")
    parts.append("<li>10 Week 1 Scripts — <code>03_scripts_week1.pdf</code></li>")
    parts.append("<li>Folder structure — <code>brands/askgauravai/raw_recordings/week_1/</code></li>")
    parts.append("</ul>")

    parts.append("<h2>Running In Background (no action from you)</h2><ul>")
    parts.append("<li>Brand Guardian — voice/positioning consistency check across all outputs</li>")
    parts.append("<li>Creative Director Phase A — 3 IG carousel decks + thumbnails + cover frames</li>")
    parts.append("</ul>")

    parts.append("<h2>Waiting On You</h2><ul>")
    parts.append("<li>Record the 7 video pieces (Day 2 long-form + Day 3, 4, 5, 6 Reels + Day 4, 6 Shorts)</li>")
    parts.append("<li>Drop raw files in the matching post folders</li>")
    parts.append("<li>Ping me when uploads complete</li>")
    parts.append("</ul>")

    return "\n".join(parts)


def main():
    print(f"[render] output dir: {OUT_DIR}")

    strategy_path = BRAND_DIR / "strategy_90day.json"
    if strategy_path.exists():
        write_deliverable("01_strategy_90day", "90-Day Strategy", render_strategy(json.loads(strategy_path.read_text())))

    cal_path = BRAND_DIR / "content_calendar.json"
    if cal_path.exists():
        write_deliverable("02_content_calendar", "30-Day Content Calendar", render_calendar(json.loads(cal_path.read_text())))

    pa = BRAND_DIR / "outputs" / "pending_approval" / "script-writer"
    latest_scripts = None
    if pa.exists():
        candidates = sorted(pa.glob("*scripts*.json"))
        if candidates:
            latest_scripts = candidates[-1]
    if latest_scripts:
        raw = latest_scripts.read_text()
        idx = raw.find("{")
        scripts_data = json.loads(raw[idx:] if idx > 0 else raw)
        write_deliverable("03_scripts_week1", "Week 1 Scripts — Recording Plan", render_scripts(scripts_data))
    else:
        print("[render] no scripts file yet — skipping scripts pdf")

    profile_path = BRAND_DIR / "brand_profile.json"
    if profile_path.exists():
        write_deliverable("04_brand_book_v2", "ASKGauravAI Brand Book v2", render_brand_book(json.loads(profile_path.read_text())))

    # 00 — Recording Checklist (always-first reference page)
    if cal_path.exists():
        cal_data = json.loads(cal_path.read_text())
        scripts_data = None
        if latest_scripts:
            raw_s = latest_scripts.read_text()
            idx_s = raw_s.find("{")
            scripts_data = json.loads(raw_s[idx_s:] if idx_s > 0 else raw_s)
        write_deliverable("00_recording_checklist", "Week 1 — Your Recording Checklist", render_recording_checklist(cal_data, scripts_data))

    print(f"[render] DONE — {OUT_DIR}")
    print("[render] Open PDFs:")
    for f in sorted(OUT_DIR.glob("*.pdf")):
        print(f"  open '{f}'")


if __name__ == "__main__":
    main()
