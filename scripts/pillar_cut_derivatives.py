#!/usr/bin/env python3
"""
Cut derivative Reels and Shorts FROM the final assembled YouTube pillar video.

GaryVee pillar model: derivatives come from the published long-form, not raw clips.
Uses chapter timestamps from the assembly report to find clip marker positions.

Produces:
- 3 IG Reels (9:16, 1080x1920, <60s)
- 2 YouTube Shorts (9:16, 1080x1920, <60s)
- 1 LinkedIn clip (16:9, 1920x1080, <90s)

Run this AFTER pillar_assemble_direct.py or pillar_assemble_agent.py completes.
"""

import subprocess
import os
import json
import sys
from datetime import datetime
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
BRAND_DIR = PROJECT_ROOT / "brands" / "askgauravai"


def log(msg):
    print(f"[DerivativeCutter] {msg}")


def get_duration(path):
    return float(subprocess.run(
        ["ffprobe", "-v", "quiet", "-show_entries", "format=duration", "-of", "csv=p=0", str(path)],
        capture_output=True, text=True
    ).stdout.strip())


def find_pillar_video():
    """Find the most recent assembled pillar video from either path."""
    candidates = []
    for subdir in ["pillar_direct", "pillar"]:
        d = BRAND_DIR / "outputs" / "pending_approval" / "creative-director" / subdir
        if d.exists():
            for f in d.glob("*_pillar_*.mp4"):
                candidates.append(f)

    if not candidates:
        return None, None

    # Pick most recent
    candidates.sort(key=lambda f: f.stat().st_mtime, reverse=True)
    pillar = candidates[0]

    # Find matching assembly report
    report_path = pillar.parent / pillar.name.replace("_pillar_direct.mp4", "_assembly_report.json").replace("_pillar_agent.mp4", "_assembly_report.json")
    if not report_path.exists():
        # Try any report in the directory
        reports = list(pillar.parent.glob("*_assembly_report.json"))
        report_path = reports[0] if reports else None

    return pillar, report_path


def cut_derivative(pillar_path, output_path, start, duration, portrait=True):
    """Cut a derivative from the pillar video.
    portrait=True → 9:16 (Reels/Shorts), False → 16:9 (LinkedIn)
    """
    if portrait:
        vf = "crop=ih*9/16:ih,scale=1080:1920"
    else:
        vf = "scale=1920:1080"

    subprocess.run([
        "ffmpeg", "-y",
        "-ss", f"{start:.1f}",
        "-i", str(pillar_path),
        "-t", f"{duration:.1f}",
        "-vf", vf,
        "-c:v", "libx264", "-preset", "medium", "-crf", "20",
        "-c:a", "aac", "-b:a", "128k",
        "-pix_fmt", "yuv420p",
        str(output_path)
    ], capture_output=True, check=True)


