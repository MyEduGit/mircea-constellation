#!/bin/bash
# Geaboc Subtitle Console — double-click launcher.
#
# Works from two places, deliberately:
#   1. Inside the extracted geaboc_subtitle_console folder (engine is a
#      sibling file), so the console can be tried before installing.
#   2. On the Desktop after installing (engine lives in Application
#      Support), so the Desktop stays a single icon rather than a folder.
#
# UrantiOS governed — Truth, Beauty, Goodness.
set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
INSTALL_DIR="$HOME/Library/Application Support/GeabocSubtitleConsole"

# ── Locate the engine ──────────────────────────────────────────────────
ENGINE=""
for candidate in "$SCRIPT_DIR/geaboc_console.py" "$INSTALL_DIR/geaboc_console.py"; do
  if [ -f "$candidate" ]; then
    ENGINE="$candidate"
    break
  fi
done

dialog() {
  /usr/bin/osascript -e "tell application \"System Events\" to display dialog \"$1\" with title \"Geaboc Subtitle Console\" buttons {\"OK\"} default button \"OK\"" >/dev/null 2>&1
}

if [ -z "$ENGINE" ]; then
  dialog "The console engine is missing.\n\nRe-run install_Geaboc_Subtitle_Console.command from the geaboc_subtitle_console folder."
  echo "ERROR: geaboc_console.py not found in:"
  echo "  $SCRIPT_DIR"
  echo "  $INSTALL_DIR"
  echo ""
  echo "Press Return to close this window."
  read -r _
  exit 1
fi

# ── Locate a working python3 ───────────────────────────────────────────
# macOS ships /usr/bin/python3 as a stub that triggers the Command Line
# Tools installer on first use, so presence is not enough — it has to run.
PYTHON=""
for candidate in python3 /usr/bin/python3 /opt/homebrew/bin/python3 /usr/local/bin/python3; do
  if command -v "$candidate" >/dev/null 2>&1 && "$candidate" -c 'import sys' >/dev/null 2>&1; then
    PYTHON="$candidate"
    break
  fi
done

if [ -z "$PYTHON" ]; then
  dialog "Python 3 is not installed yet.\n\nOpen Terminal and run:\n\nxcode-select --install\n\nThen accept the Apple installer and double-click this console again."
  echo "ERROR: no working python3 found."
  echo "Run:  xcode-select --install"
  echo ""
  echo "Press Return to close this window."
  read -r _
  exit 1
fi

# ── Run ────────────────────────────────────────────────────────────────
"$PYTHON" "$ENGINE" "$@"
STATUS=$?

echo ""
if [ $STATUS -eq 0 ]; then
  echo "Finished. You can close this window."
else
  echo "Finished with errors (exit $STATUS). The message above says why."
fi
echo "Press Return to close."
read -r _
exit $STATUS
