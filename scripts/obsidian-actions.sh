#!/usr/bin/env bash
# obsidian-actions.sh — CLI interface to Obsidian via Actions URI plugin.
#
# Wraps obsidian://actions-uri/* URL schemes so constellation scripts,
# cron jobs, and Apple Shortcuts can drive Obsidian from the command line.
#
# Requirements:
#   - macOS (uses `open` to launch URL schemes)
#   - Obsidian running
#   - Actions URI community plugin installed and enabled in each target vault
#
# Usage:
#   bash scripts/obsidian-actions.sh <command> [options]
#
# Commands:
#   open-vault   <vault>                Open a vault
#   daily        <vault>                Open today's daily note (creates if needed)
#   note-create  <vault> <path> [body]  Create a new note
#   note-open    <vault> <path>         Open an existing note
#   note-append  <vault> <path> <text>  Append text to an existing note
#   note-prepend <vault> <path> <text>  Prepend text to an existing note
#   search       <vault> <query>        Search all notes
#   command      <vault> <command-id>   Execute an Obsidian command by ID
#   capture      <vault> <text>         Quick-capture: append to today's daily note
#   tags         <vault>                List all tags in the vault
#   list-vaults                         List registered vaults from obsidian.json
#   test         <vault>                Smoke-test Actions URI on a vault

set -euo pipefail

OBSIDIAN_JSON="$HOME/Library/Application Support/obsidian/obsidian.json"

uri_encode() {
  jq -rn --arg s "$1" '$s|@uri'
}

fire_uri() {
  local uri="$1"
  if ! pgrep -xq Obsidian; then
    echo "Starting Obsidian..." >&2
    open -a Obsidian
    sleep 2
  fi
  open "$uri"
}

actions_uri() {
  local route="$1"; shift
  local vault_encoded
  vault_encoded="$(uri_encode "$1")"; shift
  local uri="obsidian://actions-uri/${route}?vault=${vault_encoded}"
  while (( $# )); do
    local key="$1" val
    val="$(uri_encode "$2")"
    uri="${uri}&${key}=${val}"
    shift 2
  done
  fire_uri "$uri"
}

cmd_open_vault() {
  local vault="${1:?Usage: open-vault <vault-name>}"
  actions_uri "vault/open" "$vault"
  echo "Opened vault: $vault"
}

cmd_daily() {
  local vault="${1:?Usage: daily <vault-name>}"
  actions_uri "daily-note/open-current" "$vault"
  echo "Opened daily note in: $vault"
}

cmd_note_create() {
  local vault="${1:?Usage: note-create <vault> <path> [body]}"
  local path="${2:?Usage: note-create <vault> <path> [body]}"
  local body="${3:-}"
  if [[ -n "$body" ]]; then
    actions_uri "note/create" "$vault" "file" "$path" "content" "$body" "if-exists" "skip"
  else
    actions_uri "note/create" "$vault" "file" "$path" "if-exists" "skip"
  fi
  echo "Created note: $path in $vault"
}

cmd_note_open() {
  local vault="${1:?Usage: note-open <vault> <path>}"
  local path="${2:?Usage: note-open <vault> <path>}"
  actions_uri "note/open" "$vault" "file" "$path"
  echo "Opened note: $path in $vault"
}

cmd_note_append() {
  local vault="${1:?Usage: note-append <vault> <path> <text>}"
  local path="${2:?Usage: note-append <vault> <path> <text>}"
  local text="${3:?Usage: note-append <vault> <path> <text>}"
  actions_uri "note/append" "$vault" "file" "$path" "content" "$text" "ensure-newline" "true"
  echo "Appended to: $path in $vault"
}

cmd_note_prepend() {
  local vault="${1:?Usage: note-prepend <vault> <path> <text>}"
  local path="${2:?Usage: note-prepend <vault> <path> <text>}"
  local text="${3:?Usage: note-prepend <vault> <path> <text>}"
  actions_uri "note/prepend" "$vault" "file" "$path" "content" "$text" "ensure-newline" "true"
  echo "Prepended to: $path in $vault"
}

cmd_search() {
  local vault="${1:?Usage: search <vault> <query>}"
  local query="${2:?Usage: search <vault> <query>}"
  actions_uri "search/all-notes" "$vault" "search-term" "$query"
  echo "Searching '$query' in: $vault"
}

cmd_command() {
  local vault="${1:?Usage: command <vault> <command-id>}"
  local command_id="${2:?Usage: command <vault> <command-id>}"
  actions_uri "command" "$vault" "command-id" "$command_id"
  echo "Executed command: $command_id in $vault"
}

cmd_capture() {
  local vault="${1:?Usage: capture <vault> <text>}"
  local text="${2:?Usage: capture <vault> <text>}"
  local timestamp
  timestamp="$(date '+%Y-%m-%d %H:%M')"
  local entry=$'\n'"- **${timestamp}** — ${text}"
  actions_uri "daily-note/append" "$vault" "content" "$entry" "ensure-newline" "true" "create-if-not-found" "true"
  echo "Captured to daily note in: $vault"
}

cmd_tags() {
  local vault="${1:?Usage: tags <vault>}"
  actions_uri "tags/list" "$vault"
  echo "Listing tags in: $vault"
}

cmd_list_vaults() {
  if [[ ! -f "$OBSIDIAN_JSON" ]]; then
    echo "No obsidian.json found at $OBSIDIAN_JSON" >&2
    exit 1
  fi
  if command -v jq >/dev/null 2>&1; then
    jq -r '.vaults // {} | to_entries[] | "\(.value.path | split("/") | last)\t\(.value.path)"' "$OBSIDIAN_JSON" \
    | while IFS=$'\t' read -r name path; do
        if [[ -d "$path" ]]; then
          printf '  %-30s %s\n' "$name" "$path"
        else
          printf '  %-30s %s (MISSING)\n' "$name" "$path"
        fi
      done
  else
    cat "$OBSIDIAN_JSON"
  fi
}

cmd_test() {
  local vault="${1:?Usage: test <vault-name>}"
  echo "Testing Actions URI on vault: $vault"
  echo ""

  echo "1. Listing vault info..."
  actions_uri "vault/info" "$vault"
  sleep 1

  echo "2. Listing folders..."
  actions_uri "vault/list-all-folders" "$vault"
  sleep 1

  echo "3. Opening daily note..."
  actions_uri "daily-note/open-current" "$vault"
  sleep 1

  echo ""
  echo "If Obsidian responded to all three, Actions URI is working."
  echo "If nothing happened, ensure the Actions URI plugin is installed and enabled."
}

usage() {
  sed -n '/^# Commands:/,/^$/p' "$0" | sed 's/^#//' >&2
  exit 2
}

case "${1:-}" in
  open-vault)   shift; cmd_open_vault "$@" ;;
  daily)        shift; cmd_daily "$@" ;;
  note-create)  shift; cmd_note_create "$@" ;;
  note-open)    shift; cmd_note_open "$@" ;;
  note-append)  shift; cmd_note_append "$@" ;;
  note-prepend) shift; cmd_note_prepend "$@" ;;
  search)       shift; cmd_search "$@" ;;
  command)      shift; cmd_command "$@" ;;
  capture)      shift; cmd_capture "$@" ;;
  tags)         shift; cmd_tags "$@" ;;
  list-vaults)  shift; cmd_list_vaults ;;
  test)         shift; cmd_test "$@" ;;
  *)            usage ;;
esac
