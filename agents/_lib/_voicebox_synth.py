"""
agents/_lib/_voicebox_synth.py — standalone Chatterbox synth worker (voicebox).

Run BY the voicebox venv's Python (VOICEBOX_PYTHON, default ~/.venvs/voicebox/bin/python),
NOT by the main Grid Control interpreter. Grid Control runs on 3.14; Chatterbox's deps
(torch 2.6, transformers) live in a 3.12 venv — so synthesis is shelled out to this script to
keep the two Python worlds apart. Intentionally imports nothing from Grid Control.

Usage: <venv-python> _voicebox_synth.py --out OUT.wav --ref SAMPLE.wav --text "..."
Prints the output path on success; exits non-zero with the error on stderr otherwise.
"""
import argparse
import sys


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    ap.add_argument("--ref", required=True, help="reference voice sample (wav) to clone")
    ap.add_argument("--text", required=True)
    a = ap.parse_args()

    import torch
    import torchaudio as ta
    from chatterbox.tts import ChatterboxTTS

    device = "mps" if torch.backends.mps.is_available() else (
        "cuda" if torch.cuda.is_available() else "cpu")
    model = ChatterboxTTS.from_pretrained(device=device)
    wav = model.generate(a.text, audio_prompt_path=a.ref)
    ta.save(a.out, wav.cpu() if hasattr(wav, "cpu") else wav, model.sr)
    print(a.out)


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"voicebox synth error: {e}", file=sys.stderr)
        sys.exit(1)
