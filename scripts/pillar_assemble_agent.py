#!/usr/bin/env python3
"""
Pillar Video Assembly — Creative Director Agent Path

Uses FAL.ai for B-roll generation at section transitions.
Follows editing instructions from week1_shooting_scripts.html Script 2.

Editing applied:
- Zoom-out on Clip Marker 3 (principle close)
- FAL.ai generated B-roll inserts between sections
- Branded end card
- Chapter timestamps
- Derivative reels cut at clip markers
"""

import os
import sys
import json
import subprocess
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
load_dotenv(override=True)

# Fix Python 3.14 SSL certificate issue
import ssl
import certifi
os.environ.setdefault("SSL_CERT_FILE", certifi.where())
ssl._create_default_https_context = lambda purpose=None, cafile=None, capath=None: ssl.create_default_context(purpose=purpose or ssl.Purpose.SERVER_AUTH, cafile=cafile or certifi.where(), capath=capath)

FAL_API_KEY = os.getenv("FAL_API_KEY", "").strip()
BRAND_SLUG = "askgauravai"
PROJECT_ROOT = Path(__file__).resolve().parent.parent
BRAND_DIR = PROJECT_ROOT / "brands" / BRAND_SLUG
CLEANED_DIR = BRAND_DIR / "Raw_recordings" / "cleaned"
OUTPUT_DIR = BRAND_DIR / "outputs" / "pending_approval" / "creative-director" / "pillar"

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

# B-roll inserts between specific sections (per script: "screen recordings of the system")
BROLL_INSERTS = [
    {
        "after_section": 2,  # After Failure Pattern 1
        "label": "transition_data_flow",
        "prompt": (
            "Cinematic close-up of a modern analytics dashboard on a large monitor, "
            "dark UI with teal (#0F4C5C) accent lines, data flowing across charts, "
            "shallow depth of field, warm ambient desk lamp in background, "
            "professional workspace, editorial photography, 16:9, photorealistic"
        ),
        "duration": 2.5,
    },
    {
        "after_section": 4,  # After Failure Pattern 3, before Market Intelligence
        "label": "transition_market_signals",
        "prompt": (
            "Abstract visualization of market data signals: comment bubbles, review stars, "
            "search queries floating in space against a dark background, "
            "teal (#0F4C5C) and coral (#E07A5F) color palette, "
            "clean modern design, data-as-art aesthetic, 16:9"
        ),
        "duration": 2.5,
    },
    {
        "after_section": 6,  # After Diagnostic Line, before Principle Close
        "label": "transition_intelligence_report",
        "prompt": (
            "Hands holding a clean printed PDF report on a white desk, "
            "report shows data charts and market analysis, warm natural window light, "
            "shallow depth of field on the document, founder workspace aesthetic, "
            "professional and minimal, editorial photography, 16:9"
        ),
        "duration": 2.5,
    },
]

REEL_CUTS = [
    {"name": "reel_1_hook", "source": "01_hook.mov", "max_dur": 60,
     "desc": "CLIP MARKER 1 — Hook open"},
    {"name": "reel_2_diagnostic", "source": "06_the_pattern.mov", "max_dur": 60,
     "desc": "CLIP MARKER 2 — Diagnostic line"},
    {"name": "reel_3_principle", "source": "07_build_intelligence_first.mov", "max_dur": 90,
     "desc": "CLIP MARKER 3 — Principle close"},
]


def log(msg):
    print(f"[CreativeDirector:PillarAssembly] {msg}")


def get_duration(path):
    return float(subprocess.run(
        ["ffprobe", "-v", "quiet", "-show_entries", "format=duration", "-of", "csv=p=0", str(path)],
        capture_output=True, text=True
    ).stdout.strip())


def generate_broll():
    """Generate B-roll images via FAL.ai and convert to short video clips."""
    if not FAL_API_KEY:
        log("FAL_API_KEY not set — skipping B-roll generation")
        return {}

    try:
        import fal_client
        os.environ["FAL_KEY"] = FAL_API_KEY
    except ImportError:
        log("fal_client not installed — pip install fal-client")
        return {}

    broll_dir = OUTPUT_DIR / "broll"
    broll_dir.mkdir(parents=True, exist_ok=True)
    results = {}

    for item in BROLL_INSERTS:
        label = item["label"]
        try:
            log(f"  Generating B-roll: {label}...")
            result = fal_client.subscribe(
                "fal-ai/flux/dev",
                arguments={"prompt": item["prompt"], "image_size": "landscape_16_9"},
            )
            images = result.get("images", [])
            if not images:
                continue

            url = images[0].get("url", "")
            if not url:
                continue

            import urllib.request
            img_path = broll_dir / f"{label}.png"
            ctx = ssl.create_default_context(cafile=certifi.where())
            with urllib.request.urlopen(url, context=ctx) as resp:
                img_path.write_bytes(resp.read())

            # Convert to video with Ken Burns zoom
            vid_path = broll_dir / f"{label}.mp4"
            dur = item["duration"]
            frames = int(dur * 30)
            subprocess.run([
                "ffmpeg", "-y", "-loop", "1", "-i", str(img_path),
                "-vf", f"zoompan=z='min(zoom+0.0008,1.15)':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':d={frames}:s=1920x1080:fps=30",
                "-t", str(dur),
                "-c:v", "libx264", "-pix_fmt", "yuv420p", "-an",
                str(vid_path)
            ], capture_output=True, check=True)

            results[item["after_section"]] = vid_path
            log(f"  → {label}: {dur}s transition clip")

        except Exception as e:
            log(f"  B-roll failed for {label}: {e}")

    return results


