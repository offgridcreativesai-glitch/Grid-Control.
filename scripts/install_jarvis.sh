#!/bin/bash
# scripts/install_jarvis.sh
# One-time setup for Jarvis voice layer
# Run from project root: bash scripts/install_jarvis.sh

set -e

echo "=== Installing Jarvis voice layer dependencies ==="

# Python packages
pip install edge-tts openai-whisper yt-dlp

# Optional: OpenJarvis framework
echo ""
echo "Installing OpenJarvis framework..."
pip install open-jarvis || echo "open-jarvis not yet on PyPI — skip for now, use morning_digest.py directly"

# macOS: portaudio for microphone input (optional)
if [[ "$OSTYPE" == "darwin"* ]]; then
    if command -v brew &>/dev/null; then
        brew install portaudio || true
        pip install pyaudio SpeechRecognition || true
    else
        echo "Homebrew not found — skipping portaudio/pyaudio (mic input unavailable)"
    fi
fi

echo ""
echo "=== Done ==="
echo ""
echo "Test TTS:          python jarvis_config/tts.py 'Hello, Jarvis is online'"
echo "Morning digest:    python jarvis_config/morning_digest.py"
echo ""
echo "Cron for 8am:      crontab -e"
echo "  0 8 * * * cd $(pwd) && python jarvis_config/morning_digest.py >> logs/jarvis.log 2>&1"
