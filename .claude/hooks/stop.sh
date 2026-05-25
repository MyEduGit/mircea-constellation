#!/bin/bash
# Stop hook — commit and push all work when session ends
set -euo pipefail

REPO_DIR="${CLAUDE_PROJECT_DIR:-$(git rev-parse --show-toplevel 2>/dev/null)}"
[ -z "$REPO_DIR" ] && exit 0
cd "$REPO_DIR"

git rev-parse --git-dir &>/dev/null || exit 0

BRANCH=$(git branch --show-current 2>/dev/null)
[ -z "$BRANCH" ] && exit 0

# Commit any remaining uncommitted changes
if ! git diff --quiet 2>/dev/null || ! git diff --cached --quiet 2>/dev/null; then
  git add -A
  git commit -m "wip: auto-save on session stop [$(date -u +%Y-%m-%dT%H:%M:%SZ)]" \
    --no-verify -q 2>/dev/null || true
  echo "[stop] WIP committed on branch: $BRANCH"
fi

# Push with retry (exponential backoff: 2s, 4s, 8s, 16s)
PUSHED=false
for WAIT in 0 2 4 8 16; do
  [ "$WAIT" -gt 0 ] && sleep "$WAIT"
  if git push -u origin "$BRANCH" -q 2>/dev/null; then
    PUSHED=true
    echo "[stop] Pushed to origin/$BRANCH"
    break
  fi
done

$PUSHED || echo "[stop] WARN: push failed after retries — work is committed locally"
