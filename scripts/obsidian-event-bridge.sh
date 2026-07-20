#!/usr/bin/env bash
# obsidian-event-bridge.sh — Watches for constellation events and routes
# them to Obsidian vaults via Actions URI.
#
# Monitored:
#   ~/.constellation/events/*.event  — drop an event file, it gets captured
#
# Each .event file should contain (one key=value per line):
#   vault=<VaultName>
#   text=<capture text>
#   [action=capture|note-create|note-append]
#   [path=<note path for note-create/note-append>]
#
# Processed files are moved to ~/.constellation/events/processed/
#
# Triggered by launchd WatchPaths — runs once per batch of new .event files.
#
# Usage:
#   bash scripts/obsidian-event-bridge.sh              # process pending events
#   bash scripts/obsidian-event-bridge.sh --emit \     # create a new event
#       vault=PhD-Triune-Monism text="Bot fleet OK"

set -euo pipefail

EVENTS_DIR="$HOME/.constellation/events"
PROCESSED_DIR="$EVENTS_DIR/processed"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
CLI="$SCRIPT_DIR/obsidian-actions.sh"

mkdir -p "$EVENTS_DIR" "$PROCESSED_DIR"

# --emit mode: create an event file from command-line args
if [[ "${1:-}" == "--emit" ]]; then
  shift
  event_file="$EVENTS_DIR/$(date +%s)-$$.event"
  for arg in "$@"; do
    echo "$arg"
  done > "$event_file"
  echo "Event created: $event_file"
  exit 0
fi

process_event() {
  local file="$1"
  local vault="" text="" action="capture" path=""

  while IFS='=' read -r key val; do
    key="$(echo "$key" | tr -d '[:space:]')"
    case "$key" in
      vault)  vault="$val" ;;
      text)   text="$val" ;;
      action) action="$val" ;;
      path)   path="$val" ;;
    esac
  done < "$file"

  if [[ -z "$vault" || -z "$text" ]]; then
    echo "[bridge] Malformed event file: $file" >&2
    mv "$file" "$PROCESSED_DIR/$(basename "$file").malformed"
    return
  fi

  case "$action" in
    capture)
      bash "$CLI" capture "$vault" "$text"
      ;;
    note-create)
      bash "$CLI" note-create "$vault" "${path:-00_Inbox/$(date +%Y-%m-%d)-event}" "$text"
      ;;
    note-append)
      bash "$CLI" note-append "$vault" "${path:?note-append requires path=}" "$text"
      ;;
    *)
      echo "[bridge] Unknown action: $action in $file" >&2
      ;;
  esac

  mv "$file" "$PROCESSED_DIR/"
  echo "[bridge] Processed: $(basename "$file")"
}

count=0
for f in "$EVENTS_DIR"/*.event; do
  [[ -f "$f" ]] || continue
  process_event "$f"
  count=$((count+1))
done

if (( count == 0 )); then
  echo "[bridge] No pending events in $EVENTS_DIR"
else
  echo "[bridge] Processed $count event(s)"
fi
