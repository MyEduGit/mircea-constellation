#!/usr/bin/env python3
"""reformat_srt.py — Merge split-sentence SRT segments into complete phrases.

Reads a corrected SRT where segments are cut mid-sentence (YouTube ASR artifact),
merges them into complete sentences, then re-splits at natural break points with
proper subtitle length (≤42 chars/line, ≤2 lines, ≤7s per card).

Usage:
    python3 reformat_srt.py GFttc7f5zEo_RO_corrected.srt
    → writes GFttc7f5zEo_RO_final.srt
"""
from __future__ import annotations
import re
import sys
from pathlib import Path

MAX_LINE_CHARS = 42
MAX_CARD_CHARS = MAX_LINE_CHARS * 2   # 84 chars = 2 lines
MAX_CARD_MS    = 7_000                # 7 seconds max per card


# ── Timecode helpers ──────────────────────────────────────────────────────────

def tc_to_ms(tc: str) -> int:
    h, m, rest = tc.split(":")
    s, ms = rest.split(",")
    return int(h)*3_600_000 + int(m)*60_000 + int(s)*1_000 + int(ms)

def ms_to_tc(ms: int) -> str:
    ms = max(0, int(ms))
    h, r = divmod(ms, 3_600_000)
    m, r = divmod(r, 60_000)
    s, ms_ = divmod(r, 1_000)
    return f"{h:02d}:{m:02d}:{s:02d},{ms_:03d}"


# ── SRT parse / render ────────────────────────────────────────────────────────

def parse_srt(raw: str) -> list[dict]:
    entries = []
    for block in re.split(r"\n{2,}", raw.strip()):
        lines = block.strip().splitlines()
        if len(lines) < 3:
            continue
        try:
            int(lines[0].strip())
        except ValueError:
            continue
        m = re.match(r"(\d{2}:\d{2}:\d{2},\d{3})\s*-->\s*(\d{2}:\d{2}:\d{2},\d{3})", lines[1])
        if not m:
            continue
        text = " ".join(l.strip() for l in lines[2:])
        entries.append({"start": tc_to_ms(m.group(1)), "end": tc_to_ms(m.group(2)), "text": text})
    return entries

def render_srt(cards: list[dict]) -> str:
    parts = []
    for i, c in enumerate(cards, 1):
        parts.append(f"{i}\n{ms_to_tc(c['start'])} --> {ms_to_tc(c['end'])}\n{c['text']}")
    return "\n\n".join(parts) + "\n"


# ── Sentence-end detection ────────────────────────────────────────────────────

_ENDS_SENTENCE = re.compile(r'[.!?»"]\s*$')

# Romanian words that appear at segment start but are continuations, not new sentences
_CONTINUATION_WORDS = {
    "și", "sau", "dar", "că", "care", "pe", "în", "la", "cu", "de",
    "prin", "spre", "când", "dacă", "pentru", "ca", "să", "o", "un",
    "cei", "cel", "cele", "tot", "toți", "toată", "atunci", "după",
    "înainte", "între", "mai", "nu", "se", "din", "despre", "astfel",
    "deci", "iar", "ci", "fie", "nici",
}

def _is_continuation(prev: str, nxt: str) -> bool:
    """True if nxt continues the sentence from prev."""
    prev = prev.strip()
    nxt  = nxt.strip()
    if not prev or not nxt:
        return False
    # If prev ends with sentence-final punctuation → NOT a continuation
    if _ENDS_SENTENCE.search(prev):
        return False
    # If next starts lowercase → definitely a continuation
    if nxt[0].islower():
        return True
    # If next starts with a known continuation word (any case) → continuation
    first = nxt.split()[0].rstrip(",.;:").lower()
    if first in _CONTINUATION_WORDS:
        return True
    return False


# ── Merge + re-split ──────────────────────────────────────────────────────────

def merge_continuations(entries: list[dict]) -> list[dict]:
    """Join adjacent entries that form a single sentence."""
    if not entries:
        return []
    groups = [dict(entries[0])]
    for e in entries[1:]:
        if _is_continuation(groups[-1]["text"], e["text"]):
            groups[-1]["text"] = groups[-1]["text"].rstrip() + " " + e["text"].lstrip()
            groups[-1]["end"]  = e["end"]
        else:
            groups.append(dict(e))
    return groups


