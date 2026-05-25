#!/usr/bin/env bash
# install.sh — Install the Perpetual Capture automation.
# macOS: registers a launchd agent (runs every 15 min).
# Linux: installs a cron job (runs every 15 min).
# Idempotent — safe to re-run.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VAULT="${OBSIDIAN_URANTIPEDIA_VAULT:-${HOME}/Obsidian/UrantiPedia}"
PYTHON="$(command -v python3 || echo python3)"

say()  { printf '\033[1;36m[pc-install]\033[0m %s\n' "$*"; }
ok()   { printf '\033[1;32m  [ok]\033[0m %s\n' "$*"; }
warn() { printf '\033[1;33m  [warn]\033[0m %s\n' "$*"; }
fail() { printf '\033[1;31m  [FAIL]\033[0m %s\n' "$*" >&2; exit 1; }

# ── 1. Scaffold vault ─────────────────────────────────────────────────────────
say "Scaffolding vault..."
OBSIDIAN_URANTIPEDIA_VAULT="$VAULT" bash "$SCRIPT_DIR/scaffold-vault.sh"

# ── 2. Python check ───────────────────────────────────────────────────────────
say "Checking Python..."
"$PYTHON" --version || fail "python3 not found"
"$PYTHON" -c "from zoneinfo import ZoneInfo; ZoneInfo('Australia/Melbourne')" 2>/dev/null \
  || fail "zoneinfo for Australia/Melbourne not available — update Python to 3.9+"
ok "Python OK: $("$PYTHON" --version)"

# ── 3. macOS: launchd agent ───────────────────────────────────────────────────
if [[ "$(uname)" == "Darwin" ]]; then
  say "Installing launchd agent..."
  PLIST_SRC="$SCRIPT_DIR/launchd/com.mircea.perpetual-capture.plist"
  PLIST_DEST="${HOME}/Library/LaunchAgents/com.mircea.perpetual-capture.plist"

  # Substitute real paths into plist
  sed \
    -e "s|PYTHON_PATH|${PYTHON}|g" \
    -e "s|CAPTURE_PY_PATH|${SCRIPT_DIR}/capture.py|g" \
    -e "s|SYNC_SH_PATH|${SCRIPT_DIR}/sync-all.sh|g" \
    -e "s|VAULT_PATH|${VAULT}|g" \
    "$PLIST_SRC" > "$PLIST_DEST"

  # Unload if already loaded, then load
  launchctl unload "$PLIST_DEST" 2>/dev/null || true
  launchctl load -w "$PLIST_DEST"
  ok "launchd agent loaded: $PLIST_DEST"

# ── 4. Linux: cron job ────────────────────────────────────────────────────────
else
  say "Installing cron job..."
  CRON_CMD="*/15 * * * * OBSIDIAN_URANTIPEDIA_VAULT=${VAULT} ${PYTHON} ${SCRIPT_DIR}/capture.py >> ${HOME}/.cloud-backup/logs/perpetual-cron.log 2>&1 && bash ${SCRIPT_DIR}/sync-all.sh >> ${HOME}/.cloud-backup/logs/perpetual-cron.log 2>&1"
  MARKER="# perpetual-capture"

  # Remove old entry, add fresh one
  (crontab -l 2>/dev/null | grep -v "$MARKER"; echo "$CRON_CMD $MARKER") | crontab -
  ok "cron job installed (every 15 min)"
  crontab -l | grep perpetual-capture
fi

say "Install complete."
say "Run manually: OBSIDIAN_URANTIPEDIA_VAULT=$VAULT $PYTHON $SCRIPT_DIR/capture.py"
