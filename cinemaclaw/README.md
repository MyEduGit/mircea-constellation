# CinemaClaw — YouTube Video Pipeline

> **Canonical claw map:**
> NemoClaw sees · Fireclaw reacts · LuciferiClaw adjudicates ·
> OpenClaw runs · NanoClaw serves at the edge ·
> **CinemaClaw renders the moving image** ·
> Paperclip preserves the evidence.

CinemaClaw is the Claw of the moving image. It turns raw footage into
YouTube-ready artefacts — cut, loudness-normalised, thumbnailed, and
metadata-tagged — via an ordered, declarative pipeline expressed in
`pipeline.yaml`.

Governance: UrantiOS — Truth, Beauty, Goodness.

---

## Truth label (v0.1.0)

- **REAL**       — `ingest`, `probe`, `render_thumbnail`
- **RENDER**     — `trim`, `normalize_audio`, `concat`, `burn_captions`
  (all real ffmpeg invocations; require `ffmpeg`/`ffprobe` on PATH)
- **STAGED**     — `write_metadata` (writes a YouTube-upload-ready
  sidecar; never touches the network)
- **DRY-ONLY**   — `publish_youtube` (validates every precondition
  including the Father Function signature, then refuses. API wiring
  is deliberately a follow-up PR — see "Publishing" below.)

CinemaClaw does not claim to have features it doesn't. The stage
taxonomy is the contract; anything missing lives as a stub that
refuses loudly.

---

## Responsibilities (and only these)

- Ingest raw video into a canonical inbox
- Cut, concatenate, and trim segments losslessly where possible
- Loudness-normalise audio to YouTube's reference (~-14 LUFS)
- Burn captions for Shorts / social cuts where soft subs don't survive
- Extract a YouTube-sized thumbnail frame
- Write a schema-versioned metadata sidecar (`cinemaclaw.metadata/v1`)
- Stage everything an upload needs — without pushing to YouTube
- Append an evidence record for every stage (including refusals)

## Non-responsibilities

- ✗ Not a general executor (use OpenClaw)
- ✗ Not a publisher by default (publish is DRY-ONLY in v0.1.0 — and even
  once wired, requires `--signed-by-father`)
- ✗ Not a transcript generator (bring your own `.srt`; whisper wiring
  belongs in a sibling module)
- ✗ Not a dashboard (use NemoClaw)
- ✗ Not a bundler (use Paperclip when it ships)

---

## Architecture

```
  inbox/*.mp4 ──► probe ──► trim ──► [concat] ──► normalize_audio ──► thumbnail
                                                           │                 │
                                                           ▼                 ▼
                                                    outbox/final.mp4   outbox/thumb.jpg
                                                           │
                                                           ▼
                                                    write_metadata
                                                           │
                                                           ▼
                                                   outbox/metadata.json
                                                           │
                                                           ▼
                                                    publish_youtube
                                                     (DRY-ONLY; requires
                                                      --signed-by-father)
```

Inputs live under `~/cinemaclaw/inbox/`. Intermediate artefacts go to
`~/cinemaclaw/work/<pipeline_id>/`. Uploadable output bundles land in
`~/cinemaclaw/outbox/<pipeline_id>/`.

---

## Files

| File                                  | Purpose                                                      |
|---------------------------------------|--------------------------------------------------------------|
| `cinemaclaw.py`                       | CLI + pipeline runner (loads YAML, substitutes vars, runs).  |
| `handlers.py`                         | The stage allowlist. Nothing outside it can execute.         |
| `pipeline.yaml`                       | Declared pipelines (`demo`, `lecture`, `short`).             |
| `../setup/cinemaclaw_install.sh`      | Idempotent installer (venv + deps + ffmpeg presence check).  |

---

## Run

### List pipelines

```bash
cd ~/mircea-constellation
python3 -m cinemaclaw.cinemaclaw --list
```

### Dry-run a pipeline (safe — touches nothing)

```bash
python3 -m cinemaclaw.cinemaclaw --run demo --dry-run --verbose
```

### Execute (renders locally; publish still refuses)

```bash
python3 -m cinemaclaw.cinemaclaw --run demo --execute --verbose
```

