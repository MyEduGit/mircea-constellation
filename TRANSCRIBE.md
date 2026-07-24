---
title: TRANSCRIBE — audio → text
type: how-to
status: canonical
updated_at: 2026-07-24
aliases:
  - transcribe
  - transcription
  - audio to text
  - speech to text
  - how do I transcribe
  - how to transcribe
  - subtitle
  - subtitles
  - captions
  - srt
  - Geaboc subtitles
  - Romanian transcription
tags:
  - transcribe
  - how-to
  - assemblyai
  - subtitles
  - canonical
  - geaboc
tool: scribeclaw/geaboc/geaboc_subtitle_console.py
launcher: scribeclaw/geaboc/Transcribe.command
engine: AssemblyAI (only)
key_location: "see SERVICES_REGISTER.md — Apple Passwords / Keychain, never in repo"
related:
  - "[[SERVICES_REGISTER]]"
  - "[[AssemblyAI_Console]]"
  - "[[DASHBOARD]]"
---

# TRANSCRIBE — audio → text (the one way)

> [!tip] The whole thing, in one breath
> **Double-click `Transcribe.command`** → your browser opens → **drag in the
> audio** → click **Transcribe with AssemblyAI** → the finished `.srt` lands on
> your SSD, in Obsidian, and in Drive. That's it.

There is exactly **one** tool. It is **AssemblyAI-only** (no MacWhisper, no
setup each time). You do not need to remember flags, paths, or API keys.

---

## The easy way (human — double-click)

1. Open the folder **`scribeclaw/geaboc/`**
   (on your Mac: `~/Applications/Geaboc Subtitle Console/`).
2. **Double-click `Transcribe.command`.**
   *(First time only, if macOS blocks it: right-click → Open.)*
3. A page opens in your browser. **Drag in the audio file** and click
   **Transcribe with AssemblyAI**.
4. Wait for **QA: PASS**. Done — the final subtitles are saved everywhere.

That's the entire skill. If you only ever remember one thing, remember
**double-click `Transcribe.command`**.

## The same thing from a Terminal

```bash
python3 "scribeclaw/geaboc/geaboc_subtitle_console.py" serve
```

…then use the browser page exactly as above.

## The one-liner (for an agent, or when you already know the file)

```bash
python3 "scribeclaw/geaboc/geaboc_subtitle_console.py" run \
  --episode C0083 \
  --audio "/absolute/path/to/final-audio.mp3"
```

Add `--sbv "/path/timing.sbv"` only if you have YouTube timing to reuse (its
**timing** is used, its text is ignored). Agents: the full contract is
`scribeclaw/geaboc/AGENTS.md`.

---

## If it says the API key is missing

The tool looks for the AssemblyAI key in this order — macOS **Keychain**
(`Geaboc AssemblyAI API Key`) → env `ASSEMBLYAI_API_KEY` → `~/.openclaw/secrets.env`.
Enter it once in the console page and tick **Save to Keychain** and you'll never
be asked again. **Where the key itself lives:** see **[[SERVICES_REGISTER]]**
(Apple Passwords). The key is never stored in this repo, in logs, or in reports.

## Where the output goes

- **SSD** (canonical): `/Volumes/SSD_Adobe:FCP/C00XX/`
- **Obsidian**: `…/UrantiPedia/Urantia-Vault/JRP/Geaboc/` (episode note + transcript)
- **Google Drive** (if mounted): `UrantiPedia/03_Content/YouTube/C00XX/`

The file to hand to YouTube is `C00XX_subtitles_ro_FINAL_*.srt`.

---

_The tool: `scribeclaw/geaboc/`. Credential locations: [[SERVICES_REGISTER]].
Console background: [[AssemblyAI_Console]]. Return to [[DASHBOARD]]._
