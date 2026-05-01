"""resegment_phrase_cues — break a transcript into phrase-length caption cues.

Goal: a cue layout suitable for YouTube/BBC caption guidance (the
"C0066-style" phrase-cue pattern) — short, reading-friendly lines
rather than the long sentence blocks Whisper/AssemblyAI return. For a
60-minute speech this typically produces ~600-800 cues (~3-5 s each),
which matches the ~690 target cited in operator discussions.

Algorithm (deterministic — no LLM):
  1. Load segments.clean.json if postprocess_transcript ran, else
     segments.json.
  2. Flatten to a word stream with per-word timestamps. If the upstream
     transcriber didn't emit word timestamps (AssemblyAI dashboard
     imports), interpolate linearly across each segment — honest
     approximation, not silence.
  3. Greedy cue builder obeys four caps:
       a. hard break on sentence terminator (. ! ?)
       b. soft break on conjunction / punctuation when the running cue
          has enough substance (≥ MIN_CUE_WORDS and ≥ MIN_CUE_CHARS)
       c. length cap (MAX_CUE_CHARS across up to 2 lines)
       d. duration cap (MAX_CUE_SEC)
  4. Split each cue into ≤ 2 lines of ≤ MAX_LINE_CHARS, balanced.
  5. Enforce MIN_CUE_SEC by extending short cues into the gap before
     the next one (never overlapping).

All defaults are overridable per-call via payload.
"""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

# Defaults align with YouTube recommended caption layout, tuned against a
# one-hour Romanian talking-head sample so output lands near the C0066
# ~690-cues-per-hour target rather than the sub-2-second hyper-dense
# output a naive soft-punctuation splitter produces.
_MAX_LINE_CHARS = 42
_MAX_CUE_CHARS = 84          # 2 * MAX_LINE_CHARS
_MIN_CUE_WORDS = 5
_MIN_CUE_CHARS = 35
_MIN_CUE_SEC = 1.5
_MAX_CUE_SEC = 6.0

_HARD_BREAK = re.compile(r"[.!?…]+$")
# Trailing punctuation that MAY close a cue when the cue already carries
# enough substance. Conjunction-as-start-of-phrase heuristics were tried
# and removed — they over-split Romanian speech on every "și" / "iar".
_SOFT_PUNCT = re.compile(r"[;:—–]$")

_WORD_RE = re.compile(r"\S+")


def _format_ts(seconds: float, sep: str) -> str:
    ms = int(round(seconds * 1000))
    h, ms = divmod(ms, 3_600_000)
    m, ms = divmod(ms, 60_000)
    s, ms = divmod(ms, 1000)
    return f"{h:02d}:{m:02d}:{s:02d}{sep}{ms:03d}"


def _flatten_words(segments: list[dict]) -> list[dict]:
    """Return [{start, end, word}] across the whole transcript.

    When a segment carries per-word timestamps we honour them. Otherwise
    we interpolate linearly across the segment's [start, end]. This is
    transparent approximation — the returned dict has `approx: True`
    for interpolated words so a caller can expose the fact honestly.
    """
    words: list[dict] = []
    for seg in segments:
        text = (seg.get("text") or "").strip()
        if not text:
            continue
        s = float(seg.get("start", 0.0))
        e = float(seg.get("end", s))
        per_word = seg.get("words")
        if per_word:
            for w in per_word:
                tok = (w.get("word") or "").strip()
                if not tok:
                    continue
                words.append({
                    "start": float(w["start"]),
                    "end": float(w["end"]),
                    "word": tok,
                    "approx": False,
                })
            continue
        tokens = _WORD_RE.findall(text)
        n = len(tokens)
        if n == 0:
            continue
        dur = max(e - s, 0.0)
        step = (dur / n) if n > 0 and dur > 0 else 0.0
        for i, tok in enumerate(tokens):
            ws = s + step * i
            we = s + step * (i + 1) if dur > 0 else s
            words.append({"start": ws, "end": we, "word": tok, "approx": True})
    return words


