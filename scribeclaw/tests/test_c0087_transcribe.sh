#!/usr/bin/env bash
#
# Offline tests for scribeclaw/C0087_transcribe.sh.
#
# Covers the two things that break silently in a transcription CLI:
#   1. refusals — bad args, missing file, missing/garbled API key
#   2. rendering — timestamps, diarization, Romanian cleanup, fallbacks
#
# The end-to-end block runs the real script against a stub AssemblyAI server
# on localhost (needs python3), so upload / job start / polling / import are
# exercised without touching the network or spending API credit.
#
# Run from the repo root:
#   bash scribeclaw/tests/test_c0087_transcribe.sh

set -uo pipefail

SCRIPT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)/C0087_transcribe.sh"
TMP="$(mktemp -d "${TMPDIR:-/tmp}/c0087test.XXXXXX")"
SERVER_PID=""
PASS=0
FAIL=0

# localhost must never go through a proxy, in CI or on a laptop
export no_proxy="127.0.0.1,localhost" NO_PROXY="127.0.0.1,localhost"

cleanup() {
  [ -n "$SERVER_PID" ] && kill "$SERVER_PID" 2>/dev/null
  rm -rf "$TMP"
  return 0
}
trap cleanup EXIT INT TERM

ok()   { PASS=$((PASS + 1)); printf '  ok   %s\n' "$1"; }
bad()  { FAIL=$((FAIL + 1)); printf '  FAIL %s\n' "$1"; shift; [ $# -gt 0 ] && printf '       %s\n' "$@"; return 0; }
group(){ printf '\n%s\n' "$1"; }

assert_eq() { # expected actual label
  if [ "$1" = "$2" ]; then ok "$3"; else bad "$3" "expected: $1" "actual:   $2"; fi
}

assert_contains() { # haystack needle label
  case "$1" in
    *"$2"*) ok "$3" ;;
    *)      bad "$3" "missing: $2" "in:      $(printf '%s' "$1" | head -3)" ;;
  esac
}

assert_status() { # expected_exit label command...
  local want="$1" label="$2"; shift 2
  "$@" >/dev/null 2>&1
  assert_eq "$want" "$?" "$label"
}

# ── fixtures ─────────────────────────────────────────────────────────────────
mkdir -p "$TMP/fx"

cat > "$TMP/fx/raw.json" <<'JSON'
{"id": "fixture-1", "status": "completed", "language_code": "ro",
 "audio_duration": 3671.25, "speech_model": "best",
 "text": "Bună seara, fraţi şi surori."}
JSON

cat > "$TMP/fx/sentences.json" <<'JSON'
{"id": "fixture-1", "sentences": [
  {"start": 120,  "end": 3500,    "text": "  Bună seara, fraţi şi surori.  "},
  {"start": 3500, "end": 9000,    "text": "Astăzi vorbim despre religia lui Isus ."},
  {"start": 9000, "end": 3671250, "text": "Religia lui Isus nu este religia despre Isus."}]}
JSON

cat > "$TMP/fx/diarized.json" <<'JSON'
{"id": "fixture-2", "status": "completed", "language_code": "ro",
 "audio_duration": 12, "speech_model": "best", "text": "ignored when utterances exist",
 "utterances": [
   {"speaker": "A", "start": 0,    "end": 4000,  "text": "Bună, cum eşti?",
    "words": [{"start": 0, "end": 500, "text": "Bună", "confidence": 0.98}]},
   {"speaker": "B", "start": 4000, "end": 12000, "text": "Mulţumesc, bine."}]}
JSON

cat > "$TMP/fx/textonly.json" <<'JSON'
{"id": "fixture-3", "status": "completed", "language_code": "ro",
 "audio_duration": 5, "text": "   Doar text, fără segmente.   "}
JSON

printf 'testkey123\n' > "$TMP/fx/key.txt"
printf '# a .env\nOTHER=1\nexport ASSEMBLYAI_API_KEY="testkey123"\n' > "$TMP/fx/key.env"
head -c 4096 /dev/urandom > "$TMP/fx/audio.mp3"
: > "$TMP/fx/empty.mp3"

