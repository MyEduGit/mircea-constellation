#!/usr/bin/env bash
#
# C0087_transcribe.sh — standalone AssemblyAI transcription (ScribeClaw CLI path)
#
# Transcribes one local audio/video file with AssemblyAI and writes the exact
# output shape the ScribeClaw pipeline produces, so `postprocess_transcript`
# and `youtube_metadata` stay drop-in compatible:
#
#   <out-dir>/
#       assemblyai.raw.json        full API response (provenance)
#       assemblyai.sentences.json  sentence endpoint response (provenance)
#       segments.json              normalized segments, seconds
#       transcript.srt
#       transcript.vtt
#       transcript.txt
#       segments.clean.json        Romanian orthography normalized
#       transcript.clean.txt       cleaned + reflowed into paragraphs
#       evidence.json              run record (input sha256, ids, timings)
#
# Dependencies: bash, curl, jq. Nothing else — no Docker, no Python.
# Bash 3.2 compatible (ships with macOS).
#
# stdout = one JSON summary object. stderr = human progress.
# So this pipes:  ./C0087_transcribe.sh audio.mp3 | jq -r .output_dir
#
# UrantiOS governed — Truth, Beauty, Goodness.

set -euo pipefail

VERSION="1.0.0"
TOOL="C0087_transcribe.sh"
API="${ASSEMBLYAI_API_BASE:-https://api.assemblyai.com/v2}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# ── defaults ─────────────────────────────────────────────────────────────────
MODE="transcribe"          # transcribe | import | render
AUDIO=""
TRANSCRIPT_ID=""
RAW_IN=""
SENTENCES_IN=""
OUT_DIR=""
LANGUAGE="ro"              # Romanian-first, like the rest of ScribeClaw
DETECT_LANGUAGE=0
SPEAKER_LABELS=0
PUNCTUATE=1
FORMAT_TEXT=1
SPEECH_MODEL=""
WITH_WORDS=0
POLL_SEC=5
TIMEOUT_SEC=1800           # 30 min covers a one-hour recording
HTTP_MAX_TIME=180
UPLOAD_MAX_TIME=7200
API_KEY_FILE=""
QUIET=0
DRY_RUN=0
LAST_STATUS=""
_opt=""
_val=""

usage() {
  cat <<'HELPTEXT'
C0087_transcribe.sh — AssemblyAI transcription, one file, no runtime deps.

USAGE
  C0087_transcribe.sh [options] <audio-file>
  C0087_transcribe.sh --import <transcript-id> [options]
  C0087_transcribe.sh --render <assemblyai.raw.json> [options]

MODES
  <audio-file>              upload the file, transcribe, write outputs
  --import <id>             reuse a transcript that is ALREADY completed in
                            the AssemblyAI dashboard (no upload, no re-bill)
  --render <raw.json>       re-render outputs from a saved raw response
                            (offline; no network, no API key needed)

OPTIONS
  -o, --out-dir DIR         output directory
                            default: <audio-dir>/transcripts/<stem>
                            --import default: ./transcripts/<id>
                            --render default: the raw.json's own directory
  -l, --language CODE       language_code sent to AssemblyAI (default: ro)
      --detect-language     let AssemblyAI detect it (drops --language)
  -s, --speaker-labels      request diarization; segments carry "speaker"
  -m, --speech-model ID     AssemblyAI speech_model (e.g. best, nano)
      --sentences FILE      --render only: sentences response to pair with raw
      --words               keep word-level timestamps in segments.json
      --no-punctuate        disable automatic punctuation
      --no-format-text      disable text formatting
      --poll-sec N          poll interval in seconds (default: 5)
      --timeout SEC         give up polling after SEC seconds (default: 1800)
      --api-key-file FILE   read the key from FILE (bare key, or a .env line)
      --dry-run             validate + print the request body, send nothing
  -q, --quiet               suppress progress on stderr
  -h, --help                this text
      --version             print version

API KEY (first hit wins)
  1. --api-key-file FILE
  2. $ASSEMBLYAI_API_KEY
  3. <script dir>/.env          (ASSEMBLYAI_API_KEY=...)
  4. ~/.assemblyai              (bare key or ASSEMBLYAI_API_KEY=...)
  Get a key at https://www.assemblyai.com/app/api-keys

EXAMPLES
  export ASSEMBLYAI_API_KEY=...
  ./C0087_transcribe.sh ~/Downloads/C0087_AUDIO_.mp3
  ./C0087_transcribe.sh -s -o ~/Desktop/c0087 ~/Downloads/C0087_AUDIO_.mp3
  ./C0087_transcribe.sh --import 6f2b... -o ./transcripts/c0087
  ./C0087_transcribe.sh --render ./transcripts/c0087/assemblyai.raw.json
HELPTEXT
}

