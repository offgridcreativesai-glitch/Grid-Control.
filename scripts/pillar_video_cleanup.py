#!/usr/bin/env python3
"""
Clean up and trim all 8 pillar video clips:
- Trim false starts, slates, retakes
- Apply noise reduction (afftdn)
- Highpass 80Hz, lowpass 14kHz (voice focus)
- Compress dynamic range (consistent voice level)
- Normalize audio level
"""

import subprocess
import os
import json

SYNCED_DIR = "brands/askgauravai/Raw_recordings/synced"
CLEAN_DIR = "brands/askgauravai/Raw_recordings/cleaned"

# Audio filter chain: noise reduction → EQ → compression → normalization
AUDIO_FILTER = (
    "afftdn=nf=-25:nt=w,"         # FFT denoise: -25dB noise floor, wiener method
    "highpass=f=80:p=2,"           # Cut rumble below 80Hz
    "lowpass=f=14000:p=2,"         # Cut hiss above 14kHz
    "compand="                     # Dynamic range compression
        "attacks=0.05:decays=0.3:"
        "points=-80/-80|-45/-30|-27/-20|-15/-10|0/-5|20/-5,"
    "loudnorm=I=-16:LRA=11:TP=-1" # EBU R128 loudness normalization
)

# Trim definitions: (start_seconds, end_seconds or None for full clip)
# Based on Whisper SRT analysis
CLIPS = [
    {
        "name": "01_hook",
        "source": "01_hook.mov",
        "trim_start": 4.0,   # Skip "3, 2, 1, action."
        "trim_end": None,
    },
    {
        "name": "02_failure_pattern_1",
        "source": "02_failure_pattern_1.mov",
        "trim_start": 15.5,  # Skip "Asgharab AI, section 1, failure pattern 1, we record the whole script in 3, 2, 1 action."
        "trim_end": None,
    },
    {
        "name": "03_failure_pattern_2",
        "source": "03_failure_pattern_2.mov",
        # First take: 0:00-0:28 (includes slate + first attempt)
        # Second take: 0:28+ (the good take starting "The second pattern is borrowed framework")
        # But 0:00-3.16 has "to one action." tail from slate
        # Good take starts at ~44.7s based on SRT entry 6→7 transition
        "trim_start": 44.0,  # Skip slate + first take, use second clean take
        "trim_end": None,
    },
    {
        "name": "04_failure_pattern_3",
        "source": "04_failure_pattern_3.mov",
        # Multiple false starts through ~1:13
        # Clean take: "The third pattern is the one nobody talks about..." at ~1:13
        "trim_start": 73.0,  # Skip all false starts, "3 2 1 action" before final take
        "trim_end": None,
    },
    {
        "name": "05_market_intelligence",
        "source": "05_market_intelligence.mov",
        "trim_start": 0,     # Clean start
        "trim_end": None,
    },
    {
        "name": "06_the_pattern",
        "source": "06_the_pattern.mov",
        "trim_start": 28.0,  # Skip "Asgore AI, next section of record, clip maker 2, starting in 3, 2, 1, action."
        "trim_end": None,
    },
    {
        "name": "07_build_intelligence_first",
        "source": "07_build_intelligence_first.mov",
        "trim_start": 0,     # Clean start
        "trim_end": None,    # Video ends cleanly at 1:46
    },
    {
        "name": "08_cta",
        "source": "08_cta.mov",
        "trim_start": 0,     # Clean start
        "trim_end": None,
    },
]


def process_clip(clip):
    name = clip["name"]
    source = os.path.join(SYNCED_DIR, clip["source"])
    output = os.path.join(CLEAN_DIR, f"{name}.mov")

    if not os.path.exists(source):
        print(f"  SKIP: {source} not found")
        return None

    cmd = ["ffmpeg", "-y"]

    # Input with trim
    if clip["trim_start"] > 0:
        cmd += ["-ss", f"{clip['trim_start']:.1f}"]
    cmd += ["-i", source]
    if clip["trim_end"]:
        cmd += ["-t", f"{clip['trim_end'] - clip['trim_start']:.1f}"]

    # Video: copy (no re-encode)
    # Audio: full cleanup chain
    cmd += [
        "-c:v", "copy",
        "-af", AUDIO_FILTER,
        "-c:a", "aac", "-b:a", "192k",
        output
    ]

    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"  ERROR: {result.stderr[-300:]}")
        return None

    # Get output duration
    dur = float(subprocess.run(
        ["ffprobe", "-v", "quiet", "-show_entries", "format=duration", "-of", "csv=p=0", output],
        capture_output=True, text=True
    ).stdout.strip())

    return {"name": name, "duration": round(dur, 1), "output": output}


def main():
    os.makedirs(CLEAN_DIR, exist_ok=True)

    results = []
    for i, clip in enumerate(CLIPS):
        print(f"[{i+1}/{len(CLIPS)}] {clip['name']} (trim from {clip['trim_start']:.0f}s)...")
        r = process_clip(clip)
        if r:
            results.append(r)
            print(f"  → {r['duration']:.1f}s")

    total = sum(r["duration"] for r in results)
    print(f"\n{'='*60}")
    print(f"{len(results)} clips cleaned → {CLEAN_DIR}/")
    print(f"Total: {total:.0f}s ({total/60:.1f} min)")

    with open(os.path.join(CLEAN_DIR, "cleanup_report.json"), "w") as f:
        json.dump(results, f, indent=2)


if __name__ == "__main__":
    os.chdir("/Users/gauravoffgrid/offgrid-marketing-os")
    main()
