#!/usr/bin/env bash
set -u

echo "=== PRESERVATION QUICK AUDIT ==="
date '+%A, %d %B %Y — %H:%M:%S %Z'
echo

echo "1) Obsidian app:"
if [ -d "/Applications/Obsidian.app" ]; then
  echo "FOUND: /Applications/Obsidian.app"
else
  echo "MISSING: /Applications/Obsidian.app"
fi
echo

echo "2) Obsidian vault candidates:"
for p in \
  "$HOME/Obsidian/UrantiPedia" \
  "$HOME/Obsidian/Urantia-Vault" \
  "$HOME/Library/Mobile Documents/iCloud~md~obsidian/Documents/UrantiPedia" \
  "$HOME/Library/Mobile Documents/iCloud~md~obsidian/Documents/Urantia-Vault" \
  "$HOME/Library/Mobile Documents/com~apple~CloudDocs/Obsidian/UrantiPedia" \
  "$HOME/Library/Mobile Documents/com~apple~CloudDocs/Obsidian/Urantia-Vault"
do
  if [ -d "$p" ]; then
    echo "FOUND: $p"
  else
    echo "MISSING: $p"
  fi
done
echo

echo "3) iCloud backup folder:"
IC="$HOME/Library/Mobile Documents/com~apple~CloudDocs/UOS_Backups"
mkdir -p "$IC"
echo "FOUND/CREATED: $IC"
echo

echo "STATUS: QUICK_AUDIT_COMPLETE"
