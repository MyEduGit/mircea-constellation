#!/usr/bin/env bash
# SessionEnd hook for Claude Code.
#
# When a Claude Code session ends, this script harvests the just-closed
# transcript into the Obsidian vault and (optionally) fires a Google Drive
# mirror via rclone.
#
# Install by adding to ~/.claude/settings.json:
#
#   {
#     "hooks": {
#       "SessionEnd": [
#         {
#           "hooks": [
#             { "type": "command", "command": "/absolute/path/to/session_end_hook.sh" }
#           ]
#         }
#       ]
#     }
#   }
#
# Environment variables (override the defaults below):
#   OBSIDIAN_CLAUDE_CODE_DIR  target folder inside the vault
#   OBSIDIAN_SYNC_REPO        path to this repo (so we can find the .py script)
#   GDRIVE_REMOTE             rclone remote name:path (empty disables gdrive sync)

set -euo pipefail

REPO="${OBSIDIAN_SYNC_REPO:-$HOME/mircea-constellation}"
TARGET="${OBSIDIAN_CLAUDE_CODE_DIR:-$HOME/Library/Mobile Documents/iCloud~md~obsidian/Documents/Urantia-Vault/Claude-Archive/claude-code}"
GDRIVE_REMOTE="${GDRIVE_REMOTE:-}"

LOG="${HOME}/.claude/session_end_hook.log"

{
  echo "=== $(date -u +%FT%TZ) SessionEnd ==="
  python3 "${REPO}/obsidian_sync/export_claude_code.py" "${TARGET}" --since "$(date -u -v-1d +%Y-%m-%d 2>/dev/null || date -u -d '1 day ago' +%Y-%m-%d)" || true
  if [ -n "${GDRIVE_REMOTE}" ]; then
    "${REPO}/obsidian_sync/sync_to_gdrive.sh" || true
  fi
} >> "${LOG}" 2>&1
