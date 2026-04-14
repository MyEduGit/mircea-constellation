#!/usr/bin/env bash
# install.sh — Diagram-On-Completion (DOC) installer
# Run on your local machine (iMac/Mac). Idempotent.
#
# What it does:
#   1. Creates the standalone Obsidian vault at ~/Documents/Obsidian/Jobs/
#   2. Appends the DOC rule to ~/.claude/CLAUDE.md (once)
#   3. Installs the /doc skill to ~/.claude/skills/diagram-on-completion.md
#   4. Installs Stop + SessionStart hooks to ~/.claude/hooks/
#   5. Merges hook config into ~/.claude/settings.json (preserves existing keys)
#   6. Installs mmdc (Mermaid CLI) if npm is available and mmdc is missing
#
# Re-run safely: every step checks "already present" before writing.
set -euo pipefail

SRC_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CLAUDE_DIR="${HOME}/.claude"
VAULT="${HOME}/Documents/Obsidian/Jobs"
MARKER="# [[DOC-RULE v1]]"

say() { printf "\033[1;36m[doc-install]\033[0m %s\n" "$*"; }
ok()  { printf "\033[1;32m  ✓\033[0m %s\n" "$*"; }
warn(){ printf "\033[1;33m  ⚠\033[0m %s\n" "$*"; }

mkdir -p "$CLAUDE_DIR/skills" "$CLAUDE_DIR/hooks" "$CLAUDE_DIR/.doc-markers"

# ── 1. Vault ────────────────────────────────────────────────────────────────
say "Ensuring vault at $VAULT"
mkdir -p "$VAULT/.obsidian" "$VAULT/templates"
if [ ! -f "$VAULT/README.md" ]; then
  cat > "$VAULT/README.md" <<'EOF'
# Jobs — Claude Diagram-On-Completion Vault

This vault is populated automatically by Claude Code's /doc skill.
Each completed "job" lands under `YYYY-MM-DD/<job-slug>/` with:

- `job.md` — summary, transcript, controls
- `diagram.md` — Mermaid diagram
- `diagram.mmd`, `diagram.svg`, `diagram.png` — diagram exports
- `assets/` — screenshots, drops, attachments

Open this folder in Obsidian as a standalone vault:
  Obsidian → "Open folder as vault" → select this directory.
EOF
  ok "Seeded README.md"
else
  ok "README.md already present"
fi

# ── 2. CLAUDE.md rule (append once, idempotent via marker) ──────────────────
say "Installing DOC rule into $CLAUDE_DIR/CLAUDE.md"
touch "$CLAUDE_DIR/CLAUDE.md"
if grep -qF "$MARKER" "$CLAUDE_DIR/CLAUDE.md"; then
  ok "Rule already present (marker found)"
else
  {
    echo ""
    echo "$MARKER"
    cat "$SRC_DIR/rule.md"
    echo ""
    echo "<!-- end DOC-RULE v1 -->"
  } >> "$CLAUDE_DIR/CLAUDE.md"
  ok "Appended rule (marker: $MARKER)"
fi

# ── 3. Skill ────────────────────────────────────────────────────────────────
say "Installing /doc skill"
cp "$SRC_DIR/skills/diagram-on-completion.md" "$CLAUDE_DIR/skills/diagram-on-completion.md"
ok "Skill installed at $CLAUDE_DIR/skills/diagram-on-completion.md"

# ── 4. Hooks ────────────────────────────────────────────────────────────────
say "Installing hooks"
cp "$SRC_DIR/hooks/doc-reminder.sh" "$CLAUDE_DIR/hooks/doc-reminder.sh"
cp "$SRC_DIR/hooks/doc-verify.sh"   "$CLAUDE_DIR/hooks/doc-verify.sh"
chmod +x "$CLAUDE_DIR/hooks/doc-reminder.sh" "$CLAUDE_DIR/hooks/doc-verify.sh"
ok "Hooks copied + chmod +x"

# ── 5. settings.json merge ──────────────────────────────────────────────────
say "Merging hook config into $CLAUDE_DIR/settings.json"
SETTINGS="$CLAUDE_DIR/settings.json"
if [ ! -f "$SETTINGS" ]; then echo '{}' > "$SETTINGS"; fi

if command -v jq >/dev/null 2>&1; then
  TMP=$(mktemp)
  jq '
    .hooks = (.hooks // {}) |
    .hooks.Stop = ((.hooks.Stop // []) + [{"hooks":[{"type":"command","command":"$HOME/.claude/hooks/doc-reminder.sh"}]}] | unique_by(.hooks[0].command)) |
    .hooks.SessionStart = ((.hooks.SessionStart // []) + [{"hooks":[{"type":"command","command":"$HOME/.claude/hooks/doc-verify.sh"}]}] | unique_by(.hooks[0].command))
  ' "$SETTINGS" > "$TMP" && mv "$TMP" "$SETTINGS"
  ok "Merged via jq"
else
  warn "jq not installed — please manually merge $SRC_DIR/settings.snippet.json into $SETTINGS"
fi

# ── 6. mmdc (optional) ──────────────────────────────────────────────────────
say "Checking Mermaid CLI (mmdc)"
if command -v mmdc >/dev/null 2>&1; then
  ok "mmdc already installed"
elif command -v npm >/dev/null 2>&1; then
  warn "Installing @mermaid-js/mermaid-cli globally..."
  npm install -g @mermaid-js/mermaid-cli --no-audit --no-fund >/dev/null 2>&1 && ok "mmdc installed" || warn "mmdc install failed — SVG/PNG will fall back to inline"
else
  warn "npm absent — skipping mmdc install"
fi

echo ""
say "Done. Next:"
echo "  1. Open Obsidian → 'Open folder as vault' → select $VAULT"
echo "  2. Start a new Claude Code session — doc-verify.sh will confirm readiness"
echo "  3. Complete any task, then ask Claude to run /doc (or let the Stop hook nudge)"
echo ""
say "To disable the Stop-hook reminder for a non-job session:"
echo "  touch $CLAUDE_DIR/.doc-markers/none"
