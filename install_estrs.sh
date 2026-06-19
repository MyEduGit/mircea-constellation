#!/usr/bin/env bash
# ESTRS installer — run once on macOS to set up the system.
# Usage:  bash install_estrs.sh

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ESTRS_DIR="$SCRIPT_DIR/estrs"
PLIST_SRC="$SCRIPT_DIR/com.geaboc.estrs.plist"
PLIST_DST="$HOME/Library/LaunchAgents/com.geaboc.estrs.plist"

echo "=== ESTRS Installer ==="
echo "Repo root: $SCRIPT_DIR"

# ── 1. Check Python ───────────────────────────────────────────────────────────
if ! command -v python3 &>/dev/null; then
    echo "ERROR: python3 not found. Install Python 3.9+ from https://python.org"
    exit 1
fi
PY_VERSION=$(python3 -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')
echo "Python: $PY_VERSION"

# ── 2. Install dependencies ───────────────────────────────────────────────────
echo "Installing Python dependencies…"
python3 -m pip install --quiet --upgrade pip
python3 -m pip install --quiet -r "$ESTRS_DIR/requirements.txt"
echo "Dependencies installed."

# ── 3. Smoke-test the import ──────────────────────────────────────────────────
echo "Smoke-testing ESTRS import…"
PYTHONPATH="$SCRIPT_DIR" python3 -c "
from estrs.config import VERSION
from estrs.discovery import iter_sermon_folders
from estrs.processor import process_sermon
from estrs.watcher import Watcher
print(f'ESTRS v{VERSION} — import OK')
"

# ── 4. Install launchd agent (macOS only) ────────────────────────────────────
if [[ "$(uname)" == "Darwin" ]]; then
    if [[ -f "$PLIST_SRC" ]]; then
        echo "Installing launchd agent…"
        mkdir -p "$HOME/Library/LaunchAgents"
        cp "$PLIST_SRC" "$PLIST_DST"
        # Patch the path inside the plist to point to this repo
        sed -i '' "s|__ESTRS_REPO__|$SCRIPT_DIR|g" "$PLIST_DST"
        sed -i '' "s|__PYTHON3__|$(which python3)|g" "$PLIST_DST"
        launchctl unload "$PLIST_DST" 2>/dev/null || true
        launchctl load -w "$PLIST_DST"
        echo "launchd agent loaded: com.geaboc.estrs"
        echo "ESTRS will start automatically on login and restart after crashes."
    else
        echo "No plist file found — skipping launchd setup."
        echo "To run manually: bash start_estrs.sh"
    fi
fi

echo ""
echo "=== Installation complete ==="
echo ""
echo "Quick-start commands:"
echo "  # Scan all volumes once:"
echo "  PYTHONPATH=$SCRIPT_DIR python3 -m estrs"
echo ""
echo "  # Process a single sermon folder:"
echo "  PYTHONPATH=$SCRIPT_DIR python3 -m estrs --folder /Volumes/SSD/C0001"
echo ""
echo "  # Start persistent watcher:"
echo "  PYTHONPATH=$SCRIPT_DIR python3 -m estrs --watch"
echo ""
echo "  # Force re-process everything:"
echo "  PYTHONPATH=$SCRIPT_DIR python3 -m estrs --force"
