#!/usr/bin/env bash
# Install the Claude diagram viewer tools into ~/.claude/
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
CLAUDE_DIR="$HOME/.claude"
mkdir -p "$CLAUDE_DIR"
echo ">> Installing diagram viewer tools into $CLAUDE_DIR"
cp "$HERE/diagram-view.sh" "$CLAUDE_DIR/diagram-view.sh"
cp "$HERE/diagram-viewer.html.tmpl" "$CLAUDE_DIR/diagram-viewer.html.tmpl"
cp "$HERE/mermaid-validate.mjs" "$CLAUDE_DIR/mermaid-validate.mjs"
chmod +x "$CLAUDE_DIR/diagram-view.sh"
if [[ ! -d "$CLAUDE_DIR/node_modules/mermaid" ]]; then
  echo ">> Installing mermaid + jsdom into $CLAUDE_DIR/node_modules"
  (cd "$CLAUDE_DIR" && npm init -y --silent 2>/dev/null; npm install --silent mermaid jsdom)
fi
echo ">> Done. Test: ~/.claude/diagram-view.sh /tmp/test.mmd --open"