# ── 1. surface + refusals ────────────────────────────────────────────────────
group "surface + refusals"

out="$(bash "$SCRIPT" --help 2>&1)"; rc=$?
assert_eq 0 "$rc" "--help exits 0"
assert_contains "$out" "USAGE" "--help prints usage"

assert_status 2 "no arguments exits 2" bash "$SCRIPT"
assert_status 0 "--version exits 0" bash "$SCRIPT" --version

out="$(bash "$SCRIPT" --bogus 2>&1)"; rc=$?
assert_eq 1 "$rc" "unknown option exits 1"
assert_contains "$out" "unknown option" "unknown option is named"

out="$(env ASSEMBLYAI_API_KEY=testkey123 bash "$SCRIPT" /nope/missing.mp3 2>&1)"
assert_contains "$out" "not found" "missing audio file is refused"

out="$(env ASSEMBLYAI_API_KEY=testkey123 bash "$SCRIPT" "$TMP/fx/empty.mp3" 2>&1)"
assert_contains "$out" "empty" "empty audio file is refused"

out="$(env ASSEMBLYAI_API_KEY=testkey123 bash "$SCRIPT" "$TMP/fx" 2>&1)"
assert_contains "$out" "not a regular file" "a directory is refused"

out="$(env -u ASSEMBLYAI_API_KEY HOME="$TMP/nohome" bash "$SCRIPT" "$TMP/fx/audio.mp3" 2>&1)"
assert_contains "$out" "ASSEMBLYAI_API_KEY is not set" "missing key is refused with a fix"

out="$(env ASSEMBLYAI_API_KEY='key with spaces' bash "$SCRIPT" "$TMP/fx/audio.mp3" 2>&1)"
assert_contains "$out" "unexpected characters" "garbled key is refused"

out="$(env ASSEMBLYAI_API_KEY=testkey123 bash "$SCRIPT" --poll-sec abc "$TMP/fx/audio.mp3" 2>&1)"
assert_contains "$out" "whole seconds" "non-numeric --poll-sec is refused"

# ── 2. key discovery + request shaping (dry run, no network) ─────────────────
group "key discovery + request shaping"

out="$(env -u ASSEMBLYAI_API_KEY bash "$SCRIPT" --dry-run --api-key-file "$TMP/fx/key.txt" "$TMP/fx/audio.mp3" 2>/dev/null)"
assert_eq "$TMP/fx/key.txt" "$(printf '%s' "$out" | jq -r .api_key_source)" "bare key file is read"

out="$(env -u ASSEMBLYAI_API_KEY bash "$SCRIPT" --dry-run --api-key-file "$TMP/fx/key.env" "$TMP/fx/audio.mp3" 2>/dev/null)"
assert_eq "$TMP/fx/key.env" "$(printf '%s' "$out" | jq -r .api_key_source)" ".env-style key file is read"

mkdir -p "$TMP/home"
cp "$TMP/fx/key.txt" "$TMP/home/.assemblyai"
out="$(env -u ASSEMBLYAI_API_KEY HOME="$TMP/home" bash "$SCRIPT" --dry-run "$TMP/fx/audio.mp3" 2>/dev/null)"
assert_eq "$TMP/home/.assemblyai" "$(printf '%s' "$out" | jq -r .api_key_source)" "the .assemblyai dotfile in HOME is discovered"

mkdir -p "$TMP/portable"
cp "$SCRIPT" "$TMP/portable/"
cp "$TMP/fx/key.env" "$TMP/portable/.env"
out="$(env -u ASSEMBLYAI_API_KEY HOME="$TMP/nohome" bash "$TMP/portable/C0087_transcribe.sh" --dry-run "$TMP/fx/audio.mp3" 2>/dev/null)"
assert_eq "$TMP/portable/.env" "$(printf '%s' "$out" | jq -r .api_key_source)" "<script dir>/.env is discovered"

