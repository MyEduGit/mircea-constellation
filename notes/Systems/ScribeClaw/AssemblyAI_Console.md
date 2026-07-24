---
title: AssemblyAI Console
type: service-locator
status: canonical
vault: UrantiPedia
updated_at: 2026-07-24
aliases:
  - AssemblyAI
  - AssemblyAI Console
  - AssemblyAI Dashboard
  - AssemblyAI web app
  - Assembly AI console
  - transcription console
  - ScribeClaw transcription backend
  - where is my assemblyai
tags:
  - service
  - console
  - transcription
  - assemblyai
  - scribeclaw
  - api-key
  - media-pipeline
  - service-locator
canonical_register: "[[SERVICES_REGISTER]]"
console_url: https://www.assemblyai.com/dashboard/login
api_keys_page: https://app.assemblyai.com
api_base: https://api.assemblyai.com/v2
env_var: ASSEMBLYAI_API_KEY
key_location: "Apple Passwords -> entry 'Assembly AI - API key' (never in repo)"
account: mirceamatthews@gmail.com
host: iMac M4 · 127.0.0.1:8081 (ScribeClaw)
repo: myedugit/mircea-constellation
module: scribeclaw/
related:
  - "[[SERVICES_REGISTER]]"
  - "[[DASHBOARD]]"
  - "[[SYSTEM_MAP]]"
---

# AssemblyAI Console

> [!tip] Just want to transcribe? → **[[TRANSCRIBE]]**
> Double-click `scribeclaw/geaboc/Transcribe.command`, drag in the audio, click
> Transcribe. This note is the background/reference; TRANSCRIBE is the how-to.

> [!info] One-line answer
> The **AssemblyAI console** is the external web app at
> **<https://www.assemblyai.com/dashboard/login>** (API keys at
> **<https://app.assemblyai.com>**). In this constellation it is the cloud
> transcription backend of **ScribeClaw** (iMac M4, port `:8081`).

> [!important] Canonical source for the credential *location* is
> [[SERVICES_REGISTER]] (`SERVICES_REGISTER.md`, row 1, Proof Tier
> **VERIFIED** 2026-07-24). This note is the **ScribeClaw-integration**
> companion: it says how the repo *uses* AssemblyAI. If the two ever
> disagree on where the key/console lives, the register wins.

This note is a service locator so any human, LLM, agent, or search that asks
*"where is the AssemblyAI console?"* lands on a correct, secret-free answer.

---

## Where it is (pointers only — no secret ever lives here)

| What | Where |
|:---|:---|
| **Web console** (login/dashboard) | <https://www.assemblyai.com/dashboard/login> |
| **API keys page** | <https://app.assemblyai.com> |
| **Transcripts / history** | console → **Transcripts** |
| **Account** | `mirceamatthews@gmail.com` |
| **Key location** | Apple Passwords → entry `Assembly AI - API key` |
| **API base** (what the code calls) | `https://api.assemblyai.com/v2` |
| **Runtime consumes key from** | `scribeclaw/.env` → `ASSEMBLYAI_API_KEY` |
| **Integration code** | `scribeclaw/assemblyai.py` |
| **Docs / how-to** | `scribeclaw/README.md` → *"AssemblyAI alternative"* |

The API **key itself lives only in Apple Passwords**. It is never written to
this repo, this note, or the register — only its *location* is recorded.

---

## What it is (in the constellation)

**ScribeClaw** is an OpenClaw-class controlled-execution instance whose
sub-scope is the media pipeline: media edit → audio extract → transcription
→ Romanian post-processing → YouTube packaging. Transcription has two
interchangeable backends:

1. **faster-whisper** — offline, local, `language="ro"` (no console, no key).
2. **AssemblyAI** — cloud, requires `ASSEMBLYAI_API_KEY`. **This** is the one
   with a web console.

Both backends write the same on-disk shape
(`segments.json` / `.srt` / `.vtt` / `.txt`), so everything downstream is
backend-agnostic.

---

## For AI agents — how to use it

If a task needs AssemblyAI, do **not** re-transcribe blindly; the console
often already holds the work.

- **Reuse a finished transcript** (no re-billing) — grab its id from the
  console's Transcripts tab and call the handler:
  ```bash
  curl -sX POST http://127.0.0.1:8081/tasks \
    -H 'Content-Type: application/json' \
    -d '{"handler":"import_assemblyai_transcript","payload":{"transcript_id":"<id-from-console>","stem":"interviu"}}'
  ```
- **Clone every Romanian transcript** from the console in bulk (idempotent):
  ```bash
  curl -sX POST http://127.0.0.1:8081/tasks \
    -H 'Content-Type: application/json' \
    -d '{"handler":"bulk_import_assemblyai_romanian","payload":{"max_transcripts":50}}'
  ```
- **Transcribe a new local file** through AssemblyAI:
  ```bash
  curl -sX POST http://127.0.0.1:8081/tasks \
    -H 'Content-Type: application/json' \
    -d '{"handler":"transcribe_assemblyai","payload":{"input":"interviu.edited.wav","speaker_labels":true}}'
  ```

**Handlers:** `transcribe_assemblyai`, `import_assemblyai_transcript`,
`bulk_import_assemblyai_romanian` (all in `scribeclaw/assemblyai.py`).

**Precondition:** `ASSEMBLYAI_API_KEY` must be set in `scribeclaw/.env`. If it
is missing, every handler refuses with `status:error` /
`ASSEMBLYAI_API_KEY_missing` — there is no silent fallback and no hard-coded
key. Get/rotate the key at <https://app.assemblyai.com> (the secret then goes
into Apple Passwords and `scribeclaw/.env`, never into a tracked file).

---

## Common confusion — read this first

- ✅ Credential location is **governed** by [[SERVICES_REGISTER]] (row 1).
- ❌ **Not** in the Council-of-Seven / n8n LLM-seat key table
  (`01_System/HANDOVER_ClaudeCode_2026-04-12.md`). That table is the LLM
  seats (Anthropic, OpenAI, Grok, …). AssemblyAI is a transcription service,
  tracked in the SERVICES REGISTER instead.
- ❌ **Not** its own hosted service node — it is the cloud backend of
  ScribeClaw. On the constellation map (`index.html`) it appears **inside the
  ScribeClaw node's detail panel**, not as a standalone service.

---

## Links

- [[SERVICES_REGISTER]] — canonical credential-location register (no secrets)
- Map node: **ScribeClaw** in `index.html` (click it → AssemblyAI Console link)
- [[DASHBOARD]] — fleet status (ScribeClaw row: iMac M4 `:8081`)
- [[SYSTEM_MAP]] — architecture + external consoles
- `scribeclaw/README.md` — full pipeline + handler reference

_Part of `myedugit/mircea-constellation`. See [[DASHBOARD]] to return to Mission Control._
