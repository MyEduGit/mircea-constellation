# Cold-Open Builder — Geaboc Pipeline

Two scripts that together solve the broken-audio-timecode problem and automate it for C0074+.

## The Problem They Solve

When Mircea exports the FCP-edited master ("C0073_Unified.mp3"), the timecodes shift from the raw Canon recording by a **non-uniform** amount — because FCP edits are concentrated (intros, silences, coughs) not spread evenly. Proportional scaling from the raw SRT fails.

**Solution:** Transcribe the edited audio directly → find phrases by text search → use those exact timecodes.

---

## Step 1 — `find_phrases.py`

Run once per sermon, on the iMac M4.

```bash
# Install faster-whisper (one-time):
pip3 install faster-whisper

# Run (downloads whisper-large-v3 ~3GB on first run):
python3 channels/jabbokriver/tools/find_phrases.py /path/to/C0073_Unified.mp3
```

**What it does:**
- Transcribes the 47-min audio with whisper-large-v3 (3-5 min on M4)
- Searches for the 5 viral phrases for C0073
- Prints exact IN/OUT timecodes
- Writes `C0073_Unified_timecodes.json` alongside the audio file

**Output example:**
```
✅  UFO / UAP / Congres
    IN:  00:38:14.200   OUT: 00:38:21.200   (7s)
    Card: CONGRESUL A DECLASIFICAT 46 DE VIDEOCLIPURI

✅  Kenneth Copeland — Tu ești Dumnezeu
    IN:  00:23:41.800   OUT: 00:23:48.800   (7s)
    Card: COPELAND: «TU EȘTI DUMNEZEU.»
    …
```

---

## Step 2 — `build_coldopen.py`

Run after `find_phrases.py` succeeds.

```bash
# Install Pillow if not already:
pip3 install Pillow

# Automatic (reads the JSON file produced by find_phrases.py):
python3 channels/jabbokriver/tools/build_coldopen.py /path/to/C0073_Unified.mp3
```

**Output:** `C0073_ColdOpen_30sec.mp4` in the same folder as the audio.

### Manual override (if you found a timecode by ear in FCP)

```bash
python3 channels/jabbokriver/tools/build_coldopen.py /path/to/C0073_Unified.mp3 \
    --ufo       "00:38:14.200" "00:38:21.200" \
    --copeland  "00:23:41.800" "00:23:48.800" \
    --tomb      "00:16:30.100" "00:16:37.100" \
    --daughters "00:11:42.000" "00:11:48.000" \
    --pivot     "00:44:35.500" "00:44:43.500"
```

Only the arguments you supply override the JSON — omit any phrase to keep the auto-detected value.

---

## Step 3 — Drop into FCP

1. Open your FCP project
2. Press **Home** to go to 0:00
3. In the Browser, click `C0073_ColdOpen_30sec.mp4` once
4. Press **W** (Insert) — the cold-open is placed at 0:00 and the sermon shifts to ~0:32

Then place the 3 lower-third PNGs on an upper track:
| File | Track position | Duration |
|---|---|---|
| `C0073_LT_01_Identity.png` | 0:34 | 5 sec |
| `C0073_LT_02_CTA.png` | [end − 0:18] | 8 sec |
| `C0073_LT_03_Subscribe.png` | [end − 0:10] | 8 sec |

---

## For C0074+ (fully automated)

The scripts are **generic** — works on any sermon. Just change the audio path:

```bash
# C0074:
python3 find_phrases.py /Volumes/SSD_AdobeFCP/C0074/C0074_Unified.mp3
python3 build_coldopen.py /Volumes/SSD_AdobeFCP/C0074/C0074_Unified.mp3
```

The 5 viral phrases are defined in `find_phrases.py → PHRASES`. To update them for a new sermon topic, edit that list. The build script reads card text from the JSON, so no changes needed there.

---

## Integrating with n8n (Tier 2)

Once the n8n workflow is set up on NemoClaw, add a node after "audio extract":

```json
{
  "node": "Execute Command",
  "command": "python3 /home/mircea/Pipeline/find_phrases.py {{ $json.audio_path }}"
}
```

Then another node:
```json
{
  "node": "Execute Command",
  "command": "python3 /home/mircea/Pipeline/build_coldopen.py {{ $json.audio_path }}"
}
```

The output path is deterministic (`<stem>_ColdOpen_30sec.mp4`) so the next node can reference it by path.

---

## Troubleshooting

| Symptom | Fix |
|---|---|
| `faster_whisper not installed` | `pip3 install faster-whisper` |
| `ffmpeg_not_on_path` | `brew install ffmpeg` |
| Phrase NOT FOUND | Edit the `_timecodes.json` manually and set `clip_in`/`clip_out`, then run `build_coldopen.py` |
| Audio plays but card text doesn't appear | Check ffmpeg has `libx264` — `ffmpeg -codecs \| grep x264` |
| Model download slow | Set `WHISPER_CACHE_DIR=~/Models` to keep across script runs |
| Wrong language detected | Force it: `python3 find_phrases.py audio.mp3 large-v3` (the model arg) |