out="$(env ASSEMBLYAI_API_KEY=testkey123 bash "$SCRIPT" --dry-run "$TMP/fx/audio.mp3" 2>/dev/null)"
assert_eq "ro" "$(printf '%s' "$out" | jq -r .request.language_code)" "language defaults to ro"
assert_eq "false" "$(printf '%s' "$out" | jq -r .request.speaker_labels)" "diarization is off by default"
assert_eq "$TMP/fx/transcripts/audio" "$(printf '%s' "$out" | jq -r .output_dir)" "output dir defaults beside the audio"

out="$(env ASSEMBLYAI_API_KEY=testkey123 bash "$SCRIPT" --dry-run --detect-language -s -m nano "$TMP/fx/audio.mp3" 2>/dev/null)"
assert_eq "true" "$(printf '%s' "$out" | jq -r .request.language_detection)" "--detect-language sets language_detection"
assert_eq "null" "$(printf '%s' "$out" | jq -r '.request.language_code // "null"')" "--detect-language drops language_code"
assert_eq "true" "$(printf '%s' "$out" | jq -r .request.speaker_labels)" "-s requests diarization"
assert_eq "nano" "$(printf '%s' "$out" | jq -r .request.speech_model)" "-m sets speech_model"

out="$(env ASSEMBLYAI_API_KEY=testkey123 bash "$SCRIPT" --dry-run --out-dir="$TMP/eq" "$TMP/fx/audio.mp3" 2>/dev/null)"
assert_eq "$TMP/eq" "$(printf '%s' "$out" | jq -r .output_dir)" "--opt=value form is accepted"

# ── 3. rendering ─────────────────────────────────────────────────────────────
group "rendering"

bash "$SCRIPT" --render "$TMP/fx/raw.json" --sentences "$TMP/fx/sentences.json" \
     --out-dir "$TMP/r1" -q >/dev/null 2>&1
for f in segments.json segments.clean.json transcript.srt transcript.vtt \
         transcript.txt transcript.clean.txt assemblyai.raw.json \
         assemblyai.sentences.json evidence.json; do
  if [ -s "$TMP/r1/$f" ]; then ok "wrote $f"; else bad "wrote $f"; fi
done

assert_eq 3 "$(jq '.segments | length' "$TMP/r1/segments.json")" "one segment per sentence"
assert_eq "0.12" "$(jq -r '.segments[0].start' "$TMP/r1/segments.json")" "ms converted to seconds"
assert_contains "$(cat "$TMP/r1/transcript.srt")" "00:00:00,120 --> 00:00:03,500" "SRT timestamps"
assert_contains "$(cat "$TMP/r1/transcript.srt")" "01:01:11,250" "SRT handles past one hour"
assert_contains "$(cat "$TMP/r1/transcript.vtt")" "00:00:00.120 --> 00:00:03.500" "VTT timestamps"
assert_eq "WEBVTT" "$(head -1 "$TMP/r1/transcript.vtt")" "VTT header"

assert_contains "$(cat "$TMP/r1/transcript.txt")" "fraţi şi surori" "raw .txt keeps AssemblyAI text verbatim"
assert_contains "$(cat "$TMP/r1/transcript.clean.txt")" "frați și surori" "clean .txt normalizes cedilla to comma-below"
assert_contains "$(cat "$TMP/r1/transcript.clean.txt")" "religia lui Isus." "clean .txt removes the space before punctuation"
assert_eq 3 "$(grep -c . "$TMP/r1/transcript.clean.txt")" "clean .txt reflows into one paragraph per sentence"
assert_eq "Bună seara, fraţi şi surori." "$(jq -r '.segments[0].text' "$TMP/r1/segments.json")" "segment text is trimmed but unmodified"
assert_eq "Bună seara, frați și surori." "$(jq -r '.segments[0].text' "$TMP/r1/segments.clean.json")" "clean segments carry cleaned text"
assert_eq "fixture-1" "$(jq -r '.assemblyai_id' "$TMP/r1/segments.json")" "transcript id is preserved"
assert_eq "assemblyai:best" "$(jq -r '.model' "$TMP/r1/segments.json")" "model is recorded"
assert_eq "null" "$(jq -r '.segments[0].words // "null"' "$TMP/r1/segments.json")" "word timestamps are dropped by default"

