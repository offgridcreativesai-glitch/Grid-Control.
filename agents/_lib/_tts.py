"""
agents/_lib/_tts.py — text-to-speech provider router ("voicebox", Jul 12 2026).

Swaps the Creative Director's narration backend behind a TTS_PROVIDER flag (mirrors the
SCRAPE_PROVIDER pattern). Default 'elevenlabs' — unchanged behavior, zero regression. Flip to
'chatterbox' for a local, on-device founder-voice clone (free, private, no per-character billing);
'say' is the macOS built-in stopgap.

Zero-assumption: never raises, never fabricates. Returns the written file path (str) or None.
The caller owns the audio directory + relative-path bookkeeping; this module only synthesizes
and writes one file. Heavy deps (torch/chatterbox) are imported LAZILY inside the chatterbox path,
so nothing here forces a multi-GB install unless that provider is actually selected.

Activation (chatterbox): (1) pip install chatterbox-tts (needs a Python the wheels support — 3.14
has none yet, use a 3.11/3.12 venv); (2) drop a clean ~15s founder sample at
brands/<slug>/voice_sample.wav; (3) set TTS_PROVIDER=chatterbox. Until all three, the default
ElevenLabs path (or a graceful skip) stays in force.
"""
from __future__ import annotations

import os
import subprocess

_noop = lambda _m: None


def provider() -> str:
    return (os.getenv("TTS_PROVIDER") or "elevenlabs").strip().lower()


def synthesize(text: str, *, out_dir, base_name: str, voice_id: str = "", api_key: str = "",
               ref_sample: str | None = None, log=_noop) -> str | None:
    """Text → one audio file in out_dir named base_name.<ext>. Returns the abs path or None.
    Routes by TTS_PROVIDER. Never raises."""
    text = (text or "").strip()
    if not text:
        return None
    os.makedirs(out_dir, exist_ok=True)
    p = provider()
    if p == "chatterbox":
        return _chatterbox(text, str(out_dir), base_name, ref_sample, log)
    if p == "say":
        return _macos_say(text, str(out_dir), base_name, log)
    return _elevenlabs(text, str(out_dir), base_name, voice_id, api_key, log)


# ── ElevenLabs (default — identical to the prior in-line CD behavior) ──────────
def _elevenlabs(text, out_dir, base_name, voice_id, api_key, log):
    if not api_key:
        log(f"Skipping narration for '{base_name}' — no ElevenLabs key.")
        return None
    try:
        from elevenlabs import ElevenLabs
        client = ElevenLabs(api_key=api_key)
        log(f"Generating narration via ElevenLabs: '{text[:60]}...'")
        audio_gen = client.text_to_speech.convert(
            voice_id=voice_id, text=text,
            model_id="eleven_multilingual_v2", output_format="mp3_44100_128",
        )
        audio_bytes = b"".join(audio_gen)
        out = os.path.join(out_dir, base_name + ".mp3")
        with open(out, "wb") as f:
            f.write(audio_bytes)
        log(f"✅ Narration saved: {base_name}.mp3 ({len(audio_bytes):,} bytes)")
        return out
    except Exception as e:
        log(f"⚠️  ElevenLabs narration failed for '{base_name}': {e}")
        return None


# ── Chatterbox (local founder-voice clone) ────────────────────────────────────
# Chatterbox lives in an isolated Python (its torch/transformers pins don't match the main
# 3.14 app), so synthesis is shelled out to _voicebox_synth.py run by VOICEBOX_PYTHON rather
# than imported in-process. ponytail: the model reloads per call (a few seconds); for the
# 1–3 narration lines a creative run produces that's fine — swap to a persistent worker only
# if narration volume ever makes the reload cost matter.
_VOICEBOX_PY_DEFAULT = os.path.expanduser("~/.venvs/voicebox/bin/python")


def _chatterbox(text, out_dir, base_name, ref_sample, log):
    if not ref_sample or not os.path.exists(ref_sample):
        log("⚠️  Chatterbox needs a founder voice sample at brands/<slug>/voice_sample.wav — none found.")
        return None
    py = (os.getenv("VOICEBOX_PYTHON") or _VOICEBOX_PY_DEFAULT).strip()
    if not os.path.exists(py):
        log(f"⚠️  Chatterbox venv Python not found at {py} — install chatterbox-tts there or set VOICEBOX_PYTHON.")
        return None
    synth = os.path.join(os.path.dirname(__file__), "_voicebox_synth.py")
    out = os.path.join(out_dir, base_name + ".wav")
    try:
        r = subprocess.run([py, synth, "--out", out, "--ref", ref_sample, "--text", text],
                           capture_output=True, text=True, timeout=300)
        if r.returncode == 0 and os.path.exists(out) and os.path.getsize(out) > 0:
            log(f"✅ Chatterbox narration saved: {base_name}.wav (cloned voice)")
            return out
        log(f"⚠️  Chatterbox synth failed: {((r.stderr or r.stdout) or '').strip()[-300:]}")
        return None
    except subprocess.TimeoutExpired:
        log(f"⚠️  Chatterbox synth timed out (>5min) for '{base_name}'.")
        return None
    except Exception as e:
        log(f"⚠️  Chatterbox synth error for '{base_name}': {e}")
        return None


# ── macOS `say` (zero-dep stopgap) ────────────────────────────────────────────
def _macos_say(text, out_dir, base_name, log):
    out = os.path.join(out_dir, base_name + ".aiff")
    try:
        subprocess.run(["say", "-o", out, text], check=True, timeout=60,
                       capture_output=True, text=True)
        log(f"✅ macOS say narration saved: {base_name}.aiff")
        return out
    except Exception as e:
        log(f"⚠️  macOS say failed for '{base_name}': {e}")
        return None


if __name__ == "__main__":  # ponytail self-check — routes + writes a file (darwin, no heavy deps)
    import sys, tempfile
    if sys.platform != "darwin":
        print("tts self-check skipped (needs macOS `say`)"); sys.exit(0)
    os.environ["TTS_PROVIDER"] = "say"
    d = tempfile.mkdtemp()
    got = synthesize("Grid Control voicebox self check.", out_dir=d, base_name="probe", log=print)
    assert got and os.path.exists(got) and os.path.getsize(got) > 0, "say provider produced no file"
    assert provider() == "say"
    print("tts router self-check ok")
