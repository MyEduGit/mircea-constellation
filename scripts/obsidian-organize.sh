#!/usr/bin/env bash
# obsidian-organize.sh — move every registered Obsidian vault into its
# canonical location based on detected sync method.
#
# Rules (matching Obsidian's own guidance for mac):
#   iCloud-intended vaults      -> ~/Library/Mobile Documents/iCloud~md~obsidian/Documents/<Name>
#   git / local / Obsidian Sync -> ~/ObsidianVaults/<Name>
#
# Vault *names* (folder basenames) are preserved, so "Actions for Obsidian"
# keeps working — that app references vaults by name, not path.
#
# Usage:
#   bash scripts/obsidian-organize.sh --dry-run   # default; prints plan only
#   bash scripts/obsidian-organize.sh --apply     # performs moves
#
# Safety:
#   - refuses to run --apply while Obsidian.app is open
#   - refuses to overwrite an existing destination
#   - does not mutate obsidian.json; instead prints the obsidian:// URL for
#     each moved vault so you can re-register them with one click

set -euo pipefail

MODE="${1:---dry-run}"
case "$MODE" in
  --dry-run|--apply) ;;
  *) echo "Usage: $0 [--dry-run|--apply]" >&2; exit 2 ;;
esac

OBSIDIAN_JSON="$HOME/Library/Application Support/obsidian/obsidian.json"
LOCAL_ROOT="$HOME/ObsidianVaults"
ICLOUD_ROOT="$HOME/Library/Mobile Documents/iCloud~md~obsidian/Documents"

command -v jq >/dev/null 2>&1 || {
  echo "jq is required. Install with: brew install jq" >&2
  exit 1
}
[[ -f "$OBSIDIAN_JSON" ]] || {
  echo "No obsidian.json at $OBSIDIAN_JSON — has Obsidian ever opened a vault on this Mac?" >&2
  exit 1
}

if [[ "$MODE" == "--apply" ]] && pgrep -xq Obsidian; then
  echo "ERROR: Obsidian is running. Quit it (Cmd+Q) before --apply." >&2
  exit 1
fi

classify() {
  local path="$1"
  [[ "$path" == *"iCloud~md~obsidian"* ]] && { echo "icloud"; return; }
  [[ -d "$path/.git" ]]                   && { echo "git"; return; }
  [[ -d "$path/.obsidian/sync" ]]         && { echo "obsidian-sync"; return; }
  echo "local"
}

canonical_target() {
  local name="$1" method="$2"
  case "$method" in
    icloud) printf '%s/%s\n' "$ICLOUD_ROOT" "$name" ;;
    *)      printf '%s/%s\n' "$LOCAL_ROOT"  "$name" ;;
  esac
}

printf 'Mode: %s\n' "$MODE"
printf 'Local root:  %s\n' "$LOCAL_ROOT"
printf 'iCloud root: %s\n\n' "$ICLOUD_ROOT"

moves=0
skips=0
oks=0

while IFS= read -r path; do
  [[ -z "$path" ]] && continue
  if [[ ! -d "$path" ]]; then
    printf 'SKIP (missing): %s\n' "$path"
    skips=$((skips+1))
    continue
  fi
  name="$(basename "$path")"
  method="$(classify "$path")"
  dst="$(canonical_target "$name" "$method")"

  printf 'Vault: %s  (method: %s)\n' "$name" "$method"

  if [[ "$path" == "$dst" ]]; then
    printf '  OK — already at canonical path\n'
    oks=$((oks+1))
    continue
  fi
  if [[ -e "$dst" ]]; then
    printf '  SKIP — destination already exists: %s\n' "$dst"
    skips=$((skips+1))
    continue
  fi

  printf '  FROM: %s\n' "$path"
  printf '  TO:   %s\n' "$dst"

  if [[ "$MODE" == "--apply" ]]; then
    mkdir -p "$(dirname "$dst")"
    mv "$path" "$dst"
    encoded="$(jq -rn --arg s "$dst" '$s|@uri')"
    printf '  moved. re-register in Obsidian by running:\n'
    printf '    open "obsidian://open?path=%s"\n' "$encoded"
  else
    printf '  (dry-run — no change made)\n'
  fi
  moves=$((moves+1))
done < <(jq -r '.vaults // {} | to_entries[] | .value.path' "$OBSIDIAN_JSON")

printf '\nSummary: %d to move, %d skipped, %d already correct.\n' "$moves" "$skips" "$oks"

if [[ "$MODE" == "--dry-run" && "$moves" -gt 0 ]]; then
  printf '\nRe-run with --apply to execute. Quit Obsidian first.\n'
elif [[ "$MODE" == "--apply" && "$moves" -gt 0 ]]; then
  printf '\nDone. Re-open Obsidian, use the obsidian:// URLs above to re-register\n'
  printf 'each moved vault, then re-scan your "Actions for Obsidian" shortcuts so\n'
  printf 'they pick up the current vault IDs.\n'
fi