bash "$SCRIPT" --render "$TMP/fx/diarized.json" --out-dir "$TMP/r2" --words -q >/dev/null 2>&1
assert_eq "A" "$(jq -r '.segments[0].speaker' "$TMP/r2/segments.json")" "utterances carry speakers"
assert_contains "$(cat "$TMP/r2/transcript.srt")" "Speaker A: Bună, cum eşti?" "SRT labels speakers"
assert_contains "$(cat "$TMP/r2/transcript.clean.txt")" "Speaker B: Mulțumesc, bine." "clean .txt keeps speaker turns"
assert_eq "Bună" "$(jq -r '.segments[0].words[0].word' "$TMP/r2/segments.json")" "--words keeps word timestamps"
assert_eq "0.5" "$(jq -r '.segments[0].words[0].end' "$TMP/r2/segments.json")" "word timestamps are in seconds"

bash "$SCRIPT" --render "$TMP/fx/textonly.json" --out-dir "$TMP/r3" -q >/dev/null 2>&1
assert_eq 1 "$(jq '.segments | length' "$TMP/r3/segments.json")" "falls back to a single segment"
assert_eq "Doar text, fără segmente." "$(jq -r '.segments[0].text' "$TMP/r3/segments.json")" "fallback text is trimmed"

out="$(bash "$SCRIPT" --render "$TMP/fx/textonly.json" --sentences "$TMP/fx/sentences.json" --out-dir "$TMP/r4" -q 2>&1)"; rc=$?
assert_eq 1 "$rc" "sentences from another transcript are refused"
assert_contains "$out" "different transcript" "mismatch says why"

mkdir -p "$TMP/r5"
cp "$TMP/fx/textonly.json" "$TMP/r5/assemblyai.raw.json"
cp "$TMP/fx/sentences.json" "$TMP/r5/assemblyai.sentences.json"
out="$(bash "$SCRIPT" --render "$TMP/r5/assemblyai.raw.json" -q 2>&1)"; rc=$?
assert_contains "$out" "ignoring" "a stale sibling sentences file is ignored"
assert_eq 1 "$(jq '.segments | length' "$TMP/r5/segments.json")" "stale sibling does not reshape the transcript"

out="$(bash "$SCRIPT" --render "$TMP/fx/key.txt" --out-dir "$TMP/r6" -q 2>&1)"; rc=$?
assert_eq 1 "$rc" "non-JSON input to --render is refused"

# ── 4. end-to-end against a stub AssemblyAI (needs python3) ──────────────────
group "end-to-end (stub AssemblyAI)"

if ! command -v python3 >/dev/null 2>&1; then
  printf '  skip python3 not available — end-to-end block skipped\n'
else
  cat > "$TMP/stub.py" <<'PY'
"""Smallest AssemblyAI stand-in that the CLI can drive end to end."""
import json, sys
from http.server import BaseHTTPRequestHandler, HTTPServer

KEY = "testkey123"
STATE = {"uploaded": 0, "polls": 0, "request": None}
RAW = {"id": "stub-1", "status": "completed", "language_code": "ro",
       "audio_duration": 9.0, "speech_model": "best", "text": "Bună seara. Aşa să fie."}
SENTENCES = {"id": "stub-1", "sentences": [
    {"start": 0, "end": 4000, "text": "Bună seara."},
    {"start": 4000, "end": 9000, "text": "Aşa să fie ."}]}


