#!/bin/bash
# Geaboc Subtitle Console — installer.
#
# Idempotent. Copies the console into Application Support, puts one
# double-clickable icon on the Desktop, clears the download quarantine so
# Gatekeeper stops asking, and runs a self-test.
#
# Installs nothing system-wide: no Homebrew, no pip, no sudo. The console
# runs on the Python that ships with macOS.
#
# UrantiOS governed — Truth, Beauty, Goodness.
set -uo pipefail

CYAN='\033[0;36m'; GREEN='\033[0;32m'; RED='\033[0;31m'; YELLOW='\033[1;33m'; NC='\033[0m'
info() { printf "${CYAN}[INFO]${NC}  %s\n" "$*"; }
ok()   { printf "${GREEN}[OK]${NC}    %s\n" "$*"; }
warn() { printf "${YELLOW}[WARN]${NC}  %s\n" "$*"; }

SRC_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
INSTALL_DIR="$HOME/Library/Application Support/GeabocSubtitleConsole"
DESKTOP="$HOME/Desktop"
CONSOLE_NAME="Geaboc Subtitle Console.command"

fail() {
  printf "${RED}[FAIL]${NC}  %s\n" "$*"
  /usr/bin/osascript -e "tell application \"System Events\" to display dialog \"Install failed.\n\n$1\" with title \"Geaboc Subtitle Console\" buttons {\"OK\"} default button \"OK\"" >/dev/null 2>&1
  echo ""
  echo "Press Return to close this window."
  read -r _
  exit 1
}

echo ""
echo "================================================="
echo "  Geaboc Subtitle Console — install"
echo "================================================="
echo ""

# ── 1. Preconditions ───────────────────────────────────────────────────
info "[1/5] Checking preconditions..."

[ "$(uname -s)" = "Darwin" ] || fail "This installer is for macOS."
[ -f "$SRC_DIR/geaboc_console.py" ] || \
  fail "geaboc_console.py is missing next to this installer.\n\nRe-extract the ZIP and run the installer from inside the extracted folder."

PYTHON=""
for candidate in python3 /usr/bin/python3 /opt/homebrew/bin/python3 /usr/local/bin/python3; do
  if command -v "$candidate" >/dev/null 2>&1 && "$candidate" -c 'import sys' >/dev/null 2>&1; then
    PYTHON="$candidate"
    break
  fi
done
[ -n "$PYTHON" ] || \
  fail "Python 3 is not installed.\n\nOpen Terminal, run:  xcode-select --install\n\nThen run this installer again."

ok "macOS $(sw_vers -productVersion 2>/dev/null || echo '?') · $("$PYTHON" --version 2>&1)"

# ── 2. Install files ───────────────────────────────────────────────────
info "[2/5] Installing to $INSTALL_DIR ..."
mkdir -p "$INSTALL_DIR" || fail "Could not create $INSTALL_DIR"
cp "$SRC_DIR/geaboc_console.py" "$INSTALL_DIR/geaboc_console.py" || \
  fail "Could not copy the console engine."
cp "$SRC_DIR/$CONSOLE_NAME" "$INSTALL_DIR/$CONSOLE_NAME" 2>/dev/null || true
chmod +x "$INSTALL_DIR/$CONSOLE_NAME" 2>/dev/null || true
ok "engine installed"

# ── 3. Desktop icon ────────────────────────────────────────────────────
info "[3/5] Putting the console on the Desktop..."
if [ ! -d "$DESKTOP" ]; then
  warn "No Desktop folder found — skipping the shortcut."
else
  cp "$SRC_DIR/$CONSOLE_NAME" "$DESKTOP/$CONSOLE_NAME" || \
    fail "Could not write to the Desktop."
  chmod +x "$DESKTOP/$CONSOLE_NAME" || fail "Could not make the console executable."
  ok "$DESKTOP/$CONSOLE_NAME"
fi

# ── 4. Clear the download quarantine ───────────────────────────────────
# Files that arrived in a downloaded ZIP carry com.apple.quarantine, which
# is why Gatekeeper demands Control-click → Open. Stripping it on files the
# operator just chose to install turns that into a plain double-click.
info "[4/5] Clearing Gatekeeper quarantine..."
QUARANTINE_CLEARED=0
for target in "$INSTALL_DIR/geaboc_console.py" "$INSTALL_DIR/$CONSOLE_NAME" "$DESKTOP/$CONSOLE_NAME"; do
  if [ -e "$target" ]; then
    xattr -d com.apple.quarantine "$target" >/dev/null 2>&1 && QUARANTINE_CLEARED=$((QUARANTINE_CLEARED + 1))
  fi
done
ok "cleared on $QUARANTINE_CLEARED file(s)"

# ── 5. Self-test ───────────────────────────────────────────────────────
info "[5/5] Running self-test (no network, no API credits)..."
if "$PYTHON" "$INSTALL_DIR/geaboc_console.py" --self-test; then
  ok "self-test passed"
else
  fail "Self-test failed. The console was copied but is not working."
fi

echo ""
echo "================================================="
echo "  Installed."
echo "================================================="
echo ""
echo "  Next:"
echo "    1. Double-click \"$CONSOLE_NAME\" on your Desktop."
echo "    2. Choose \"Transcribe with AssemblyAI\"."
echo "    3. Type the episode code (C0086) and pick the MP3."
echo ""
echo "  Results land in:  ~/Desktop/Geaboc Subtitles/C0086/"
echo ""

/usr/bin/osascript -e 'tell application "System Events" to display dialog "Geaboc Subtitle Console is installed.\n\nDouble-click “Geaboc Subtitle Console” on your Desktop, choose “Transcribe with AssemblyAI”, enter C0086 and pick the MP3.\n\nResults appear in:\nDesktop → Geaboc Subtitles → C0086" with title "Geaboc Subtitle Console" buttons {"OK"} default button "OK"' >/dev/null 2>&1

open -R "$DESKTOP/$CONSOLE_NAME" 2>/dev/null || true

echo "Press Return to close this window."
read -r _
exit 0
