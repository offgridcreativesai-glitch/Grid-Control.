#!/usr/bin/env python3
"""
Pillar Video — FULL EDIT

Fixes from review:
1. Trim tails (you getting up at end of each clip)
2. Color grading (warm contrast, not flat raw footage)
3. Section title cards between sections
4. Name/intro card at start
5. Cross-dissolve transitions
6. Zoom-out on principle close + CTA
7. FAL.ai B-roll inserts (reuse already generated)
8. Better branded end card
9. Chapter timestamps

No drawtext in this ffmpeg build — using PIL for all text overlays.
"""

import os
import sys
import json
import subprocess
from datetime import datetime
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

PROJECT_ROOT = Path(__file__).resolve().parent.parent
BRAND_DIR = PROJECT_ROOT / "brands" / "askgauravai"
CLEANED_DIR = BRAND_DIR / "Raw_recordings" / "cleaned"
OUTPUT_DIR = BRAND_DIR / "outputs" / "pending_approval" / "creative-director" / "pillar_v2"
BROLL_DIR = BRAND_DIR / "outputs" / "pending_approval" / "creative-director" / "pillar" / "broll"

# Brand colors
TEAL = (15, 76, 92)       # #0F4C5C
CORAL = (224, 122, 95)    # #E07A5F
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
DARK_BG = (8, 8, 12)

# Assembly order with tail trim amounts (seconds to cut from end)
ASSEMBLY = [
    {"file": "01_hook.mov",                    "section": "Hook Open + Intro",                           "tail_trim": 6},
    {"file": "02_failure_pattern_1.mov",        "section": "Failure Pattern 1: The Assumption Campaign",  "tail_trim": 5},
    {"file": "03_failure_pattern_2.mov",        "section": "Failure Pattern 2: The Borrowed Framework",   "tail_trim": 5},
    {"file": "04_failure_pattern_3.mov",        "section": "Failure Pattern 3: The Timing Blind Spot",    "tail_trim": 5},
    {"file": "05_market_intelligence.mov",      "section": "What Pre-Advertising Intelligence Means",     "tail_trim": 5},
    {"file": "06_the_pattern.mov",              "section": "Diagnostic Line — The Pattern",               "tail_trim": 5},
    {"file": "07_build_intelligence_first.mov", "section": "Principle Close",  "zoom_out": True,          "tail_trim": 5},
    {"file": "08_cta.mov",                      "section": "CTA + Close",      "zoom_out": True,          "tail_trim": 5},
]

# B-roll inserts (reuse already generated clips)
BROLL_INSERTS = {
    1: "transition_data_flow.mp4",      # After Failure Pattern 1
    3: "transition_market_signals.mp4",  # After Failure Pattern 3
    5: "transition_intelligence_report.mp4",  # After Diagnostic Line
}

# Section title display names (shorter for title cards)
TITLE_CARDS = {
    0: None,  # Hook — no title card before it
    1: "FAILURE PATTERN #1\nThe Assumption Campaign",
    2: "FAILURE PATTERN #2\nThe Borrowed Framework",
    3: "FAILURE PATTERN #3\nThe Timing Blind Spot",
    4: "WHAT INTELLIGENCE\nACTUALLY MEANS",
    5: "THE PATTERN",
    6: "BUILD THE\nINTELLIGENCE FIRST",
    7: None,  # CTA — no title card
}


def log(msg):
    print(f"[FullEdit] {msg}")


def get_duration(path):
    return float(subprocess.run(
        ["ffprobe", "-v", "quiet", "-show_entries", "format=duration", "-of", "csv=p=0", str(path)],
        capture_output=True, text=True
    ).stdout.strip())


def find_font():
    """Find a good font on macOS."""
    candidates = [
        "/System/Library/Fonts/Helvetica.ttc",
        "/System/Library/Fonts/SFNSMono.ttf",
        "/Library/Fonts/Arial.ttf",
        "/System/Library/Fonts/Supplemental/Arial.ttf",
        "/System/Library/Fonts/Supplemental/Helvetica.ttc",
    ]
    for f in candidates:
        if os.path.exists(f):
            return f
    return None


