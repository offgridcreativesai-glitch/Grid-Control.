"""
Creative Director — OffGrid Marketing OS
Agent ID: 4 | Runs after Script Writer is approved.
Model: claude-opus-4-6
Rule 1: Zero assumptions. Reads real competitor data before any creative decision.
Rule 9: AutoResearch Loop — Minimal/Visual-led vs Bold/Headline vs Story/Sequential.
Reads:  brands/{slug}/pending_approval/Script Writer/ + competitors_db.json + brand_profile.json
Writes: brands/{slug}/outputs/pending_approval/Creative Director/ + Notion card
"""

import os
import sys
import json
import base64
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import anthropic
from ceo_brain.orchestrator import CEOBrain
import cost_reporter
# Rule 10 — Source citation enforcement
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _provenance import (
    build_source_index,
    validate_citations,
    build_violation_message,
    MAX_RERUN_ATTEMPTS,
)


def _escape_literal_newlines_in_strings(json_str: str) -> str:
    result = []
    in_string = False
    i = 0
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
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return json.loads(_escape_literal_newlines_in_strings(raw))


load_dotenv(override=True)

ANTHROPIC_API_KEY  = os.getenv("ANTHROPIC_API_KEY", "").strip()
ELEVENLABS_API_KEY = os.getenv("ELEVENLABS_API_KEY", "").strip()
FAL_API_KEY        = os.getenv("FAL_API_KEY", "").strip()
MODEL = "claude-opus-4-6"
BRAND_SLUG = os.getenv("ACTIVE_BRAND", "offgrid-creatives-ai")

# ElevenLabs voice ID — "George" (business, authoritative)
ELEVENLABS_VOICE_ID = "JBFqnCBsd6RMkjVDRZzb"


