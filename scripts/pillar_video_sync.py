#!/usr/bin/env python3
"""
Sync wireless mic audio (.m4a) to video (.mov) using envelope cross-correlation,
then merge into clean clips ready for assembly.
"""

import subprocess
import numpy as np
from scipy import signal as sig
import os
import json

RAW_DIR = "brands/askgauravai/Raw_recordings/Week 1/Youtube long form"
OUT_DIR = "brands/askgauravai/Raw_recordings/synced"
TEMP_DIR = "/tmp/pillar_sync"

CLIPS = [
    {"name": "01_hook", "video": "AskGauravAI - YT Script Clip maker 1.mov", "audio": "AskGauravAI - YT Script Clip maker 1.m4a"},
    {"name": "02_failure_pattern_1", "video": "AskGauravAI - YT Script Failure pattern 1.mov", "audio": "AskGauravAI - YT Script Failure pattern 1.m4a"},
    {"name": "03_failure_pattern_2", "video": "AskGauravAI - YT Script Failure pattern 2.mov", "audio": "AskGauravAI - YT Script Failure pattern 2.m4a"},
    {"name": "04_failure_pattern_3", "video": "AskGauravAI - YT Script Failure pattern 3.MOV", "audio": "AskGauravAI - YT Script Failure pattern 3.m4a"},
    {"name": "05_market_intelligence", "video": "AskGauravAI - YT Script Section 4.mov", "audio": "AskGauravAI - YT Script Section 4.m4a"},
    {"name": "06_the_pattern", "video": "AskGauravAI - YT Script Clip maker 2.MOV", "audio": "AskGauravAI - YT Script Clip maker 2.m4a"},
    {"name": "07_build_intelligence_first", "video": "AskGauravAI - YT Script Clip maker 3.mov", "audio": "AskGauravAI - YT Script Clip maker 3.m4a"},
    {"name": "08_cta", "video": "AskGauravAI - YT Script CTA.mov", "audio": "AskGauravAI - YT Script CTA.m4a"},
]

SAMPLE_RATE = 16000
ENVELOPE_RATE = 100  # downsample envelope to 100 Hz for fast correlation


def extract_raw_audio(input_path):
    """Extract mono 16kHz raw audio as float32 array."""
    raw = subprocess.run([
        "ffmpeg", "-i", input_path, "-f", "s16le", "-ac", "1", "-ar", str(SAMPLE_RATE), "-"
    ], capture_output=True, check=True)
    return np.frombuffer(raw.stdout, dtype=np.int16).astype(np.float32)


def compute_envelope(audio, sr, target_rate):
    """Compute amplitude envelope by downsampling absolute signal."""
    abs_audio = np.abs(audio)
    window = sr // target_rate
    # Pad to multiple of window
    pad_len = window - (len(abs_audio) % window) if len(abs_audio) % window else 0
    padded = np.concatenate([abs_audio, np.zeros(pad_len)])
    envelope = padded.reshape(-1, window).mean(axis=1)
    return envelope


def find_offset_envelope(video_audio, mic_audio):
    """
    Find where mic_audio best aligns within video_audio using envelope correlation.
    Returns offset in seconds (positive = mic starts after video start).
    """
    va_env = compute_envelope(video_audio, SAMPLE_RATE, ENVELOPE_RATE)
    ma_env = compute_envelope(mic_audio, SAMPLE_RATE, ENVELOPE_RATE)

    # Normalize
    va_env = va_env - np.mean(va_env)
    ma_env = ma_env - np.mean(ma_env)
    va_norm = np.sqrt(np.sum(va_env ** 2)) + 1e-8
    ma_norm = np.sqrt(np.sum(ma_env ** 2)) + 1e-8

    # Cross-correlate: find where mic fits within video
    corr = sig.correlate(va_env, ma_env, mode='full')
    lag = np.argmax(corr) - len(ma_env) + 1
    offset_seconds = lag / ENVELOPE_RATE
    confidence = float(np.max(corr) / (va_norm * ma_norm))

    return offset_seconds, confidence


