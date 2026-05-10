#!/usr/bin/env bash
# sync-all.sh — Mirror ~/Obsidian/UrantiPedia/ to iCloud, Google Drive,
#               and external SSD (if mounted).
# Fails loudly if rclone is missing. Warns (non-fatal) if a remote is absent.
set -euo pipefail

VAULT="${OBSIDIAN_URANTIPEDIA_VAULT:-${HOME}/Obsidian/UrantiPedia}"
CRED_FILE="${HOME}/.cloud-backup/.env"
LOG_DIR="${HOME}/.cloud-backup/logs"
LOG_FILE="${LOG_DIR}/perpetual-sync-$(date +%Y-%m-%d).log"

mkdir -p "$LOG_DIR"

say()  { printf '\033[1;36m[sync-all]\033[0m %s\n' "$*" | tee -a "$LOG_FILE"; }
ok()   { printf '\033[1;32m  [ok]\033[0m %s\n' "$*" | tee -a "$LOG_FILE"; }
warn() { printf '\033[1;33m  [WARN]\033[0m %s\n' "$*" | tee -a "$LOG_FILE"; }
fail() { printf '\033[1;31m  [FAIL]\033[0m %s\n' "$*" | tee -a "$LOG_FILE" >&2; exit 1; }

# ── Guard: rclone required ────────────────────────────────────────────────────
command -v rclone &>/dev/null || fail "rclone not found — run: setup/cloud-backup/install.sh"

# ── Guard: vault must exist ───────────────────────────────────────────────────
[ -d "$VAULT" ] || fail "Vault not found at $VAULT — run: setup/perpetual-capture/scaffold-vault.sh"

# ── Load credentials ──────────────────────────────────────────────────────────
if [ -f "$CRED_FILE" ]; then
  set +u
  # shellcheck disable=SC1090
  source "$CRED_FILE"
  set -u
fi

RCLONE_OPTS=(
  --create-empty-src-dirs
  --transfers 8
  --checkers 16
  --log-level INFO
  --log-file "$LOG_FILE"
  --filter "- .DS_Store"
  --filter "- .obsidian/workspace*"
  --filter "- *.tmp"
)

rclone_sync() {
  local src="$1" dest="$2" label="$3"
  say "Syncing $label..."
  if rclone sync "$src" "$dest" "${RCLONE_OPTS[@]}" 2>&1 | tail -3; then
    ok "$label → done"
  else
    warn "$label → non-zero exit (check $LOG_FILE)"
  fi
}

check_remote() { rclone listremotes 2>/dev/null | grep -q "^${1}:$"; }

# ── 1. Google Drive ───────────────────────────────────────────────────────────
say "=== Google Drive ==="
if check_remote gdrive; then
  rclone_sync "$VAULT" "gdrive:UrantiPedia" "UrantiPedia → GDrive"
else
  warn "gdrive remote not configured — run: setup/cloud-backup/install.sh"
fi

# ── 2. iCloud WebDAV ─────────────────────────────────────────────────────────
say "=== iCloud ==="
if check_remote icloud; then
  ICLOUD_PATH="${ICLOUD_URANTIPEDIA_PATH:-Documents/Obsidian/UrantiPedia}"
  rclone_sync "$VAULT" "icloud:$ICLOUD_PATH" "UrantiPedia → iCloud"
else
  warn "icloud remote not configured — run: setup/cloud-backup/install.sh"
fi

# ── 3. External SSD (macOS Volumes) ──────────────────────────────────────────
say "=== External SSD ==="
SSD_DEST="${PERPETUAL_CAPTURE_SSD_PATH:-}"
if [ -z "$SSD_DEST" ]; then
  # Auto-detect first mounted external volume on macOS
  if [[ "$(uname)" == "Darwin" ]]; then
    SSD_DEST="$(find /Volumes -maxdepth 1 -mindepth 1 -type d ! -name 'Macintosh HD' 2>/dev/null | head -1)/UrantiPedia"
  fi
fi

if [ -n "$SSD_DEST" ] && [ -d "$(dirname "$SSD_DEST")" ]; then
  mkdir -p "$SSD_DEST"
  say "Copying to SSD: $SSD_DEST"
  rsync -a --delete \
    --exclude='.DS_Store' \
    --exclude='.obsidian/workspace*' \
    "$VAULT/" "$SSD_DEST/" 2>&1 | tail -3
  ok "SSD copy done: $SSD_DEST"
else
  warn "No external SSD detected — skipping (set PERPETUAL_CAPTURE_SSD_PATH to override)"
fi

# ── Proof ─────────────────────────────────────────────────────────────────────
say "=== PROOF ==="
VAULT_SIZE="$(du -sh "$VAULT" 2>/dev/null | cut -f1)"
FILE_COUNT="$(find "$VAULT" -name '*.md' | wc -l | tr -d ' ')"
say "Vault size:  $VAULT_SIZE"
say "Total .md:   $FILE_COUNT files"
say "Timestamp:   $(date -u +%Y-%m-%dT%H:%M:%SZ)"
say "Log:         $LOG_FILE"