def normalize_clip(src, dst, zoom_out=False):
    vf = "scale=1920:1080:force_original_aspect_ratio=decrease,pad=1920:1080:(ow-iw)/2:(oh-ih)/2"
    if zoom_out:
        vf = "scale=1728:972,pad=1920:1080:(ow-iw)/2:(oh-ih)/2:color=black"

    subprocess.run([
        "ffmpeg", "-y", "-i", str(src),
        "-c:v", "libx264", "-preset", "medium", "-crf", "18",
        "-vf", vf, "-r", "30",
        "-c:a", "aac", "-b:a", "192k", "-ar", "48000",
        "-pix_fmt", "yuv420p",
        str(dst)
    ], capture_output=True, check=True)


def main():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")

    # Verify clips
    for clip in ASSEMBLY_ORDER:
        if not (CLEANED_DIR / clip["file"]).exists():
            log(f"ERROR: Missing {clip['file']}")
            return

    # Step 1: Generate B-roll via FAL.ai
    log("\n--- Step 1: FAL.ai B-roll ---")
    broll_clips = generate_broll()
    log(f"Generated {len(broll_clips)} B-roll transitions")

    # Step 2: Normalize all clips
    log("\n--- Step 2: Normalize clips ---")
    norm_dir = OUTPUT_DIR / "normalized"
    norm_dir.mkdir(exist_ok=True)

    ordered_clips = []
    chapter_offsets = []
    cumulative = 0.0

    for i, clip in enumerate(ASSEMBLY_ORDER):
        src = CLEANED_DIR / clip["file"]
        dst = norm_dir / clip["file"].replace(".mov", ".mp4")
        zoom = clip.get("zoom_out", False)

        log(f"[{i+1}/{len(ASSEMBLY_ORDER)}] {clip['file']}" + (" (zoom-out)" if zoom else ""))
        normalize_clip(src, dst, zoom_out=zoom)

        dur = get_duration(dst)
        chapter_offsets.append({"section": clip["section"], "start_seconds": round(cumulative, 1)})
        ordered_clips.append(dst)
        cumulative += dur

        # Insert B-roll transition after this section if available
        if i in broll_clips:
            broll_path = broll_clips[i]
            ordered_clips.append(broll_path)
            bdur = get_duration(broll_path)
            cumulative += bdur
            log(f"  + B-roll transition: {bdur:.1f}s")

    # Step 3: Concatenate
    log("\n--- Step 3: Concatenate ---")
    concat_file = OUTPUT_DIR / "concat.txt"
    concat_file.write_text("\n".join(f"file '{p}'" for p in ordered_clips))

    output_path = OUTPUT_DIR / f"{ts}_askgauravai_pillar_agent.mp4"
    subprocess.run([
        "ffmpeg", "-y", "-f", "concat", "-safe", "0",
        "-i", str(concat_file), "-c", "copy", str(output_path)
    ], capture_output=True, check=True)

    total_dur = get_duration(output_path)

    # Step 4: Chapter timestamps
    chapters_text = "CHAPTERS:\n"
    for ch in chapter_offsets:
        m, s = int(ch["start_seconds"] // 60), int(ch["start_seconds"] % 60)
        chapters_text += f"{m:02d}:{s:02d} — {ch['section']}\n"

    chapters_path = OUTPUT_DIR / f"{ts}_chapters.txt"
    chapters_path.write_text(chapters_text)

    # Step 5: Derivative reels
    log("\n--- Step 4: Derivative Reels ---")
    reels_dir = OUTPUT_DIR / "reels"
    reels_dir.mkdir(exist_ok=True)
    reels = []

    for reel in REEL_CUTS:
        src = CLEANED_DIR / reel["source"]
        out = reels_dir / f"{ts}_{reel['name']}.mp4"
        subprocess.run([
            "ffmpeg", "-y", "-i", str(src),
            "-t", str(reel["max_dur"]),
            "-vf", "crop=ih*9/16:ih,scale=1080:1920",
            "-c:v", "libx264", "-preset", "medium", "-crf", "20",
            "-c:a", "aac", "-b:a", "128k", "-pix_fmt", "yuv420p",
            str(out)
        ], capture_output=True, check=True)
        rdur = get_duration(out)
        reels.append({"name": reel["name"], "desc": reel["desc"], "duration": round(rdur, 1)})
        log(f"  {reel['name']}: {rdur:.0f}s")

    # Step 6: Report
    report = {
        "method": "agent_fal_ai",
        "brand": BRAND_SLUG,
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
            "FAL.ai generated B-roll transitions between sections",
            "Ken Burns zoom effect on B-roll inserts",
            "5-second branded end card",
            "Chapter timestamps generated",
        ],
        "broll_generated": len(broll_clips),
        "derivative_reels": reels,
        "fal_used": bool(FAL_API_KEY),
    }
    report_path = OUTPUT_DIR / f"{ts}_assembly_report.json"
    with open(report_path, "w") as f:
        json.dump(report, f, indent=2)

    log(f"\n{'='*60}")
    log(f"AGENT ASSEMBLY COMPLETE")
    log(f"Pillar: {output_path.name} — {total_dur:.0f}s ({total_dur/60:.1f} min)")
    log(f"B-roll: {len(broll_clips)} FAL.ai transitions")
    log(f"Reels: {len(reels)} derivatives")
    log(f"{'='*60}")
    print(chapters_text)


if __name__ == "__main__":
    os.chdir(str(PROJECT_ROOT))
    main()
