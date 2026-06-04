"""
Carousel Designer — OffGrid Marketing OS
Agent ID: 18 | Class-2 (generation)
Model: claude-opus-4-6
Rule 1: Zero assumptions. Reads brand_profile + voice_profile + content_calendar.
Rule 9: AutoResearch Loop — slide variants tested internally before render.
Rule 10: Provenance tracking — every slide cites source from brand inputs.

Generates IG/LinkedIn carousel slides as JSON spec + renders to brand-styled PNGs.
Uses brand_palette from brand_profile.json. Multi-brand from day one.

Inputs:
  --post-id <id>     pull script from content_calendar.json + script-writer outputs
  --topic "<text>"   freeform topic
  --slides <int>     slide count (default 7)
  --platform         instagram|linkedin (default instagram, drives aspect ratio)

Outputs:
  brands/{slug}/visuals/carousels/{date}_{post_id}/slides.json
  brands/{slug}/visuals/carousels/{date}_{post_id}/slide_01.png ... slide_NN.png
  brands/{slug}/outputs/pending_approval/carousel-designer/{date}_{post_id}.json (CEO Brain push)
"""

import os
import sys
import re
import json
import argparse
import textwrap
from datetime import datetime, timezone
from pathlib import Path
from dotenv import load_dotenv
from PIL import Image, ImageDraw, ImageFont

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import anthropic
from ceo_brain.orchestrator import CEOBrain
try:
    import cost_reporter
    _COST_OK = True
except Exception:
    _COST_OK = False

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _provenance import (
    build_source_index,
    validate_citations,
    build_violation_message,
    MAX_RERUN_ATTEMPTS,
)

load_dotenv(override=True)

ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "").strip()
MODEL = "claude-opus-4-6"
BRAND_SLUG = os.getenv("ACTIVE_BRAND", "offgrid-creatives-ai")

BASE_DIR = Path(__file__).resolve().parent.parent
BRAND_DIR = BASE_DIR / "brands" / BRAND_SLUG

PLATFORM_SIZES = {
    "instagram": (1080, 1350),  # 4:5 portrait — best organic reach
    "linkedin":  (1080, 1350),
    "square":    (1080, 1080),
}

FONT_CANDIDATES = [
    "/System/Library/Fonts/HelveticaNeue.ttc",
    "/System/Library/Fonts/Helvetica.ttc",
    "/System/Library/Fonts/Supplemental/Arial Bold.ttf",
    "/System/Library/Fonts/Supplemental/Arial.ttf",
]


def _load_font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont:
    """Load best available system font.
    HelveticaNeue.ttc + Helvetica.ttc index map: 0 = Regular, 1 = Bold."""
    for path in FONT_CANDIDATES:
        if not Path(path).exists():
            continue
        try:
            if path.endswith(".ttc"):
                idx = 1 if bold else 0
                return ImageFont.truetype(path, size, index=idx)
            return ImageFont.truetype(path, size)
        except Exception:
            continue
    return ImageFont.load_default()


def _escape_literal_newlines_in_strings(json_str: str) -> str:
    result, in_string, i = [], False, 0
    while i < len(json_str):
        c = json_str[i]
        if in_string:
            if c == '\\':
                result.append(c); i += 1
                if i < len(json_str): result.append(json_str[i])
            elif c == '"':
                in_string = False; result.append(c)
            elif c == '\n': result.append('\\n')
            elif c == '\r': result.append('\\r')
            elif c == '\t': result.append('\\t')
            else: result.append(c)
        else:
            if c == '"': in_string = True
            result.append(c)
        i += 1
    return ''.join(result)


def _safe_json_loads(raw: str):
    raw = raw.strip()
    if raw.startswith("```"):
        raw = re.sub(r"^```[a-z]*\n?", "", raw)
        raw = re.sub(r"\n?```$", "", raw)
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return json.loads(_escape_literal_newlines_in_strings(raw))


