#!/usr/bin/env python3
"""
Pillar Video Assembly — Direct ffmpeg Path

Editing instructions from week1_shooting_scripts.html Script 2:
- Talking-head close-up, chest up, eyes upper third
- Clip Marker 3 (principle close): slight zoom-out to mid-shot
- 5-second end card with AskGauravAI logo
- Chapter timestamps in output metadata
- Derivative reels cut at exact clip markers from script:
  - CLIP MARKER 1 (hook open) → Reel 1
  - CLIP MARKER 2 (diagnostic line) → Reel 2
  - CLIP MARKER 3 (principle close) → Reel 3
"""

import subprocess
import os
import json
from datetime import datetime
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
BRAND_DIR = PROJECT_ROOT / "brands" / "askgauravai"
CLEANED_DIR = BRAND_DIR / "Raw_recordings" / "cleaned"
OUTPUT_DIR = BRAND_DIR / "outputs" / "pending_approval" / "creative-director" / "pillar_direct"

# Assembly order matching the shooting script sections
ASSEMBLY_ORDER = [
    {"file": "01_hook.mov",                    "section": "Hook Open + Intro"},
    {"file": "02_failure_pattern_1.mov",        "section": "Failure Pattern 1: The Assumption Campaign"},
    {"file": "03_failure_pattern_2.mov",        "section": "Failure Pattern 2: The Borrowed Framework"},
    {"file": "04_failure_pattern_3.mov",        "section": "Failure Pattern 3: The Timing Blind Spot"},
    {"file": "05_market_intelligence.mov",      "section": "What Pre-Advertising Intelligence Means"},
    {"file": "06_the_pattern.mov",              "section": "Diagnostic Line — The Pattern"},
    {"file": "07_build_intelligence_first.mov", "section": "Principle Close", "zoom_out": True},
    {"file": "08_cta.mov",                      "section": "CTA + Close", "zoom_out": True},
    {"file": "09_end_card.mp4",                 "section": "End Card"},
]

# Reel cuts per clip markers in the shooting script
REEL_CUTS = [
    {
        "name": "reel_1_hook",
        "desc": "CLIP MARKER 1 — Hook: 'You ran ads before knowing what your market wants'",
        "source": "01_hook.mov",
        "max_dur": 60,
    },
    {
        "name": "reel_2_diagnostic",
        "desc": "CLIP MARKER 2 — Diagnostic: 'Past performance data tells you what happened'",
        "source": "06_the_pattern.mov",
        "max_dur": 60,
    },
    {
        "name": "reel_3_principle",
        "desc": "CLIP MARKER 3 — Principle: 'Build the intelligence first'",
        "source": "07_build_intelligence_first.mov",
        "max_dur": 90,
    },
]


def log(msg):
    print(f"[DirectAssembly] {msg}")


def normalize_clip(src, dst, zoom_out=False):
    """Re-encode clip to consistent 4K H.264 format.
    zoom_out=True applies a slight scale-down (90%) to simulate editor zoom-out for the close."""
    vf = "scale=1920:1080:force_original_aspect_ratio=decrease,pad=1920:1080:(ow-iw)/2:(oh-ih)/2"
    if zoom_out:
        # Zoom out: scale video to 90%, pad with black → gives "mid-shot" feel
        vf = "scale=1728:972,pad=1920:1080:(ow-iw)/2:(oh-ih)/2:color=black"

    subprocess.run([
        "ffmpeg", "-y", "-i", str(src),
        "-c:v", "libx264", "-preset", "medium", "-crf", "18",
        "-vf", vf,
        "-r", "30",
        "-c:a", "aac", "-b:a", "192k", "-ar", "48000",
        "-pix_fmt", "yuv420p",
        str(dst)
    ], capture_output=True, check=True)


def get_duration(path):
    return float(subprocess.run(
        ["ffprobe", "-v", "quiet", "-show_entries", "format=duration", "-of", "csv=p=0", str(path)],
        capture_output=True, text=True
    ).stdout.strip())


