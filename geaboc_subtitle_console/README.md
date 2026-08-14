# Geaboc Subtitle Console

Double-clickable macOS console that transcribes a Geaboc sermon with
**AssemblyAI** and produces upload-ready Romanian subtitles.

This is the tool the C0086 workflow assumed already existed. It did not —
`scribeclaw/` holds the same AssemblyAI logic, but only as a Docker service
with a FastAPI endpoint and `/opt/scribeclaw-data` mounts. Nothing there can
be opened by double-clicking, which is why searching for
"Geaboc Subtitle Console" came back **not found**.

**AssemblyAI is the only transcription engine.** MacWhisper output is not
accepted and there is no fallback — a silent swap to another engine would
break the approved workflow without anyone noticing.

---

## Install

1. Double-click **`geaboc_subtitle_console.zip`**.
2. Open the extracted **`geaboc_subtitle_console`** folder.
3. Control-click **`install_Geaboc_Subtitle_Console.command`** → **Open** →
   **Open** again.

The installer copies the console to
`~/Library/Application Support/GeabocSubtitleConsole/`, puts **Geaboc
Subtitle Console** on the Desktop, clears the Gatekeeper quarantine so
later launches are a plain double-click, and runs a self-test.

Nothing else is installed: **no Homebrew, no pip, no sudo**. The console
runs on the Python that ships with macOS and uses only the standard
library. If Python 3 is missing, the installer says exactly what to run
(`xcode-select --install`).

Build the ZIP from this repo with:

```bash
bash geaboc_subtitle_console/make_zip.sh    # → dist/geaboc_subtitle_console.zip
```

---

## Transcribe an episode

1. Double-click **Geaboc Subtitle Console** on the Desktop.
2. Choose **Transcribe with AssemblyAI**.
3. Type the episode code — `C0086`.
4. Pick the final MP3.

First run only, it asks for the AssemblyAI API key (from
assemblyai.com → Dashboard → API Keys) and stores it in the login
Keychain. The field is masked, the key is never printed, never written
into the output folder, and **never needs to be pasted into a chat
window**.

Results land in **`~/Desktop/Geaboc Subtitles/C0086/`**, which Finder
opens automatically when the run finishes:

| File | What it is |
|------|-----------|
| `C0086.srt` | **Upload this to YouTube.** Wrapped to 2 lines × 42 characters. |
| `C0086.vtt` | Same subtitles in WebVTT. |
| `transcript.clean.txt` | Romanian-corrected reading transcript. |
| `transcript.txt` | Verbatim transcript, uncorrected. |
| `transcript.srt` / `.vtt` | One cue per sentence, unwrapped. |
| `segments.json` | Timed segments — `scribeclaw`-compatible. |
| `segments.clean.json` | Same, orthography corrected. |
| `assemblyai.raw.json` | Full API response, kept for provenance. |
| `youtube_metadata.txt` | Worksheet: runtime, chapter marks, opening lines. |
| `RUN.json` | Job id, duration, engine, timestamp. |

Send the whole `C0086` folder for correction and validation.

There is no chunking or compression step. AssemblyAI accepts the full MP3
directly, so a 90-minute sermon is uploaded whole — splitting it would
only introduce seams at the joins.

---

## WhatsApp announcement

Choose **Make WhatsApp announcement**, enter the code, the video title and
the YouTube link. The text is written to
`whatsapp_announcement.txt` **and copied to the clipboard**, ready to paste.

This mode exists because of three specific defects in the previous
announcements, each now covered by a regression test:

- **"the link does not work"** and **"it does not start at the beginning"**
  — the same bug. A link copied from YouTube's share sheet carries
  `?si=…` (share tracking) and `&t=1907` (start offset), so it opened
  half-way through. Every parameter is stripped down to a clean
  `https://youtu.be/<id>`.
- **"still pastes unformatted"** — WhatsApp has no Markdown. Pasting
  `**bold**` or `# Heading` leaves the punctuation visible on screen. The
  console emits WhatsApp's own markup (`*bold*`, `_italic_`) with real
  line breaks, and the URL sits alone on its line so WhatsApp auto-links it.

---

## Command line

The same engine runs headless, for scripting or when the GUI is not
wanted:

```bash
python3 geaboc_console.py --self-test                      # verify, no API credits
python3 geaboc_console.py transcribe --code C0086 --audio "C0086 - FINAL_AUDIO_.mp3"
python3 geaboc_console.py announce --code C0086 --url "https://youtu.be/…" --title "…"
```

In headless mode the key comes from `ASSEMBLYAI_API_KEY`, matching the
convention in `scribeclaw/assemblyai.py`. The environment variable takes
precedence over the Keychain when both are set.

---

## Tests

```bash
python3 geaboc_subtitle_console/tests/test_geaboc_console.py
```

132 checks over the pure logic: timestamp formatting, segment
normalization, caption wrapping and cue timing, Romanian orthography, the
output folder contract, episode-code validation (including path-traversal
attempts), YouTube link normalization and WhatsApp formatting.

The macOS dialog and Keychain layers are thin `subprocess` wrappers around
`osascript` and `security`; they are covered by the installer's
`--self-test` on a real Mac rather than mocked here.

---

## Troubleshooting

**"Apple could not verify this app is free from malware"** — Control-click
the file → **Open** → **Open**. This only happens before the installer has
run; afterwards the quarantine flag is cleared.

**"Python 3 is not installed yet"** — open Terminal, run
`xcode-select --install`, accept Apple's installer, then double-click the
console again.

**"AssemblyAI rejected the API key"** — the key is wrong or was revoked.
Run the console and choose **Change AssemblyAI key**.

**The transcription seems stuck** — a 90-minute sermon takes a few
minutes. The Terminal window prints elapsed time every 30 seconds. The
console waits up to 90 minutes before giving up, and prints the transcript
id so the job can be recovered from the AssemblyAI dashboard.

**Wrong language** — the console requests Romanian (`ro`). For another
language use the command line with `--language`.

---

## Relationship to `scribeclaw/`

`scribeclaw/assemblyai.py` remains the pipeline implementation for the
server. This console is the operator-facing path to the same result and
writes the **same output shape** — `segments.json`, `transcript.srt`,
`transcript.vtt`, `transcript.txt`, `assemblyai.raw.json` — so a folder
produced here can be fed to `postprocess_transcript` and
`youtube_metadata` unchanged.

The Romanian cleanup applied to `transcript.clean.txt` uses the same
deterministic rules as `scribeclaw/postprocess.py`: legacy cedilla forms
(`ş`→`ș`, `ţ`→`ț`) are corrected, spacing is normalized, and **missing
diacritics are never guessed** — that needs a language model and a human
reviewer, and a wrong guess in a sermon transcript is worse than a visible
gap.

Per `channels/jabbokriver/OPERATOR.md`, transcription is permitted before
the launch gate; **publishing is not**. This console transcribes and
packages. It does not upload anything to YouTube.

UrantiOS governed — Truth, Beauty, Goodness.
