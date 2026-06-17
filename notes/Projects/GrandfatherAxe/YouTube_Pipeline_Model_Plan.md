# YouTube / Sermon Pipeline — Tools, Models, and What's Blocking It

**Purpose:** the complete plan for the Geaboc sermon → YouTube pipeline —
which tool or AI handles each step, and the exact logins/keys that unblock it.
Companion to the large-print sheet `one-sermon-test-sheet.html`.

**Verdict:** Do **not** buy Hermes or KiloClaw. The existing stack
(ScribeClaw + NemoClaw + OpenClaw + Jarvis + Headroom) already does more.
The blockers are credentials and consent, not missing software.

---

## Who does what (per step)

Most of this pipeline is **not** LLM work — don't pay a frontier model for a
deterministic step.

| Step | Handler | LLM? | Notes |
|------|---------|------|-------|
| Trim / loudnorm / silence (`media_edit`) | ffmpeg (ScribeClaw) | No | Pure media |
| Extract 16 kHz mono audio (`audio_extract`) | ffmpeg (ScribeClaw) | No | Pure media |
| Speech → text (`transcribe_ro`) | faster-whisper, offline, RO | No (speech model) | Free, local, no key |
| Speech → text alt (`transcribe_assemblyai`) | AssemblyAI | No (speech model) | Needs `ASSEMBLYAI_API_KEY` |
| Diacritics / punctuation (`postprocess_transcript`) | deterministic | No | cedilla→comma, spacing |
| **Fix mis-heard names & doctrine** | **Claude Opus 4.8** (`claude-opus-4-8`) | Yes | High-stakes; Whisper mistakes on names like *Melchizedek* |
| **Translate RO → EN/ES** | **Claude Opus 4.8**, or **Fable 5** (`claude-fable-5`) for hardest passages | Yes | Highest-stakes, public, unforgiving |
| Rewrite for reading levels | **Claude Sonnet 4.6** (`claude-sonnet-4-6`) | Yes | Capable workhorse, lower cost |
| Titles / description / chapters / tags (`youtube_metadata`) | **Claude Haiku 4.5** (`claude-haiku-4-5`) or **local Hermes 4 14B / gemma** | Yes (light) | Low-stakes — you review before publish |
| Subtitle/SRT timing & formatting | deterministic | No | Whisper already gives timestamps |
| Upload (`youtube_upload`) | YouTube Data API v3 | No | Gated on consent + OAuth (below) |
| Orchestration / scheduling | NemoClaw (n8n) + OpenClaw cron, driven by Claude Code | n/a | Code, not a model |

### Spending principle
Spend the model budget where a mistake is **public and hard to undo** —
**translation** and **name/term cleanup** → Opus 4.8 (Fable 5 for the hardest).
Anywhere a human reviews the output (titles, tags, descriptions) →
Haiku 4.5 or the **local gemma** model. Approximate price per 1M tokens
(input / output): Fable 5 $10/$50 · Opus 4.8 $5/$25 · Sonnet 4.6 $3/$15 ·
Haiku 4.5 $1/$5.

### Cost / consistency tips
- Feed `channels/jabbokriver/geaboc-glossary.md` to Claude as a **cached
  system prompt** for translation + cleanup. Keeps terminology consistent
  across every sermon, and prompt caching makes the glossary nearly free to
  reuse after the first call.
- Route the heavier Opus / Fable calls **through the Headroom proxy** — it
  caches/compresses prompt context on the M4 and cuts cost further.

---

## What unlocks each step (the real blockers)

It's almost never missing software — it's a missing key or login.

- 🟢 **Transcription works now.** `transcribe_ro` is offline faster-whisper —
  no key, no internet.
- 🟡 **Cloud transcription (optional):** add `ASSEMBLYAI_API_KEY=...` to
  `scribeclaw/.env`.
- 🔴 **Publish to YouTube — two gates** (see `channels/jabbokriver/OPERATOR.md`):
  1. **Consent first.** No upload until Dr. Emanoil Geaboc signs the consent
     letter. Drafts are ready in `channels/jabbokriver/consent/`
     (`LETTER-TEMPLATE-ro.md`, `LETTER-TEMPLATE-en.md`) — fill blanks, send.
     Then flip `host.consent_status` `pending` → `confirmed` in
     `channels/jabbokriver/channel.json`.
  2. **One-time Google login.** Google Cloud project → enable YouTube Data
     API v3 → OAuth client → `client_secret.json` into
     `/opt/scribeclaw-data/youtube/credentials/` → mint a refresh token
     (browser, once). `youtube_upload` refuses (returns `not_ready`) until
     this is in place — by design.

**Single most useful next action (costs nothing):** send Dr. Geaboc a consent
letter. It's the real thing standing between you and a published sermon.

---

## Model ID reference (current)

| Use | Model ID |
|-----|----------|
| Hardest translation / reasoning | `claude-fable-5` |
| Translation, name/term cleanup (default) | `claude-opus-4-8` |
| Reading-level rewrites | `claude-sonnet-4-6` |
| Titles/tags/descriptions (cheap) | `claude-haiku-4-5` |
| Titles/tags (free, private, on-device) | local Ollama (gemma) |

**Tag:** #ga #ai-universe #pipeline