def _wrap_text(text: str) -> str:
    """Wrap text into ≤2 lines of ≤MAX_LINE_CHARS chars (never truncates)."""
    words = text.split()
    if len(text) <= MAX_LINE_CHARS:
        return text
    # Find split point closest to midpoint where line1 ≤ MAX_LINE_CHARS
    best_i, best_len = 0, 0
    acc = 0
    for i, w in enumerate(words):
        acc += len(w) + (1 if i else 0)
        if acc <= MAX_LINE_CHARS:
            best_i, best_len = i + 1, acc
    if best_i:
        line1 = " ".join(words[:best_i])
        line2 = " ".join(words[best_i:])
        return line1 + "\n" + line2
    return text   # single very-long word — leave as-is


def _split_at_boundary(text: str) -> list[str]:
    """Split text into chunks of ≤MAX_CARD_CHARS at natural break points.

    Never truncates — every word appears in exactly one output chunk.
    """
    text = text.strip()
    if not text:
        return []

    # Tokenise at sentence boundaries, then clause/comma boundaries
    # Strategy: greedily fill chunks up to MAX_CARD_CHARS, breaking at
    # sentence-end > comma > word boundaries (in that priority order).
    words = text.split()
    chunks: list[str] = []
    buf: list[str] = []

    def buf_str() -> str:
        return " ".join(buf)

    for w in words:
        trial = buf_str() + (" " if buf else "") + w
        if len(trial) <= MAX_CARD_CHARS:
            buf.append(w)
            # Flush at sentence-end punctuation
            if w[-1] in ".!?»" and len(buf_str()) > MAX_LINE_CHARS // 2:
                chunks.append(buf_str())
                buf = []
        else:
            # Current word doesn't fit — flush buf, start new with w
            if buf:
                # Try to flush at last comma position for natural break
                flush_at = None
                for i in range(len(buf) - 1, -1, -1):
                    if buf[i].endswith(",") and i > 0:
                        flush_at = i + 1
                        break
                if flush_at and flush_at < len(buf):
                    chunks.append(" ".join(buf[:flush_at]))
                    buf = buf[flush_at:]
                else:
                    chunks.append(buf_str())
                    buf = []
            buf.append(w)

    if buf:
        chunks.append(buf_str())

    # Merge very short trailing chunks into the previous one if they fit
    merged: list[str] = []
    for c in chunks:
        if merged and len(merged[-1]) + 1 + len(c) <= MAX_CARD_CHARS:
            merged[-1] = merged[-1] + " " + c
        else:
            merged.append(c)

    return [c.strip() for c in merged if c.strip()]


def split_into_cards(groups: list[dict]) -> list[dict]:
    """Re-split merged groups into subtitle-sized cards with proportional timing."""
    cards: list[dict] = []
    for g in groups:
        text = g["text"].strip()
        dur  = g["end"] - g["start"]
        chunks = _split_at_boundary(text)
        if not chunks:
            continue
        total_chars = sum(len(c) for c in chunks) or 1
        t = g["start"]
        for i, chunk in enumerate(chunks):
            frac = len(chunk) / total_chars
            card_dur = min(int(dur * frac), MAX_CARD_MS)
            end = t + card_dur if i < len(chunks) - 1 else g["end"]
            end = min(end, g["end"])
            cards.append({
                "start": int(t),
                "end":   int(end),
                "text":  _wrap_text(chunk),
            })
            t = end
    return cards


# ── Verify no text lost ───────────────────────────────────────────────────────

def _flatten(entries: list[dict]) -> str:
    return " ".join(e["text"].replace("\n", " ") for e in entries)


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    if len(sys.argv) < 2:
        print("Usage: reformat_srt.py <input.srt> [output.srt]")
        sys.exit(1)

    in_path  = Path(sys.argv[1])
    out_path = Path(sys.argv[2]) if len(sys.argv) > 2 else \
               in_path.with_stem(in_path.stem.replace("_corrected", "_final"))

    raw = in_path.read_text(encoding="utf-8")
    entries = parse_srt(raw)
    print(f"Input:  {len(entries)} segments")

    merged = merge_continuations(entries)
    print(f"Merged: {len(merged)} sentence groups")

    cards = split_into_cards(merged)
    print(f"Output: {len(cards)} subtitle cards")

    # Verify no text lost
    in_words  = _flatten(entries).split()
    out_words = _flatten(cards).split()
    if len(in_words) != len(out_words):
        print(f"⚠️  Word count: in={len(in_words)}  out={len(out_words)}  "
              f"diff={len(in_words)-len(out_words)}")
    else:
        print(f"✅ Word count preserved: {len(out_words)} words")

    out_path.write_text(render_srt(cards), encoding="utf-8")
    print(f"✅ Written: {out_path}")

    print("\n── Preview (first 10 cards) ──")
    for c in cards[:10]:
        print(f"[{ms_to_tc(c['start'])} → {ms_to_tc(c['end'])}]")
        print(c["text"])
        print()


if __name__ == "__main__":
    main()
