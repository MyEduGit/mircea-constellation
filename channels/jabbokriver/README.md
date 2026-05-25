# JabbokRiverProductions

A new YouTube channel under Mircea's Constellation, contrasting current
Seventh-day Adventist discourse with the **religion *of* Jesus** vs. the
**religion *about* Jesus** framing — a phrasing taken directly from
*The Urantia Book*, **Paper 196 — The Faith of Jesus**.

> "The religion of Jesus is the most dynamic influence ever to activate
> the human race." — *The Urantia Book*, Paper 196

The channel takes Dr. Emanoil Geaboc's existing Romanian-language SDA
talks (publicly uploaded across multiple SDA YouTube channels, plus
recordings held in the operator's `messagetostephanos@gmail.com`
archive) as **source material for original editorial commentary**.

---

## Why this fits the constellation

Mircea's Constellation is governed by `COVENANT.md`:

> "Ambiguity defaults to the Three Values. When two paths present
> themselves, choose the one that better embodies **Truth · Beauty ·
> Goodness**."

The "religion of Jesus" framing is already the constellation's native
theology — Paper 196 is part of the source corpus served by
`urantipedia` and ingested by `openclaw_ingest`. JabbokRiverProductions
becomes an SDA-facing outreach arm of that mission, not a new editorial
stance.

---

## The face

**Dr. Emanoil Geaboc** — Romanian-speaking SDA theologian. The
constellation's transcription stack (`scribeclaw`, faster-whisper
Romanian, Romanian stopword list) is already tuned for his language.

`channel.json` records `host.consent_status` (currently `"pending"`).
**No public episode ships until that flips to `"confirmed"` with a
signed letter on file under `consent/`** (see `OPERATOR.md`).

---

## Publishing policy: catalog & link, not re-upload

This channel **does not re-host** other people's videos. The catalog
(`catalog.yaml`) tracks public source URLs for transcription and study.
Public outputs are **original editorial/commentary clips** that:

1. Cite and link the source video.
2. Credit the original SDA YouTube channel that uploaded it.
3. Stay within fair-use bounds (short excerpts under commentary, when
   used at all).

This policy keeps the channel resilient to copyright claims and
respects the labor of the source-channel operators.

---

## Layout

```
channels/jabbokriver/
├── channel.json              # identity, host, footer, tags, policy
├── series.json               # named series with title + description templates
├── catalog.yaml              # source-video manifest (operator-edited)
├── schema/
│   └── catalog.schema.json   # JSON Schema enforced by validate_catalog.py
├── consent/                  # signed letters from Dr. Geaboc (operator-supplied)
├── tools/
│   ├── catalog_fetch.py      # archives catalog entries via yt-dlp (dry-run default)
│   └── validate_catalog.py   # validates catalog.yaml against the schema
├── README.md                 # this file
└── OPERATOR.md               # manual-only launch + per-episode runbook
```

---

## Wiring

- **scribeclaw** (`/scribeclaw/youtube.py`): when invoked with
  `payload.channel_slug = "jabbokriver"`, it loads `channel.json` and
  optionally `series.json`, then prepends the channel footer, dedupes
  channel-level tags onto the auto-derived tag list, and prefixes the
  first title candidate with `series_title_prefix`. All existing
  behavior is preserved when `channel_slug` is absent — protects the
  evidence-hash determinism contract in `scribeclaw/main.py`.

- **remotion** (`/remotion/src/jabbok/`): four compositions
  (`JabbokIntro`, `JabbokOutro`, `HostLowerThird`, `ThesisTitleCard`)
  for branded intro/outro and on-screen identification. Render via
  `npx remotion render <id> out/<id>.mp4` from `/remotion/`.

- **dashboard** (`/index.html`, `/status.json`): a `jabbokriver`
  service-tier node appears under Services with current status.

---

## See also

- `OPERATOR.md` — required manual steps before public launch
- `COVENANT.md` (repo root) — the standing covenant all subsystems inherit
- `/scribeclaw/README.md` — media pipeline reference
- The Urantia Book, Paper 196 — `https://urantipedia.org/`
