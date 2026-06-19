#!/usr/bin/env bash
# ESTRS — start watcher manually (alternative to launchd).
# Usage:  bash start_estrs.sh [--root /path/to/SSD]

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LOG_FILE="$SCRIPT_DIR/estrs_watcher.log"

echo "Starting ESTRS watcher… (log: $LOG_FILE)"
echo "Press Ctrl-C to stop."

PYTHONPATH="$SCRIPT_DIR" python3 -m estrs --watch "$@" 2>&1 | tee -a "$LOG_FILE"
