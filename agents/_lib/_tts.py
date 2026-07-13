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
_cbx_model = None  # module-level cache — loading the model per call would be brutal


def _load_chatterbox(device, log):
    global _cbx_model
    if _cbx_model is not None:
        return _cbx_model
    from chatterbox.tts import ChatterboxTTS
    log(f"Loading Chatterbox model on {device} (first call only)…")
    _cbx_model = ChatterboxTTS.from_pretrained(device=device)
    return _cbx_model


def _chatterbox(text, out_dir, base_name, ref_sample, log):
    if not ref_sample or not os.path.exists(ref_sample):
        log("⚠️  Chatterbox needs a founder voice sample at brands/<slug>/voice_sample.wav — none found.")
        return None
    try:
        import torch
        import torchaudio as ta
    except Exception as e:
        log(f"⚠️  Chatterbox deps missing ({e}) — pip install chatterbox-tts torch torchaudio.")
        return None
    try:
        device = "mps" if torch.backends.mps.is_available() else ("cuda" if torch.cuda.is_available() else "cpu")
        model = _load_chatterbox(device, log)
        wav = model.generate(text, audio_prompt_path=ref_sample)
        out = os.path.join(out_dir, base_name + ".wav")
        ta.save(out, wav.cpu() if hasattr(wav, "cpu") else wav, model.sr)
        log(f"✅ Chatterbox narration saved: {base_name}.wav (cloned voice, device={device})")
        return out
    except Exception as e:
        log(f"⚠️  Chatterbox narration failed for '{base_name}': {e}")
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