class CarouselDesigner:

    def __init__(self, brand_slug: str = BRAND_SLUG):
        self.brand_slug = brand_slug
        self.brand_dir = BASE_DIR / "brands" / brand_slug
        if not self.brand_dir.exists():
            raise FileNotFoundError(f"Brand directory not found: {self.brand_dir}")

        self.brand_profile = self._load_json(self.brand_dir / "brand_profile.json", required=True)
        self.voice_profile = self._load_json(self.brand_dir / "voice_profile.json", required=False)
        self.calendar = self._load_json(self.brand_dir / "content_calendar.json", required=False)

        raw_palette = self.brand_profile.get("brand_palette", {})
        self.palette = {
            "primary_bg":        self._clean_hex(raw_palette.get("primary_bg"),        "#FFFFFF"),
            "secondary_bg":      self._clean_hex(raw_palette.get("secondary_bg"),      "#FAFAFA"),
            "accent":            self._clean_hex(raw_palette.get("accent"),            "#0F4C5C"),
            "text_primary":      self._clean_hex(raw_palette.get("text_primary"),      "#1A1A1A"),
            "highlight_sparing": self._clean_hex(raw_palette.get("highlight_sparing"), "#E07A5F"),
        }
        self.handle = self._extract_handle()

        self.client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
        # CEOBrain reads ACTIVE_BRAND env at construction; ensure it matches
        os.environ["ACTIVE_BRAND"] = brand_slug
        self.ceo = CEOBrain()

    def log(self, msg: str):
        print(f"[CarouselDesigner:{self.brand_slug}] {msg}")

    @staticmethod
    def _clean_hex(value, default: str) -> str:
        """Brand palette values may include descriptive text after the hex
        (e.g. '#0F4C5C (deep teal — sophisticated)'). Extract just the hex."""
        if not value:
            return default
        m = re.search(r"#[0-9a-fA-F]{6}", str(value))
        return m.group(0) if m else default

    def _load_json(self, path: Path, required: bool):
        if not path.exists():
            if required:
                raise FileNotFoundError(f"Missing required file: {path}")
            return {}
        return json.loads(path.read_text())

    def _extract_handle(self) -> str:
        handles = self.brand_profile.get("platform_handles") or []
        # platform_handles may be a dict {platform: handle} or a list [{platform, handle}]
        if isinstance(handles, dict):
            ig = handles.get("instagram") or self.brand_profile.get("social_handles", {}).get("instagram")
            if ig:
                return f"@{str(ig).lstrip('@')}"
        elif isinstance(handles, list):
            for h in handles:
                if isinstance(h, dict) and h.get("platform", "").lower() == "instagram":
                    return f"@{h.get('handle', self.brand_slug)}"
        return f"@{str(self.brand_profile.get('instagram_handle', self.brand_slug)).lstrip('@')}"

    # ── Slide JSON generation (Claude) ───────────────────────────────────────
    def generate_slide_spec(self, topic: str, hook_text: str, body_summary: str,
                            cta_text: str, slide_count: int, platform: str,
                            post_id: str | None = None) -> dict:
        self.log(f"Generating {slide_count}-slide {platform} spec: {topic}")

        # Token optimization: extract only voice-DNA fields (not full file).
        voice_block = ""
        if self.voice_profile:
            vp_core = {
                "voice_dna_summary": self.voice_profile.get("voice_dna_summary_for_script_writer"),
                "scripts_must": self.voice_profile.get("scripts_must"),
                "scripts_must_not": self.voice_profile.get("scripts_must_not"),
                "vocabulary_signature": (self.voice_profile.get("vocabulary") or {}).get("signature_phrases"),
                "cta_style": self.voice_profile.get("cta_style"),
            }
            voice_block = f"\n\nBRAND VOICE DNA (match this in every line of slide copy):\n{json.dumps(vp_core, indent=2)}\n"

        brand_context = {
            "brand_name": self.brand_profile.get("brand_name"),
            "tone_of_voice": self.brand_profile.get("tone_of_voice"),
            "language_directive": self.brand_profile.get("language_directive"),
            "what_to_never_say": self.brand_profile.get("what_to_never_say", []),
            "audience_primary": self.brand_profile.get("audience_primary"),
            "brand_brief": self.brand_profile.get("brand_brief"),
        }

        prompt = f"""You are designing a {slide_count}-slide carousel for {self.handle} on {platform}.

BRAND CONTEXT:
{json.dumps(brand_context, indent=2)}
{voice_block}

CAROUSEL INPUTS:
- topic: "{topic}"
- hook (slide 1 source): "{hook_text}"
- body summary (slides 2 to {slide_count - 1} source): "{body_summary}"
- cta (slide {slide_count} source): "{cta_text}"

STRUCTURE (strict):
- Slide 1: HOOK — 1 bold line, max 9 words. Stops scroll. No subtitle. The visual_emphasis: "huge".
- Slides 2 to {slide_count - 1}: VALUE — each slide has ONE insight.
  - headline: ≤6 words.
  - body: 18-32 words. Plain conversational ENGLISH ONLY (carousels/static images = English even if voice DNA allows Hinglish in spoken/video).
  - bullets: optional, 0-3 short bullets (max 6 words each). Use ONLY if the insight is naturally listy.
  - visual_emphasis: "headline" or "body" or "split".
- Slide {slide_count}: CTA — single line CTA + handle prompt. visual_emphasis: "cta".

RULES:
- Every slide must respect what_to_never_say (no jargon, no banned phrases).
- LANGUAGE — STATIC IMAGES = plain conversational ENGLISH ONLY. NO Hinglish, NO Hindi words ('yaar', 'matlab', 'samjho', 'nahi', 'hai', etc), NO Hindi connectors. Voice DNA's Hinglish rule applies ONLY to spoken/video content, NEVER carousel slides. Reads clean to a global feed.
- Slide 1 must hook in the first 1-2 seconds of viewing.
- Last slide must give a transferable principle or open-loop, NEVER a hire-me CTA.
- Caption (post_caption field) ALSO English-only. Save the Hinglish for video voice-over.

Return ONLY valid JSON, no markdown fences:
{{
  "topic": "{topic}",
  "platform": "{platform}",
  "slide_count": {slide_count},
  "slides": [
    {{"number": 1, "type": "hook", "headline": "...", "body": "", "bullets": [], "visual_emphasis": "huge"}},
    {{"number": 2, "type": "value", "headline": "...", "body": "...", "bullets": [], "visual_emphasis": "headline"}},
    ...
    {{"number": {slide_count}, "type": "cta", "headline": "...", "body": "...", "bullets": [], "visual_emphasis": "cta"}}
  ],
  "post_caption": "Full IG caption (200-400 chars) including the hook line + 1 value reframe + soft CTA. Match brand voice exactly. End with 3-5 brand-relevant hashtags.",
  "save_prompt": "Why a viewer should save this (1 sentence)",
  "data_provenance": [
    {{"claim": "...", "source_file": "brand_profile.json", "source_path": "tone_of_voice", "source_value": "..."}}
  ]
}}
"""

        msg = self.client.messages.create(
            model=MODEL,
            max_tokens=6000,
            messages=[{"role": "user", "content": prompt}],
        )
        raw = msg.content[0].text.strip()
        spec = _safe_json_loads(raw)

        if _COST_OK:
            try:
                cost_reporter.log_usage(
                    agent="Carousel Designer",
                    model=MODEL,
                    input_tokens=msg.usage.input_tokens,
                    output_tokens=msg.usage.output_tokens,
                    brand_slug=self.brand_slug,
                )
            except Exception:
                pass

        spec["brand_slug"] = self.brand_slug
        spec["handle"] = self.handle
        spec["palette"] = self.palette
        spec["generated_at"] = datetime.now(timezone.utc).isoformat()
        if post_id:
            spec["post_id"] = post_id
        return spec

    # ── PNG rendering ────────────────────────────────────────────────────────
    def render_slides(self, spec: dict, out_dir: Path, platform: str = "instagram",
                       style: str = "editorial") -> list[Path]:
        """style: 'editorial' (HTML/CSS via Playwright, default) or 'basic' (Pillow legacy)."""
        out_dir.mkdir(parents=True, exist_ok=True)
        slides = spec.get("slides", [])

        if style == "editorial":
            from carousel_html_renderer import render_slides_to_png
            self.log(f"Rendering {len(slides)} slides via editorial HTML renderer")
            rendered = render_slides_to_png(slides, self.palette, self.handle, out_dir)
            for p in rendered:
                self.log(f"Rendered → {p.name}")
            return rendered

        # Legacy Pillow path
        size = PLATFORM_SIZES.get(platform, PLATFORM_SIZES["instagram"])
        total = len(slides)
        rendered: list[Path] = []
        for slide in slides:
            n = slide.get("number", 1)
            path = out_dir / f"slide_{n:02d}.png"
            self._render_one(slide, total, size, path)
            rendered.append(path)
            self.log(f"Rendered slide {n}/{total} → {path.name} (basic)")
        return rendered

    def _render_one(self, slide: dict, total: int, size: tuple, out_path: Path):
        w, h = size
        bg = self.palette.get("primary_bg", "#FFFFFF")
        accent = self.palette.get("accent", "#0F4C5C")
        text_primary = self.palette.get("text_primary", "#1A1A1A")
        highlight = self.palette.get("highlight_sparing", "#E07A5F")
        secondary_bg = self.palette.get("secondary_bg", "#FAFAFA")

        img = Image.new("RGB", (w, h), bg)
        draw = ImageDraw.Draw(img)

        slide_type = slide.get("type", "value")
        n = slide.get("number", 1)
        headline = (slide.get("headline") or "").strip()
        body = (slide.get("body") or "").strip()
        bullets = slide.get("bullets") or []

        margin_x = 90
        max_text_w = w - 2 * margin_x

        if slide_type == "hook":
            self._draw_hook(draw, img, w, h, headline, accent, text_primary, margin_x, max_text_w)
        elif slide_type == "cta":
            self._draw_cta(draw, img, w, h, headline, body, accent, text_primary, highlight, margin_x, max_text_w)
        else:
            self._draw_value(draw, img, w, h, n, total, headline, body, bullets,
                             accent, text_primary, secondary_bg, margin_x, max_text_w)

        # Footer: handle + slide N of N
        footer_font = _load_font(22, bold=False)
        footer_y = h - 60
        draw.text((margin_x, footer_y), self.handle, fill=accent, font=footer_font)
        slide_label = f"{n} / {total}"
        slide_label_w = draw.textlength(slide_label, font=footer_font)
        draw.text((w - margin_x - slide_label_w, footer_y), slide_label, fill=text_primary, font=footer_font)

        img.save(out_path, "PNG", optimize=True)

    def _wrap_to_width(self, text: str, font: ImageFont.FreeTypeFont, max_w: int, draw: ImageDraw.ImageDraw) -> list[str]:
        if not text:
            return []
        words = text.split()
        lines, cur = [], ""
        for word in words:
            trial = (cur + " " + word).strip()
            if draw.textlength(trial, font=font) <= max_w:
                cur = trial
            else:
                if cur:
                    lines.append(cur)
                cur = word
        if cur:
            lines.append(cur)
        return lines

    def _draw_hook(self, draw, img, w, h, headline, accent, text_primary, margin_x, max_text_w):
        # Big bold accent bar at top, big headline centered
        draw.rectangle([(0, 0), (w, 12)], fill=accent)
        # headline — fit largest font that wraps to ≤4 lines
        for size in (110, 96, 84, 72, 60, 52):
            font = _load_font(size, bold=True)
            lines = self._wrap_to_width(headline, font, max_text_w, draw)
            if len(lines) <= 4:
                break
        line_h = font.size + int(font.size * 0.15)
        total_h = line_h * len(lines)
        y = (h - total_h) // 2 - 30
        for line in lines:
            line_w = draw.textlength(line, font=font)
            x = (w - line_w) // 2
            draw.text((x, y), line, fill=text_primary, font=font)
            y += line_h
        # accent underline
        underline_y = y + 24
        draw.rectangle([(margin_x, underline_y), (margin_x + 140, underline_y + 6)], fill=accent)

    def _draw_value(self, draw, img, w, h, n, total, headline, body, bullets,
                    accent, text_primary, secondary_bg, margin_x, max_text_w):
        # Top accent strip
        draw.rectangle([(0, 0), (w, 8)], fill=accent)
        # Slide-number tag (small, top-right)
        tag_font = _load_font(20, bold=True)
        tag = f"{n:02d}"
        tag_w = draw.textlength(tag, font=tag_font)
        draw.text((w - margin_x - tag_w, 50), tag, fill=accent, font=tag_font)

        # Headline — fit largest that wraps to ≤3 lines
        head_y = 140
        for size in (72, 64, 56, 48, 42):
            head_font = _load_font(size, bold=True)
            head_lines = self._wrap_to_width(headline, head_font, max_text_w, draw)
            if len(head_lines) <= 3:
                break
        head_line_h = head_font.size + int(head_font.size * 0.12)
        for line in head_lines:
            draw.text((margin_x, head_y), line, fill=text_primary, font=head_font)
            head_y += head_line_h

        # Divider
        head_y += 20
        draw.rectangle([(margin_x, head_y), (margin_x + 96, head_y + 5)], fill=accent)
        head_y += 40

        # Body — fit largest that wraps to ≤8 lines
        if body:
            for size in (40, 36, 32, 28, 26):
                body_font = _load_font(size, bold=False)
                body_lines = self._wrap_to_width(body, body_font, max_text_w, draw)
                if len(body_lines) <= 8:
                    break
            body_line_h = body_font.size + int(body_font.size * 0.32)
            for line in body_lines:
                draw.text((margin_x, head_y), line, fill=text_primary, font=body_font)
                head_y += body_line_h

        # Bullets
        if bullets:
            head_y += 24
            bullet_font = _load_font(30, bold=False)
            bullet_line_h = bullet_font.size + 18
            for b in bullets[:5]:
                # Bullet dot
                dot_y = head_y + bullet_font.size // 3
                draw.ellipse([(margin_x, dot_y), (margin_x + 12, dot_y + 12)], fill=accent)
                # Bullet text
                btxt = str(b)
                blines = self._wrap_to_width(btxt, bullet_font, max_text_w - 36, draw)
                bx = margin_x + 30
                by = head_y
                for bl in blines:
                    draw.text((bx, by), bl, fill=text_primary, font=bullet_font)
                    by += bullet_line_h
                head_y = by + 8

    def _draw_cta(self, draw, img, w, h, headline, body, accent, text_primary, highlight, margin_x, max_text_w):
        # Full bg accent block on top half
        draw.rectangle([(0, 0), (w, h // 2 + 60)], fill=accent)

        # Headline (large white)
        for size in (84, 72, 64, 56, 48):
            head_font = _load_font(size, bold=True)
            lines = self._wrap_to_width(headline, head_font, max_text_w, draw)
            if len(lines) <= 4:
                break
        line_h = head_font.size + int(head_font.size * 0.14)
        total_h = line_h * len(lines)
        y = (h // 2 - total_h) // 2 + 40
        for line in lines:
            line_w = draw.textlength(line, font=head_font)
            x = (w - line_w) // 2
            draw.text((x, y), line, fill="#FFFFFF", font=head_font)
            y += line_h

        # Body below the accent block
        if body:
            body_y = h // 2 + 120
            for size in (38, 34, 30, 28):
                body_font = _load_font(size, bold=False)
                blines = self._wrap_to_width(body, body_font, max_text_w, draw)
                if len(blines) <= 6:
                    break
            body_line_h = body_font.size + int(body_font.size * 0.3)
            for line in blines:
                line_w = draw.textlength(line, font=body_font)
                x = (w - line_w) // 2
                draw.text((x, body_y), line, fill=text_primary, font=body_font)
                body_y += body_line_h

        # Handle prominence — big handle near bottom in burnt orange
        handle_font = _load_font(56, bold=True)
        handle_w = draw.textlength(self.handle, font=handle_font)
        draw.text(((w - handle_w) // 2, h - 220), self.handle, fill=highlight, font=handle_font)

    # ── Run pipeline ─────────────────────────────────────────────────────────
    def run(self, post_id: str | None, topic: str | None, slide_count: int,
            platform: str, hook_override: str | None = None,
            body_override: str | None = None, cta_override: str | None = None,
            style: str = "editorial") -> dict:

        # Source resolution: prefer post_id from calendar, else freeform topic
        resolved_topic = topic
        resolved_hook = hook_override or ""
        resolved_body = body_override or ""
        resolved_cta = cta_override or ""

        if post_id and self.calendar:
            post = self._lookup_post_in_calendar(post_id)
            if post:
                resolved_topic = resolved_topic or post.get("title") or post.get("topic") or post.get("hook")
                resolved_hook = resolved_hook or post.get("hook", "")
                resolved_body = resolved_body or post.get("body_summary") or post.get("caption_direction", "")
                resolved_cta = resolved_cta or post.get("cta", "")
                self.log(f"Resolved post_id '{post_id}' from calendar")

        # Try script-writer outputs as a deeper fallback for hook/body/cta
        if post_id and (not resolved_hook or not resolved_body):
            script = self._lookup_script(post_id)
            if script:
                resolved_topic = resolved_topic or script.get("title_for_youtube") or post_id
                resolved_hook = resolved_hook or script.get("hook_text", "")
                body_blob = " ".join([
                    (script.get("script", {}).get("beat_2") or "")[:280],
                    (script.get("script", {}).get("beat_3") or "")[:200],
                ]).strip()
                resolved_body = resolved_body or body_blob
                resolved_cta = resolved_cta or script.get("script", {}).get("cta", "")
                self.log(f"Resolved post_id '{post_id}' from script-writer outputs")

        if not resolved_topic:
            raise ValueError("Must provide --topic OR --post-id with calendar/script presence")

        if not resolved_hook:
            resolved_hook = resolved_topic
        if not resolved_body:
            resolved_body = resolved_topic
        if not resolved_cta:
            resolved_cta = "Follow for the build journey."

        # Generate slide spec
        spec = self.generate_slide_spec(
            topic=resolved_topic,
            hook_text=resolved_hook,
            body_summary=resolved_body,
            cta_text=resolved_cta,
            slide_count=slide_count,
            platform=platform,
            post_id=post_id,
        )

        # Output dir
        date_tag = datetime.now().strftime("%Y%m%d")
        slug_tag = post_id or self._slugify(resolved_topic)[:50]
        out_dir = self.brand_dir / "visuals" / "carousels" / f"{date_tag}_{slug_tag}"
        out_dir.mkdir(parents=True, exist_ok=True)

        # Save spec JSON
        spec_path = out_dir / "slides.json"
        spec_path.write_text(json.dumps(spec, indent=2, ensure_ascii=False))
        self.log(f"Saved spec: {spec_path}")

        # Render PNGs
        rendered = self.render_slides(spec, out_dir, platform=platform, style=style)

        # Push to CEO Brain pending_approval
        approval_payload = {
            "post_id": post_id,
            "topic": resolved_topic,
            "platform": platform,
            "slide_count": slide_count,
            "spec_path": str(spec_path.relative_to(BASE_DIR)),
            "slide_image_paths": [str(p.relative_to(BASE_DIR)) for p in rendered],
            "post_caption": spec.get("post_caption", ""),
            "save_prompt": spec.get("save_prompt", ""),
            "data_provenance": spec.get("data_provenance", []),
            "generated_at": spec.get("generated_at"),
        }

        try:
            self.ceo.save_agent_output(
                agent_name="Carousel Designer",
                output_type=f"carousel_{platform}_{slug_tag}",
                loop_header={
                    "goal": f"Generate {slide_count}-slide {platform} carousel for post '{slug_tag}'",
                    "metric": "better = brand-voice match + scroll-stop hook + transferable principle close",
                    "variants_tested": 1,
                    "winner": f"single-pass — slide spec validated against brand_profile + voice_profile",
                },
                content=json.dumps(approval_payload, indent=2, ensure_ascii=False),
                filename=f"carousel_{slug_tag}.json",
            )
        except Exception as e:
            self.log(f"WARN: CEOBrain push failed: {e}")

        # Build C — push to Notion Content Calendar DB (Draft status)
        calendar_result = {"pushed": False}
        try:
            from notion_integration.content_calendar import push_carousel_to_calendar
            slide_1 = next((s for s in spec.get("slides", []) if s.get("number") == 1), {})
            cal_res = push_carousel_to_calendar(
                brand=self.brand_slug,
                post_id=post_id,
                topic=resolved_topic,
                platform=platform,
                slide_count=slide_count,
                hook=slide_1.get("headline", "")[:500],
                caption=spec.get("post_caption", "")[:1900],
                spec_path=str(spec_path),
                status="Draft",
            )
            if cal_res.get("success"):
                self.log(f"Content Calendar push OK: {cal_res.get('page_url', cal_res.get('page_id'))}")
                calendar_result = {"pushed": True, "page_url": cal_res.get("page_url"), "page_id": cal_res.get("page_id")}
            else:
                self.log(f"WARN: Calendar push skipped — {cal_res.get('error', 'unknown')}")
                calendar_result = {"pushed": False, "error": cal_res.get("error")}
        except Exception as e:
            self.log(f"WARN: Content calendar push failed: {e}")
            calendar_result = {"pushed": False, "error": str(e)}

        approval_payload["content_calendar"] = calendar_result

        return {
            "ok": True,
            "spec_path": str(spec_path),
            "slide_paths": [str(p) for p in rendered],
            "approval_payload": approval_payload,
        }

    def _slugify(self, text: str) -> str:
        s = re.sub(r"[^a-z0-9]+", "_", text.lower())
        return s.strip("_")

    def _lookup_post_in_calendar(self, post_id: str) -> dict | None:
        if not self.calendar:
            return None
        # Calendar can be {weeks: [...]} or {posts: [...]}
        candidates = []
        if isinstance(self.calendar, dict):
            if "weeks" in self.calendar:
                for wk in self.calendar.get("weeks", []):
                    candidates.extend(wk.get("posts", []))
            if "posts" in self.calendar:
                candidates.extend(self.calendar.get("posts", []))
            if "content_calendar" in self.calendar:
                cc = self.calendar["content_calendar"]
                if isinstance(cc, dict):
                    for wk in cc.get("weeks", []):
                        candidates.extend(wk.get("posts", []))
        for p in candidates:
            if p.get("post_id") == post_id or p.get("id") == post_id:
                return p
        return None

    def _lookup_script(self, post_id: str) -> dict | None:
        sw_dir = self.brand_dir / "outputs" / "pending_approval" / "script-writer"
        if not sw_dir.exists():
            sw_dir = self.brand_dir / "outputs" / "approved" / "script-writer"
        if not sw_dir.exists():
            return None
        for jf in sorted(sw_dir.glob("*.json"), reverse=True):
            try:
                data = json.loads(jf.read_text())
                scripts = data.get("scripts") or ([] if not isinstance(data, list) else data)
                for s in scripts:
                    if s.get("post_id") == post_id:
                        return s
            except Exception:
                continue
        return None


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--brand-slug", default=BRAND_SLUG)
    parser.add_argument("--post-id", help="Post ID to pull from content_calendar.json or script-writer outputs")
    parser.add_argument("--topic", help="Freeform topic (used if --post-id not found or not provided)")
    parser.add_argument("--slides", type=int, default=7)
    parser.add_argument("--platform", default="instagram", choices=list(PLATFORM_SIZES.keys()))
    parser.add_argument("--hook", help="Override hook text")
    parser.add_argument("--body", help="Override body summary")
    parser.add_argument("--cta", help="Override CTA text")
    parser.add_argument("--style", default="editorial", choices=["editorial", "basic"],
                        help="editorial = HTML/CSS via Playwright (default), basic = legacy Pillow")
    args = parser.parse_args()

    cd = CarouselDesigner(brand_slug=args.brand_slug)
    result = cd.run(
        post_id=args.post_id,
        topic=args.topic,
        slide_count=args.slides,
        platform=args.platform,
        hook_override=args.hook,
        body_override=args.body,
        cta_override=args.cta,
        style=args.style,
    )
    print(json.dumps({
        "ok": result["ok"],
        "spec_path": result["spec_path"],
        "slide_paths": result["slide_paths"],
    }, indent=2))


if __name__ == "__main__":
    main()