# ── plumbing ─────────────────────────────────────────────────────────────────
log()  { [ "$QUIET" -eq 0 ] && printf '%s\n' "$*" >&2 || true; }
warn() { printf '%s\n' "WARN: $*" >&2; }
die()  { printf '%s\n' "ERROR: $*" >&2; exit 1; }

need() {
  command -v "$1" >/dev/null 2>&1 || die "$1 is required but not on PATH.${2:+ $2}"
}

progress() {
  [ "$QUIET" -eq 0 ] || return 0
  if [ -t 2 ]; then
    printf '\r  ... %-12s %4ds' "$1" "$2" >&2
  elif [ "$1" != "$LAST_STATUS" ]; then
    printf '  ... %s\n' "$1" >&2
    LAST_STATUS="$1"
  fi
}

progress_done() {
  [ "$QUIET" -eq 0 ] || return 0
  [ -t 2 ] && printf '\n' >&2
  return 0
}

sha256_of() {
  if command -v shasum >/dev/null 2>&1; then
    shasum -a 256 "$1" | awk '{print $1}'
  elif command -v sha256sum >/dev/null 2>&1; then
    sha256sum "$1" | awk '{print $1}'
  else
    printf 'unavailable'
  fi
}

bytes_of() { wc -c < "$1" | tr -d ' '; }

human_size() { # bytes -> "12.4 MiB"
  if   [ "$1" -ge 1073741824 ]; then awk -v b="$1" 'BEGIN{printf "%.1f GiB", b/1073741824}'
  elif [ "$1" -ge 1048576 ];    then awk -v b="$1" 'BEGIN{printf "%.1f MiB", b/1048576}'
  elif [ "$1" -ge 1024 ];       then awk -v b="$1" 'BEGIN{printf "%.1f KiB", b/1024}'
  else printf '%s B' "$1"; fi
}
now_iso()  { date -u +%Y-%m-%dT%H:%M:%SZ; }

# ── argument parsing ─────────────────────────────────────────────────────────
[ $# -gt 0 ] || { usage; exit 2; }

while [ $# -gt 0 ]; do
  case "$1" in
    --*=*)              # --opt=value -> --opt value; ${1+"$@"} keeps bash 3.2
                        _opt="${1%%=*}"; _val="${1#*=}"; shift
                        set -- "$_opt" "$_val" ${1+"$@"}      # (macOS) happy under set -u
                        continue ;;
    -h|--help)          usage; exit 0 ;;
    --version)          printf '%s %s\n' "$TOOL" "$VERSION"; exit 0 ;;
    --import)           MODE="import"; TRANSCRIPT_ID="${2:-}"; shift 2 ;;
    --render)           MODE="render"; RAW_IN="${2:-}"; shift 2 ;;
    --sentences)        SENTENCES_IN="${2:-}"; shift 2 ;;
    -o|--out-dir)       OUT_DIR="${2:-}"; shift 2 ;;
    -l|--language)      LANGUAGE="${2:-}"; shift 2 ;;
    --detect-language)  DETECT_LANGUAGE=1; shift ;;
    -s|--speaker-labels) SPEAKER_LABELS=1; shift ;;
    -m|--speech-model)  SPEECH_MODEL="${2:-}"; shift 2 ;;
    --words)            WITH_WORDS=1; shift ;;
    --no-punctuate)     PUNCTUATE=0; shift ;;
    --no-format-text)   FORMAT_TEXT=0; shift ;;
    --poll-sec)         POLL_SEC="${2:-}"; shift 2 ;;
    --timeout)          TIMEOUT_SEC="${2:-}"; shift 2 ;;
    --api-key-file)     API_KEY_FILE="${2:-}"; shift 2 ;;
    --dry-run)          DRY_RUN=1; shift ;;
    -q|--quiet)         QUIET=1; shift ;;
    --)                 shift; break ;;
    -*)                 die "unknown option: $1 (try --help)" ;;
    *)                  [ -z "$AUDIO" ] || die "only one input file is accepted (got '$AUDIO' and '$1')"
                        AUDIO="$1"; shift ;;
  esac
