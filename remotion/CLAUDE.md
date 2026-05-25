# Remotion — Clip Factory (guide for Claude Code sessions)

This directory turns Dr. Emanoil Geaboc's long-form YouTube teachings into
short-form clips in **four locales** — Romanian (the master, face-to-camera)
plus English, Spanish, Portuguese (image-driven, cloned-voice narration).
Goal: **evergreen virality**. One idea per clip, word-level captions, no
dated references. Everything is driven by JSON manifests so Python (see
`scribeclaw/shorts/`, Phase 2B PR) can render headlessly.

Cross-cutting docs live under `/docs/shorts/`:
- `docs/shorts/CONSENT.md` — voice cloning consent record (required before
  any non-Romanian render uses cloned audio).
- `docs/shorts/LAUNCH_TIMING.md` — researched optimal post times per
  language, platform, and audience archetype.

## Anatomy

```
remotion/
  fixtures/
    sample-clip.json           ← Romanian face-to-camera (ShortClip)
    sample-clip-en.json        ← English image-driven (ImageShortClip)
    sample-clip-es.json        ← Spanish image-driven
    sample-clip-pt.json        ← Portuguese image-driven
    sample-sequence.json       ← all four strung together (ClipSequence)
  src/
    Root.tsx                   ← registers all compositions + calculateMetadata
    compositions/shorts/
      ShortClip.tsx            ← face-to-camera (Romanian masters)
      ImageShortClip.tsx       ← image timeline + cloned narration audio
      ClipSequence.tsx         ← concatenates N clips into one long video
      KenBurnsImage.tsx        ← pan/zoom helper for image beats
      Captions.tsx             ← word-level highlighted captions (3-word window)
      TitleCard.tsx            ← hook at top
      ChannelLockup.tsx        ← subtle name lockup, fades in ~2s
      ProgressBar.tsx          ← bottom retention cue (takes own duration prop)
      CTA.tsx                  ← final-2s call to action
      types.ts                 ← all props + ClipManifest discriminated union
```

## Compositions

### `ShortClip` (face format, Romanian)

Source video full-bleed + word-level captions. Use this for the original
Romanian masters — Dr. Geaboc speaking on camera.

### `ImageShortClip` (image format, EN/ES/PT)

A timeline of still images with Ken Burns drift, plus a single cloned-voice
narration audio track and the same caption engine. Used for non-Romanian
clips because we cannot lip-sync the source — the cloned voice tells the
story over curated imagery.

### `ClipSequence` (concatenation)

Strings any number of `ShortClip` and `ImageShortClip` manifests back-to-back
into one longer video — the weekly compilation. Inputs use the
`ClipManifest` discriminated union (`format: "face" | "image"`).

## Manifest schema (v2)

`face` clip — see `ShortClipProps` in `types.ts`:

| Field               | Type                 | Notes                                            |
|---------------------|----------------------|--------------------------------------------------|
| `format`            | `"face"`             | Required when embedded in a `ClipSequence`.      |
| `sourceVideo`       | `string \| null`     | Public URL or `staticFile()` path. `null` → gradient preview. |
| `sourceStartSec`    | `number`             | Offset into `sourceVideo` to start playback.     |
| `durationInSeconds` | `number`             | Drives `durationInFrames` via `calculateMetadata`. |
| `title`             | `string`             | The hook. Max ~60 chars.                         |
| `subtitle`          | `string \| null`     | Small accent chip above the title.               |
| `words`             | `Word[]`             | `{ text, start, end }` in seconds, clip-relative.|
| `channelName`       | `string`             | e.g. `"Dr. Emanoil Geaboc"`.                     |
| `channelHandle`     | `string \| null`     | e.g. `"@drgeaboc"`.                              |
| `cta`               | `string \| null`     | Shown during the final ~2s only.                 |
| `accentColor`       | `string`             | Hex; defaults to `DEFAULT_ACCENT` (`#FFD34E`).   |

`image` clip — see `ImageShortClipProps`:

| Field               | Type                 | Notes                                            |
|---------------------|----------------------|--------------------------------------------------|
| `format`            | `"image"`            | Required when embedded in a `ClipSequence`.      |
| `locale`            | `Locale`             | `"ro-RO" \| "en-US" \| "es-MX" \| "pt-BR"`.       |
| `narrationAudio`    | `string \| null`     | Path/URL to cloned-voice MP3/WAV. `null` for silent preview. |
| `images`            | `ImageBeat[]`        | Timeline of `{ src, start, end, panFrom?, panTo? }`. |
| ...rest             | same as face         | `title / subtitle / words / channel* / cta / accentColor / durationInSeconds`. |

`ImageBeat.panFrom / panTo` use `{ x, y, scale }` where `x`/`y` are
percentage offsets and `scale` is the multiplicative zoom (1.05–1.25 is a
calm Ken Burns range). Default if omitted: gentle 1.05 → 1.20 zoom.

