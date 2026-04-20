#!/usr/bin/env bash
# ~/.claude/diagram-view.sh
#
# Turn a Mermaid source file into a standalone, detachable HTML viewer with:
#   + / −  zoom (buttons + keyboard + scroll-wheel)
#   ⛶      fullscreen (button + F key)
#   </>    toggle source panel (S key)
#   📋     copy Mermaid source / copy rendered SVG
#   💾     download SVG
#   🖼     download PNG (2x, dark background baked in)
#   🖨     print → PDF (browser print dialog)
#
# The viewer is a single self-contained .html file. Open with:
#   open path/to/diagram.html     (macOS)
#   xdg-open path/to/diagram.html (Linux)
#
# Usage:
#   diagram-view.sh input.mmd              # prints the output HTML path
#   diagram-view.sh input.mmd -o out.html  # write to a specific location
#   diagram-view.sh input.mmd --open       # also try to open it
#   cat input.mmd | diagram-view.sh - --open
set -euo pipefail

TMPL="${DIAGRAM_VIEWER_TMPL:-$HOME/.claude/diagram-viewer.html.tmpl}"

if [[ ! -f "$TMPL" ]]; then
  echo "ERROR: template not found: $TMPL" >&2
  exit 2
fi

in=""
out=""
open_it=0
title=""

while [[ $# -gt 0 ]]; do
  case "$1" in
    -o|--out)  out="$2"; shift 2 ;;
    --title)   title="$2"; shift 2 ;;
    --open)    open_it=1; shift ;;
    -h|--help)
      sed -n '2,25p' "$0"; exit 0 ;;
    -)         in="-"; shift ;;
    *)         in="$1"; shift ;;
  esac
done

if [[ -z "$in" ]]; then
  echo "ERROR: no input file (use - for stdin)" >&2
  exit 2
fi

# Read source
if [[ "$in" = "-" ]]; then
  src=$(cat)
  base="diagram"
else
  src=$(cat "$in")
  base=$(basename "$in" .mmd)
fi

# Derive output path
if [[ -z "$out" ]]; then
  ts=$(date +%Y%m%d-%H%M%S)
  out="/tmp/claude-diag-${base}-${ts}.html"
fi

[[ -z "$title" ]] && title="$base"

# Render template. We use python for reliable placeholder substitution because
# the source may contain bash-special chars, quotes, backticks, etc. Pass the
# Mermaid source via a temp file (stdin would collide with python's own
# script-on-stdin mechanism).
_src_tmp=$(mktemp)
trap 'rm -f "$_src_tmp"' EXIT
printf "%s" "$src" > "$_src_tmp"

python3 -c '
import sys, pathlib, html as htmllib
tmpl_path, out_path, title, src_path = sys.argv[1:5]
src = pathlib.Path(src_path).read_text()
tmpl = pathlib.Path(tmpl_path).read_text()
raw = src.replace("\\", "\\\\").replace("`", "\\`").replace("${", "\\${").replace("\r", "")
out = (tmpl
       .replace("__TITLE__", htmllib.escape(title))
       .replace("__MERMAID_SOURCE_ESCAPED__", htmllib.escape(src))
       .replace("__MERMAID_SOURCE_RAW__", raw))
pathlib.Path(out_path).write_text(out)
' "$TMPL" "$out" "$title" "$_src_tmp"

echo "$out"

if [[ "$open_it" -eq 1 ]]; then
  if command -v open >/dev/null 2>&1; then
    open "$out"
  elif command -v xdg-open >/dev/null 2>&1; then
    xdg-open "$out" >/dev/null 2>&1 &
  else
    echo "(no 'open' or 'xdg-open' found — open the path manually)" >&2
  fi
fi
