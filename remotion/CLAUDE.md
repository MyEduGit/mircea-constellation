# Remotion — Clip Factory (guide for Claude Code sessions)

This directory turns Dr. Emanoil Geaboc's long-form YouTube teachings into
short-form clips. The goal is **evergreen virality**: one idea per clip,
word-level captions, no dated references. Everything is driven by JSON
manifests so Python (see `scribeclaw/shorts/`, coming in a later PR) can
render clips headlessly without touching TSX.

## Anatomy

```
remotion/
  fixtures/
    sample-clip.json           ← canonical example manifest (Romanian)
  src/
    Root.tsx                   ← registers HelloWorld + ShortClip
    index.ts
    compositions/
      shorts/
        ShortClip.tsx          ← the composition (1080×1920 @ 30fps)
        Captions.tsx           ← word-level highlighted captions
        TitleCard.tsx          ← hook at top (first 2s prime estate)
        ChannelLockup.tsx      ← subtle name lockup fading in at ~2s
        ProgressBar.tsx        ← retention cue at the bottom
        CTA.tsx                ← final-2s call to action
        types.ts               ← ShortClipProps, Word, accent
```

## Composition: `ShortClip`

Input props (see `src/compositions/shorts/types.ts`):

| Field               | Type                  | Notes                                            |
|---------------------|-----------------------|--------------------------------------------------|
| `sourceVideo`       | `string \| null`      | Public URL or `staticFile()` path. `null` → gradient preview. |
| `sourceStartSec`    | `number`              | Offset into `sourceVideo` to start playback.     |
| `durationInSeconds` | `number`              | Drives `durationInFrames` via `calculateMetadata`. |
| `title`             | `string`              | The hook. Max ~60 chars.                         |
| `subtitle`          | `string \| null`      | Small accent chip above the title.               |
| `words`             | `Word[]`              | `{ text, start, end }` in seconds, clip-relative.|
| `channelName`       | `string`              | e.g. `"Dr. Emanoil Geaboc"`.                     |
| `channelHandle`     | `string \| null`      | e.g. `"@drgeaboc"`.                              |
| `cta`               | `string \| null`      | Shown during the final ~2s only.                 |
| `accentColor`       | `string`              | Hex; defaults to `DEFAULT_ACCENT` (`#FFD34E`).   |

`calculateMetadata` in `Root.tsx` derives `durationInFrames` from
`durationInSeconds × 30fps` per manifest.

## Preview

```
cd remotion
npm start                     # Remotion Studio at http://localhost:3000
```

Pick the **ShortClip** composition — it boots with `fixtures/sample-clip.json`.

## Render one clip

```
npx remotion render ShortClip out/clip-01.mp4 \
  --props=./fixtures/sample-clip.json
```

Requires Chromium (Remotion auto-downloads on first run) and ffmpeg (already
used by `scribeclaw/`).

## Render a batch (Phase 2)

The Python side will drop one JSON per clip into `remotion/shorts-queue/`.
A helper (TBD) iterates the queue calling `remotion render ShortClip`
per manifest, emitting to `out/<manifest-stem>.mp4`.

## Editorial rails (why this looks the way it looks)

- **Hook first 1.5s.** Title appears before channel branding so the viewer
  commits to the idea before they clock who it is.
- **Word-level highlighted captions.** 85% of short-form is watched muted;
  highlighting the active word correlates with retention.
- **Accent color** used sparingly: chip, active caption word, CTA, progress
  bar. Keep brand recognizable across clips without being gaudy.
- **No dates, no news.** `title` and `cta` must read as well in 2030 as
  today — this is how theological content stays evergreen.
- **Vertical 1080×1920 @ 30fps** — universal for Shorts / Reels / TikTok.

## Adding a new composition

1. Create `src/compositions/<feature>/YourComp.tsx`.
2. Export a Props type from a sibling `types.ts`.
3. Register it in `src/Root.tsx` with `<Composition id="..." />` and, if the
   duration is data-driven, a `calculateMetadata` function.
4. Drop a fixture into `remotion/fixtures/`.
5. Preview via `npm start`, render via `npx remotion render ...`.

## Debugging tips

- `npx remotion compositions` — lists every registered composition by id.
  In sandboxed environments without outbound access, the first run may fail
  downloading Chrome Headless Shell — that is environmental, not a code bug.
- `npx tsc --noEmit -p .` — typecheck without rendering.
- OffthreadVideo vs Video: use `<OffthreadVideo>` inside `ShortClip` — it is
  the recommended component for rendering (more stable under Puppeteer).

## Related parts of the repo

- `scribeclaw/` — Python transcription pipeline (ffmpeg + AssemblyAI).
  Phase 2 will add `scribeclaw/shorts/` to go YouTube URL → transcript →
  Claude-picked segments → manifest JSON feeding this composition.
- `council/` — multi-model orchestration; used to judge which segments
  are likeliest to go viral and rank them before cutting.
