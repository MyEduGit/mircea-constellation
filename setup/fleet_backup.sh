#!/usr/bin/env bash
# ================================================================
# OpenClaw Fleet Backup
# Install on server:  run deploy_hardening.sh
# Schedule (auto):    deploy_hardening.sh installs cron entry
# Manual run:         bash ~/openclaw-backup.sh
# ================================================================
set -uo pipefail

CYAN='\033[0;36m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; RED='\033[0;31m'; NC='\033[0m'
ok()   { echo -e "${GREEN}✓${NC} $*"; }
warn() { echo -e "${YELLOW}⚠${NC}  $*"; }
err()  { echo -e "${RED}✗${NC} $*"; exit 1; }

BACKUP_ROOT="$HOME/openclaw-backups"
DATE_TAG=$(date +%Y-%m-%d)
BACKUP_DIR="$BACKUP_ROOT/$DATE_TAG"
ARCHIVE="$BACKUP_ROOT/openclaw-${DATE_TAG}.tar.gz"

mkdir -p "$BACKUP_DIR"

echo "[$(date '+%Y-%m-%d %H:%M:%S')] Starting OpenClaw backup..."

# Workspace, memories, skills
for SRC in ~/.openclaw/workspace ~/.openclaw/memories ~/.openclaw/skills; do
  if [[ -d "$SRC" ]]; then
    cp -r "$SRC" "$BACKUP_DIR/" 2>/dev/null && ok "Copied $SRC"
  fi
done

# Config — redact secrets
if [[ -f ~/.openclaw/config.json ]]; then
  python3 - << 'PYEOF'
import json, re, sys, os, pathlib
src = pathlib.Path.home() / ".openclaw" / "config.json"
dst = pathlib.Path(os.environ.get("BACKUP_DIR", "/tmp")) / "config.json"
try:
    with open(src) as f:
        raw = f.read()
    # Redact known secret fields
    raw = re.sub(r'("apiKey"\s*:\s*)"[^"]+"', r'\1"REDACTED"', raw)
    raw = re.sub(r'("token"\s*:\s*)"[^"]+"', r'\1"REDACTED"', raw)
    raw = re.sub(r'("botToken"\s*:\s*)"[^"]+"', r'\1"REDACTED"', raw)
    with open(dst, "w") as f:
        f.write(raw)
    print(f"\033[0;32m✓\033[0m Config backed up (secrets redacted)")
except Exception as e:
    print(f"\033[1;33m⚠\033[0m  Config backup failed: {e}")
PYEOF
fi

# Archive
tar -czf "$ARCHIVE" -C "$BACKUP_ROOT" "$DATE_TAG" 2>/dev/null \
  && ok "Archive: $ARCHIVE" \
  || warn "Archive creation failed"

# Clean up staging dir
rm -rf "$BACKUP_DIR"

# Keep last 30 backups
ls -1t "$BACKUP_ROOT"/*.tar.gz 2>/dev/null | tail -n +31 | xargs rm -f 2>/dev/null || true

echo "[$(date '+%Y-%m-%d %H:%M:%S')] Backup complete: $ARCHIVE"
ls -lh "$ARCHIVE" 2>/dev/null || true
