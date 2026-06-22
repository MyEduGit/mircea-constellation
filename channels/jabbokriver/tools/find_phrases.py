#!/usr/bin/env python3
"""find_phrases.py — Locate specific Romanian phrases in an audio file.

Run this on the iMac M4 where whisper-large-v3 runs at full speed.

Usage:
    python3 find_phrases.py /path/to/C0073_Unified.mp3

The script:
  1. Transcribes the audio with faster-whisper large-v3 (word timestamps)
  2. Searches for the 5 C0073 viral phrases
  3. Prints exact IN/OUT timecodes for each clip (HH:MM:SS.mmm)
  4. Writes timecodes.json alongside the audio file for use by build_coldopen.py

Requirements (install once on iMac):
    pip3 install faster-whisper

First run downloads the model (~3GB). Subsequent runs use the cache.
On iMac M4, a 47-min audio file takes ~3-5 minutes.
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from typing import NamedTuple


# ─── Phrases to locate ──────────────────────────────────────────────────────
# Each entry: (id, label, search_string, clip_duration_sec, card_text_ro)
# search_string is a short distinctive substring — Whisper output may have
# slightly different punctuation/spacing, so we normalise before matching.

PHRASES = [
    (
        "ufo",
        "UFO / UAP / Congres",
        "46 de videoclipuri",
        7,
        "CONGRESUL A DECLASIFICAT 46 DE VIDEOCLIPURI",
    ),
    (
        "copeland",
        "Kenneth Copeland — Tu ești Dumnezeu",
        "tu ești dumnezeu",
        7,
        "COPELAND: «TU EȘTI DUMNEZEU.»",
    ),
    (
        "tomb",
        "Tombsucking la Bethel",
        "tombsucking",
        7,
        "BETHEL: DORM PE MORMINTE.",
    ),
    (
        "daughters",
        "Fetițele misionarului",
        "fetițele apar",
        6,
        "FETIȚELE MOARTE — AU APĂRUT DUMINICA.",
    ),
    (
        "pivot",
        "Sora White — vizitatori / spirite rele",
        "vizitatori",
        8,
        "ȘI O FEMEIE A PREZIS TOT — DE 170 DE ANI.",
    ),
]

# Fallback search strings (tried if primary search fails)
PHRASE_FALLBACKS: dict[str, list[str]] = {
    "ufo":       ["46 de video", "videoclipuri cu privire", "fenomene care au"],
    "copeland":  ["voi sunteți dumnezeu", "tu esti dumnezeu", "kenneth copeland"],
    "tomb":      ["suge puterea din mormant", "morminte", "bethel"],
    "daughters": ["fetitele apar", "fetite", "se asaza pe scaune"],
    "pivot":     ["vizitatorii sunt spirite", "spirite rele", "sora white spune"],
}


# ─── Helpers ─────────────────────────────────────────────────────────────────

def _normalise(text: str) -> str:
    """Lower-case, strip diacritics variants, collapse whitespace."""
    text = text.lower()
    # map diacritic variants (Whisper sometimes uses ș vs ş, etc.)
    text = text.replace("ș", "s").replace("ş", "s")
    text = text.replace("ț", "t").replace("ţ", "t")
    text = text.replace("ă", "a").replace("â", "a").replace("î", "i")
    text = re.sub(r"[^\w\s]", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def _fmt(seconds: float) -> str:
    """Format seconds → HH:MM:SS.mmm (ffmpeg-compatible)."""
    ms = int(round(seconds * 1000))
    h, ms = divmod(ms, 3_600_000)
    m, ms = divmod(ms, 60_000)
    s, ms = divmod(ms, 1000)
    return f"{h:02d}:{m:02d}:{s:02d}.{ms:03d}"


class Hit(NamedTuple):
    phrase_id: str
    label: str
    card_text: str
    clip_duration: int
    seg_start: float
    seg_end: float
    clip_in: str   # ffmpeg HH:MM:SS.mmm
    clip_out: str


def _search_segments(
    segments: list[dict],
    phrase_id: str,
    label: str,
    primary: str,
    fallbacks: list[str],
    clip_duration: int,
    card_text: str,
) -> Hit | None:
    """Search segments (and a joined window) for the phrase."""
    norm_primary = _normalise(primary)
    norm_fallbacks = [_normalise(f) for f in fallbacks]

    # Build a sliding window of 3 consecutive segments for context matching
    joined_windows: list[tuple[float, float, str]] = []
    for i in range(len(segments)):
        chunk = segments[i : i + 3]
        combined = " ".join(s["text"] for s in chunk)
        start = chunk[0]["start"]
        end = chunk[-1]["end"]
        joined_windows.append((start, end, combined))

    def _match(text: str) -> bool:
        n = _normalise(text)
        if norm_primary in n:
            return True
        return any(fb in n for fb in norm_fallbacks)

    # First pass: individual segments
    for seg in segments:
        if _match(seg["text"]):
            seg_start = seg["start"]
            seg_end = seg["end"]
            # align clip to seg start; clip_out = start + duration
            clip_in_sec = max(0.0, seg_start - 0.1)  # 100ms lead
            clip_out_sec = clip_in_sec + clip_duration
            return Hit(
                phrase_id=phrase_id,
                label=label,
                card_text=card_text,
                clip_duration=clip_duration,
                seg_start=seg_start,
                seg_end=seg_end,
                clip_in=_fmt(clip_in_sec),
                clip_out=_fmt(clip_out_sec),
            )

    # Second pass: joined windows
    for start, end, text in joined_windows:
        if _match(text):
            clip_in_sec = max(0.0, start - 0.1)
            clip_out_sec = clip_in_sec + clip_duration
            return Hit(
                phrase_id=phrase_id,
                label=label,
                card_text=card_text,
                clip_duration=clip_duration,
                seg_start=start,
                seg_end=end,
                clip_in=_fmt(clip_in_sec),
                clip_out=_fmt(clip_out_sec),
            )

    return None


# ─── Main ────────────────────────────────────────────────────────────────────

def _load_phrases_from_json(json_path: Path) -> list[tuple]:
    """Load phrases from a per-sermon JSON config.

    Format:
      [
        {"id": "ufo", "label": "UFO hook", "search": "46 de videoclipuri",
         "duration": 7, "card_text": "CONGRESUL A DECLASIFICAT 46 DE VIDEOCLIPURI",
         "fallbacks": ["46 de video", "videoclipuri cu privire"]}
      ]
    """
    data = json.loads(json_path.read_text("utf-8"))
    phrases = []
    for item in data:
        phrases.append((
            item["id"],
            item["label"],
            item["search"],
            int(item.get("duration", 7)),
            item["card_text"],
        ))
        if "fallbacks" in item:
            PHRASE_FALLBACKS[item["id"]] = item["fallbacks"]
    return phrases


def main() -> None:
    import argparse
    parser = argparse.ArgumentParser(
        description="Find viral phrase timecodes in a Geaboc sermon audio file."
    )
    parser.add_argument("audio", help="Path to unified edited audio (MP3/WAV)")
    parser.add_argument(
        "--model", default="large-v3",
        help="Whisper model (default: large-v3). Use 'small' for a quick test."
    )
    parser.add_argument(
        "--phrases", metavar="PHRASES_JSON",
        help="JSON file defining this sermon's viral phrases (overrides built-in C0073 list)"
    )
    args = parser.parse_args()

    audio_path = Path(args.audio).expanduser().resolve()
    if not audio_path.exists():
        print(f"ERROR: file not found: {audio_path}")
        sys.exit(1)

    model_size = args.model

    # Override phrases if a JSON config is provided (for C0074+)
    phrases_to_use = PHRASES
    if args.phrases:
        phrases_json = Path(args.phrases).expanduser().resolve()
        if not phrases_json.exists():
            print(f"ERROR: phrases JSON not found: {phrases_json}")
            sys.exit(1)
        phrases_to_use = _load_phrases_from_json(phrases_json)
        print(f"Loaded {len(phrases_to_use)} phrases from {phrases_json.name}")

    print(f"\n{'='*60}")
    print(f"  Geaboc Phrase Finder — {audio_path.name}")
    print(f"  Model: whisper-{model_size}")
    print(f"  Phrases: {len(phrases_to_use)}")
    print(f"{'='*60}\n")

    try:
        from faster_whisper import WhisperModel
    except ImportError:
        print("ERROR: faster-whisper not installed.")
        print("Fix:   pip3 install faster-whisper")
        sys.exit(1)

    print("Loading model (downloads ~3 GB on first run)…")
    model = WhisperModel(model_size, device="cpu", compute_type="int8")

    print(f"Transcribing {audio_path.name} — may take 3-5 min on iMac M4…\n")
    segments_iter, info = model.transcribe(
        str(audio_path),
        language="ro",
        beam_size=5,
        vad_filter=True,
        word_timestamps=True,
    )

    segments: list[dict] = []
    for seg in segments_iter:
        segments.append({
            "start": seg.start,
            "end":   seg.end,
            "text":  seg.text,
        })
        print(f"  [{_fmt(seg.start)} → {_fmt(seg.end)}] {seg.text.strip()[:80]}")

    print(f"\nTranscribed {len(segments)} segments "
          f"({info.duration:.1f}s, language={info.language})\n")

    # Search
    hits: dict[str, Hit | None] = {}
    for pid, label, primary, duration, card in phrases_to_use:
        fallbacks = PHRASE_FALLBACKS.get(pid, [])
        hit = _search_segments(segments, pid, label, primary, fallbacks, duration, card)
        hits[pid] = hit

    # Report
    print(f"\n{'─'*60}")
    print("  RESULTS — Copy these into build_coldopen.py")
    print(f"{'─'*60}\n")

    timecodes: dict[str, dict] = {}
    all_found = True
    for pid, label, primary, duration, card in phrases_to_use:
        hit = hits[pid]
        if hit:
            print(f"✅  {label}")
            print(f"    IN:  {hit.clip_in}   OUT: {hit.clip_out}   ({duration}s)")
            print(f"    Card: {card}\n")
            timecodes[pid] = {
                "label":         label,
                "card_text_ro":  card,
                "clip_in":       hit.clip_in,
                "clip_out":      hit.clip_out,
                "clip_duration": duration,
            }
        else:
            print(f"❌  {label}")
            print(f"    NOT FOUND — searched for: '{primary}'")
            print(f"    Try scrubbing FCP around the topic manually.\n")
            all_found = False

    # Write JSON
    out_json = audio_path.parent / f"{audio_path.stem}_timecodes.json"
    out_json.write_text(
        json.dumps({
            "audio_file": str(audio_path),
            "duration_sec": info.duration,
            "model": model_size,
            "timecodes": timecodes,
        }, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(f"{'─'*60}")
    print(f"Timecodes written to: {out_json}")
    if all_found:
        print("All 5 phrases found. Run build_coldopen.py next.")
    else:
        print("Some phrases not found — edit the JSON manually for missing entries,")
        print("then run build_coldopen.py.")
    print(f"{'─'*60}\n")


if __name__ == "__main__":
    main()