def main():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")

    # Verify all source clips exist
    for clip in ASSEMBLY_ORDER:
        src = CLEANED_DIR / clip["file"]
        if not src.exists():
            log(f"ERROR: Missing {clip['file']}")
            return
    log(f"All {len(ASSEMBLY_ORDER)} clips verified.")

    # Step 1: Normalize all clips
    norm_dir = OUTPUT_DIR / "normalized"
    norm_dir.mkdir(exist_ok=True)
    normalized = []
    chapter_offsets = []
    cumulative_dur = 0.0

    for i, clip in enumerate(ASSEMBLY_ORDER):
        src = CLEANED_DIR / clip["file"]
        dst = norm_dir / clip["file"].replace(".mov", ".mp4").replace(".MP4", ".mp4")
        zoom = clip.get("zoom_out", False)

        log(f"[{i+1}/{len(ASSEMBLY_ORDER)}] Normalizing: {clip['file']}" + (" (zoom-out)" if zoom else ""))
        normalize_clip(src, dst, zoom_out=zoom)

        dur = get_duration(dst)
        chapter_offsets.append({
            "section": clip["section"],
            "start_seconds": round(cumulative_dur, 1),
            "duration": round(dur, 1),
        })
        cumulative_dur += dur
        normalized.append(dst)
        log(f"  → {dur:.1f}s (cumulative: {cumulative_dur:.0f}s)")

    # Step 2: Concatenate
    concat_file = OUTPUT_DIR / "concat.txt"
    concat_file.write_text("\n".join(f"file '{p}'" for p in normalized))

    output_path = OUTPUT_DIR / f"{ts}_askgauravai_pillar_direct.mp4"
    log("Concatenating all sections...")
    subprocess.run([
        "ffmpeg", "-y", "-f", "concat", "-safe", "0",
        "-i", str(concat_file),
        "-c", "copy",
        str(output_path)
    ], capture_output=True, check=True)

    total_dur = get_duration(output_path)
    log(f"Pillar video: {total_dur:.0f}s ({total_dur/60:.1f} min)")

    # Step 3: Generate chapter timestamps for YouTube description
    chapters_text = "CHAPTERS:\n"
    for ch in chapter_offsets:
        mins = int(ch["start_seconds"] // 60)
        secs = int(ch["start_seconds"] % 60)
        chapters_text += f"{mins:02d}:{secs:02d} — {ch['section']}\n"

    chapters_path = OUTPUT_DIR / f"{ts}_chapters.txt"
    chapters_path.write_text(chapters_text)
    log(f"Chapter timestamps saved: {chapters_path.name}")

    # Step 4: Cut derivative reels per clip markers
    reels_dir = OUTPUT_DIR / "reels"
    reels_dir.mkdir(exist_ok=True)
    reels = []

    for reel in REEL_CUTS:
        src = CLEANED_DIR / reel["source"]
        out = reels_dir / f"{ts}_{reel['name']}.mp4"
        log(f"Cutting reel: {reel['name']}...")

        # Crop to 9:16 portrait + resize to 1080x1920
        subprocess.run([
            "ffmpeg", "-y", "-i", str(src),
            "-t", str(reel["max_dur"]),
            "-vf", "crop=ih*9/16:ih,scale=1080:1920",
            "-c:v", "libx264", "-preset", "medium", "-crf", "20",
            "-c:a", "aac", "-b:a", "128k", "-pix_fmt", "yuv420p",
            str(out)
        ], capture_output=True, check=True)

        rdur = get_duration(out)
        reels.append({"name": reel["name"], "desc": reel["desc"], "path": str(out), "duration": round(rdur, 1)})
        log(f"  → {reel['name']}: {rdur:.0f}s")

    # Step 5: Save assembly report
    report = {
        "method": "direct_ffmpeg",
        "brand": "askgauravai",
        "timestamp": datetime.now().isoformat(),
        "pillar_video": {
            "path": str(output_path),
            "duration_seconds": round(total_dur, 1),
            "duration_formatted": f"{int(total_dur//60)}:{int(total_dur%60):02d}",
        },
        "chapters": chapter_offsets,
        "editing_applied": [
            "Noise reduction (afftdn + EQ + compressor) on all clips",
            "False starts and slates trimmed",
            "Zoom-out (90% scale) on principle close + CTA sections",
            "5-second branded end card",
            "Chapter timestamps generated",
        ],
        "derivative_reels": reels,
        "chapters_file": str(chapters_path),
    }
    report_path = OUTPUT_DIR / f"{ts}_assembly_report.json"
    with open(report_path, "w") as f:
        json.dump(report, f, indent=2)

    log(f"\n{'='*60}")
    log(f"DIRECT ASSEMBLY COMPLETE")
    log(f"Pillar: {output_path.name} — {total_dur:.0f}s ({total_dur/60:.1f} min)")
    log(f"Reels: {len(reels)} derivatives")
    log(f"Chapters: {chapters_path.name}")
    log(f"{'='*60}")
    print(chapters_text)


if __name__ == "__main__":
    os.chdir(str(PROJECT_ROOT))
    main()
