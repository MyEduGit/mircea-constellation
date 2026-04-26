#!/usr/bin/env bash
# sync-obsidian.sh — Sync Obsidian vaults to Google Drive and iCloud via rclone.
# Reads credentials from ~/.cloud-backup/.env (created by install.sh).
# Safe to run repeatedly; rclone only transfers changed files.
set -euo pipefail

CRED_FILE="${HOME}/.cloud-backup/.env"
LOG_DIR="${HOME}/.cloud-backup/logs"
LOG_FILE="${LOG_DIR}/sync-$(date +%Y-%m-%d).log"

say()  { printf '\033[1;36m[sync-obsidian]\033[0m %s\n' "$*" | tee -a "$LOG_FILE"; }
ok()   { printf '\033[1;32m  [ok]\033[0m %s\n' "$*" | tee -a "$LOG_FILE"; }
warn() { printf '\033[1;33m  [warn]\033[0m %s\n' "$*" | tee -a "$LOG_FILE"; }
err()  { printf '\033[1;31m  [err]\033[0m %s\n' "$*" | tee -a "$LOG_FILE" >&2; }

mkdir -p "$LOG_DIR"

# ── Load credentials ──────────────────────────────────────────────────────────
if [ ! -f "$CRED_FILE" ]; then
  err "Credentials not found at $CRED_FILE — run: setup/cloud-backup/install.sh"
  exit 1
fi
# shellcheck disable=SC1090
set +u; source "$CRED_FILE"; set -u

JOBS_VAULT="${OBSIDIAN_JOBS_VAULT:-${HOME}/Documents/Obsidian/Jobs}"
ANTHR_VAULT="${OBSIDIAN_ANTHROPIC_VAULT:-${HOME}/Documents/Obsidian/Anthropic-Data}"

GDRIVE_JOBS_DEST="gdrive:ObsidianJobs"
GDRIVE_ANTHR_DEST="gdrive:AnthropicData"
if [ -n "${GDRIVE_OBSIDIAN_FOLDER_ID:-}" ]; then
  GDRIVE_JOBS_DEST="gdrive:ObsidianJobs --drive-root-folder-id=${GDRIVE_OBSIDIAN_FOLDER_ID}"
fi

ICLOUD_JOBS_DEST="icloud:${ICLOUD_OBSIDIAN_PATH:-Documents/Obsidian/Jobs}"
ICLOUD_ANTHR_DEST="icloud:${ICLOUD_ANTHROPIC_PATH:-Documents/Obsidian/Anthropic-Data}"

RCLONE_OPTS=(
  --create-empty-src-dirs
  --transfers 4
  --checkers 8
  --log-level INFO
  --log-file "$LOG_FILE"
  --filter "- *.DS_Store"
  --filter "- .obsidian/workspace*"
)

rclone_sync() {
  local src="$1" dest="$2" label="$3"
  if [ ! -d "$src" ]; then
    warn "$label: source $src not found — skipping"
    return 0
  fi
  say "Syncing $label → $dest"
  if rclone sync "$src" $dest "${RCLONE_OPTS[@]}" 2>&1 | grep -v '^$' | tail -5; then
    ok "$label synced"
  else
    warn "$label sync exited non-zero (check $LOG_FILE)"
  fi
}

check_remote() {
  local remote="$1"
  rclone listremotes 2>/dev/null | grep -q "^${remote}:$"
}

# ── Google Drive sync ─────────────────────────────────────────────────────────
say "=== Google Drive ==="
if check_remote gdrive; then
  rclone_sync "$JOBS_VAULT"  "gdrive:ObsidianJobs"   "Jobs vault → GDrive"
  rclone_sync "$ANTHR_VAULT" "gdrive:AnthropicData"  "Anthropic data → GDrive"
else
  warn "gdrive remote not configured — run: setup/cloud-backup/install.sh"
fi

# ── iCloud WebDAV sync ────────────────────────────────────────────────────────
say "=== iCloud ==="
if check_remote icloud; then
  rclone_sync "$JOBS_VAULT"  "$ICLOUD_JOBS_DEST"   "Jobs vault → iCloud"
  rclone_sync "$ANTHR_VAULT" "$ICLOUD_ANTHR_DEST"  "Anthropic data → iCloud"
else
  warn "icloud remote not configured — run: setup/cloud-backup/install.sh"
fi

say "Sync complete. Full log: $LOG_FILE"