def _should_break(running_text: str, running_words: int,
                  token: str,
                  cue_start: float, word_end: float,
                  max_cue_chars: int, max_cue_sec: float,
                  min_cue_words: int, min_cue_chars: int) -> tuple[bool, bool]:
    """Return (break_before, break_after) for the incoming token."""
    # Would adding this word exceed the char budget? → break BEFORE.
    projected = len(running_text) + (1 if running_text else 0) + len(token)
    if running_text and projected > max_cue_chars:
        return True, False
    # Did we cross the duration cap already? → break BEFORE.
    if running_text and (word_end - cue_start) > max_cue_sec:
        return True, False

    # Hard sentence terminator always closes the cue.
    if _HARD_BREAK.search(token):
        return False, True
    # Semicolon / colon / em-dash close only when there's enough substance.
    has_substance = (running_words + 1 >= min_cue_words
                     and projected >= min_cue_chars)
    if has_substance and _SOFT_PUNCT.search(token):
        return False, True
    return False, False


def _balance_two_lines(text: str, max_line_chars: int) -> list[str]:
    """Split into ≤ 2 lines of ≤ max_line_chars, balanced by length."""
    if len(text) <= max_line_chars:
        return [text]
    tokens = text.split()
    if len(tokens) < 2:
        return [text]  # single long token — can't break it
    best: tuple[int, list[str]] | None = None
    for i in range(1, len(tokens)):
        left = " ".join(tokens[:i])
        right = " ".join(tokens[i:])
        if len(left) > max_line_chars or len(right) > max_line_chars:
            continue
        score = abs(len(left) - len(right))
        if best is None or score < best[0]:
            best = (score, [left, right])
    if best is None:
        # Hard fall-back: cut at max_line_chars.
        return [text[:max_line_chars], text[max_line_chars:]]
    return best[1]


def _build_cues(words: list[dict], *, max_cue_chars: int, max_cue_sec: float,
                min_cue_words: int, min_cue_chars: int,
                min_cue_sec: float, max_line_chars: int) -> list[dict]:
    cues: list[dict] = []
    cur_words: list[dict] = []
    cur_text = ""

    def flush():
        if not cur_words:
            return
        start = cur_words[0]["start"]
        end = cur_words[-1]["end"]
        text = " ".join(w["word"] for w in cur_words)
        lines = _balance_two_lines(text, max_line_chars)
        cues.append({
            "start": start,
            "end": end,
            "text": "\n".join(lines),
            "word_count": len(cur_words),
            "char_count": len(text),
            "approx_timing": any(w["approx"] for w in cur_words),
        })

    for w in words:
        token = w["word"]
        cue_start = cur_words[0]["start"] if cur_words else w["start"]
        break_before, break_after = _should_break(
            cur_text, len(cur_words), token,
            cue_start, w["end"],
            max_cue_chars, max_cue_sec,
            min_cue_words, min_cue_chars,
        )
        if break_before:
            flush()
            cur_words = []
            cur_text = ""
        cur_words.append(w)
        cur_text = (cur_text + " " + token).strip() if cur_text else token
        if break_after:
            flush()
            cur_words = []
            cur_text = ""
    flush()

    # Minimum duration: extend short cues forward into the gap before the
    # next cue. Never overlap.
    for i, cue in enumerate(cues):
        dur = cue["end"] - cue["start"]
        if dur >= min_cue_sec:
            continue
        need = min_cue_sec - dur
        next_start = cues[i + 1]["start"] if i + 1 < len(cues) else cue["end"] + need
        cue["end"] = min(cue["end"] + need, next_start)

    return cues


