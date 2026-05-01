# ScribeClaw

**Truthful label:** deployable scaffold. Real handlers: `media_edit`,
`audio_extract`, `transcribe_ro`, `transcribe_assemblyai`,
`import_assemblyai_transcript`, `postprocess_transcript`,
`youtube_metadata`. Stub: `youtube_upload` (refuses — operator must
supply OAuth credentials in a follow-up PR).

Singular primary role: **controlled execution** (media-pipeline sub-role).
Does not observe, remediate, adjudicate, explain, or bundle evidence —
those belong to NemoClaw / Fireclaw / LuciferiClaw / VisualUrantiClaw /
Paperclip respectively. This module emits evidence records on every
handler call; Paperclip owns the bundling contract once it ships.

UrantiOS governed — Truth, Beauty, Goodness.

---

## Canonical sentence

> NemoClaw sees. VisualUrantiClaw explains. Fireclaw reacts to technical
> faults. LuciferiClaw adjudicates intent and mandate violation.
> **OpenClaw instances execute.** Paperclip preserves the evidence.

ScribeClaw is another OpenClaw-class instance. Same role (controlled
execution), different sub-scope: media editing, Romanian transcription,
YouTube packaging.

---

## Pipeline

```
  /data/media/in/<video>               # operator drops source here
          │
          ▼    media_edit              # ffmpeg: trim / loudnorm / silence
  /data/media/edited/<video>.edited.<ext>
          │
          ▼    audio_extract           # ffmpeg: 16 kHz mono WAV
  /data/media/audio/<stem>.wav
          │
          ▼    transcribe_ro           # faster-whisper, language="ro"
  /data/transcripts/<stem>/
      segments.json, transcript.srt, .vtt, .txt
          │
          ▼    postprocess_transcript  # cedilla→comma-below, punctuation
      segments.clean.json, transcript.clean.txt
          │
          ▼    youtube_metadata        # title candidates + chapters + tags
  /data/youtube/<stem>/
      bundle.json, description.txt, tags.txt, thumbnail.spec.txt
          │
          ▼    youtube_upload          # stub (requires OAuth)
```

Every step emits an evidence record under `/data/evidence/`.

---

## Allowlist — the canonical boundary

```python
ALLOWED_HANDLERS = {
    "smoke_test",
    "media_edit",                    # REAL — ffmpeg required on PATH
    "audio_extract",                 # REAL — ffmpeg required on PATH
    "transcribe_ro",                 # REAL — faster-whisper, offline
    "transcribe_assemblyai",            # REAL — AssemblyAI, needs API key
    "import_assemblyai_transcript",     # REAL — reuse a dashboard transcript by id
    "bulk_import_assemblyai_romanian",  # REAL — clone every Romanian transcript
    "postprocess_transcript",        # REAL — deterministic, no LLM
    "youtube_metadata",                 # REAL — deterministic packaging
    "youtube_upload",                   # STUB — refuses without OAuth creds
    "export_obsidian",                  # REAL — writes transcript into vault
}
```

Anything outside this set is **rejected** with an evidence record
stamped `status: rejected`. No free-form shell. No `--command` escape.

---

## Install + run

```bash
cd ~/mircea-constellation
bash setup/scribeclaw_install.sh
```

The installer:
1. Discovers UID/GID via `id -u` / `id -g` (no hardcoding).
2. Creates `/opt/scribeclaw-data/` with correct ownership.
3. Writes `scribeclaw/.env` with `HOST_UID`, `HOST_GID`, Whisper defaults.
4. Runs `docker compose up --build -d` from `scribeclaw/`.
5. Waits for `/health` to respond.

### Verify

```bash
docker logs scribeclaw --tail 30
curl -s http://127.0.0.1:8081/health | python3 -m json.tool
```

`/health` returns `ffmpeg_on_path` and `faster_whisper_installed`
honestly. If either is `false`, the related handlers will refuse with a
clear error, not silently fail.

---

## Invoke a handler

The only way to run handlers is `POST /tasks` (bound to `127.0.0.1:8081`):

```bash
# 1. Drop a Romanian video
cp /path/to/interviu.mp4 /opt/scribeclaw-data/media/in/

# 2. Edit
curl -sX POST http://127.0.0.1:8081/tasks \
  -H 'Content-Type: application/json' \
  -d '{"handler":"media_edit","payload":{"input":"interviu.mp4","loudnorm":true,"remove_silence":true}}'

# 3. Extract audio
curl -sX POST http://127.0.0.1:8081/tasks \
  -H 'Content-Type: application/json' \
  -d '{"handler":"audio_extract","payload":{"input":"interviu.edited.mp4"}}'

# 4. Transcribe (Romanian)
curl -sX POST http://127.0.0.1:8081/tasks \
  -H 'Content-Type: application/json' \
  -d '{"handler":"transcribe_ro","payload":{"input":"interviu.edited.wav","model":"large-v3"}}'

# 5. Post-process diacritics + punctuation
curl -sX POST http://127.0.0.1:8081/tasks \
  -H 'Content-Type: application/json' \
  -d '{"handler":"postprocess_transcript","payload":{"stem":"interviu.edited"}}'

# 6. YouTube bundle
curl -sX POST http://127.0.0.1:8081/tasks \
  -H 'Content-Type: application/json' \
  -d '{"handler":"youtube_metadata","payload":{"stem":"interviu.edited","channel_footer":"Canal Mircea — https://..."}}'
```

