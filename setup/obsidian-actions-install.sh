#!/usr/bin/env bash
# obsidian-actions-install.sh — Set up the Obsidian + Actions for Obsidian
# integration on macOS.
#
# What it does:
#   1. Verifies Obsidian is installed
#   2. Reads obsidian.json to discover all registered vaults
#   3. Installs the "Actions URI" community plugin into each vault
#   4. Creates a launchd agent for constellation → Obsidian event bridge
#   5. Wires the scripts/obsidian-actions.sh CLI into ~/bin
#
# Safe to re-run. Does not overwrite existing plugin config.
#
# Usage:  bash setup/obsidian-actions-install.sh

set -euo pipefail

REPO_DIR="$(cd "$(dirname "$0")/.." && pwd)"
OBSIDIAN_JSON="$HOME/Library/Application Support/obsidian/obsidian.json"
PLUGIN_ID="actions-uri"
PLUGIN_REPO="czottmann/obsidian-actions-uri"
BIN_DIR="$HOME/bin"

say()  { printf '\033[1;36m[obsidian-actions]\033[0m %s\n' "$*"; }
ok()   { printf '\033[1;32m  [ok]\033[0m %s\n' "$*"; }
warn() { printf '\033[1;33m  [warn]\033[0m %s\n' "$*"; }
err()  { printf '\033[1;31m  [err]\033[0m %s\n' "$*" >&2; }

# ── Step 0: Preflight ─────────────────────────────────────────────────────────
say "Preflight checks"

if [[ "$(uname)" != "Darwin" ]]; then
  err "This script is macOS-only (needs open(1) + launchd)."
  exit 1
fi

if ! command -v jq >/dev/null 2>&1; then
  err "jq is required. Install with: brew install jq"
  exit 1
fi

if [[ ! -d "/Applications/Obsidian.app" ]]; then
  err "Obsidian.app not found in /Applications. Install from https://obsidian.md"
  exit 1
fi
ok "Obsidian.app found"

if [[ ! -f "$OBSIDIAN_JSON" ]]; then
  err "No obsidian.json — open Obsidian and create at least one vault first."
  exit 1
fi
ok "obsidian.json found"

# ── Step 1: Discover vaults ──────────────────────────────────────────────────
say "Discovering vaults"

mapfile -t vault_paths < <(jq -r '.vaults // {} | to_entries[] | .value.path' "$OBSIDIAN_JSON")

