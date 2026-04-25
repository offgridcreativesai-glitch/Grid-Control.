"""
jarvis_config/tts.py
edge-tts wrapper for Jarvis voice output.
Requires: pip install edge-tts
Uses en-US-GuyNeural (closest to JARVIS sound).
"""

import asyncio
import os
import subprocess
import sys
import tempfile


async def _speak_async(text: str, voice: str = "en-US-GuyNeural") -> str:
    """Generate TTS audio file. Returns path to .mp3 file."""
    try:
        import edge_tts  # type: ignore
    except ImportError:
        raise ImportError("edge-tts not installed. Fix: pip install edge-tts")

    with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as f:
        tmp_path = f.name

    communicate = edge_tts.Communicate(text, voice)
    await communicate.save(tmp_path)
    return tmp_path


def speak(text: str, play: bool = True, voice: str = "en-US-GuyNeural") -> str:
    """
    Generate and optionally play TTS audio.
    Returns path to generated .mp3 file.
    play=True: plays via afplay (macOS) or aplay (Linux).
    """
    path = asyncio.run(_speak_async(text, voice))

    if play and os.path.exists(path):
        if sys.platform == "darwin":
            subprocess.run(["afplay", path], check=False)
        elif sys.platform.startswith("linux"):
            subprocess.run(["aplay", path], check=False)

    return path


if __name__ == "__main__":
    test_text = sys.argv[1] if len(sys.argv) > 1 else "Hello, I am Jarvis. Grid Control is online."
    print(f"Speaking: {test_text}")
    speak(test_text, play=True)
    print("Done.")
