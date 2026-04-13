#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────────────────────
# NemoClaw Observer — bootstrap + run script
#
#   ./run.sh              # one-shot: setup + single check cycle (print)
#   ./run.sh telegram     # one-shot: post to Telegram
#   ./run.sh json         # one-shot: emit JSON to stdout
#   ./run.sh loop         # long-running: every NEMO_INTERVAL seconds (default 21600 = 6h)
#   ./run.sh loop telegram
#
# Environment:
#   NEMO_INTERVAL  seconds between loop runs (default 21600 = 6h)
#   NEMO_VENV      path to venv (default ./.venv)
# ─────────────────────────────────────────────────────────────────────────────
set -euo pipefail

HERE="$(cd "$(dirname "$0")" && pwd)"
cd "$HERE"

NEMO_VENV="${NEMO_VENV:-$HERE/.venv}"
NEMO_INTERVAL="${NEMO_INTERVAL:-21600}"

# 1. Python
if ! command -v python3 >/dev/null 2>&1; then
    echo "ERROR: python3 not found. Install Python 3.10+ first." >&2
    exit 1
fi

# 2. venv
if [ ! -d "$NEMO_VENV" ]; then
    echo ">> Creating venv at $NEMO_VENV"
    python3 -m venv "$NEMO_VENV"
fi
# shellcheck disable=SC1091
source "$NEMO_VENV/bin/activate"

# 3. dependencies
echo ">> Installing requirements"
pip install --quiet --upgrade pip
pip install --quiet -r "$HERE/requirements.txt"

# 4. .env
if [ ! -f "$HERE/.env" ]; then
    echo ">> Seeding .env from config.env.example (edit secrets before prod use)"
    cp "$HERE/config.env.example" "$HERE/.env"
fi
# shellcheck disable=SC1091
set -a; . "$HERE/.env"; set +a

# 5. mode dispatch
MODE="${1:-print}"

if [ "$MODE" = "loop" ]; then
    shift || true
    SUBMODE="${1:-print}"
    echo ">> Entering loop (every ${NEMO_INTERVAL}s, mode=${SUBMODE}). Ctrl-C to stop."
    while true; do
        python3 observer.py "$SUBMODE" || echo "!! observer run failed — retrying next cycle"
        sleep "$NEMO_INTERVAL"
    done
else
    python3 observer.py "$MODE"
fi
