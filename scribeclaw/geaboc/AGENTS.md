# Geaboc Subtitle Agent Contract

Use this contract whenever the user asks to transcribe, subtitle, finalize, sync, or audit a Dr. Emanoil Geaboc episode.

## Non-negotiable rules

1. Use AssemblyAI as the sole speech-to-text engine.
2. Do not call MacWhisper, Whisper, or any local ASR engine.
3. Use a supplied YouTube SBV only for cue start/end times; ignore its text.
4. Transcribe the audio extracted from the final video edit.
5. Use episode folder `C00XX`, without a trailing underscore.
6. Include `Codex` in final output names unless the active agent has been explicitly told to use another name.
7. Never expose or persist API keys in logs, reports, Obsidian, Drive, Notion, or GitHub.

## Execute

```bash
python3 "$HOME/Applications/Geaboc Subtitle Console/geaboc_subtitle_console.py" run \
  --episode C00XX \
  --audio "/absolute/path/to/final-audio.mp3" \
  --sbv "/absolute/path/to/timing-only.sbv"
```

Omit `--sbv` when unavailable. Do not replace AssemblyAI text with YouTube words.

## Verify before reporting success

- QA file says `PASS`.
- Final SRT has no empty cues, invalid durations, or overlaps.
- Manifest says `"macwhisper_used": false`.
- SSD destination is `/Volumes/SSD_Adobe:FCP/C00XX/`.
- Obsidian episode note and transcript exist.
- If Google Drive for Desktop is mounted, both Drive destinations exist.
- Update the Notion hub using `C00XX_cloud_handoff_Codex.md` when a Notion connector is available.

## Connected source-of-truth locations

- Obsidian: `~/Library/Mobile Documents/com~apple~CloudDocs/UrantiPedia/Urantia-Vault/JRP/Geaboc/`
- SSD: `/Volumes/SSD_Adobe:FCP/`
- Drive: `UrantiPedia/03_Content/YouTube/` and `UrantiPedia/03_Content/Transcripts/`
- Notion: `https://app.notion.com/p/29e8525ab5a081619084f31301c6cf2e`
- GitHub historical branch: `MyEduGit/mircea-constellation`, `claude/fix-romanian-subtitles-Hg00H`

If a connected destination is unavailable, keep the completed SSD/Obsidian artifacts, state exactly which destination is blocked, and use the cloud handoff file on the next connected run.
