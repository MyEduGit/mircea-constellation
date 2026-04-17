#!/usr/bin/env bash
# verify-diagram.sh - renders a Mermaid source and FAILS on any parse error.
#
# CRITICAL: mmdc exits 0 even when the rendered SVG contains "Syntax error".
# We must also grep mmdc's stderr+stdout for parse errors and grep the
# produced SVG for the "Syntax error" bomb glyph.
#
# Usage:   verify-diagram.sh <input.mmd> [output.svg]
# Exit:    0 = verified rendering OK
#          1 = parse error or syntax error in rendered SVG
#          2 = mmdc not installed
#          3 = input file missing
set -euo pipefail

if [ "$#" -lt 1 ]; then
  echo "usage: $0 <input.mmd> [output.svg]" >&2
  exit 3
fi

IN="$1"
OUT="${2:-${IN%.mmd}.svg}"

if [ ! -f "$IN" ]; then
  echo "[verify-diagram] input not found: $IN" >&2
  exit 3
fi

if ! command -v mmdc >/dev/null 2>&1; then
  echo "[verify-diagram] mmdc not installed. Run: npm i -g @mermaid-js/mermaid-cli" >&2
  exit 2
fi

# Build a puppeteer config that works when running as root (common in CI + containers).
PPT_CFG="$(mktemp --suffix=.json)"
cat > "$PPT_CFG" <<'EOF'
{ "args": ["--no-sandbox", "--disable-setuid-sandbox"] }
EOF
trap 'rm -f "$PPT_CFG"' EXIT

LOG="$(mktemp)"
trap 'rm -f "$PPT_CFG" "$LOG"' EXIT

if ! mmdc -p "$PPT_CFG" -i "$IN" -o "$OUT" >"$LOG" 2>&1; then
  echo "[verify-diagram] mmdc exited non-zero:" >&2
  cat "$LOG" >&2
  exit 1
fi

# mmdc exits 0 even on Mermaid parse errors. Check the log.
if grep -qiE 'parse error|^Error:' "$LOG"; then
  echo "[verify-diagram] parse error detected in mmdc output:" >&2
  grep -iE 'parse error|^Error:|expecting' "$LOG" >&2 || cat "$LOG" >&2
  exit 1
fi

# Even if mmdc claims success, a bad diagram renders to the "Syntax error" bomb SVG.
if [ -f "$OUT" ] && grep -qi 'Syntax error in text' "$OUT"; then
  echo "[verify-diagram] rendered SVG is the 'Syntax error' error page" >&2
  exit 1
fi

echo "[verify-diagram] OK -> $OUT"
exit 0
