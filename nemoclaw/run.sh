#!/usr/bin/env bash
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$(dirname "$SCRIPT_DIR")"
if ! python3 -c "import crewai" 2>/dev/null; then
  pip3 install -q -r "$SCRIPT_DIR/requirements.txt"
fi
exec python3 -m nemoclaw.dispatcher "$@"