done
if [ $# -gt 0 ]; then                       # anything after a literal --
  if [ -z "$AUDIO" ]; then AUDIO="$1"; shift; fi
  [ $# -eq 0 ] || die "unexpected extra argument: $1"
fi

case "$POLL_SEC$TIMEOUT_SEC" in
  *[!0-9]*) die "--poll-sec and --timeout must be whole seconds" ;;
esac
[ "$POLL_SEC" -ge 1 ] || die "--poll-sec must be at least 1"

need curl
need jq "On macOS: brew install jq"

# ── key discovery ────────────────────────────────────────────────────────────
_key_from_file() {
  local f="$1" line=""
  [ -f "$f" ] || return 1
  line="$(grep -m1 -E '^[[:space:]]*(export[[:space:]]+)?ASSEMBLYAI_API_KEY[[:space:]]*=' "$f" 2>/dev/null || true)"
  if [ -n "$line" ]; then
    line="${line#*=}"
  else
    line="$(grep -m1 -E '[^[:space:]]' "$f" 2>/dev/null || true)"
  fi
  line="$(printf '%s' "$line" | tr -d "\"' \r\n\t")"
  [ -n "$line" ] || return 1
  printf '%s' "$line"
}

resolve_api_key() {
  local key="" src=""
  if [ -n "$API_KEY_FILE" ]; then
    [ -f "$API_KEY_FILE" ] || die "--api-key-file not found: $API_KEY_FILE"
    key="$(_key_from_file "$API_KEY_FILE" || true)"
    src="$API_KEY_FILE"
    [ -n "$key" ] || die "no API key found in $API_KEY_FILE"
  elif [ -n "${ASSEMBLYAI_API_KEY:-}" ]; then
    key="$ASSEMBLYAI_API_KEY"
    src="\$ASSEMBLYAI_API_KEY"
  else
    local f
    for f in "$SCRIPT_DIR/.env" "$HOME/.assemblyai" "$HOME/.assemblyai_api_key"; do
      if key="$(_key_from_file "$f" 2>/dev/null)"; then src="$f"; break; fi
      key=""
    done
  fi

  if [ -z "$key" ]; then
    die "ASSEMBLYAI_API_KEY is not set.
  Set it for this shell:      export ASSEMBLYAI_API_KEY='your-key'
  Or store it once:           printf '%s' 'your-key' > ~/.assemblyai && chmod 600 ~/.assemblyai
  Or point at a file:         $TOOL --api-key-file /path/to/key ...
  Keys live at https://www.assemblyai.com/app/api-keys"
  fi
  case "$key" in
    *[!A-Za-z0-9._-]*) die "the API key from $src contains unexpected characters — check for stray quotes or a wrapped line" ;;
  esac
  API_KEY="$key"
  API_KEY_SRC="$src"
}

# ── HTTP (key travels in a 0600 curl config, never in argv) ──────────────────
setup_curl() {
  CURL_CFG="$WORK/curl.cfg"
  ( umask 077; printf 'header = "authorization: %s"\n' "$API_KEY" > "$CURL_CFG" )
}

http_get() { # url outfile -> prints http_code
  curl --silent --show-error --location --config "$CURL_CFG" \
       --retry 3 --retry-delay 2 --max-time "$HTTP_MAX_TIME" \
       --write-out '%{http_code}' --output "$2" "$1"
}

http_post_json() { # url bodyfile outfile -> prints http_code
  curl --silent --show-error --location --config "$CURL_CFG" \
       --header 'content-type: application/json' \
       --retry 2 --retry-delay 2 --max-time "$HTTP_MAX_TIME" \
       --data-binary "@$2" \
       --write-out '%{http_code}' --output "$3" "$1"
}

http_upload() { # file outfile -> prints http_code
  # --upload-file streams from disk (no whole-file buffering); -X POST keeps
  # the verb AssemblyAI expects. Expect: header off — some proxies stall on it.
  local meter="--silent"
  [ "$QUIET" -eq 0 ] && [ -t 2 ] && meter="--progress-bar"
  curl "$meter" --show-error --location --config "$CURL_CFG" \
       --request POST --upload-file "$1" --header 'Expect:' \
       --max-time "$UPLOAD_MAX_TIME" \
       --write-out '%{http_code}' --output "$2" "$API/upload"
}