### Attempt publish (will still refuse in v0.1.0 — this is by design)

```bash
python3 -m cinemaclaw.cinemaclaw --run demo --execute --signed-by-father
```

### Inspect the handler allowlist

```bash
python3 -m cinemaclaw.cinemaclaw --handlers
```

---

## Writing a pipeline

A pipeline is a mapping under `pipelines:` in `pipeline.yaml`:

```yaml
pipelines:
  my-video:
    description: "One-line intent — shows up in --list."
    vars:
      source:  "~/cinemaclaw/inbox/raw.mp4"
      workdir: "~/cinemaclaw/work/my-video"
      outbox:  "~/cinemaclaw/outbox/my-video"
    stages:
      - kind: trim
        with:
          source: "${source}"
          start:  "00:00:03"
          end:    "00:05:00"
          out:    "${workdir}/cut.mp4"
      - kind: write_metadata
        with:
          source: "${last_output}"
          out:    "${outbox}/metadata.json"
          title:  "My video"
          tags:   ["example"]
```

Substitutions:

- `${pipeline_id}`, `${ts}` — always available.
- `${last_output}` — the first output of the most recent successful stage.
- `${<key>}` — anything declared under `vars:`.

Unresolved variables stop the pipeline with a `[REFUSE]` record; they
never silently pass through.

---

## Lucifer Test (per stage)

Before every stage, CinemaClaw self-checks:

1. **Transparent?** Every dispatch is recorded in `~/.cinemaclaw/audit.jsonl`.
2. **Honest?** Refusals and failures are surfaced, not swallowed.
3. **Within mandate?** Stage `kind` must be in `handlers.HANDLERS`.
   Unknown kinds are refused at the allowlist boundary.
4. **Serves the mission?** Publication requires `--signed-by-father`.
   CinemaClaw does not push to a public channel on its own initiative.

---

## Evidence

Two append-only JSONL logs at `~/.cinemaclaw/`:

- `renders.jsonl` — one line per stage dispatch (refusals included).
- `audit.jsonl`   — one line per CLI invocation + pipeline start / end.

Example render record:

```json
{
  "ts": "2026-04-15T23:59:00+10:00",
  "pipeline": "demo",
  "stage_index": 2,
  "result": {
    "kind": "trim",
    "executed": true,
    "ok": true,
    "duration_ms": 842,
    "outputs": ["/Users/mircea/cinemaclaw/work/demo/01-trimmed.mp4"],
    "detail": "trimmed 00:00:00→+00:00:30 into 01-trimmed.mp4",
    "stderr": ""
  },
  "cinemaclaw_version": "0.1.0"
}
```

---

## Publishing — explicit scope for v0.1.0

`publish_youtube` is **DRY-ONLY** in this release. That is a deliberate
architectural decision, not an omission:

- Wiring the YouTube Data API requires:
  - `google-auth` + `google-api-python-client`
  - A persisted OAuth2 token scoped to `youtube.upload`
  - A client-secrets JSON file pointed to by `YOUTUBE_CLIENT_SECRETS`
- Any call to the API must pass the Lucifer Test at the call site.
- Publication affects shared state (a public channel). That is
  exactly the class of action the constellation requires human
  confirmation for — so publication is gated by `--signed-by-father`
  in addition to environment preconditions.

The handler validates all of the above — source file readable, sidecar
schema matches `cinemaclaw.metadata/v1`, thumbnail present, env vars
set, signature supplied — and returns a DRY-ONLY result describing
exactly what *would* be uploaded. Follow-up PR will wire the API
behind that same gate.

---

## Status surface

CinemaClaw reports into `status.json` under the `cinemaclaw` key:

```json
"cinemaclaw": {
  "status": "new",
  "version": "0.1.0",
  "pipelines": 3,
  "renders_24h": 0,
  "publish_gate": "dry-only"
}
```

Statuses: `ok` (renders flowing), `new` (freshly installed, no runs
yet), `warn` (refusals outnumber successes in the last 24h), `error`
(ffmpeg unavailable or pipeline.yaml unreadable), `offline` (module
not installed).