class CreativeDirector:

    def __init__(self, brand_slug: str = BRAND_SLUG):
        self.brand_slug = brand_slug
        self.log("Initialising Creative Director...")

        self.ceo = CEOBrain()
        self.brand_profile = self.ceo.brand_profile
        self.brand_dir = Path(self.ceo.brand_dir)

        if not ANTHROPIC_API_KEY:
            raise ValueError("ANTHROPIC_API_KEY not found in .env")
        self.client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

        if ELEVENLABS_API_KEY:
            self.log(f"✅ ElevenLabs API key loaded ({ELEVENLABS_API_KEY[:8]}...)")
        else:
            self.log("⚠️  ELEVENLABS_API_KEY not set — audio narration will be skipped")

        if FAL_API_KEY:
            self.log(f"✅ FAL.ai API key loaded ({FAL_API_KEY[:8]}...)")
        else:
            self.log("ℹ️  FAL_API_KEY not set — image prompts will be generated but not executed")

        self._total_input_tokens = 0
        self._total_output_tokens = 0
        self._fal_generations = 0

    def log(self, msg: str) -> None:
        print(f"[CreativeDirector] {msg}")

    # ── Data loaders ──────────────────────────────────────────────────────────

    def load_scripts(self) -> list[dict]:
        """Load most recent Script Writer output from pending_approval/ (slug-cased path)."""
        # Try slug-cased folder first (current convention), fall back to legacy spaces format
        candidates = [
            self.brand_dir / "outputs" / "pending_approval" / "script-writer",
            self.brand_dir / "outputs" / "pending_approval" / "Script Writer",
            self.brand_dir / "outputs" / "approved" / "script-writer",
            self.brand_dir / "outputs" / "approved" / "Script Writer",
        ]
        script_dir = next((p for p in candidates if p.exists()), None)
        if script_dir is None:
            raise FileNotFoundError(
                "No Script Writer outputs found in pending_approval/ or approved/. "
                "Run script_writer.py first."
            )
        self.log(f"Loading scripts from: {script_dir}")
        files = sorted(script_dir.glob("*.json"), key=lambda f: f.stat().st_mtime, reverse=True)
        if not files:
            raise FileNotFoundError("No JSON files found in Script Writer output directory.")

        latest = files[0]
        self.log(f"Loading scripts from: {latest.name}")
        raw = latest.read_text()
        if "---" in raw:
            raw = raw.split("---", 1)[1].strip()
        data = json.loads(raw)
        scripts = data.get("scripts", [])
        self.log(f"Loaded {len(scripts)} scripts.")
        return scripts

    def load_competitors(self) -> dict:
        """Load competitors_db.json — graceful fallback if missing or empty."""
        path = self.brand_dir / "competitors_db.json"
        if path.exists():
            raw = path.read_text().strip()
            if raw:
                try:
                    data = json.loads(raw)
                    self.log(f"Loaded competitors_db.json ({len(data)} keys).")
                    return data
                except json.JSONDecodeError:
                    self.log("⚠️  competitors_db.json is malformed — proceeding without it.")
            else:
                self.log("⚠️  competitors_db.json is empty — proceeding without competitor data.")
        else:
            self.log("⚠️  competitors_db.json not found — proceeding without competitor visual data.")
        return {}

    # ── Brand safety check ────────────────────────────────────────────────────

    def run_brand_safety_check(self, concept: str) -> dict:
        """4-point brand safety check per spec. Returns {passed: bool, flags: []}."""
        prompt = f"""You are a brand safety reviewer for OffGrid Creatives AI.

Run a 4-point brand safety check on this creative concept:

CONCEPT:
{concept}

BRAND: OffGrid Creatives AI — AI-powered Ad Intelligence Reports for D2C founders.
MOOD: Dark, premium, data-driven. Electric green / amber accents on deep black.
PLATFORMS: Instagram + LinkedIn

CHECK THESE 4 POINTS:
1. COPYRIGHT RISK — Does the concept reference any trademarked audio, visual style, or brand?
2. CULTURAL SENSITIVITY — Does it accidentally touch current news tragedies or sensitive topics?
3. PLATFORM POLICY — Would this violate Meta TOS, Instagram guidelines, or LinkedIn policies?
4. BRAND CONSISTENCY — Does this still represent OffGrid Creatives AI correctly?

Return a JSON object ONLY:
{{
  "passed": true or false,
  "flags": ["flag 1 if any", "flag 2 if any"],
  "verdict": "PASS" or "FAIL",
  "notes": "brief reason"
}}

If all 4 checks pass, return passed: true and empty flags array."""

        response = self.client.messages.create(
            model=MODEL,
            max_tokens=512,
            messages=[{"role": "user", "content": prompt}]
        )
        self._total_input_tokens += response.usage.input_tokens
        self._total_output_tokens += response.usage.output_tokens
        raw = response.content[0].text.strip()
        if "```" in raw:
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            return {"passed": True, "flags": [], "verdict": "PASS", "notes": "Parse fallback — assume pass"}

    # ── AutoResearch Loop — Rule 9 ────────────────────────────────────────────

    def run_autoresearch_loop(self, scripts: list[dict], competitors: dict) -> dict:
        """
        3 creative variants:
        A — Minimal text, visual-led
        B — Bold headline, image support
        C — Story format, sequential
        Metric: maximises Save + Share rate on Instagram + LinkedIn
        """
        brand_name = self.brand_profile.get("brand_name", "OffGrid Creatives AI")
        product = self.brand_profile.get("product", "AI Ad Intelligence Report")
        audience = ", ".join(self.brand_profile.get("audience", ["D2C founders"]))
        platforms = ", ".join(self.brand_profile.get("platforms", ["Instagram", "LinkedIn"]))

        # Sample first 3 scripts for context
        script_samples = []
        for item in scripts[:3]:
            s = item.get("script", {})
            script_samples.append({
                "platform": s.get("platform", ""),
                "format": s.get("format", ""),
                "hook": s.get("hook", ""),
                "body_preview": str(s.get("body", ""))[:200],
                "cta": s.get("cta", ""),
                "requires_human_face": item.get("requires_human_face", False),
            })

        competitor_summary = json.dumps(competitors, indent=2)[:800] if competitors else "No competitor data available."

        prompt = f"""You are the Creative Director for {brand_name}.

PRODUCT: {product}
AUDIENCE: {audience}
PLATFORMS: {platforms}
VISUAL DIRECTION: Dark (#0A0A0A / #0D1117), Electric green (#00C853) or Amber (#F5A623) accent, Inter Bold or Space Grotesk, data-driven aesthetic.

SCRIPTS TO DIRECT (sample):
{json.dumps(script_samples, indent=2)}

COMPETITOR VISUAL CONTEXT:
{competitor_summary}

Generate 3 creative direction variants for the first script. Each variant must be complete enough to brief a visual AI.

VARIANT A — Minimal text, visual-led:
Focus on one powerful visual. Text is minimal (3-5 words max). The visual does the heavy lifting.

VARIANT B — Bold headline, image support:
Dominant headline text + supporting data visual or founder image. Text and image have equal weight.

VARIANT C — Story format, sequential (Carousel or Reel):
Multi-frame narrative that builds from problem → stakes → solution → proof → CTA.

For EACH variant provide:
- creative_direction: (Variant A/B/C)
- target_emotion: (Urgency / Calm Authority / Awe / Intrigue / Confidence / Alarm)
- safe_option: (Safe Brand-Aligned direction)
  - image_prompt: (detailed Ideogram prompt — specify: mood, lighting, typography, composition)
  - video_prompt: (detailed Runway/Kling prompt — specify: lens mm, aperture, lighting style, motion)
  - narration_text: (ElevenLabs voiceover — 1-2 sentences, 15-20 words max)
  - hook_text: (3-5 words for thumbnail/text overlay)
  - brand_safety_concept: (brief concept description for safety check)
- viral_option: (Bold Viral direction — must reference 2+ STEPPS levers)
  - stepps_levers: (which 2+ STEPPS levers: Social Currency / Triggers / Emotion / Public / Practical Value / Stories)
  - image_prompt: (detailed Ideogram prompt)
  - video_prompt: (detailed Runway/Kling prompt)
  - narration_text: (ElevenLabs voiceover)
  - hook_text: (3-5 words)
  - brand_safety_concept: (brief concept description for safety check)

⚠️ RULE 10 — SOURCE CITATION ENFORCEMENT (HARD REQUIREMENT) ⚠️

Every creative direction (image_prompt, video_prompt, narration_text, hook_text) MUST trace
back to a real source data point in:
  - brand_profile.json (visual identity, audience, tone)
  - competitors_db.json (visual reference data)
  - content_calendar.json (the post slot context)

For each variant, add an entry to "data_provenance" with:
  - "claim": short text of the creative direction it justifies
  - "source_file": one of: brand_profile.json | competitors_db.json | (script file)
  - "source_path": dot.notation path
  - "source_value": verbatim ≥30-char snippet from the source

Aim for 3–6 provenance entries (one per variant minimum).

Return ONLY valid JSON in this structure:
{{
  "loop_goal": "maximise Save + Share rate across Instagram and LinkedIn",
  "loop_metric": "better = higher save+share rate than last 3 posts combined",
  "data_provenance": [
    {{"claim": "...", "source_file": "brand_profile.json", "source_path": "tone_of_voice", "source_value": "..."}}
  ],
  "variants": [
    {{
      "creative_direction": "Variant A — Minimal text, visual-led",
      "target_emotion": "...",
      "safe_option": {{...}},
      "viral_option": {{...}}
    }}
  ]
}}"""

        # ── Rule 10: source index ──
        project_root = Path(__file__).resolve().parent.parent
        source_files = [
            project_root / "brands" / self.brand_slug / "brand_profile.json",
            project_root / "brands" / self.brand_slug / "competitors_db.json",
            project_root / "brands" / self.brand_slug / "content_calendar.json",
        ]
        source_index = build_source_index(source_files)
        self.log(f"Rule 10: Source index built — {len(source_index)} citable keys")

        # ── Rule 10: Claude call with retry loop ──
        messages = [{"role": "user", "content": prompt}]
        result = None
        validation_report = None
        attempt = 0
        max_attempts = MAX_RERUN_ATTEMPTS + 1

        self.log("Running AutoResearch Loop — 3 creative variants with Rule 10 enforcement...")
        while attempt < max_attempts:
            attempt += 1
            self.log(f"Calling Claude {MODEL} (attempt {attempt}/{max_attempts})...")
            response = self.client.messages.create(
                model=MODEL,
                max_tokens=16000,
                messages=messages
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

            try:
                result = _safe_json_loads(raw)
            except Exception:
                self.log("⚠️  JSON parse failed — attempting partial recovery")
                idx = raw.find("{")
                if idx >= 0:
                    try:
                        result = _safe_json_loads(raw[idx:])
                    except Exception:
                        raise ValueError(f"Could not parse: {raw[:200]}")
                else:
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
        return result

    # ── FAL.ai image generation ───────────────────────────────────────────────

    def generate_image(self, prompt: str, label: str, text_heavy: bool = False) -> str | None:
        """
        Generate image via FAL.ai.
        text_heavy=True  → fal-ai/ideogram/v2  (better for text-on-image)
        text_heavy=False → fal-ai/flux/dev      (photorealistic / mood visuals)
        Returns local file path relative to brand_dir, or None on failure.
        """
        if not FAL_API_KEY:
            self.log(f"  ℹ️  FAL_API_KEY not set — skipping image generation for '{label}'")
            return None

        try:
            import fal_client
            os.environ["FAL_KEY"] = FAL_API_KEY  # fal_client reads FAL_KEY env var

            model = "fal-ai/ideogram/v2" if text_heavy else "fal-ai/flux/dev"
            self.log(f"  Generating image via FAL.ai [{model}] for '{label}'...")

            result = fal_client.subscribe(
                model,
                arguments={"prompt": prompt, "image_size": "landscape_16_9"},
            )

            # fal_client returns dict with images[0].url
            images = result.get("images", [])
            if images:
                self._fal_generations += 1
            if not images:
                self.log(f"  ⚠️  FAL.ai returned no images for '{label}'")
                return None

            image_url = images[0].get("url", "")
            if not image_url:
                return None

            # Download and save the image
            import urllib.request
            image_dir = self.brand_dir / "outputs" / "pending_approval" / "Creative Director" / "images"
            image_dir.mkdir(parents=True, exist_ok=True)
            ts = datetime.now().strftime("%Y%m%d_%H%M%S")
            safe_label = label.lower().replace(" ", "_")[:40]
            ext = "png" if "png" in image_url else "jpg"
            image_path = image_dir / f"{ts}_{safe_label}.{ext}"
            urllib.request.urlretrieve(image_url, image_path)

            self.log(f"  ✅ Image saved: {image_path.name}")
            return str(image_path.relative_to(self.brand_dir))

        except Exception as e:
            self.log(f"  ⚠️  FAL.ai image generation failed for '{label}': {e}")
            return None

    # ── ElevenLabs narration ──────────────────────────────────────────────────

    def generate_narration(self, text: str, label: str) -> str | None:
        """Generate audio narration via ElevenLabs. Returns file path or None."""
        if not ELEVENLABS_API_KEY:
            self.log(f"Skipping narration for '{label}' — no ElevenLabs key.")
            return None

        try:
            from elevenlabs import ElevenLabs
            client = ElevenLabs(api_key=ELEVENLABS_API_KEY)

            self.log(f"Generating narration via ElevenLabs: '{text[:60]}...'")
            audio_gen = client.text_to_speech.convert(
                voice_id=ELEVENLABS_VOICE_ID,
                text=text,
                model_id="eleven_multilingual_v2",
                output_format="mp3_44100_128",
            )
            audio_bytes = b"".join(audio_gen)

            # Save audio file
            audio_dir = self.brand_dir / "outputs" / "pending_approval" / "Creative Director" / "audio"
            audio_dir.mkdir(parents=True, exist_ok=True)
            ts = datetime.now().strftime("%Y%m%d_%H%M%S")
            safe_label = label.lower().replace(" ", "_")[:40]
            audio_path = audio_dir / f"{ts}_{safe_label}.mp3"
            audio_path.write_bytes(audio_bytes)

            self.log(f"✅ Narration saved: {audio_path.name} ({len(audio_bytes):,} bytes)")
            return str(audio_path.relative_to(self.brand_dir))

        except Exception as e:
            self.log(f"⚠️  ElevenLabs narration failed for '{label}': {e}")
            return None

    # ── FAL.ai video transcription ────────────────────────────────────────────

    def _transcribe_video(self, video_path: "Path") -> dict:
        """
        Transcribe video/audio via FAL.ai Whisper.
        Returns {"text": str, "segments": list} with word-level timestamps.
        """
        if not FAL_API_KEY:
            self.log("  ℹ️  FAL_API_KEY not set — transcription skipped, captions unavailable")
            return {"text": "", "segments": []}

        try:
            import fal_client
            os.environ["FAL_KEY"] = FAL_API_KEY

            self.log(f"  Uploading {video_path.name} to FAL.ai storage...")
            with open(video_path, "rb") as f:
                audio_url = fal_client.upload(f.read(), "video/mp4")

            self.log("  Transcribing via FAL.ai Whisper (word-level timestamps)...")
            result = fal_client.subscribe(
                "fal-ai/whisper",
                arguments={
                    "audio_url": audio_url,
                    "task": "transcribe",
                    "language": "en",
                    "chunk_level": "word",
                }
            )
            text = result.get("text", "")
            chunks = result.get("chunks", [])
            self.log(f"  ✅ Transcript: {len(text.split())} words, {len(chunks)} chunks")
            return {"text": text, "segments": chunks}

        except Exception as e:
            self.log(f"  ⚠️  Transcription failed: {e}")
            return {"text": "", "segments": []}

    def _build_caption_clips(self, transcript: dict, duration: float, video_size: tuple) -> list:
        """Build word-grouped caption TextClips from Whisper segments."""
        try:
            from moviepy.editor import TextClip

            segments = transcript.get("segments", [])
            if not segments:
                return []

            w, h = video_size
            chunk_size = 5
            words = []
            for seg in segments:
                if isinstance(seg, dict):
                    ts = seg.get("timestamp", [0, 0])
                    words.append({
                        "word": seg.get("word", "").strip(),
                        "start": ts[0] if isinstance(ts, list) and len(ts) > 0 else 0,
                        "end":   ts[1] if isinstance(ts, list) and len(ts) > 1 else 0,
                    })

            caption_clips = []
            for i in range(0, len(words), chunk_size):
                chunk = words[i:i + chunk_size]
                if not chunk:
                    continue
                text = " ".join(wd["word"] for wd in chunk)
                t_start = chunk[0]["start"]
                t_end   = chunk[-1]["end"] if chunk[-1]["end"] > 0 else t_start + 2.0
                try:
                    txt = (
                        TextClip(
                            text,
                            fontsize=52,
                            color="white",
                            stroke_color="black",
                            stroke_width=2,
                            font="Arial-Bold",
                            method="caption",
                            size=(w - 80, None),
                        )
                        .set_position(("center", h - 280))
                        .set_start(t_start)
                        .set_end(min(t_end, duration))
                    )
                    caption_clips.append(txt)
                except Exception:
                    pass
            return caption_clips

        except Exception as e:
            self.log(f"  ⚠️  Caption build failed: {e}")
            return []

    def _edit_video(self, video_path: "Path", transcript: dict, output_dir: "Path") -> "str | None":
        """
        Founder-Journal reel assembly (delegates to reel_editor):
          • footage to vertical 1080×1920 + warm grade (no crop when already 9:16)
          • kinetic captions timed to the transcript
          • branded motion-graphic inserts at the script beats
          • AI b-roll (FAL t2v) at chosen beats
        Returns output path relative to brand_dir, or None on failure.
        """
        try:
            import reel_editor
            handle = "@" + (self.brand_profile.get("instagram_handle") or self.brand_slug).lstrip("@")
            ts = datetime.now().strftime("%Y%m%d_%H%M%S")
            out = output_dir / f"{ts}_{video_path.stem.lower().replace(' ', '_')[:30]}_reel.mp4"
            res = reel_editor.build_reel(
                video_path, transcript, out, handle=handle,
                work_dir=output_dir / "_work", enable_broll=bool(FAL_API_KEY), log=self.log,
            )
            if res and Path(out).exists():
                self.log(f"  ✅ Reel saved: {out.name} "
                         f"({res['inserts']} inserts, {res['captions']} captions)")
                return str(out.relative_to(self.brand_dir))
            self.log("  ⚠️  reel_editor returned no output")
            return None
        except Exception as e:
            self.log(f"  ⚠️  Reel assembly failed for {video_path.name}: {e}")
            return None

    def _edit_video_legacy(self, video_path: "Path", transcript: dict, output_dir: "Path") -> "str | None":
        """Deprecated moviepy caption-only path (kept for reference)."""
        try:
            from moviepy.editor import VideoFileClip, CompositeVideoClip

            self.log(f"  Editing: {video_path.name}")
            clip = VideoFileClip(str(video_path))
            w, h = clip.size

            # Crop to 9:16 portrait
            target_ratio = 9 / 16
            current_ratio = w / h
            if abs(current_ratio - target_ratio) > 0.05:
                if current_ratio > target_ratio:   # wider — crop sides
                    new_w = int(h * target_ratio)
                    x0 = (w - new_w) // 2
                    clip = clip.crop(x1=x0, x2=x0 + new_w)
                else:                               # taller — crop top/bottom
                    new_h = int(w / target_ratio)
                    y0 = (h - new_h) // 2
                    clip = clip.crop(y1=y0, y2=y0 + new_h)
                self.log("  ✅ Cropped to 9:16")

            # Resize to Reels standard (1080×1920)
            clip = clip.resize((1080, 1920))

            # Overlay captions
            final = clip
            if transcript.get("text"):
                caps = self._build_caption_clips(transcript, clip.duration, clip.size)
                if caps:
                    final = CompositeVideoClip([clip] + caps)
                    self.log(f"  ✅ {len(caps)} caption segments overlaid")

            # Export
            ts = datetime.now().strftime("%Y%m%d_%H%M%S")
            safe_name = video_path.stem.lower().replace(" ", "_")[:30]
            out_path = output_dir / f"{ts}_{safe_name}_reel.mp4"

            final.write_videofile(
                str(out_path), fps=30, codec="libx264",
                audio_codec="aac", bitrate="4000k",
                verbose=False, logger=None,
            )
            clip.close()
            final.close()
            self.log(f"  ✅ Reel saved: {out_path.name}")
            return str(out_path.relative_to(self.brand_dir))

        except Exception as e:
            self.log(f"  ⚠️  Video editing failed for {video_path.name}: {e}")
            return None

    def process_raw_footage(self) -> list:
        """
        Scan brands/{slug}/raw_footage/ for new video files.
        For each: transcribe via FAL.ai Whisper → edit via moviepy → save polished reel.
        Requires: pip install moviepy ffmpeg-python
        Returns list of output reel paths.
        """
        raw_dir = self.brand_dir / "raw_footage"
        if not raw_dir.exists():
            self.log("No raw_footage/ directory found — skipping video pipeline")
            return []

        video_files = (
            list(raw_dir.glob("*.mp4"))
            + list(raw_dir.glob("*.mov"))
            + list(raw_dir.glob("*.m4v"))
        )
        if not video_files:
            self.log("raw_footage/ is empty — skipping video pipeline")
            return []

        try:
            import moviepy  # noqa: F401 — confirm installed before processing
        except ImportError:
            self.log(
                "⚠️  moviepy not installed — skipping video pipeline\n"
                "   Install with: pip install moviepy ffmpeg-python"
            )
            return []

        self.log(f"Found {len(video_files)} raw footage file(s) — starting video pipeline...")
        reel_dir = self.brand_dir / "outputs" / "pending_approval" / "Creative Director" / "reels"
        reel_dir.mkdir(parents=True, exist_ok=True)

        output_paths = []
        for vf in video_files:
            self.log(f"\nProcessing raw footage: {vf.name}")
            transcript = self._transcribe_video(vf)
            out = self._edit_video(vf, transcript, reel_dir)
            if out:
                output_paths.append(out)

        self.log(f"\n✅ Video pipeline complete — {len(output_paths)} reel(s) ready for approval")
        return output_paths

    # ── Main run ──────────────────────────────────────────────────────────────

    def run(self) -> None:
        self.log("=" * 60)
        self.log("CREATIVE DIRECTOR — Starting run")
        self.log("=" * 60)

        # Step 1 — Load data
        scripts = self.load_scripts()
        competitors = self.load_competitors()

        # Step 1.5 — Process any raw footage in brands/{slug}/raw_footage/
        reel_paths = self.process_raw_footage()

        # Step 2 — Run AutoResearch Loop
        loop_result = self.run_autoresearch_loop(scripts, competitors)
        variants = loop_result.get("variants", [])
        self.log(f"AutoResearch Loop complete — {len(variants)} variants generated.")

        # Step 3 — Brand safety checks + select winners per variant
        approved_variants = []
        for variant in variants:
            direction = variant.get("creative_direction", "")
            self.log(f"\nProcessing: {direction}")

            for option_key in ["safe_option", "viral_option"]:
                option = variant.get(option_key, {})
                concept = option.get("brand_safety_concept", option.get("image_prompt", ""))

                self.log(f"  Running brand safety check on {option_key}...")
                safety = self.run_brand_safety_check(concept)

                if safety.get("passed", True):
                    self.log(f"  ✅ {option_key} passed brand safety: {safety.get('verdict')}")
                    option["brand_safety"] = safety

                    # Generate narration if text available
                    narration_text = option.get("narration_text", "")
                    if narration_text:
                        audio_path = self.generate_narration(
                            narration_text,
                            f"{direction[:20]}_{option_key}"
                        )
                        if audio_path:
                            option["narration_audio_path"] = audio_path

                    # FAL.ai image generation
                    image_prompt = option.get("image_prompt", "")
                    if image_prompt and FAL_API_KEY:
                        # Detect text-heavy: Variant B (bold headline) uses text overlay → ideogram
                        is_text_heavy = "headline" in direction.lower() or "text" in direction.lower()
                        img_path = self.generate_image(
                            image_prompt,
                            f"{direction[:20]}_{option_key}",
                            text_heavy=is_text_heavy,
                        )
                        if img_path:
                            option["generated_image_path"] = img_path
                    elif image_prompt:
                        self.log(f"  ℹ️  FAL_API_KEY not set — image_prompt saved for manual execution")

                else:
                    self.log(f"  ❌ {option_key} FAILED brand safety: {safety.get('flags')}")
                    self.log(f"  STOPPING this direction. Flag: {safety.get('notes')}")
                    option["brand_safety"] = safety
                    option["blocked"] = True

            approved_variants.append(variant)

        # Step 4 — Select winning variant
        # Winner = first variant where both options passed safety
        winner = None
        winner_idx = 0
        for i, v in enumerate(approved_variants):
            safe_pass  = v.get("safe_option",  {}).get("brand_safety", {}).get("passed", False)
            viral_pass = v.get("viral_option", {}).get("brand_safety", {}).get("passed", False)
            if safe_pass and viral_pass:
                winner = v
                winner_idx = i
                break
        if not winner and approved_variants:
            winner = approved_variants[0]
            winner_idx = 0

        winning_direction = winner.get("creative_direction", f"Variant {winner_idx + 1}")
        self.log(f"\n✅ WINNER: {winning_direction} — both options passed brand safety.")

        # Step 5 — Build loop header
        loop_header = {
            "goal": loop_result.get("loop_goal", "Maximise Save + Share rate across Instagram and LinkedIn"),
            "metric": loop_result.get("loop_metric", "higher save+share rate than last 3 posts combined"),
            "variants_tested": len(variants),
            "winner": f"{winning_direction} — both safe + viral options cleared brand safety check",
        }

        # Step 6 — Assemble final output
        output = {
            "agent": "Creative Director",
            "brand": self.brand_slug,
            "timestamp": datetime.now().isoformat(),
            "scripts_processed": len(scripts),
            "loop_header": loop_header,
            "winning_variant": winner,
            "all_variants": approved_variants,
            "elevenlabs_key_used": bool(ELEVENLABS_API_KEY),
            "fal_key_used": bool(FAL_API_KEY),
            "production_notes": {
                "audio": "Narration MP3 files saved in pending_approval/Creative Director/audio/" if ELEVENLABS_API_KEY else "No audio — set ELEVENLABS_API_KEY",
                "images": (
                    "Images generated via FAL.ai and saved in pending_approval/Creative Director/images/"
                    if FAL_API_KEY
                    else "Image prompts saved — set FAL_API_KEY to auto-generate (fal-ai/flux/dev for photorealistic, fal-ai/ideogram/v2 for text-heavy)"
                ),
                "video": (
                    f"Raw footage pipeline: {len(reel_paths)} reel(s) processed via FAL.ai Whisper + moviepy → pending_approval/Creative Director/reels/"
                    if reel_paths
                    else "Drop .mp4/.mov files into brands/{slug}/raw_footage/ → agent auto-edits, captions, crops to 9:16 via FAL.ai Whisper + moviepy. Requires: pip install moviepy ffmpeg-python"
                ),
            }
        }

        # Step 7 — Save output file
        output_dir = self.brand_dir / "outputs" / "pending_approval" / "Creative Director"
        output_dir.mkdir(parents=True, exist_ok=True)
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{ts}_creatives.json"
        output_path = output_dir / filename

        loop_header_text = (
            f"LOOP: Creative Director — Creative Direction Briefs\n"
            f"GOAL: {loop_header['goal']}\n"
            f"METRIC: better = {loop_header['metric']}\n"
            f"VARIANTS TESTED: {loop_header['variants_tested']}\n"
            f"WINNER: {loop_header['winner']}\n"
            f"---\n"
        )
        output_path.write_text(loop_header_text + json.dumps(output, indent=2))
        self.log(f"✅ Output saved: {filename}")

        # Step 8 — Push to Notion
        self.log("Pushing to Notion approval pipeline...")
        self.ceo.save_agent_output(
            agent_name="Creative Director",
            output_type="Creative Direction Briefs",
            loop_header=loop_header,
            content=json.dumps(output, indent=2),
            filename=filename,
        )

        # Step 9 — Mark complete in session state
        self.ceo.mark_agent_complete("creative-director")

        self.log("=" * 60)
        self.log("CREATIVE DIRECTOR — Run complete")
        self.log(f"Variants generated : {len(variants)}")
        self.log(f"Winner             : {winning_direction}")
        self.log(f"Audio narrations   : {'✅ Generated' if ELEVENLABS_API_KEY else '⚠️  Skipped (no key)'}")
        self.log(f"FAL.ai images      : {'✅ Generated' if FAL_API_KEY else '⚠️  Prompts saved (set FAL_API_KEY to auto-generate)'}")
        self.log(f"Video pipeline     : {'✅ ' + str(len(reel_paths)) + ' reel(s) edited' if reel_paths else 'ℹ️  No raw footage found (drop .mp4/.mov into brands/{slug}/raw_footage/)'}")
        self.log(f"Notion card        : ✅ Pushed")
        self.log(f"Output file        : {filename}")
        self.log("=" * 60)
        cost_reporter.record(MODEL, self._total_input_tokens, self._total_output_tokens, fal_generations=self._fal_generations)


if __name__ == "__main__":
    director = CreativeDirector()
    director.run()