if (( ${#vault_paths[@]} == 0 )); then
  err "No vaults registered in obsidian.json."
  exit 1
fi

for vp in "${vault_paths[@]}"; do
  name="$(basename "$vp")"
  if [[ -d "$vp" ]]; then
    ok "vault: $name ($vp)"
  else
    warn "vault MISSING on disk: $name ($vp)"
  fi
done

# ── Step 2: Install Actions URI plugin into each vault ───────────────────────
say "Installing Actions URI plugin"

LATEST_TAG=""
if command -v curl >/dev/null 2>&1; then
  LATEST_TAG="$(curl -sL "https://api.github.com/repos/$PLUGIN_REPO/releases/latest" \
    | jq -r '.tag_name // empty' 2>/dev/null || true)"
fi

for vp in "${vault_paths[@]}"; do
  [[ ! -d "$vp" ]] && continue
  name="$(basename "$vp")"
  plugin_dir="$vp/.obsidian/plugins/$PLUGIN_ID"

  if [[ -f "$plugin_dir/main.js" ]]; then
    ok "$name: Actions URI already installed"
    continue
  fi

  if [[ -z "$LATEST_TAG" ]]; then
    warn "$name: cannot fetch latest release — install Actions URI manually via Obsidian settings"
    continue
  fi

  say "  Downloading Actions URI $LATEST_TAG for $name..."
  mkdir -p "$plugin_dir"

  base_url="https://github.com/$PLUGIN_REPO/releases/download/$LATEST_TAG"
  for file in main.js manifest.json styles.css; do
    if curl -sL "$base_url/$file" -o "$plugin_dir/$file" 2>/dev/null; then
      true
    else
      warn "  Failed to download $file for $name"
    fi
  done

  if [[ -f "$plugin_dir/main.js" ]]; then
    ok "$name: Actions URI $LATEST_TAG installed"
    echo "  IMPORTANT: Open Obsidian → Settings → Community Plugins → Enable 'Actions URI'"
  else
    warn "$name: download failed — install manually via Obsidian Community Plugins browser"
    rm -rf "$plugin_dir" 2>/dev/null || true
  fi
done

# ── Step 3: Ensure the plugin is in Obsidian's enabled-plugins list ──────────
say "Checking plugin activation status"

for vp in "${vault_paths[@]}"; do
  [[ ! -d "$vp" ]] && continue
  name="$(basename "$vp")"
  community_plugins="$vp/.obsidian/community-plugins.json"

  if [[ ! -f "$community_plugins" ]]; then
    echo '[]' > "$community_plugins"
  fi

  if jq -e ". | index(\"$PLUGIN_ID\")" "$community_plugins" >/dev/null 2>&1; then
    ok "$name: Actions URI already in enabled list"
  else
    jq ". + [\"$PLUGIN_ID\"]" "$community_plugins" > "${community_plugins}.tmp" \
      && mv "${community_plugins}.tmp" "$community_plugins"
    ok "$name: Actions URI added to enabled list (restart Obsidian to activate)"
  fi
done

# ── Step 4: Wire CLI into ~/bin ──────────────────────────────────────────────
say "Wiring CLI"

mkdir -p "$BIN_DIR"
CLI_LINK="$BIN_DIR/obsidian-actions"
CLI_SRC="$REPO_DIR/scripts/obsidian-actions.sh"

if [[ -L "$CLI_LINK" || -f "$CLI_LINK" ]]; then
  rm "$CLI_LINK"
fi
ln -s "$CLI_SRC" "$CLI_LINK"
chmod +x "$CLI_SRC"
ok "Linked: $CLI_LINK → $CLI_SRC"

if ! echo "$PATH" | tr ':' '\n' | grep -qx "$BIN_DIR"; then
  warn "~/bin is not in your PATH. Add to your shell profile:"
  echo '  export PATH="$HOME/bin:$PATH"'
fi

# ── Step 5: Create launchd event bridge ──────────────────────────────────────
say "Setting up constellation event bridge"

BRIDGE_SCRIPT="$REPO_DIR/scripts/obsidian-event-bridge.sh"
PLIST_DIR="$HOME/Library/LaunchAgents"
PLIST_FILE="$PLIST_DIR/com.mircea.obsidian-event-bridge.plist"

mkdir -p "$PLIST_DIR"

if [[ ! -f "$BRIDGE_SCRIPT" ]]; then
  err "Event bridge script not found at $BRIDGE_SCRIPT — repo may be incomplete."
  exit 1
fi
chmod +x "$BRIDGE_SCRIPT"
ok "Event bridge script: $BRIDGE_SCRIPT"

cat > "$PLIST_FILE" <<PLIST_EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN"
  "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>Label</key>
  <string>com.mircea.obsidian-event-bridge</string>
  <key>ProgramArguments</key>
  <array>
    <string>/bin/bash</string>
    <string>${BRIDGE_SCRIPT}</string>
  </array>
  <key>WatchPaths</key>
  <array>
    <string>${HOME}/.constellation/events</string>
  </array>
  <key>StandardOutPath</key>
  <string>${HOME}/.constellation/logs/obsidian-bridge.log</string>
  <key>StandardErrorPath</key>
  <string>${HOME}/.constellation/logs/obsidian-bridge.log</string>
</dict>
</plist>
PLIST_EOF

mkdir -p "$HOME/.constellation/events" "$HOME/.constellation/logs"

launchctl unload "$PLIST_FILE" 2>/dev/null || true
launchctl load "$PLIST_FILE" 2>/dev/null || true
ok "LaunchAgent loaded: com.mircea.obsidian-event-bridge"
echo "  Bridge watches: ~/.constellation/events/*.event"

# ── Done ─────────────────────────────────────────────────────────────────────
say ""
say "Installation complete. Quick test:"
say "  obsidian-actions list-vaults"
say "  obsidian-actions test PhD-Triune-Monism"
say "  obsidian-actions capture PhD-Triune-Monism 'Test capture from CLI'"
say ""
say "Event bridge usage (from any script/bot/cron):"
say "  echo -e 'vault=PhD-Triune-Monism\ntext=Bot fleet check-in OK' > ~/.constellation/events/\$(date +%s).event"