def merge_video_mic(video_path, audio_path, output_path, offset):
    """Merge video with mic audio at the correct offset."""
    if offset > 0.05:
        # Mic started AFTER video — mic audio maps to video starting at 'offset'
        # Trim video start OR delay mic. Better: use -itsoffset to shift mic audio placement.
        cmd = [
            "ffmpeg", "-y",
            "-i", video_path,
            "-itsoffset", f"{offset:.3f}",
            "-i", audio_path,
            "-c:v", "copy", "-c:a", "aac", "-b:a", "192k",
            "-map", "0:v:0", "-map", "1:a:0",
            "-shortest",
            output_path
        ]
    elif offset < -0.05:
        # Mic started BEFORE video — trim beginning of mic audio
        cmd = [
            "ffmpeg", "-y",
            "-i", video_path,
            "-ss", f"{abs(offset):.3f}", "-i", audio_path,
            "-c:v", "copy", "-c:a", "aac", "-b:a", "192k",
            "-map", "0:v:0", "-map", "1:a:0",
            "-shortest",
            output_path
        ]
    else:
        # Near-zero offset
        cmd = [
            "ffmpeg", "-y",
            "-i", video_path,
            "-i", audio_path,
            "-c:v", "copy", "-c:a", "aac", "-b:a", "192k",
            "-map", "0:v:0", "-map", "1:a:0",
            "-shortest",
            output_path
        ]

    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"  FFMPEG ERROR: {result.stderr[-200:]}")
        raise RuntimeError("ffmpeg merge failed")


def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    os.makedirs(TEMP_DIR, exist_ok=True)

    results = []

    for i, clip in enumerate(CLIPS):
        name = clip["name"]
        video_path = os.path.join(RAW_DIR, clip["video"])
        audio_path = os.path.join(RAW_DIR, clip["audio"])
        output_path = os.path.join(OUT_DIR, f"{name}.mov")

        print(f"\n[{i+1}/{len(CLIPS)}] {name}")

        if not os.path.exists(video_path):
            print(f"  SKIP: Video not found")
            continue
        if not os.path.exists(audio_path):
            print(f"  SKIP: Audio not found")
            continue

        # Get source durations
        vdur = float(subprocess.run(
            ["ffprobe", "-v", "quiet", "-show_entries", "format=duration", "-of", "csv=p=0", video_path],
            capture_output=True, text=True
        ).stdout.strip())
        adur = float(subprocess.run(
            ["ffprobe", "-v", "quiet", "-show_entries", "format=duration", "-of", "csv=p=0", audio_path],
            capture_output=True, text=True
        ).stdout.strip())
        print(f"  Video: {vdur:.1f}s | Mic: {adur:.1f}s | Gap: {vdur-adur:.1f}s")

        # Extract raw audio
        print(f"  Extracting audio...")
        va = extract_raw_audio(video_path)
        ma = extract_raw_audio(audio_path)

        # Cross-correlate envelopes
        print(f"  Computing envelope sync...")
        offset, confidence = find_offset_envelope(va, ma)
        print(f"  Offset: {offset:.3f}s | Confidence: {confidence:.4f}")

        # Merge
        print(f"  Merging...")
        merge_video_mic(video_path, audio_path, output_path, offset)

        # Verify output
        out_dur = float(subprocess.run(
            ["ffprobe", "-v", "quiet", "-show_entries", "format=duration", "-of", "csv=p=0", output_path],
            capture_output=True, text=True
        ).stdout.strip())
        print(f"  Output: {out_dur:.1f}s")

        results.append({
            "name": name,
            "offset_seconds": round(float(offset), 3),
            "confidence": round(float(confidence), 4),
            "video_duration": round(vdur, 1),
            "mic_duration": round(adur, 1),
            "output_duration": round(out_dur, 1),
            "output": output_path,
        })

    report_path = os.path.join(OUT_DIR, "sync_report.json")
    with open(report_path, "w") as f:
        json.dump(results, f, indent=2)

    total = sum(r["output_duration"] for r in results)
    print(f"\n{'='*60}")
    print(f"{len(results)} clips synced → {OUT_DIR}/")
    print(f"Total: {total:.0f}s ({total/60:.1f} min)")
    print(f"Report: {report_path}")


if __name__ == "__main__":
    os.chdir("/Users/gauravoffgrid/offgrid-marketing-os")
    main()
