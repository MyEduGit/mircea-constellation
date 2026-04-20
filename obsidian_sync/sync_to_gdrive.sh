#!/usr/bin/env bash
# Mirror the Obsidian Claude-Archive folder to Google Drive via rclone.
#
# Prereq: `brew install rclone` and `rclone config` to create a remote named
# "gdrive" (or override via GDRIVE_REMOTE).
#
# The vault itself is already in iCloud; this script adds a second redundant
# copy on Google Drive so you have Apple + Google backups per the requirement.
#
# Environment variables:
#   VAULT_CLAUDE_ARCHIVE   source folder (Obsidian vault Claude-Archive root)
#   GDRIVE_REMOTE          rclone destination, e.g. "gdrive:Claude-Archive"

set -euo pipefail

SOURCE="${VAULT_CLAUDE_ARCHIVE:-$HOME/Library/Mobile Documents/iCloud~md~obsidian/Documents/Urantia-Vault/Claude-Archive}"
DEST="${GDRIVE_REMOTE:-gdrive:Claude-Archive}"

if ! command -v rclone >/dev/null 2>&1; then
  echo "rclone not installed. Run: brew install rclone && rclone config" >&2
  exit 1
fi

if [ ! -d "${SOURCE}" ]; then
  echo "source folder not found: ${SOURCE}" >&2
  exit 1
fi

# One-way mirror: local → Google Drive. Files deleted locally stay on gdrive
# (no --delete-* flag) so a bad local delete never destroys the remote backup.
rclone copy "${SOURCE}" "${DEST}" \
  --transfers 4 \
  --checkers 8 \
  --skip-links \
  --exclude ".DS_Store" \
  --exclude ".obsidian/**" \
  --exclude ".trash/**" \
  --log-level INFO
