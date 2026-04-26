#!/usr/bin/env bash
# install.sh — Cloud Backup installer
# Installs rclone, Python Google API client, and scaffolds ~/.cloud-backup/.env
# Idempotent — safe to re-run.
set -euo pipefail

CRED_FILE="${HOME}/.cloud-backup/.env"

say()  { printf '\033[1;36m[cloud-backup]\033[0m %s\n' "$*"; }
ok()   { printf '\033[1;32m  [ok]\033[0m %s\n' "$*"; }
warn() { printf '\033[1;33m  [warn]\033[0m %s\n' "$*"; }

# ── rclone ────────────────────────────────────────────────────────────────────
say "Checking rclone..."
if ! command -v rclone &>/dev/null; then
  say "Installing rclone..."
  if [[ "$(uname)" == "Darwin" ]] && command -v brew &>/dev/null; then
    brew install rclone
  else
    curl -fsSL https://rclone.org/install.sh | sudo bash
  fi
  ok "rclone installed: $(rclone version | head -1)"
else
  ok "rclone present: $(rclone version | head -1)"
fi

# ── Python Google API client ──────────────────────────────────────────────────
say "Checking Python Google API client..."
if command -v pip3 &>/dev/null; then
  pip3 install --quiet --user \
    google-auth \
    google-auth-httplib2 \
    google-api-python-client 2>&1 | grep -v '^$' | tail -3 || true
  ok "google-api-python-client ready"
else
  warn "pip3 not found — Google Docs upload will be unavailable"
fi

# ── Credential directory ──────────────────────────────────────────────────────
mkdir -p "${HOME}/.cloud-backup"
chmod 700 "${HOME}/.cloud-backup"

if [ ! -f "$CRED_FILE" ]; then
  say "Creating credential template at $CRED_FILE"
  cat > "$CRED_FILE" <<'ENVEOF'
# Cloud Backup Credentials — DO NOT COMMIT
# Fill in these values, then re-run install.sh to configure rclone remotes.

# ── Google Drive ──────────────────────────────────────────────────────────────
# Option A: Service Account JSON (preferred for servers)
GDRIVE_SA_FILE=~/.cloud-backup/gdrive-service-account.json
# Option B: OAuth (leave SA blank; run 'rclone config reconnect gdrive:' after install)
GDRIVE_CLIENT_ID=
GDRIVE_CLIENT_SECRET=
# Drive folder ID for Obsidian backup (leave blank = root; get ID from Drive URL)
GDRIVE_OBSIDIAN_FOLDER_ID=
# Drive folder ID where job.md files become Google Docs
GDOCS_JOBS_FOLDER_ID=

# ── iCloud WebDAV ─────────────────────────────────────────────────────────────
# Requires an app-specific password: https://appleid.apple.com → Security
APPLE_ID=
APPLE_APP_PASSWORD=
# Find your DAV shard by inspecting icloud.com traffic on login, e.g. p62-dav.icloud.com
ICLOUD_DAV_URL=https://p62-dav.icloud.com
# Destination path inside iCloud Drive
ICLOUD_OBSIDIAN_PATH=Documents/Obsidian/Jobs
ICLOUD_ANTHROPIC_PATH=Documents/Obsidian/Anthropic-Data

# ── Vault paths ───────────────────────────────────────────────────────────────
OBSIDIAN_JOBS_VAULT=${HOME}/Documents/Obsidian/Jobs
OBSIDIAN_ANTHROPIC_VAULT=${HOME}/Documents/Obsidian/Anthropic-Data
ENVEOF
  chmod 600 "$CRED_FILE"
  warn "Fill in $CRED_FILE then re-run this script to configure remotes."
  exit 0
fi

# ── Source credentials ────────────────────────────────────────────────────────
# shellcheck disable=SC1090
set +u; source "$CRED_FILE"; set -u

# ── rclone Google Drive remote ────────────────────────────────────────────────
say "Configuring rclone gdrive remote..."
if rclone listremotes 2>/dev/null | grep -q '^gdrive:$'; then
  ok "gdrive remote already configured"
elif [ -n "${GDRIVE_SA_FILE:-}" ] && [ -f "${GDRIVE_SA_FILE/#\~/$HOME}" ]; then
  rclone config create gdrive drive \
    scope=drive \
    service_account_file="${GDRIVE_SA_FILE/#\~/$HOME}" \
    --non-interactive >/dev/null
  ok "gdrive remote configured (service account)"
elif [ -n "${GDRIVE_CLIENT_ID:-}" ]; then
  rclone config create gdrive drive \
    client_id="$GDRIVE_CLIENT_ID" \
    client_secret="$GDRIVE_CLIENT_SECRET" \
    scope=drive \
    --non-interactive >/dev/null
  warn "gdrive OAuth configured — run: rclone config reconnect gdrive:"
else
  warn "No Google Drive credentials found — configure manually: rclone config"
fi

# ── rclone iCloud WebDAV remote ───────────────────────────────────────────────
say "Configuring rclone icloud remote..."
if rclone listremotes 2>/dev/null | grep -q '^icloud:$'; then
  ok "icloud remote already configured"
elif [ -n "${APPLE_ID:-}" ] && [ -n "${APPLE_APP_PASSWORD:-}" ]; then
  OBSCURED_PASS="$(rclone obscure "$APPLE_APP_PASSWORD")"
  rclone config create icloud webdav \
    url="${ICLOUD_DAV_URL:-https://p62-dav.icloud.com}" \
    vendor=other \
    user="$APPLE_ID" \
    pass="$OBSCURED_PASS" \
    --non-interactive >/dev/null
  ok "icloud WebDAV remote configured"
else
  warn "No iCloud credentials found — fill APPLE_ID + APPLE_APP_PASSWORD in $CRED_FILE"
fi

say "Install complete. Run: setup/cloud-backup/backup-all.sh"
