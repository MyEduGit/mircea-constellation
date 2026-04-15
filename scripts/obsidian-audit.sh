#!/usr/bin/env bash
# obsidian-audit.sh — discover and classify every Obsidian vault on this Mac.
#
# Prints: registered vaults from obsidian.json, stray .obsidian dirs not in
# the registry, detected sync method per vault (git / obsidian-sync / iCloud
# / local), iCloud-evictability status of ~/Documents, and the canonical
# destination each vault should live at.
#
# Read-only. Safe to run any time. Run on macOS:
#   bash scripts/obsidian-audit.sh

set -euo pipefail

OBSIDIAN_JSON="$HOME/Library/Application Support/obsidian/obsidian.json"
LOCAL_ROOT="$HOME/ObsidianVaults"
ICLOUD_ROOT="$HOME/Library/Mobile Documents/iCloud~md~obsidian/Documents"

have_jq=1
command -v jq >/dev/null 2>&1 || have_jq=0

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

printf '=== Obsidian vault audit — %s ===\n\n' "$(date)"

# --- Registered vaults ---------------------------------------------------
printf '## Registered vaults (from obsidian.json)\n'
if [[ ! -f "$OBSIDIAN_JSON" ]]; then
  printf '  no registry found at %s\n' "$OBSIDIAN_JSON"
elif (( have_jq )); then
  jq -r '.vaults // {} | to_entries[] | "\(.value.path)\t\(.value.open // false)"' "$OBSIDIAN_JSON" \
  | while IFS=$'\t' read -r path open; do
      [[ -z "$path" ]] && continue
      name="$(basename "$path")"
      if [[ ! -d "$path" ]]; then
        printf '  - %-40s MISSING on disk (stale registry entry): %s\n' "$name" "$path"
        continue
      fi
      method="$(classify "$path")"
      target="$(canonical_target "$name" "$method")"
      printf '  - %s\n' "$name"
      printf '      path:   %s\n' "$path"
      printf '      open:   %s\n' "$open"
      printf '      method: %s\n' "$method"
      printf '      target: %s\n' "$target"
      if [[ "$path" == "$target" ]]; then
        printf '      status: OK (already at canonical path)\n'
      else
        printf '      status: NEEDS MOVE\n'
      fi
    done
else
  printf '  jq not installed — showing raw file. Install with: brew install jq\n\n'
  cat "$OBSIDIAN_JSON"
fi
printf '\n'

# --- Stray vaults --------------------------------------------------------
printf '## Stray .obsidian directories on disk (excluding ~/Library)\n'
mapfile -t strays < <(find "$HOME" -name ".obsidian" -type d 2>/dev/null | grep -v "/Library/" || true)
if (( ${#strays[@]} == 0 )); then
  printf '  (none)\n'
else
  # A stray is any vault whose parent dir is NOT in obsidian.json.
  registered=""
  if (( have_jq )) && [[ -f "$OBSIDIAN_JSON" ]]; then
    registered="$(jq -r '.vaults // {} | to_entries[] | .value.path' "$OBSIDIAN_JSON")"
  fi
  for dot in "${strays[@]}"; do
    vault="$(dirname "$dot")"
    if grep -Fxq "$vault" <<<"$registered"; then
      continue
    fi
    printf '  - unregistered: %s\n' "$vault"
  done
fi
printf '\n'

# --- iCloud Documents evictability --------------------------------------
printf '## iCloud status for ~/Documents\n'
if brctl status >/dev/null 2>&1 && brctl status 2>/dev/null | grep -qi "Documents"; then
  printf '  WARNING: iCloud Drive appears to sync ~/Documents.\n'
  printf '  Any vault under ~/Documents risks silent eviction when disk is low.\n'
  printf '  Move local/git vaults to %s instead.\n' "$LOCAL_ROOT"
else
  printf '  ~/Documents does not appear iCloud-synced (local vaults are safe there,\n'
  printf '  but %s is still the recommended canonical root).\n' "$LOCAL_ROOT"
fi
printf '\n'

printf 'Next step: review the moves listed as "NEEDS MOVE", then run:\n'
printf '  bash scripts/obsidian-organize.sh --dry-run   # preview\n'
printf '  bash scripts/obsidian-organize.sh --apply     # execute (quit Obsidian first)\n'
