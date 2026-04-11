#!/bin/bash
# SessionStart hook — mircea-constellation
# Installs static web tooling (serve, html-validate) on session start.
set -euo pipefail

if [ "${CLAUDE_CODE_REMOTE:-}" != "true" ]; then
  exit 0
fi

cd "${CLAUDE_PROJECT_DIR:-$(git rev-parse --show-toplevel)}"

# ── serve (static file server) ───────────────────────────────────────────────
if command -v npm &>/dev/null; then
  if ! command -v serve &>/dev/null; then
    echo "[session-start] Installing serve..."
    npm install -g serve --no-audit --no-fund 2>&1
  else
    echo "[session-start] serve already available."
  fi

  # ── html-validate (HTML linter) ────────────────────────────────────────────
  if ! command -v html-validate &>/dev/null; then
    echo "[session-start] Installing html-validate..."
    npm install -g html-validate --no-audit --no-fund 2>&1
  else
    echo "[session-start] html-validate already available."
  fi
else
  echo "[session-start] WARN: npm not found — skipping tool install."
fi

echo "[session-start] mircea-constellation session ready."
