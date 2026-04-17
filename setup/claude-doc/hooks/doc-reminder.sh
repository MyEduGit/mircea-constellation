#!/usr/bin/env bash
# doc-reminder.sh — Stop hook
# Nudges Claude to run /doc if the job wasn't archived yet.
# Checks for a recent marker file written by the /doc skill on successful archive.
# If no marker is found and a job clearly just completed, emits a system reminder.
set -euo pipefail

MARKER_DIR="${HOME}/.claude/.doc-markers"
mkdir -p "$MARKER_DIR"

# Find marker files touched in the last 10 minutes
RECENT=$(find "$MARKER_DIR" -type f -mmin -10 2>/dev/null | head -1 || true)

if [ -z "$RECENT" ]; then
  # Emit a JSON response asking Claude to run /doc before ending
  # (Claude Code Stop-hook format: exit 2 + stderr = blocking hint to the agent)
  cat >&2 <<'EOF'
[Diagram-On-Completion] No archival marker found for the last 10 minutes.
If a job just completed, invoke the /doc skill to archive it to Obsidian,
Notion, and GitHub before ending the session. If this session did NOT
complete a job, touch ~/.claude/.doc-markers/none to silence this reminder.
EOF
  exit 2
fi

exit 0
