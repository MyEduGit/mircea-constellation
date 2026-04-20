#!/usr/bin/env bash
# Install the Claude diagram viewer tools into ~/.claude/
#
# Run from the repo root:
#   bash setup/claude-diagram-viewer/install.sh
set -euo pipefail

HERE="$(cd "$(dirname "$0")" && pwd)"
CLAUDE_DIR="$HOME/.claude"

mkdir -p "$CLAUDE_DIR"

echo ">> Installing diagram viewer tools into $CLAUDE_DIR"

cp "$HERE/diagram-view.sh"          "$CLAUDE_DIR/diagram-view.sh"
cp "$HERE/diagram-viewer.html.tmpl" "$CLAUDE_DIR/diagram-viewer.html.tmpl"
cp "$HERE/mermaid-validate.mjs"     "$CLAUDE_DIR/mermaid-validate.mjs"

chmod +x "$CLAUDE_DIR/diagram-view.sh"

# Install Node deps for the validator if missing
if [[ ! -d "$CLAUDE_DIR/node_modules/mermaid" ]]; then
  echo ">> Installing mermaid + jsdom into $CLAUDE_DIR/node_modules"
  (cd "$CLAUDE_DIR" && npm init -y --silent 2>/dev/null; npm install --silent mermaid jsdom)
fi

echo ">> Done. Test with:"
echo "   echo 'flowchart LR; A-->B' > /tmp/test.mmd"
echo "   node ~/.claude/mermaid-validate.mjs /tmp/test.mmd"
echo "   ~/.claude/diagram-view.sh /tmp/test.mmd --open"