class H(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def _send(self, code, obj):
        body = json.dumps(obj).encode()
        self.send_response(code)
        self.send_header("content-type", "application/json")
        self.send_header("content-length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _auth_ok(self):
        if self.path.endswith("/__state"):
            return True
        if self.headers.get("authorization") != KEY:
            self._send(401, {"error": "authentication failed"})
            return False
        return True

    def do_POST(self):
        if not self._auth_ok():
            return
        body = self.rfile.read(int(self.headers.get("content-length") or 0))
        if self.path.endswith("/upload"):
            STATE["uploaded"] = len(body)
            return self._send(200, {"upload_url": "https://cdn.example/stub"})
        if self.path.endswith("/transcript"):
            STATE["request"] = json.loads(body or b"{}")
            return self._send(200, {"id": RAW["id"], "status": "queued"})
        self._send(404, {"error": "no such route"})

    def do_GET(self):
        if not self._auth_ok():
            return
        if self.path.endswith("/__state"):
            return self._send(200, STATE)
        if self.path.endswith("/sentences"):
            return self._send(200, SENTENCES)
        if "/transcript/" in self.path:
            STATE["polls"] += 1
            if STATE["polls"] < 3:      # queued -> processing -> completed
                return self._send(200, {"id": RAW["id"], "status":
                                        "queued" if STATE["polls"] == 1 else "processing"})
            return self._send(200, RAW)
        self._send(404, {"error": "no such route"})


HTTPServer(("127.0.0.1", int(sys.argv[1])), H).serve_forever()
PY

  PORT="$(python3 -c 'import socket;s=socket.socket();s.bind(("127.0.0.1",0));print(s.getsockname()[1]);s.close()')"
  python3 "$TMP/stub.py" "$PORT" >/dev/null 2>&1 &
  SERVER_PID=$!
  BASE="http://127.0.0.1:$PORT/v2"

  ready=0
  for _ in 1 2 3 4 5 6 7 8 9 10; do
    curl -sf "$BASE/__state" >/dev/null 2>&1 && { ready=1; break; }
    sleep 0.3
  done

  if [ "$ready" -ne 1 ]; then
    bad "stub AssemblyAI came up"
  else
    ok "stub AssemblyAI came up"

    out="$(env ASSEMBLYAI_API_BASE="$BASE" ASSEMBLYAI_API_KEY=testkey123 \
           bash "$SCRIPT" --poll-sec 1 -s -o "$TMP/e2e" "$TMP/fx/audio.mp3" 2>/dev/null)"
    assert_eq 0 "$?" "transcribe run succeeds"
    assert_eq "success" "$(printf '%s' "$out" | jq -r .status)" "summary reports success"
    assert_eq 2 "$(printf '%s' "$out" | jq -r .segments)" "summary counts segments"

    state="$(curl -s "$BASE/__state")"
    assert_eq 4096 "$(printf '%s' "$state" | jq -r .uploaded)" "the whole audio file was uploaded"
    assert_eq "true" "$(printf '%s' "$state" | jq -r .request.speaker_labels)" "-s reached the API"
    assert_eq "https://cdn.example/stub" "$(printf '%s' "$state" | jq -r .request.audio_url)" "upload_url is passed to the job"
    assert_eq 3 "$(printf '%s' "$state" | jq -r .polls)" "polled until completed"

    assert_contains "$(cat "$TMP/e2e/transcript.clean.txt")" "Așa să fie." "end-to-end output is cleaned"
    if command -v sha256sum >/dev/null 2>&1; then
      want="$(sha256sum "$TMP/fx/audio.mp3" | awk '{print $1}')"
    else
      want="$(shasum -a 256 "$TMP/fx/audio.mp3" | awk '{print $1}')"
    fi
    assert_eq "$want" "$(jq -r '.input.sha256' "$TMP/e2e/evidence.json")" "evidence records the input digest"
    assert_eq 4096 "$(jq -r '.input.bytes' "$TMP/e2e/evidence.json")" "evidence records the input size"

    out="$(env ASSEMBLYAI_API_BASE="$BASE" ASSEMBLYAI_API_KEY=testkey123 \
           bash "$SCRIPT" --import stub-1 -o "$TMP/imported" 2>/dev/null)"
    assert_eq 2 "$(printf '%s' "$out" | jq -r .segments)" "--import rebuilds outputs without uploading"

    out="$(env ASSEMBLYAI_API_BASE="$BASE" ASSEMBLYAI_API_KEY=wrongkey \
           bash "$SCRIPT" --import stub-1 -o "$TMP/denied" 2>&1)"
    assert_contains "$out" "rejected the key" "a 401 is reported as a key problem"
  fi
fi

# ── summary ──────────────────────────────────────────────────────────────────
printf '\n%s\n' "----------------------------------------"
printf 'passed: %d   failed: %d\n' "$PASS" "$FAIL"
[ "$FAIL" -eq 0 ] || exit 1
printf 'all good\n'
