#!/usr/bin/env bash
# doc-verify.sh — SessionStart hook
# Verifies that archival targets are reachable before any job begins.
# Fails loudly so jobs never silently skip archival.
set -euo pipefail

VAULT="${HOME}/Documents/Obsidian/Jobs"
ENV_FILE="${HOME}/.claude/doc.env"

ok=1

# 1. Vault exists
if [ ! -d "$VAULT" ]; then
  echo "[doc-verify] ✗ Vault missing: $VAULT  — run setup/claude-doc/install.sh"
  ok=0
else
  echo "[doc-verify] ✓ Vault present: $VAULT"
fi

# 2. .obsidian config exists (standalone vault marker)
if [ ! -d "$VAULT/.obsidian" ]; then
  echo "[doc-verify] ⚠ $VAULT is not a registered Obsidian vault yet (missing .obsidian/). Open Obsidian → 'Open folder as vault' → select Jobs/."
fi

# 3. doc.env present (optional — only required for Zapier fan-out)
if [ -f "$ENV_FILE" ]; then
  echo "[doc-verify] ✓ doc.env present"
else
  echo "[doc-verify] · doc.env absent (ok — Zapier fan-out disabled)"
fi

# 4. Git is available (for GitHub mirror)
if command -v git >/dev/null 2>&1; then
  echo "[doc-verify] ✓ git available"
else
  echo "[doc-verify] ✗ git missing — GitHub mirror will fail"
  ok=0
fi

# 5. Markdown renderer (optional): mmdc for PNG/SVG export
if command -v mmdc >/dev/null 2>&1; then
  echo "[doc-verify] ✓ mmdc available (Mermaid CLI)"
else
  echo "[doc-verify] · mmdc absent — SVG/PNG export will fall back to inline. Install: npm i -g @mermaid-js/mermaid-cli"
fi

[ $ok -eq 1 ] || {
  echo "[doc-verify] one or more required checks failed — DOC rule may not archive correctly."
  exit 0   # warn, don't block session
}

exit 0
