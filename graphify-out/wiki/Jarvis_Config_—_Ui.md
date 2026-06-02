# Jarvis_Config — Ui

> 14 nodes · cohesion 0.19

## Key Concepts

- **speak()** (6 connections) — `jarvis_config/tts.py`
- **build_digest()** (4 connections) — `jarvis_config/morning_digest.py`
- **morning_digest.py** (4 connections) — `jarvis_config/morning_digest.py`
- **_speak_async()** (4 connections) — `jarvis_config/tts.py`
- **_get()** (3 connections) — `jarvis_config/morning_digest.py`
- **tts.py** (3 connections) — `jarvis_config/tts.py`
- **str** (2 connections) — `jarvis_config/morning_digest.py`
- **str** (2 connections) — `jarvis_config/tts.py`
- **jarvis_config/morning_digest.py Morning briefing — reads Grid Control API and sp** (1 connections) — `jarvis_config/morning_digest.py`
- **Build a 3-sentence spoken brief from Grid Control state.** (1 connections) — `jarvis_config/morning_digest.py`
- **bool** (1 connections) — `jarvis_config/tts.py`
- **jarvis_config/tts.py edge-tts wrapper for Jarvis voice output. Requires: pip ins** (1 connections) — `jarvis_config/tts.py`
- **Generate TTS audio file. Returns path to .mp3 file.** (1 connections) — `jarvis_config/tts.py`
- **Generate and optionally play TTS audio.     Returns path to generated .mp3 file.** (1 connections) — `jarvis_config/tts.py`

## Relationships

- No strong cross-community connections detected

## Source Files

- `jarvis_config/morning_digest.py`
- `jarvis_config/tts.py`

## Audit Trail

- EXTRACTED: 34 (100%)
- INFERRED: 0 (0%)
- AMBIGUOUS: 0 (0%)

---

*Part of the graphify knowledge wiki. See [[index]] to navigate.*