#!/bin/bash
# PreToolUse hook — auto-stash WIP before any destructive tool runs
# Triggers before: Edit, Write, Bash, MultiEdit
set -euo pipefail

REPO_DIR="${CLAUDE_PROJECT_DIR:-$(git rev-parse --show-toplevel 2>/dev/null)}"
[ -z "$REPO_DIR" ] && exit 0
cd "$REPO_DIR"

# Only act if inside a git repo with changes
git rev-parse --git-dir &>/dev/null || exit 0

# If there are unstaged/untracked changes, auto-commit them as WIP
if ! git diff --quiet 2>/dev/null || ! git diff --cached --quiet 2>/dev/null; then
  git add -A
  git commit -m "wip: auto-save before tool use [$(date -u +%Y-%m-%dT%H:%M:%SZ)]" \
    --no-verify -q 2>/dev/null || true
fi
