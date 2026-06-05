#!/usr/bin/env bash
set -euo pipefail
TMPL="${DIAGRAM_VIEWER_TMPL:-$HOME/.claude/diagram-viewer.html.tmpl}"
[[ ! -f "$TMPL" ]] && echo "ERROR: template not found: $TMPL" >&2 && exit 2
in=""; out=""; open_it=0; title=""
while [[ $# -gt 0 ]]; do
  case "$1" in
    -o|--out) out="$2"; shift 2 ;;
    --title) title="$2"; shift 2 ;;
    --open) open_it=1; shift ;;
    -) in="-"; shift ;;
    *) in="$1"; shift ;;
  esac
done
[[ -z "$in" ]] && echo "ERROR: no input file" >&2 && exit 2
if [[ "$in" = "-" ]]; then src=$(cat); base="diagram"; else src=$(cat "$in"); base=$(basename "$in" .mmd); fi
[[ -z "$out" ]] && out="/tmp/claude-diag-${base}-$(date +%Y%m%d-%H%M%S).html"
[[ -z "$title" ]] && title="$base"
_src_tmp=$(mktemp); trap 'rm -f "$_src_tmp"' EXIT; printf "%s" "$src" > "$_src_tmp"
python3 -c '
import sys, pathlib, html as htmllib
tmpl_path, out_path, title, src_path = sys.argv[1:5]
src = pathlib.Path(src_path).read_text()
tmpl = pathlib.Path(tmpl_path).read_text()
raw = src.replace("\\", "\\\\").replace("`", "\\`").replace("${", "\\${").replace("\r", "")
out = (tmpl.replace("__TITLE__", htmllib.escape(title))
       .replace("__MERMAID_SOURCE_ESCAPED__", htmllib.escape(src))
       .replace("__MERMAID_SOURCE_RAW__", raw))
pathlib.Path(out_path).write_text(out)
' "$TMPL" "$out" "$title" "$_src_tmp"
echo "$out"
[[ "$open_it" -eq 1 ]] && { command -v open >/dev/null 2>&1 && open "$out" || command -v xdg-open >/dev/null 2>&1 && xdg-open "$out" >/dev/null 2>&1 & || echo "(open manually)" >&2; }