def main():
    pillar_path, report_path = find_pillar_video()

    if not pillar_path:
        log("ERROR: No assembled pillar video found. Run assembly first.")
        sys.exit(1)

    log(f"Pillar video: {pillar_path.name}")
    total_dur = get_duration(pillar_path)
    log(f"Duration: {total_dur:.0f}s ({total_dur/60:.1f} min)")

    # Load chapter timestamps
    chapters = []
    if report_path and report_path.exists():
        with open(report_path) as f:
            report = json.load(f)
        chapters = report.get("chapters", [])
        log(f"Loaded {len(chapters)} chapter markers")
    else:
        log("WARNING: No assembly report found — using estimated timestamps")

    # Build timestamp map from chapters
    ts = {}
    for ch in chapters:
        section = ch["section"].lower()
        ts[section] = ch["start_seconds"]

    # Resolve clip marker positions from chapters
    # CLIP MARKER 1 = Hook Open (start of video)
    hook_start = 0.0
    # CLIP MARKER 2 = Diagnostic Line (section: "Diagnostic Line — The Pattern")
    diag_start = ts.get("diagnostic line — the pattern", None)
    # CLIP MARKER 3 = Principle Close
    principle_start = ts.get("principle close", None)
    # Section starts for other cuts
    fp1_start = ts.get("failure pattern 1: the assumption campaign", None)
    fp3_start = ts.get("failure pattern 3: the timing blind spot", None)
    market_intel_start = ts.get("what pre-advertising intelligence means", None)
    cta_start = ts.get("cta + close", None)

    # If chapters not available, estimate from cleaned clip durations
    if diag_start is None:
        log("Estimating timestamps from typical section durations...")
        # Approximate from known clip durations:
        # hook ~69s, fp1 ~146s, fp2 ~146s, fp3 ~123s, market ~144s, pattern ~94s, principle ~112s, cta ~58s
        hook_start = 0
        fp1_start = fp1_start or 69
        fp3_start = fp3_start or 69 + 146 + 146
        market_intel_start = market_intel_start or 69 + 146 + 146 + 123
        diag_start = diag_start or 69 + 146 + 146 + 123 + 144
        principle_start = principle_start or 69 + 146 + 146 + 123 + 144 + 94
        cta_start = cta_start or 69 + 146 + 146 + 123 + 144 + 94 + 112

    now = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_dir = pillar_path.parent / "derivatives"
    output_dir.mkdir(exist_ok=True)

    # Define all derivative cuts
    # Per shooting script: 3 clip markers → reels, plus additional derivatives
    derivatives = [
        # IG Reels (9:16, <60s)
        {
            "name": f"{now}_reel_1_hook",
            "platform": "Instagram Reel",
            "desc": "CLIP MARKER 1 — Hook: 'You ran ads before knowing what your market wants'",
            "start": hook_start,
            "duration": min(60, fp1_start - hook_start if fp1_start else 60),
            "portrait": True,
        },
        {
            "name": f"{now}_reel_2_diagnostic",
            "platform": "Instagram Reel",
            "desc": "CLIP MARKER 2 — Diagnostic: 'Past performance data vs market intelligence'",
            "start": diag_start,
            "duration": min(60, (principle_start - diag_start) if principle_start else 60),
            "portrait": True,
        },
        {
            "name": f"{now}_reel_3_principle",
            "platform": "Instagram Reel",
            "desc": "CLIP MARKER 3 — Principle: 'Build the intelligence first'",
            "start": principle_start,
            "duration": min(60, (cta_start - principle_start) if cta_start else 60),
            "portrait": True,
        },
        # YouTube Shorts (9:16, <60s) — different segments than reels
        {
            "name": f"{now}_short_1_assumption_campaign",
            "platform": "YouTube Short",
            "desc": "Failure Pattern 1 — The Assumption Campaign (first 55s)",
            "start": fp1_start,
            "duration": 55,
            "portrait": True,
        },
        {
            "name": f"{now}_short_2_timing_blindspot",
            "platform": "YouTube Short",
            "desc": "Failure Pattern 3 — The Timing Blind Spot (first 55s)",
            "start": fp3_start,
            "duration": 55,
            "portrait": True,
        },
        # LinkedIn clip (16:9, <90s) — the market intelligence section
        {
            "name": f"{now}_linkedin_market_intelligence",
            "platform": "LinkedIn",
            "desc": "What pre-advertising intelligence actually means",
            "start": market_intel_start,
            "duration": min(90, (diag_start - market_intel_start) if diag_start else 90),
            "portrait": False,
        },
    ]

    results = []
    for deriv in derivatives:
        out_path = output_dir / f"{deriv['name']}.mp4"
        log(f"Cutting: {deriv['platform']} — {deriv['desc'][:60]}...")
        log(f"  Start: {deriv['start']:.0f}s, Duration: {deriv['duration']:.0f}s")

        try:
            cut_derivative(
                pillar_path, out_path,
                deriv["start"], deriv["duration"],
                portrait=deriv["portrait"]
            )
            dur = get_duration(out_path)
            results.append({
                "name": deriv["name"],
                "platform": deriv["platform"],
                "desc": deriv["desc"],
                "path": str(out_path),
                "duration": round(dur, 1),
                "aspect": "9:16" if deriv["portrait"] else "16:9",
            })
            log(f"  → {dur:.0f}s")
        except Exception as e:
            log(f"  ERROR: {e}")

    # Save report
    deriv_report = {
        "source_pillar": str(pillar_path),
        "pillar_duration": round(total_dur, 1),
        "timestamp": datetime.now().isoformat(),
        "derivatives": results,
        "method": "Cut from final assembled pillar video (GaryVee pillar model)",
    }
    report_out = output_dir / f"{now}_derivatives_report.json"
    with open(report_out, "w") as f:
        json.dump(deriv_report, f, indent=2)

    log(f"\n{'='*60}")
    log(f"DERIVATIVES COMPLETE")
    log(f"Source: {pillar_path.name}")
    for r in results:
        log(f"  {r['platform']:20s} | {r['aspect']} | {r['duration']:.0f}s | {r['desc'][:50]}")
    log(f"Report: {report_out.name}")
    log(f"{'='*60}")


if __name__ == "__main__":
    os.chdir(str(PROJECT_ROOT))
    main()
