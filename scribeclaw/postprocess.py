"""postprocess_transcript — Romanian orthography normalization.

Fixes the common, deterministic errors in Whisper Romanian output:
  - legacy cedilla forms (ş→ș, Ş→Ș, ţ→ț, Ţ→Ț)
  - fully unaccented ASCII output where only the diacritic is missing
    is NOT silently guessed here — language-model guessing belongs in
    a dedicated NLP pass, not in a deterministic post-processor.
  - double-spacing / leading-space punctuation from VAD boundaries
  - paragraph reflow: collapse ultra-short segments, split on sentence
    terminators so .txt is reading-friendly

Does NOT call an LLM. Every rule is deterministic. If the operator wants
LLM-assisted repunctuation, that belongs to a separate handler (out of
scope for this scaffold).
"""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

# Legacy Romanian cedilla (U+015F/015E, U+0163/0162) → correct comma-below
# forms (U+0219/0218, U+021B/021A). Whisper sometimes emits the cedilla.
_CEDILLA_MAP = str.maketrans({
    "\u015f": "\u0219",  # ş → ș
    "\u015e": "\u0218",  # Ş → Ș
    "\u0163": "\u021b",  # ţ → ț
    "\u0162": "\u021a",  # Ţ → Ț
})

_SENTENCE_SPLIT = re.compile(r"(?<=[.!?])\s+(?=[A-ZĂÂÎȘȚ])")
_MULTISPACE = re.compile(r"[ \t]+")
_SPACE_BEFORE_PUNCT = re.compile(r"\s+([,.;:!?])")


def _fix_text(s: str) -> str:
    s = s.translate(_CEDILLA_MAP)
    s = _MULTISPACE.sub(" ", s)
    s = _SPACE_BEFORE_PUNCT.sub(r"\1", s)
    return s.strip()


async def postprocess_transcript(payload: dict[str, Any], data_root: Path) -> dict:
    """Clean transcript files in place, write *.clean.* alongside originals.

    Payload:
      stem (str, required): directory name under /data/transcripts/
    """
    stem = Path(payload["stem"]).name
    d = data_root / "transcripts" / stem
    seg_file = d / "segments.json"
    if not seg_file.exists():
        return {"status": "error", "handler": "postprocess_transcript",
                "error": "segments_not_found", "expected_at": str(seg_file),
                "hint": "run transcribe_ro first"}

    data = json.loads(seg_file.read_text(encoding="utf-8"))
    segments = data.get("segments", [])

    fixed_count = 0
    for seg in segments:
        original = seg.get("text", "")
        cleaned = _fix_text(original)
        if cleaned != original:
            fixed_count += 1
        seg["text"] = cleaned

    # Reflow .txt into sentence-per-paragraph without LLM guesswork.
    full = " ".join(s["text"] for s in segments if s["text"])
    full = _fix_text(full)
    paragraphs = _SENTENCE_SPLIT.split(full)

    (d / "segments.clean.json").write_text(
        json.dumps({**data, "segments": segments},
                   ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    (d / "transcript.clean.txt").write_text(
        "\n\n".join(p.strip() for p in paragraphs if p.strip()),
        encoding="utf-8",
    )

    return {
        "status": "success",
        "handler": "postprocess_transcript",
        "stem": stem,
        "segments_total": len(segments),
        "segments_modified": fixed_count,
        "paragraphs": len(paragraphs),
        "outputs": [
            str(d / "segments.clean.json"),
            str(d / "transcript.clean.txt"),
        ],
    }