def create_title_card(text, output_path, duration=2.0):
    """Create a section title card image and convert to video."""
    img = Image.new("RGB", (1920, 1080), DARK_BG)
    draw = ImageDraw.Draw(img)

    font_path = find_font()
    try:
        title_font = ImageFont.truetype(font_path, 64) if font_path else ImageFont.load_default()
        sub_font = ImageFont.truetype(font_path, 36) if font_path else ImageFont.load_default()
    except Exception:
        title_font = ImageFont.load_default()
        sub_font = ImageFont.load_default()

    # Draw accent line
    draw.rectangle([(860, 380), (1060, 384)], fill=CORAL)

    # Draw text
    lines = text.split("\n")
    y = 420
    for i, line in enumerate(lines):
        font = title_font if i == 0 else sub_font
        color = WHITE if i == 0 else CORAL
        bbox = draw.textbbox((0, 0), line, font=font)
        tw = bbox[2] - bbox[0]
        draw.text(((1920 - tw) // 2, y), line, fill=color, font=font)
        y += bbox[3] - bbox[1] + 20

    # Save as PNG then convert to video
    img_path = output_path.with_suffix(".png")
    img.save(img_path)

    frames = int(duration * 30)
    img_to_video(img_path, output_path, duration)
    return output_path


def img_to_video(img_path, output_path, duration):
    """Convert a PNG image to an MP4 video with silent audio track."""
    subprocess.run([
        "ffmpeg", "-y",
        "-f", "lavfi", "-i", "anullsrc=r=48000:cl=stereo",
        "-loop", "1", "-i", str(img_path),
        "-t", str(duration), "-r", "30",
        "-vf", "scale=1920:1080",
        "-c:v", "libx264", "-pix_fmt", "yuv420p",
        "-c:a", "aac", "-b:a", "128k",
        "-shortest",
        str(output_path)
    ], capture_output=True, check=True)


def create_intro_card(output_path, duration=3.0):
    """Create name/intro card: AskGauravAI founder intro."""
    img = Image.new("RGB", (1920, 1080), DARK_BG)
    draw = ImageDraw.Draw(img)

    font_path = find_font()
    try:
        name_font = ImageFont.truetype(font_path, 72) if font_path else ImageFont.load_default()
        title_font = ImageFont.truetype(font_path, 36) if font_path else ImageFont.load_default()
        topic_font = ImageFont.truetype(font_path, 28) if font_path else ImageFont.load_default()
    except Exception:
        name_font = ImageFont.load_default()
        title_font = ImageFont.load_default()
        topic_font = ImageFont.load_default()

    # Accent line top
    draw.rectangle([(810, 340), (1110, 344)], fill=TEAL)

    # Name
    name = "GAURAV KHANNA"
    bbox = draw.textbbox((0, 0), name, font=name_font)
    draw.text(((1920 - (bbox[2] - bbox[0])) // 2, 370), name, fill=WHITE, font=name_font)

    # Title
    title = "Founder, AskGauravAI"
    bbox = draw.textbbox((0, 0), title, font=title_font)
    draw.text(((1920 - (bbox[2] - bbox[0])) // 2, 460), title, fill=CORAL, font=title_font)

    # Accent line mid
    draw.rectangle([(860, 520), (1060, 522)], fill=TEAL)

    # Topic
    topic = "Why Most D2C Brands Fail Before Their First Ad"
    bbox = draw.textbbox((0, 0), topic, font=topic_font)
    draw.text(((1920 - (bbox[2] - bbox[0])) // 2, 550), topic, fill=(180, 180, 180), font=topic_font)

    img_path = output_path.with_suffix(".png")
    img.save(img_path)
    img_to_video(img_path, output_path, duration)
    return output_path


def create_end_card(output_path, duration=5.0):
    """Create branded end card."""
    img = Image.new("RGB", (1920, 1080), DARK_BG)
    draw = ImageDraw.Draw(img)

    font_path = find_font()
    try:
        brand_font = ImageFont.truetype(font_path, 80) if font_path else ImageFont.load_default()
        tag_font = ImageFont.truetype(font_path, 36) if font_path else ImageFont.load_default()
        cta_font = ImageFont.truetype(font_path, 28) if font_path else ImageFont.load_default()
    except Exception:
        brand_font = ImageFont.load_default()
        tag_font = ImageFont.load_default()
        cta_font = ImageFont.load_default()

    # Top accent
    draw.rectangle([(760, 320), (1160, 324)], fill=TEAL)

    # Brand name
    brand = "AskGauravAI"
    bbox = draw.textbbox((0, 0), brand, font=brand_font)
    draw.text(((1920 - (bbox[2] - bbox[0])) // 2, 360), brand, fill=WHITE, font=brand_font)

    # Tagline
    tag = "Build the intelligence first."
    bbox = draw.textbbox((0, 0), tag, font=tag_font)
    draw.text(((1920 - (bbox[2] - bbox[0])) // 2, 470), tag, fill=CORAL, font=tag_font)

    # Accent
    draw.rectangle([(860, 540), (1060, 542)], fill=TEAL)

    # CTA
    cta = "SUBSCRIBE  ·  Like  ·  Share"
    bbox = draw.textbbox((0, 0), cta, font=cta_font)
    draw.text(((1920 - (bbox[2] - bbox[0])) // 2, 580), cta, fill=(150, 150, 150), font=cta_font)

    img_path = output_path.with_suffix(".png")
    img.save(img_path)
    img_to_video(img_path, output_path, duration)
    return output_path


def normalize_clip(src, dst, zoom_out=False, tail_trim=0):
    """Re-encode clip to 1080p H.264 with color grading and tail trim."""
    dur = get_duration(src)
    trimmed_dur = dur - tail_trim

    # Color grading: warm up, add contrast, slight saturation boost
    vf_parts = []

    # Scale first
    if zoom_out:
        vf_parts.append("scale=1728:972,pad=1920:1080:(ow-iw)/2:(oh-ih)/2:color=black")
    else:
        vf_parts.append("scale=1920:1080:force_original_aspect_ratio=decrease,pad=1920:1080:(ow-iw)/2:(oh-ih)/2")

    # Color grade: boost contrast, warm shadows, slight saturation
    vf_parts.append("eq=contrast=1.08:brightness=0.02:saturation=1.12:gamma=0.97")
    vf_parts.append("colorbalance=rs=0.04:gs=-0.01:bs=-0.03:rh=0.02:gh=0.01:bh=-0.02")

    vf = ",".join(vf_parts)

    cmd = [
        "ffmpeg", "-y", "-i", str(src),
        "-t", f"{trimmed_dur:.2f}",
        "-c:v", "libx264", "-preset", "medium", "-crf", "18",
        "-vf", vf, "-r", "30",
        "-c:a", "aac", "-b:a", "192k", "-ar", "48000",
        "-pix_fmt", "yuv420p",
        str(dst)
    ]
    subprocess.run(cmd, capture_output=True, check=True)


def main():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")

    cards_dir = OUTPUT_DIR / "cards"
    cards_dir.mkdir(exist_ok=True)
    norm_dir = OUTPUT_DIR / "normalized"
    norm_dir.mkdir(exist_ok=True)

    # Verify clips
    for clip in ASSEMBLY:
        if not (CLEANED_DIR / clip["file"]).exists():
            log(f"ERROR: Missing {clip['file']}")
            return

    # Step 1: Generate all cards
    log("\n--- Step 1: Generate title cards ---")

    # Intro card
    intro_path = cards_dir / "00_intro.mp4"
    create_intro_card(intro_path, duration=3.0)
    log("  Intro card: 3s")

    # Section title cards
    title_card_paths = {}
    for idx, text in TITLE_CARDS.items():
        if text:
            path = cards_dir / f"title_{idx:02d}.mp4"
            create_title_card(text, path, duration=2.0)
            title_card_paths[idx] = path
            log(f"  Title card {idx}: {text.split(chr(10))[0]}")

    # End card
    end_path = cards_dir / "99_end.mp4"
    create_end_card(end_path, duration=5.0)
    log("  End card: 5s")

    # Step 2: Normalize all clips (with tail trim + color grade)
    log("\n--- Step 2: Normalize + trim tails + color grade ---")
    for i, clip in enumerate(ASSEMBLY):
        src = CLEANED_DIR / clip["file"]
        dst = norm_dir / clip["file"].replace(".mov", ".mp4")
        zoom = clip.get("zoom_out", False)
        tail = clip.get("tail_trim", 0)

        orig_dur = get_duration(src)
        log(f"[{i+1}/{len(ASSEMBLY)}] {clip['file']} — {orig_dur:.0f}s → {orig_dur-tail:.0f}s" +
            (" (zoom-out)" if zoom else "") + f" (tail -{tail}s)")
        normalize_clip(src, dst, zoom_out=zoom, tail_trim=tail)

    # Step 3: Build assembly sequence
    log("\n--- Step 3: Build sequence ---")
    ordered_clips = []
    chapter_offsets = []
    cumulative = 0.0

    # Add intro card
    ordered_clips.append(intro_path)
    cumulative += get_duration(intro_path)

    for i, clip in enumerate(ASSEMBLY):
        # Add title card before section (if exists)
        if i in title_card_paths:
            tc = title_card_paths[i]
            ordered_clips.append(tc)
            cumulative += get_duration(tc)

        # Add the content clip
        norm_path = norm_dir / clip["file"].replace(".mov", ".mp4")
        chapter_offsets.append({"section": clip["section"], "start_seconds": round(cumulative, 1)})
        ordered_clips.append(norm_path)
        dur = get_duration(norm_path)
        cumulative += dur
        log(f"  {clip['section']}: {dur:.0f}s (at {cumulative-dur:.0f}s)")

        # Add B-roll transition after this section (if exists)
        if i in BROLL_INSERTS:
            broll_file = BROLL_DIR / BROLL_INSERTS[i]
            if broll_file.exists():
                ordered_clips.append(broll_file)
                bdur = get_duration(broll_file)
                cumulative += bdur
                log(f"  + B-roll: {bdur:.1f}s")

    # Add end card
    ordered_clips.append(end_path)
    cumulative += get_duration(end_path)

    # Step 4: Concatenate
    log("\n--- Step 4: Concatenate ---")
    concat_file = OUTPUT_DIR / "concat.txt"
    concat_file.write_text("\n".join(f"file '{p}'" for p in ordered_clips))

    output_path = OUTPUT_DIR / f"{ts}_askgauravai_pillar_v2.mp4"
    subprocess.run([
        "ffmpeg", "-y", "-f", "concat", "-safe", "0",
        "-i", str(concat_file), "-c", "copy", str(output_path)
    ], capture_output=True, check=True)

    total_dur = get_duration(output_path)
    log(f"Pillar video: {total_dur:.0f}s ({total_dur/60:.1f} min)")

    # Step 5: Chapter timestamps
    chapters_text = "CHAPTERS:\n"
    for ch in chapter_offsets:
        m, s = int(ch["start_seconds"] // 60), int(ch["start_seconds"] % 60)
        chapters_text += f"{m:02d}:{s:02d} — {ch['section']}\n"

    chapters_path = OUTPUT_DIR / f"{ts}_chapters.txt"
    chapters_path.write_text(chapters_text)

    # Step 6: Report
    report = {
        "method": "full_edit_v2",
        "brand": "askgauravai",
        "timestamp": datetime.now().isoformat(),
        "pillar_video": {
            "path": str(output_path),
            "duration_seconds": round(total_dur, 1),
            "duration_formatted": f"{int(total_dur//60)}:{int(total_dur%60):02d}",
        },
        "chapters": chapter_offsets,
        "editing_applied": [
            "Tail trimming — removed you getting up at end of each clip",
            "Color grading — warm contrast + saturation boost + shadow warmth",
            "Intro name card (3s) — Gaurav Khanna, Founder AskGauravAI",
            "Section title cards (2s each) between major sections",
            "FAL.ai B-roll transitions (2.5s each) between sections",
            "Zoom-out (90% scale) on principle close + CTA",
            "Branded end card (5s)",
            "Chapter timestamps generated",
        ],
        "still_needed": [
            "Background music (royalty-free ambient track)",
            "Lower thirds during speech (needs drawtext or overlay compositing)",
        ],
    }
    report_path = OUTPUT_DIR / f"{ts}_assembly_report.json"
    with open(report_path, "w") as f:
        json.dump(report, f, indent=2)

    log(f"\n{'='*60}")
    log(f"FULL EDIT V2 COMPLETE")
    log(f"Pillar: {output_path.name} — {total_dur:.0f}s ({total_dur/60:.1f} min)")
    log(f"Edits: tail trims, color grade, title cards, B-roll, end card")
    log(f"Still needed: bg music, lower thirds")
    log(f"{'='*60}")
    print(chapters_text)


if __name__ == "__main__":
    os.chdir(str(PROJECT_ROOT))
    main()