def _write_srt(cues: list[dict], path: Path) -> None:
    lines: list[str] = []
    for i, c in enumerate(cues, start=1):
        lines.append(str(i))
        lines.append(f"{_format_ts(c['start'], ',')} --> {_format_ts(c['end'], ',')}")
        lines.append(c["text"])
        lines.append("")
    path.write_text("\n".join(lines), encoding="utf-8")


def _write_vtt(cues: list[dict], path: Path) -> None:
    lines: list[str] = ["WEBVTT", ""]
    for c in cues:
        lines.append(f"{_format_ts(c['start'], '.')} --> {_format_ts(c['end'], '.')}")
        lines.append(c["text"])
        lines.append("")
    path.write_text("\n".join(lines), encoding="utf-8")


async def resegment_phrase_cues(payload: dict[str, Any], data_root: Path) -> dict:
    """Re-segment a transcript into phrase-length caption cues.

    Payload:
      stem           (str, required): transcript directory under /data/transcripts/
      max_cue_chars  (int, optional): default 84 (2 lines × 42)
      max_line_chars (int, optional): default 42
      min_cue_words  (int, optional): default 3
      min_cue_chars  (int, optional): default 20
      min_cue_sec    (float, optional): default 1.0
      max_cue_sec    (float, optional): default 6.0
    """
    stem = Path(payload["stem"]).name
    d = data_root / "transcripts" / stem
    seg_file = d / "segments.clean.json"
    if not seg_file.exists():
        seg_file = d / "segments.json"
    if not seg_file.exists():
        return {"status": "error", "handler": "resegment_phrase_cues",
                "error": "segments_not_found", "expected_at": str(seg_file),
                "hint": "run a transcribe_* handler first"}

    data = json.loads(seg_file.read_text(encoding="utf-8"))
    segments = data.get("segments", [])
    if not segments:
        return {"status": "error", "handler": "resegment_phrase_cues",
                "error": "no_segments_in_source", "source": str(seg_file)}

    words = _flatten_words(segments)
    if not words:
        return {"status": "error", "handler": "resegment_phrase_cues",
                "error": "no_words_extracted", "source": str(seg_file)}

    cues = _build_cues(
        words,
        max_cue_chars=int(payload.get("max_cue_chars", _MAX_CUE_CHARS)),
        max_cue_sec=float(payload.get("max_cue_sec", _MAX_CUE_SEC)),
        min_cue_words=int(payload.get("min_cue_words", _MIN_CUE_WORDS)),
        min_cue_chars=int(payload.get("min_cue_chars", _MIN_CUE_CHARS)),
        min_cue_sec=float(payload.get("min_cue_sec", _MIN_CUE_SEC)),
        max_line_chars=int(payload.get("max_line_chars", _MAX_LINE_CHARS)),
    )

    _write_srt(cues, d / "transcript.cues.srt")
    _write_vtt(cues, d / "transcript.cues.vtt")
    (d / "cues.json").write_text(
        json.dumps({
            "source": str(seg_file),
            "language": data.get("language"),
            "cue_count": len(cues),
            "total_chars": sum(c["char_count"] for c in cues),
            "duration_sec": cues[-1]["end"] if cues else 0.0,
            "cues": cues,
        }, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    durations = [c["end"] - c["start"] for c in cues] or [0.0]
    chars = [c["char_count"] for c in cues] or [0]
    total_dur = cues[-1]["end"] - cues[0]["start"] if cues else 0.0
    approx_any = any(c["approx_timing"] for c in cues)
    return {
        "status": "success",
        "handler": "resegment_phrase_cues",
        "stem": stem,
        "source": str(seg_file),
        "cue_count": len(cues),
        "duration_sec": total_dur,
        "avg_duration_sec": sum(durations) / len(durations),
        "avg_chars_per_cue": sum(chars) / len(chars),
        "approx_timing": approx_any,
        "outputs": [
            str(d / "transcript.cues.srt"),
            str(d / "transcript.cues.vtt"),
            str(d / "cues.json"),
        ],
    }
