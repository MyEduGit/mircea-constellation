#!/bin/bash
# SessionStart hook — mircea-constellation
# Restores dev environment and git state on every session launch.
set -euo pipefail

if [ "${CLAUDE_CODE_REMOTE:-}" != "true" ]; then
  exit 0
fi

cd "${CLAUDE_PROJECT_DIR:-$(git rev-parse --show-toplevel)}"

# ── Git: pull latest from current branch ─────────────────────────────────────
BRANCH=$(git branch --show-current 2>/dev/null || echo "")
if [ -n "$BRANCH" ]; then
  PULLED=false
  for WAIT in 0 2 4 8 16; do
    [ "$WAIT" -gt 0 ] && sleep "$WAIT"
    if git fetch origin "$BRANCH" -q 2>/dev/null && \
       git merge --ff-only "origin/$BRANCH" -q 2>/dev/null; then
      PULLED=true
      echo "[session-start] Git: up to date on $BRANCH"
      break
    fi
  done
  $PULLED || echo "[session-start] WARN: could not pull $BRANCH — continuing with local state"
else
  echo "[session-start] WARN: not on a named branch — skipping git pull"
fi

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
