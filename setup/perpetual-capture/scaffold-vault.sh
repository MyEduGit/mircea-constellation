#!/usr/bin/env bash
# scaffold-vault.sh — Create the UrantiPedia Obsidian vault structure.
# Idempotent — safe to re-run. Fails loudly on permission errors.
set -euo pipefail

VAULT="${OBSIDIAN_URANTIPEDIA_VAULT:-${HOME}/Obsidian/UrantiPedia}"

say()  { printf '\033[1;36m[scaffold]\033[0m %s\n' "$*"; }
ok()   { printf '\033[1;32m  [ok]\033[0m %s\n' "$*"; }
fail() { printf '\033[1;31m  [FAIL]\033[0m %s\n' "$*" >&2; exit 1; }

say "Scaffolding vault at $VAULT"

# Fail loudly if parent is not writable
PARENT="$(dirname "$VAULT")"
[ -w "$PARENT" ] || fail "Cannot write to $PARENT — check permissions"

dirs=(
  "00_Inbox/AI_Captures"
  "00_Inbox/Claude"
  "00_Inbox/ChatGPT"
  "00_Inbox/Telegram"
  "00_Inbox/OpenClaw"
  "00_Inbox/NemoClaw"
  "00_Inbox/n8n"
  "00_Inbox/Terminal"
  "00_Inbox/Proof"
  "01_System"
  "02_Projects"
  "03_Workflows"
  "04_Backups_Index"
  "99_Archive"
)

for d in "${dirs[@]}"; do
  mkdir -p "$VAULT/$d"
  ok "mkdir $d"
done

# .obsidian config stub (prevents Obsidian from prompting on first open)
mkdir -p "$VAULT/.obsidian"
if [ ! -f "$VAULT/.obsidian/app.json" ]; then
  echo '{"legacyEditor":false,"livePreview":true}' > "$VAULT/.obsidian/app.json"
  ok ".obsidian/app.json"
fi

# Master index stub
INDEX="$VAULT/04_Backups_Index/PERPETUAL_CAPTURE_INDEX.md"
if [ ! -f "$INDEX" ]; then
  cat > "$INDEX" <<'EOF'
---
type: master-index
vault: UrantiPedia
---

# Perpetual Capture — Master Index

Auto-updated by `capture.py`. Do not edit manually.

## Daily Indexes
<!-- AUTO-DAILY-INDEX -->

## Source Stats
<!-- AUTO-STATS -->
EOF
  ok "04_Backups_Index/PERPETUAL_CAPTURE_INDEX.md"
fi

say "Vault scaffold complete: $VAULT"
# Proof
echo ""
echo "=== PROOF ==="
find "$VAULT" -maxdepth 3 -type d | sort
echo "============="