`ClipSequence` manifest — see `ClipSequenceProps`:

```jsonc
{
  "transitionFrames": 0,            // crossfade not yet implemented
  "width": 1080,
  "height": 1920,
  "fps": 30,
  "clips": [ /* ClipManifest[] — each with `format` discriminator */ ]
}
```

## Preview

```
cd remotion
npm start           # Studio at http://localhost:3000
```

Default props are wired so each composition boots with its canonical fixture:
- `ShortClip` → `fixtures/sample-clip.json`
- `ImageShortClip` → `fixtures/sample-clip-en.json`
- `ClipSequence` → `fixtures/sample-sequence.json` (RO + EN + ES + PT)

The `ImageShortClip` and `ClipSequence` fixtures use `https://picsum.photos`
seed URLs as placeholder imagery — replace with curated images per topic
before publishing.

## Render commands

```bash
# Single Romanian clip
npx remotion render ShortClip out/ro-clip-01.mp4 \
  --props=./fixtures/sample-clip.json

# Single English image-driven clip
npx remotion render ImageShortClip out/en-clip-01.mp4 \
  --props=./fixtures/sample-clip-en.json

# Concatenated weekly compilation
npx remotion render ClipSequence out/weekly-compilation.mp4 \
  --props=./fixtures/sample-sequence.json
```

Requires Chromium (Remotion auto-downloads on first run) and ffmpeg
(already used by `scribeclaw/`).

## Editorial rails (why it looks this way)

- **Hook first 1.5s.** Title appears before channel branding.
- **Word-level highlighted captions.** 85% of short-form is watched muted;
  active-word highlighting correlates with retention.
- **Accent color** used sparingly — chip, active caption, CTA, progress
  bar — for cross-locale brand recognition.
- **Evergreen.** `title` and `cta` must read as well in 2030 as today.
  No dates, no news. One idea per clip.
- **Vertical 1080×1920 @ 30fps** — universal for Shorts / Reels / TikTok.
- **Cross-locale parity:** the same accent, the same lockup position, the
  same caption rhythm. Different language, same brand.

## Multi-locale rules of thumb

- **Romanian** stays face-to-camera (`ShortClip`). It is the source of
  truth — Dr. Geaboc's actual voice and presence.
- **EN / ES / PT** are image-driven (`ImageShortClip`). Cloned-voice
  narration tells the same teaching over curated imagery. Lip-sync is not
  attempted, by design — better to be obviously a translation than to be
  uncanny.
- **Translations** preserve the theological register, not literal phrasing.
  Phase 2B's translator prompt enforces this.
- **Diacritics matter.** `ă â î ș ț` (RO), `á é í ó ú ñ` (ES), `ã õ ç` (PT)
  — confirm your fonts render them. Inter / Helvetica Neue do.

## Voice cloning workflow (operational)

See `docs/shorts/CONSENT.md` for the legal/ethical preconditions. Pipeline:

1. Capture 10+ minutes of clean Romanian voice samples (16-bit PCM, mono, 44.1kHz).
2. Train Professional Voice Clone on ElevenLabs (or local OpenVoice v2).
3. Generate narration audio per locale — `narrationAudio` field in manifest.
4. Word timestamps from the TTS engine populate `words[]`.
5. Render the `ImageShortClip` with all three pieces wired up.

## Adding a new composition

1. Create `src/compositions/<feature>/YourComp.tsx`.
2. Export a Props type from `compositions/shorts/types.ts` (or sibling).
3. Register in `src/Root.tsx` with `<Composition id="..." />` + a
   `calculateMetadata` if duration is data-driven.
4. Drop a fixture into `remotion/fixtures/`.
5. Preview via `npm start`, render via `npx remotion render ...`.

## Debugging tips

- `npx remotion compositions` — lists every registered composition.
  In sandboxed environments without outbound access, the first run may fail
  downloading Chrome Headless Shell — environmental, not a code bug.
- `npx tsc --noEmit -p .` — typecheck without rendering.
- `npx remotion bundle` — verifies the composition graph compiles end-to-end
  without launching Chrome.
- Inside `ClipSequence`, child compositions see the *parent's*
  `useVideoConfig().durationInFrames`. ShortClip / ImageShortClip / Ken-
  BurnsImage / ProgressBar therefore use explicit duration props instead.
- `<OffthreadVideo>` over `<Video>` for source clips — more stable under
  Puppeteer rendering.

## Related parts of the repo

- `scribeclaw/` — Python transcription pipeline (ffmpeg + AssemblyAI).
  Phase 2B PR adds `scribeclaw/shorts/`: YouTube URL → transcript →
  Claude-picked viral segments → 4 manifests (RO/EN/ES/PT) → cloned-voice
  narration → batch render.
- `council/` — multi-model orchestration; ranks segment virality before
  cutting and sets per-locale launch schedule (see
  `docs/shorts/LAUNCH_TIMING.md`).
