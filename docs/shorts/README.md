# Shorts Factory — Cross-Stack Pipeline

Multi-locale viral/evergreen short-form clip factory for Dr. Emanoil
Geaboc's channel. Spans Python (`scribeclaw/shorts/`, Phase 2B PR) and
React/Remotion (`remotion/`, Phase 1 + Phase 2A).

## End-to-end flow

```
   YouTube URL (Romanian sermon)
       │
       ▼
┌──────────────────────┐
│ scribeclaw/shorts/   │  Python (Phase 2B)
│ ─ ingest.py          │  yt-dlp → audio + video cache
│ ─ transcribe.py      │  AssemblyAI → word-level RO transcript
│ ─ select.py          │  Claude API picks 3–5 viral 20–60s segments
│ ─ translate.py       │  Claude API → EN/ES/PT (preserves register)
│ ─ clone_voice.py     │  ElevenLabs PVC → narration MP3 per locale
│ ─ images.py          │  curated/AI-generated images per beat
│ ─ manifest.py        │  emit JSON manifests (RO face + 3× image)
└──────────┬───────────┘
           │
           ▼ remotion/shorts-queue/*.json
┌──────────────────────┐
│ remotion/            │  React/TSX (Phases 1 + 2A — DONE)
│ ─ ShortClip          │  Romanian face-to-camera
│ ─ ImageShortClip     │  EN/ES/PT image-driven w/ cloned narration
│ ─ ClipSequence       │  weekly compilation
└──────────┬───────────┘
           │
           ▼ MP4s in remotion/out/
┌──────────────────────┐
│ scribeclaw/shorts/   │
│ ─ launch.py          │  schedule per docs/shorts/LAUNCH_TIMING.md
│ ─ publish.py         │  YT Shorts / IG Reels / TikTok APIs
└──────────────────────┘
```

## What's where

| Concern              | Location                              | Status        |
|----------------------|---------------------------------------|---------------|
| Composition (face)   | `remotion/src/compositions/shorts/ShortClip.tsx` | Phase 1 — done |
| Composition (image)  | `remotion/src/compositions/shorts/ImageShortClip.tsx` | Phase 2A — done |
| Concatenation        | `remotion/src/compositions/shorts/ClipSequence.tsx` | Phase 2A — done |
| Manifest schema      | `remotion/src/compositions/shorts/types.ts` | Phase 2A — done |
| Sample manifests     | `remotion/fixtures/sample-clip-{en,es,pt}.json` | Phase 2A — done |
| Voice cloning        | `scribeclaw/shorts/clone_voice.py`    | Phase 2B — pending |
| Translation          | `scribeclaw/shorts/translate.py`      | Phase 2B — pending |
| Segment selection    | `scribeclaw/shorts/select.py`         | Phase 2B — pending |
| Render driver        | `scribeclaw/shorts/render.py`         | Phase 2B — pending |
| Launch scheduler     | `scribeclaw/shorts/launch.py`         | Phase 2B — pending |
| Consent record       | `docs/shorts/CONSENT.md`              | Phase 2A — done (template; awaiting signature) |
| Launch timing prior  | `docs/shorts/LAUNCH_TIMING.md`        | Phase 2A — done |

## Editorial principles (one-line summary of CLAUDE.md)

- **One idea per clip.** No omnibus.
- **Hook in 1.5s.** Title before branding.
- **Word-level captions, every clip, every locale.** 85% watch muted.
- **Evergreen.** No dates, no news. Reads as well in 2030.
- **Consent before clone.** See `CONSENT.md`.
- **Disclosure on cloned audio.** AI-voice tag in metadata + first-publish
  on-screen note.
- **Romanian = face. EN/ES/PT = image + cloned voice.** Don't try to fake
  lip-sync in another language.

## Why this architecture

- **Python where Python is strong** (audio, AI APIs, schedulers, OAuth).
- **React/Remotion where React is strong** (declarative video composition
  with live preview, deterministic renders, easy to A/B variants).
- **JSON manifests as the contract** — Python and Remotion never share
  process; the manifest is the only handoff.
- **Manifest queue + headless render** scales horizontally on any worker
  with Node + Chromium + ffmpeg.
- **One composition per format, not one per locale** — diacritics + Inter
  cover RO/EN/ES/PT without per-locale forks.

## Open questions / TODOs (Phase 2B)

- Curated image library vs. AI image gen per beat (cost / brand control trade)
- Translation human-review workflow (how does a Romanian-speaking reviewer
  approve Claude's EN before clone is generated?)
- Per-clip A/B variants (two title hooks, pick winner after 24h)
- Long-form compilation cadence (weekly? bi-weekly?)
- Disclosure UI in `ImageShortClip` (subtle bottom-left chip on first 3s)
