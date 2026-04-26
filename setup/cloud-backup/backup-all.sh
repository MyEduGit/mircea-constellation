#!/usr/bin/env bash
# backup-all.sh — Master cloud backup orchestrator.
#
# Pipeline:
#   1. Export Anthropic/Claude data → Obsidian Anthropic-Data vault
#   2. Sync both Obsidian vaults → Google Drive + iCloud (via rclone)
#   3. Upload/update job.md files as Google Docs
#
# Run automatically via Stop hook or manually after any Claude session.
# Idempotent — only transfers changed content.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LOG_DIR="${HOME}/.cloud-backup/logs"
LOG_FILE="${LOG_DIR}/backup-all-$(date +%Y-%m-%d_%H%M%S).log"

mkdir -p "$LOG_DIR"

say()  { printf '\033[1;36m[backup-all]\033[0m %s\n' "$*" | tee -a "$LOG_FILE"; }
ok()   { printf '\033[1;32m  [ok]\033[0m %s\n' "$*" | tee -a "$LOG_FILE"; }
warn() { printf '\033[1;33m  [warn]\033[0m %s\n' "$*" | tee -a "$LOG_FILE"; }
err()  { printf '\033[1;31m  [err]\033[0m %s\n' "$*" | tee -a "$LOG_FILE" >&2; }

say "Cloud backup started: $(date -u +%Y-%m-%dT%H:%M:%SZ)"

# ── Step 1: Export Anthropic/Claude data to Obsidian vault ────────────────────
say "Step 1/3 — Export Anthropic data to Obsidian..."
if command -v python3 &>/dev/null; then
  if python3 "$SCRIPT_DIR/export-anthropic.py" 2>&1 | tee -a "$LOG_FILE"; then
    ok "Anthropic export complete"
  else
    warn "Anthropic export had errors (non-fatal, continuing)"
  fi
else
  warn "python3 not found — skipping Anthropic transcript export"
fi

# ── Step 2: Sync Obsidian vaults → Google Drive + iCloud ─────────────────────
say "Step 2/3 — Syncing Obsidian vaults to cloud storage..."
if command -v rclone &>/dev/null; then
  if bash "$SCRIPT_DIR/sync-obsidian.sh" 2>&1 | tee -a "$LOG_FILE"; then
    ok "rclone sync complete"
  else
    warn "rclone sync had errors (check $LOG_FILE)"
  fi
else
  warn "rclone not found — run: setup/cloud-backup/install.sh"
fi

# ── Step 3: Upload/update job.md files as Google Docs ─────────────────────────
say "Step 3/3 — Uploading to Google Docs..."
if command -v python3 &>/dev/null; then
  if python3 "$SCRIPT_DIR/upload-to-gdocs.py" 2>&1 | tee -a "$LOG_FILE"; then
    ok "Google Docs upload complete"
  else
    warn "Google Docs upload had errors (non-fatal, check $LOG_FILE)"
  fi
else
  warn "python3 not found — skipping Google Docs upload"
fi

say "Cloud backup finished: $(date -u +%Y-%m-%dT%H:%M:%SZ)"
say "Log: $LOG_FILE"
