#!/bin/bash
# scribeclaw — thin operator wrapper around the POST /tasks HTTP surface.
#
# Purpose: reduce every daily operator action to a single argv line,
# without caching handler names or secrets locally. Every call goes
# through the local-only 127.0.0.1:8081/tasks endpoint.
#
# Usage:
#   setup/scribeclaw.sh health
#   setup/scribeclaw.sh smoke
#   setup/scribeclaw.sh list                     # transcripts on disk
#   setup/scribeclaw.sh status                   # session_status report
#   setup/scribeclaw.sh bulk-ro [max]            # clone RO transcripts
#   setup/scribeclaw.sh import <id> [stem]       # import single AAI transcript
#   setup/scribeclaw.sh clean <stem>             # postprocess_transcript
#   setup/scribeclaw.sh correct <stem>           # correct_ro_theological
#   setup/scribeclaw.sh strip <stem>             # strip_speaker_labels
#   setup/scribeclaw.sh cues <stem>              # resegment_phrase_cues
#   setup/scribeclaw.sh meta <stem>              # youtube_metadata
#   setup/scribeclaw.sh thumb <video> <stem>     # thumbnail_generate
#   setup/scribeclaw.sh upload <stem> [privacy]  # youtube_upload (default private)
#   setup/scribeclaw.sh validate <stem>          # validate_srt
#   setup/scribeclaw.sh diff <a> <b>             # srt_diff
#   setup/scribeclaw.sh evidence [limit]         # dashboard's /api/evidence
#   setup/scribeclaw.sh raw <handler> <json>     # arbitrary call
#
# Not every subcommand maps to a handler that's live on every host —
# if the handler isn't in the allowlist you'll get {status: rejected}
# honestly rather than a silent failure.
#
# UrantiOS governed — Truth, Beauty, Goodness.
set -euo pipefail

HOST="${SCRIBECLAW_HOST:-127.0.0.1:8081}"

usage() {
  sed -n '2,26p' "$0"
  exit "${1:-0}"
}

need() {
  command -v "$1" >/dev/null 2>&1 || {
    echo "missing dependency: $1" >&2; exit 2;
  }
}

need curl

# jq is nice-to-have; we fall back to python3 when it's not around.
if command -v jq >/dev/null 2>&1; then
  pretty() { jq .; }
else
  pretty() { python3 -m json.tool; }
fi

post() {
  local handler="$1" payload="${2:-{\}}"
  curl -sS -X POST "http://${HOST}/tasks" \
    -H 'Content-Type: application/json' \
    -d "{\"handler\":\"${handler}\",\"payload\":${payload}}" \
  | pretty
}

get() {
  local path="$1"
  curl -sS "http://${HOST}${path}" | pretty
}

cmd="${1:-help}"; shift || true
case "$cmd" in
  help|-h|--help) usage ;;

  health)   get /health ;;
  smoke)    post smoke_test ;;

  list)     get /api/transcripts ;;
  status)   post session_status ;;

  bulk-ro)
    max="${1:-50}"
    post bulk_import_assemblyai_romanian "{\"max_transcripts\":${max}}"
    ;;

  import)
    [ $# -ge 1 ] || { echo "usage: import <id> [stem]" >&2; exit 2; }
    id="$1"; stem="${2:-$id}"
    post import_assemblyai_transcript \
      "{\"transcript_id\":\"${id}\",\"stem\":\"${stem}\"}"
    ;;

  clean)
    [ $# -eq 1 ] || { echo "usage: clean <stem>" >&2; exit 2; }
    post postprocess_transcript "{\"stem\":\"$1\"}"
    ;;

  correct)
    [ $# -eq 1 ] || { echo "usage: correct <stem>" >&2; exit 2; }
    post correct_ro_theological "{\"stem\":\"$1\"}"
    ;;

  strip)
    [ $# -eq 1 ] || { echo "usage: strip <stem>" >&2; exit 2; }
    post strip_speaker_labels "{\"stem\":\"$1\"}"
    ;;

  cues)
    [ $# -eq 1 ] || { echo "usage: cues <stem>" >&2; exit 2; }
    post resegment_phrase_cues "{\"stem\":\"$1\"}"
    ;;

  meta)
    [ $# -eq 1 ] || { echo "usage: meta <stem>" >&2; exit 2; }
    post youtube_metadata "{\"stem\":\"$1\"}"
    ;;

  thumb)
    [ $# -ge 2 ] || { echo "usage: thumb <video> <stem> [ts]" >&2; exit 2; }
    video="$1"; stem="$2"; ts="${3:-00:00:05}"
    post thumbnail_generate \
      "{\"input\":\"${video}\",\"stem\":\"${stem}\",\"timestamp\":\"${ts}\"}"
    ;;

  upload)
    [ $# -ge 1 ] || { echo "usage: upload <stem> [privacy]" >&2; exit 2; }
    stem="$1"; privacy="${2:-private}"
    # Never default to public — match youtube_upload's own contract.
    case "$privacy" in
      private|unlisted|public) ;;
      *) echo "privacy must be private|unlisted|public" >&2; exit 2 ;;
    esac
    post youtube_upload \
      "{\"stem\":\"${stem}\",\"privacy_status\":\"${privacy}\"}"
    ;;

  validate)
    [ $# -eq 1 ] || { echo "usage: validate <stem>" >&2; exit 2; }
    post validate_srt "{\"stem\":\"$1\"}"
    ;;

  diff)
    [ $# -eq 2 ] || { echo "usage: diff <a> <b>" >&2; exit 2; }
    post srt_diff "{\"a\":\"$1\",\"b\":\"$2\"}"
    ;;

  evidence)
    limit="${1:-30}"
    get "/api/evidence?limit=${limit}"
    ;;

  raw)
    [ $# -eq 2 ] || { echo "usage: raw <handler> <json-payload>" >&2; exit 2; }
    post "$1" "$2"
    ;;

  *)
    echo "unknown subcommand: $cmd" >&2
    usage 2
    ;;
esac