check_http() { # code bodyfile stage
  case "$1" in
    2*) return 0 ;;
  esac
  local detail
  detail="$(jq -r '.error // .message // empty' "$2" 2>/dev/null || true)"
  [ -n "$detail" ] || detail="$(head -c 400 "$2" 2>/dev/null || true)"
  case "$1" in
    401|403) die "AssemblyAI rejected the key during $3 (HTTP $1). Key source: ${API_KEY_SRC:-unknown}. ${detail:-}" ;;
    000)     die "could not reach AssemblyAI during $3 — check the network. ${detail:-}" ;;
    *)       die "AssemblyAI $3 failed (HTTP $1): ${detail:-no response body}" ;;
  esac
}

# ── renderer (jq; the only place output shape is defined) ────────────────────
write_render_program() {
  cat > "$WORK/render.jq" <<'JQPROG'
def pad($n): tostring | ("00000" + .) | .[(length - $n):];

def ts($sep):
  ((. * 1000) | round) as $ms
  | (($ms / 3600000) | floor) as $h
  | ((($ms % 3600000) / 60000) | floor) as $m
  | ((($ms % 60000) / 1000) | floor) as $s
  | ($ms % 1000) as $f
  | ($h | pad(2)) + ":" + ($m | pad(2)) + ":" + ($s | pad(2)) + $sep + ($f | pad(3));

def trim: sub("^[[:space:]]+"; "") | sub("[[:space:]]+$"; "");

# Legacy Romanian cedilla -> correct comma-below forms. Same map as
# scribeclaw/postprocess.py; deterministic, no language model involved.
def cedilla:
  gsub("ş"; "ș") | gsub("Ş"; "Ș")
  | gsub("ţ"; "ț") | gsub("Ţ"; "Ț");

def clean:
  cedilla
  | gsub("[ \t]+"; " ")
  | gsub("[[:space:]]+(?<p>[,.;:!?])"; "\(.p)")
  | trim;

def spk: if (.speaker // null) != null then "Speaker \(.speaker): " else "" end;

def words_of($keep):
  if $keep and ((.words // []) | length) > 0 then
    [ .words[] | {start: (.start / 1000), end: (.end / 1000),
                  word: (.text // .word // ""), probability: (.confidence // null)} ]
  else null end;

def to_segments($keep):
  [ to_entries[]
    | .key as $i
    | .value
    | {id: $i,
       start: ((.start // 0) / 1000),
       end: ((.end // 0) / 1000),
       text: ((.text // "") | trim),
       speaker: (.speaker // null),
       words: words_of($keep)} ];

def block($sep): (.value.start | ts($sep)) + " --> " + (.value.end | ts($sep))
                 + "\n" + (.value | spk + .text);

($raw[0] // {}) as $r
| (($sen[0] // {}).sentences // []) as $sentences
| ($with_words != 0) as $keep
| (
    if (($r.utterances // []) | length) > 0 then ($r.utterances | to_segments($keep))
    elif ($sentences | length) > 0        then ($sentences   | to_segments($keep))
    elif ((($r.text // "") | trim) != "") then
      [{id: 0, start: 0, end: 0, text: (($r.text) | trim), speaker: null, words: null}]
    else [] end
  ) as $segments
| ([ $segments[] | select(.speaker != null) ] | length > 0) as $diarized
| {
    language: ($r.language_code // "ro"),
    language_probability: 1.0,
    duration: ($r.audio_duration // 0),
    model: ("assemblyai:" + ($r.speech_model // "default")),
    segments: $segments,
    source: "assemblyai",
    assemblyai_id: ($r.id // null)
  } as $doc
| ($segments | map(.text |= clean)) as $cleaned
| {
    segments_json: $doc,
    clean_segments_json: ($doc | .segments = $cleaned),

    srt: ([ $segments | to_entries[]
            | ((.key + 1) | tostring) + "\n" + block(",") ] | join("\n\n")),

    vtt: ("WEBVTT\n\n" + ([ $segments | to_entries[] | block(".") ] | join("\n\n"))),

    txt: ([ $segments[] | select(.text != "") | spk + .text ] | join("\n\n")),

    clean_txt: (
      if $diarized then
        [ $cleaned[] | select(.text != "") | spk + .text ] | join("\n\n")
      else
        ([ $cleaned[] | .text ] | join(" ") | clean)
        | [ splits("(?<=[.!?])[[:space:]]+(?=[A-ZĂÂÎȘȚ])") ]
        | map(trim) | map(select(. != "")) | join("\n\n")
      end),

    stats: {
      assemblyai_id: ($r.id // null),
      language: ($r.language_code // "ro"),
      duration_sec: ($r.audio_duration // 0),
      segments: ($segments | length),
      diarized: $diarized
    }
  }
JQPROG
}

render_outputs() { # rawfile sentencesfile outdir
  local rawf="$1" senf="$2" out="$3"
  write_render_program
  jq -n --slurpfile raw "$rawf" --slurpfile sen "$senf" \
        --argjson with_words "$WITH_WORDS" \
        -f "$WORK/render.jq" > "$WORK/render.json" \
    || die "could not render outputs from $rawf (is it a valid AssemblyAI response?)"

  mkdir -p "$out"
  jq    '.segments_json'       "$WORK/render.json" > "$out/segments.json"
  jq    '.clean_segments_json' "$WORK/render.json" > "$out/segments.clean.json"
  jq -r '.srt'                 "$WORK/render.json" > "$out/transcript.srt"
  jq -r '.vtt'                 "$WORK/render.json" > "$out/transcript.vtt"
  jq -r '.txt'                 "$WORK/render.json" > "$out/transcript.txt"
  jq -r '.clean_txt'           "$WORK/render.json" > "$out/transcript.clean.txt"
  [ "$rawf" = "$out/assemblyai.raw.json" ]       || cp "$rawf" "$out/assemblyai.raw.json"
  [ "$senf" = "$out/assemblyai.sentences.json" ] || cp "$senf" "$out/assemblyai.sentences.json"
}

write_evidence() { # outdir
  local out="$1"
  jq -n \
    --arg tool "$TOOL" --arg version "$VERSION" \
    --arg started "$STARTED_ISO" --arg finished "$(now_iso)" \
    --argjson elapsed "$(( $(date +%s) - STARTED_EPOCH ))" \
    --arg mode "$MODE" \
    --arg input "${AUDIO:-}" --arg input_sha256 "${INPUT_SHA:-}" \
    --argjson input_bytes "${INPUT_BYTES:-0}" \
    --arg out_dir "$out" \
    --slurpfile stats <(jq '.stats' "$WORK/render.json") \
    '{claw: "ScribeClaw", tool: $tool, version: $version,
      handler: "transcribe_assemblyai_cli", mode: $mode,
      input: (if $input == "" then null
              else {path: $input, bytes: $input_bytes, sha256: $input_sha256} end),
      result: $stats[0],
      started_iso: $started, finished_iso: $finished, elapsed_sec: $elapsed,
      outputs: ["segments.json", "segments.clean.json", "transcript.srt",
                "transcript.vtt", "transcript.txt", "transcript.clean.txt",
                "assemblyai.raw.json", "assemblyai.sentences.json"],
      urantios_governed: true}' > "$out/evidence.json"
}

emit_summary() { # outdir
  jq -n --arg out_dir "$1" --slurpfile stats <(jq '.stats' "$WORK/render.json") \
    '{status: "success", handler: "transcribe_assemblyai_cli",
      output_dir: $out_dir} + $stats[0]'
}

fetch_sentences() { # transcript_id -> writes $WORK/sentences.json
  local code
  code="$(http_get "$API/transcript/$1/sentences" "$WORK/sentences.json")" \
    || die "network error fetching sentences (curl exit $?)"
  case "$code" in
    2*) : ;;
    404) printf '{"sentences":[]}\n' > "$WORK/sentences.json" ;;   # older transcripts
    *)  check_http "$code" "$WORK/sentences.json" "sentences" ;;
  esac
}

poll_transcript() { # transcript_id -> writes $WORK/raw.json
  local tid="$1" waited=0 code status
  while :; do
    code="$(http_get "$API/transcript/$tid" "$WORK/poll.json")" \
      || die "network error while polling (curl exit $?)"
    check_http "$code" "$WORK/poll.json" "poll"
    status="$(jq -r '.status // "unknown"' "$WORK/poll.json")"
    case "$status" in
      completed)
        progress_done
        mv "$WORK/poll.json" "$WORK/raw.json"
        return 0 ;;
      error)
        progress_done
        die "AssemblyAI job $tid failed: $(jq -r '.error // "unknown error"' "$WORK/poll.json")" ;;
    esac
    if [ "$waited" -ge "$TIMEOUT_SEC" ]; then
      progress_done
      die "still '$status' after ${waited}s — the job is not lost.
  Resume once it finishes with:  $TOOL --import $tid"
    fi
    progress "$status" "$waited"
    sleep "$POLL_SEC"
    waited=$((waited + POLL_SEC))
  done
}

# ── modes ────────────────────────────────────────────────────────────────────
STARTED_ISO="$(now_iso)"
STARTED_EPOCH="$(date +%s)"
WORK="$(mktemp -d "${TMPDIR:-/tmp}/c0087.XXXXXX")"
trap 'rm -rf "$WORK"' EXIT INT TERM

same_transcript() { # rawfile sentencesfile -> 0 when ids agree or are absent
  local a b
  a="$(jq -r '.id // empty' "$1" 2>/dev/null || true)"
  b="$(jq -r '.id // empty' "$2" 2>/dev/null || true)"
  [ -n "$a" ] && [ -n "$b" ] && [ "$a" != "$b" ] && return 1
  return 0
}

run_render() {
  [ -n "$RAW_IN" ] || die "--render needs a raw response file"
  [ -f "$RAW_IN" ] || die "raw response not found: $RAW_IN"
  jq -e 'type == "object"' "$RAW_IN" >/dev/null 2>&1 \
    || die "not a JSON object: $RAW_IN"

  local senf="$WORK/sentences.json" sibling
  sibling="$(dirname "$RAW_IN")/assemblyai.sentences.json"
  printf '{"sentences":[]}\n' > "$senf"
  if [ -n "$SENTENCES_IN" ]; then
    [ -f "$SENTENCES_IN" ] || die "--sentences file not found: $SENTENCES_IN"
    same_transcript "$RAW_IN" "$SENTENCES_IN" \
      || die "--sentences belongs to a different transcript than $RAW_IN"
    cp "$SENTENCES_IN" "$senf"
  elif [ "$(basename "$RAW_IN")" = "assemblyai.raw.json" ] && [ -f "$sibling" ]; then
    # Only auto-pair inside a ScribeClaw output dir, and only when the ids
    # agree — a stale neighbour must not silently reshape the transcript.
    if same_transcript "$RAW_IN" "$sibling"; then
      cp "$sibling" "$senf"
    else
      warn "ignoring $sibling — it belongs to a different transcript"
    fi
  fi

  [ -n "$OUT_DIR" ] || OUT_DIR="$(dirname "$RAW_IN")"
  log "-> re-rendering into $OUT_DIR"
  render_outputs "$RAW_IN" "$senf" "$OUT_DIR"
  write_evidence "$OUT_DIR"
  log "OK  $(jq -r '.stats.segments' "$WORK/render.json") segments written"
  emit_summary "$OUT_DIR"
}

run_import() {
  [ -n "$TRANSCRIPT_ID" ] || die "--import needs a transcript id"
  case "$TRANSCRIPT_ID" in
    *[!A-Za-z0-9._-]*) die "implausible transcript id: $TRANSCRIPT_ID" ;;
  esac
  resolve_api_key
  setup_curl
  [ -n "$OUT_DIR" ] || OUT_DIR="./transcripts/$TRANSCRIPT_ID"

  if [ "$DRY_RUN" -eq 1 ]; then
    log "dry run — would GET $API/transcript/$TRANSCRIPT_ID"
    jq -n --arg id "$TRANSCRIPT_ID" --arg out "$OUT_DIR" --arg key_src "$API_KEY_SRC" \
      '{status: "dry_run", mode: "import", transcript_id: $id,
        output_dir: $out, api_key_source: $key_src}'
    return 0
  fi

  log "-> fetching transcript $TRANSCRIPT_ID"
  local code status
  code="$(http_get "$API/transcript/$TRANSCRIPT_ID" "$WORK/raw.json")" \
    || die "network error fetching transcript (curl exit $?)"
  check_http "$code" "$WORK/raw.json" "fetch"
  status="$(jq -r '.status // "unknown"' "$WORK/raw.json")"
  [ "$status" = "completed" ] \
    || die "transcript $TRANSCRIPT_ID is '$status', not completed — wait for it to finish, or transcribe the audio instead"

  fetch_sentences "$TRANSCRIPT_ID"
  render_outputs "$WORK/raw.json" "$WORK/sentences.json" "$OUT_DIR"
  write_evidence "$OUT_DIR"
  log "OK  $OUT_DIR"
  emit_summary "$OUT_DIR"
}

run_transcribe() {
  [ -n "$AUDIO" ] || die "no audio file given (try --help)"
  [ -e "$AUDIO" ] || die "audio file not found: $AUDIO"
  [ -f "$AUDIO" ] || die "not a regular file: $AUDIO"
  [ -r "$AUDIO" ] || die "audio file is not readable: $AUDIO"
  INPUT_BYTES="$(bytes_of "$AUDIO")"
  [ "$INPUT_BYTES" -gt 0 ] || die "audio file is empty: $AUDIO"

  resolve_api_key
  setup_curl

  local stem base
  base="$(basename "$AUDIO")"
  stem="${base%.*}"
  [ -n "$OUT_DIR" ] || OUT_DIR="$(dirname "$AUDIO")/transcripts/$stem"

  jq -n \
    --arg language "$LANGUAGE" \
    --argjson detect "$DETECT_LANGUAGE" \
    --argjson speaker "$SPEAKER_LABELS" \
    --argjson punctuate "$PUNCTUATE" \
    --argjson format_text "$FORMAT_TEXT" \
    --arg model "$SPEECH_MODEL" \
    '{punctuate: ($punctuate != 0),
      format_text: ($format_text != 0),
      speaker_labels: ($speaker != 0)}
     + (if $detect != 0 then {language_detection: true} else {language_code: $language} end)
     + (if $model != "" then {speech_model: $model} else {} end)' > "$WORK/job.json"

  if [ "$DRY_RUN" -eq 1 ]; then
    log "dry run — nothing sent. Request body that would follow the upload:"
    jq -n --slurpfile body "$WORK/job.json" --arg audio "$AUDIO" \
          --argjson bytes "$INPUT_BYTES" --arg out "$OUT_DIR" \
          --arg key_src "$API_KEY_SRC" \
      '{status: "dry_run", mode: "transcribe",
        input: {path: $audio, bytes: $bytes}, output_dir: $out,
        api_key_source: $key_src,
        request: ($body[0] + {audio_url: "<set after upload>"})}'
    return 0
  fi

  [ -d "$OUT_DIR" ] && warn "output directory exists — files will be overwritten: $OUT_DIR"
  INPUT_SHA="$(sha256_of "$AUDIO")"

  log "-> uploading $base ($(human_size "$INPUT_BYTES"))"
  local code upload_url tid
  code="$(http_upload "$AUDIO" "$WORK/upload.json")" \
    || die "network error during upload (curl exit $?)"
  check_http "$code" "$WORK/upload.json" "upload"
  upload_url="$(jq -r '.upload_url // empty' "$WORK/upload.json")"
  [ -n "$upload_url" ] || die "upload succeeded but no upload_url came back"

  jq --arg u "$upload_url" '. + {audio_url: $u}' "$WORK/job.json" > "$WORK/job.final.json"
  log "-> starting job (language: $([ "$DETECT_LANGUAGE" -eq 1 ] && echo auto-detect || echo "$LANGUAGE")\
$([ "$SPEAKER_LABELS" -eq 1 ] && echo ", diarized" || true))"
  code="$(http_post_json "$API/transcript" "$WORK/job.final.json" "$WORK/job.resp.json")" \
    || die "network error starting the job (curl exit $?)"
  check_http "$code" "$WORK/job.resp.json" "job start"
  tid="$(jq -r '.id // empty' "$WORK/job.resp.json")"
  [ -n "$tid" ] || die "job started but no transcript id came back"
  log "   transcript id: $tid"

  poll_transcript "$tid"
  fetch_sentences "$tid"
  render_outputs "$WORK/raw.json" "$WORK/sentences.json" "$OUT_DIR"
  write_evidence "$OUT_DIR"
  log "OK  $OUT_DIR"
  emit_summary "$OUT_DIR"
}

case "$MODE" in
  render)     run_render ;;
  import)     run_import ;;
  transcribe) run_transcribe ;;
esac
