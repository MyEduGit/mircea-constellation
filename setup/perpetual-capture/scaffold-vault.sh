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

# Dashboard — seed from repo if available, else write inline stub
DASHBOARD="$VAULT/DASHBOARD.md"
if [ ! -f "$DASHBOARD" ]; then
  REPO_DASH="$(cd "$(dirname "$0")/../.." && pwd)/vault/DASHBOARD.md"
  if [ -f "$REPO_DASH" ]; then
    cp "$REPO_DASH" "$DASHBOARD"
    ok "DASHBOARD.md (seeded from repo)"
  else
    cat > "$DASHBOARD" <<'EOF'
---
cssClasses: [dashboard, wide-page]
type: dashboard
vault: UrantiPedia
updated_at: —
total_captures: 0
---

# UrantiPedia — Mission Control

Auto-updated by `capture.py`. Run it to populate stats.

## System Status
<!-- AUTO-STATUS-START -->
| Field | Value |
|:---|:---|
| Last capture run | — |
| Total .md files | — |
<!-- AUTO-STATUS-END -->

## Source Health
<!-- AUTO-SOURCES-START -->
| Source | Inbox Folder | Files | Last Captured |
|:---|:---|---:|:---|
<!-- AUTO-SOURCES-END -->

## Recent Captures
<!-- AUTO-RECENT-START -->
_No captures recorded yet._
<!-- AUTO-RECENT-END -->
EOF
    ok "DASHBOARD.md (stub created)"
  fi
fi

# System map stub
mkdir -p "$VAULT/01_System"
SYSMAP="$VAULT/01_System/SYSTEM_MAP.md"
if [ ! -f "$SYSMAP" ]; then
  REPO_MAP="$(cd "$(dirname "$0")/../.." && pwd)/vault/01_System/SYSTEM_MAP.md"
  if [ -f "$REPO_MAP" ]; then
    cp "$REPO_MAP" "$SYSMAP"
    ok "01_System/SYSTEM_MAP.md (seeded from repo)"
  fi
fi

say "Vault scaffold complete: $VAULT"
# Proof
echo ""
echo "=== PROOF ==="
find "$VAULT" -maxdepth 3 -type d | sort
echo "============="
