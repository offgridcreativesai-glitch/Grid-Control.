#!/usr/bin/env bash
# OffGrid brain-map — regenerate + open the live memory graph.
#   ./scripts/brainmap/brainmap.sh            # default: memory vault, type-grouped
#   ./scripts/brainmap/brainmap.sh <vault>    # any markdown folder
set -euo pipefail
DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VAULT="${1:-/Users/gauravoffgrid/.claude/projects/-Users-gauravoffgrid-offgrid-marketing-os/memory}"
python3 "$DIR/build.py" --vault "$VAULT" --by-type
exec python3 "${VAULT%/}/.brain-map/serve.py"
