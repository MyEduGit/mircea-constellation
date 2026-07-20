#!/usr/bin/env bash
# obsidian-shortcuts-export.sh — Generate macOS/iOS Shortcuts URLs for
# common Obsidian actions via the Actions URI plugin.
#
# Outputs a list of obsidian:// URLs you can:
#   - Click to test immediately
#   - Add to Apple Shortcuts as "Open URLs" actions
#   - Bind to Raycast/Alfred hotkeys
#   - Wire into "Actions for Obsidian" app
#
# Usage:
#   bash scripts/obsidian-shortcuts-export.sh [vault-name]
#   bash scripts/obsidian-shortcuts-export.sh PhD-Triune-Monism
#   bash scripts/obsidian-shortcuts-export.sh                  # all vaults

set -euo pipefail

OBSIDIAN_JSON="$HOME/Library/Application Support/obsidian/obsidian.json"

uri_encode() {
  jq -rn --arg s "$1" '$s|@uri'
}

generate_shortcuts() {
  local vault="$1"
  local ve
  ve="$(uri_encode "$vault")"

  printf '\n══════════════════════════════════════════════════\n'
  printf '  VAULT: %s\n' "$vault"
  printf '══════════════════════════════════════════════════\n\n'

  printf '  %-25s %s\n' "Open Vault" \
    "obsidian://actions-uri/vault/open?vault=${ve}"
  printf '  %-25s %s\n' "Daily Note (open)" \
    "obsidian://actions-uri/daily-note/open-current?vault=${ve}"
  printf '  %-25s %s\n' "Daily Note (create)" \
    "obsidian://actions-uri/daily-note/create?vault=${ve}"
  printf '  %-25s %s\n' "List All Folders" \
    "obsidian://actions-uri/vault/list-all-folders?vault=${ve}"
  printf '  %-25s %s\n' "List All Tags" \
    "obsidian://actions-uri/tags/list?vault=${ve}"
  printf '  %-25s %s\n' "Search (replace QUERY)" \
    "obsidian://actions-uri/search/all-notes?vault=${ve}&search-term=QUERY"
  printf '  %-25s %s\n' "Quick Capture" \
    "obsidian://actions-uri/daily-note/append?vault=${ve}&content=CAPTURE_TEXT&ensure-newline=true&create-if-not-found=true"
  printf '  %-25s %s\n' "Open Graph View" \
    "obsidian://actions-uri/command?vault=${ve}&command-id=graph%3Aopen"
  printf '  %-25s %s\n' "Open Command Palette" \
    "obsidian://actions-uri/command?vault=${ve}&command-id=command-palette%3Aopen"
  printf '  %-25s %s\n' "Vault Info" \
    "obsidian://actions-uri/vault/info?vault=${ve}"
  printf '\n'

  printf '  Constellation integration:\n'
  printf '  %-25s %s\n' "Event bridge capture" \
    "echo 'vault=${vault}' > ~/.constellation/events/\$(date +%%s).event"
  printf '\n'
}

if [[ -n "${1:-}" ]]; then
  generate_shortcuts "$1"
else
  if [[ ! -f "$OBSIDIAN_JSON" ]]; then
    echo "No obsidian.json found. Provide a vault name: $0 <vault-name>" >&2
    exit 1
  fi
  command -v jq >/dev/null 2>&1 || { echo "jq required: brew install jq" >&2; exit 1; }

  printf 'Obsidian Actions URI — Shortcuts for all registered vaults\n'
  printf 'Generated: %s\n' "$(date)"

  jq -r '.vaults // {} | to_entries[] | .value.path' "$OBSIDIAN_JSON" \
  | while read -r path; do
      [[ -d "$path" ]] || continue
      generate_shortcuts "$(basename "$path")"
    done

  printf '\n══════════════════════════════════════════════════\n'
  printf '  SETUP REMINDER\n'
  printf '══════════════════════════════════════════════════\n'
  printf '  1. Install "Actions URI" plugin in each vault\n'
  printf '     (Settings → Community Plugins → Browse → "Actions URI")\n'
  printf '  2. Or run: bash setup/obsidian-actions-install.sh\n'
  printf '  3. Test with: obsidian-actions test <VaultName>\n'
  printf '\n'
fi
