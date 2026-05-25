#!/usr/bin/env bash
# Install Claude Code VS Code extension on iMac M4 — NemoClaw
set -euo pipefail

echo "=== Claude Code VS Code Extension Installer ==="
echo "Target: iMac M4 — NemoClaw (mircea8me.com)"
echo ""

# Step 1: Verify VS Code CLI is available
echo "Step 1: Checking VS Code CLI..."
if ! command -v code &>/dev/null; then
  echo "ERROR: 'code' command not found."
  echo "Fix: Open VS Code → Cmd+Shift+P → 'Shell Command: Install code command in PATH'"
  exit 1
fi

code --version
echo "VS Code CLI: OK"
echo ""

# Step 2: Install the Claude Code extension
EXTENSION_ID="anthropic.claude-code"
echo "Step 2: Installing extension: $EXTENSION_ID"

if code --list-extensions | grep -qi "anthropic.claude-code"; then
  echo "Extension already installed. Checking for updates..."
  code --install-extension "$EXTENSION_ID" --force
else
  code --install-extension "$EXTENSION_ID"
fi

echo ""

# Step 3: Verify installation
echo "Step 3: Verifying installation..."
if code --list-extensions | grep -qi "anthropic.claude-code"; then
  echo "SUCCESS: Claude Code extension installed."
else
  echo "ERROR: Extension not found after install. Try manually:"
  echo "  code --install-extension anthropic.claude-code"
  exit 1
fi

echo ""
echo "=== Done. Restart VS Code to activate the extension. ==="