Or run the whole chain in one shot from the CLI (not the HTTP surface):

```bash
docker exec -it scribeclaw python -m scribeclaw.main --mode pipeline --input interviu.mp4
```

### AssemblyAI alternative — reuse the dashboard instead of re-transcribing

If you already use AssemblyAI (e.g. transcripts sitting in
`/dashboard/transcription-history`), you can either submit new jobs
through ScribeClaw or import a completed transcript by id. Set
`ASSEMBLYAI_API_KEY` in `scribeclaw/.env` first.

```bash
# New job — upload local audio, AssemblyAI transcribes (language=ro by default)
curl -sX POST http://127.0.0.1:8081/tasks \
  -H 'Content-Type: application/json' \
  -d '{"handler":"transcribe_assemblyai","payload":{"input":"interviu.edited.wav","speaker_labels":true}}'

# Reuse an already-completed transcript from your dashboard
curl -sX POST http://127.0.0.1:8081/tasks \
  -H 'Content-Type: application/json' \
  -d '{"handler":"import_assemblyai_transcript","payload":{"transcript_id":"<id-from-dashboard>","stem":"interviu"}}'

# Clone ONLY the Romanian transcripts from the dashboard in bulk
# (idempotent — already-downloaded ids are skipped)
curl -sX POST http://127.0.0.1:8081/tasks \
  -H 'Content-Type: application/json' \
  -d '{"handler":"bulk_import_assemblyai_romanian","payload":{"max_transcripts":50}}'
```

The bulk handler pages through completed transcripts, fetches each detail
to check `language_code == "ro"`, writes the matches to
`/data/transcripts/<id>/`, and returns a `resume_before_id` that you can
pass back as `start_before_id` to continue where the previous run stopped
(useful for dashboards with hundreds of items).

### Export into an Obsidian vault

Once a transcript exists under `/data/transcripts/<stem>/` (and,
optionally, a YouTube bundle under `/data/youtube/<stem>/`), render it
as a single markdown note inside your vault:

```bash
# Set OBSIDIAN_VAULT_HOST in scribeclaw/.env before starting the container
# so the host vault is bind-mounted into /vault inside the container.

curl -sX POST http://127.0.0.1:8081/tasks \
  -H 'Content-Type: application/json' \
  -d '{"handler":"export_obsidian","payload":{"stem":"interviu","subdir":"Transcripts"}}'
```

The note carries YAML front-matter (`title`, `language`, `duration_sec`,
`assemblyai_id`, `tags`) plus title-candidate bullets, a chapters
section, and the full transcript with per-segment timestamps. If no
vault is configured the handler refuses with `vault_path_missing` —
it will not silently write somewhere unexpected.

Both write the same `segments.json`/`.srt`/`.vtt`/`.txt` layout as
`transcribe_ro`, so `postprocess_transcript` → `youtube_metadata` run
unchanged afterwards. The raw AssemblyAI response is preserved at
`/data/transcripts/<stem>/assemblyai.raw.json` for provenance.

---

## Configuration surface

| Env var            | Default        | Purpose                                  |
|--------------------|----------------|------------------------------------------|
| `CLAW_NAME`        | `ScribeClaw`   | Logged on every record                   |
| `DATA_ROOT`        | `/data`        | Bind-mounted host path                   |
| `LOG_LEVEL`        | `INFO`         |                                          |
| `HTTP_PORT`        | `8081`         |                                          |
| `WHISPER_MODEL`    | `large-v3`     | faster-whisper model id                  |
| `WHISPER_DEVICE`   | `cpu`          | `cpu` or `cuda` (explicit opt-in)        |
| `WHISPER_COMPUTE`  | `int8`         | int8 on CPU, float16 on CUDA recommended |
| `WHISPER_CACHE_DIR`| `/data/models` | Model download location                  |
| `ASSEMBLYAI_API_KEY`| *(unset)*     | Enables AssemblyAI handlers when present |
| `OBSIDIAN_VAULT`   | *(unset)*      | Container-side vault path for `export_obsidian` |

---

## What this is **not** yet

- Not a live uploader. `youtube_upload` refuses until an operator
  provides `client_secret.json` under `/data/youtube/credentials/`
  and a follow-up PR wires `google-api-python-client`.
- Not an LLM-assisted re-punctuator. `postprocess_transcript` is
  deterministic (cedilla normalization, punctuation spacing). A
  language-model pass belongs in a separate handler.
- Not a speaker-diarizer. Whisper `word_timestamps` are stored; a
  diarization handler can be added without touching the pipeline.
- Not a GPU auto-detector. `WHISPER_DEVICE=cuda` is explicit opt-in
  to avoid silent fallback.
- Not Paperclip-integrated. Emits evidence records; bundling will come
  from Paperclip under its own contract.
