"""ESTRS — transcript file selection.

Priority:
  1. .md  (most structured, highest fidelity after editing)
  2. .txt
  3. .srt (fallback)

Among files of equal extension, select the one with the highest word count.
Ignore temporary/hidden files.
"""
from __future__ import annotations

import logging
import re
from pathlib import Path

from .config import (
    ALL_EXTENSIONS,
    FALLBACK_EXTENSIONS,
    IGNORE_PATTERN,
    MIN_WORD_COUNT,
    PREFERRED_EXTENSIONS,
)

log = logging.getLogger(__name__)

# SRT timestamp line pattern — stripped when counting words from .srt files
_SRT_STAMP = re.compile(r'^\d+$|^\d{2}:\d{2}:\d{2}[,\.]\d{3}\s*-->\s*\d{2}:\d{2}:\d{2}[,\.]\d{3}')


def _strip_srt(text: str) -> str:
    """Remove SRT sequence numbers and timestamp lines, keep only speech."""
    lines = []
    for line in text.splitlines():
        if not _SRT_STAMP.match(line.strip()):
            lines.append(line)
    return '\n'.join(lines)


def _word_count(path: Path) -> int:
    try:
        text = path.read_text(encoding='utf-8', errors='replace')
        if path.suffix.lower() == '.srt':
            text = _strip_srt(text)
        return len(text.split())
    except OSError:
        return 0


def _is_ignored(path: Path) -> bool:
    return bool(IGNORE_PATTERN.match(path.name))


def select_transcript(source_dir: Path) -> tuple[Path | None, str]:
    """Return (best_file, plain_text) for the given source directory.

    Scans recursively — source_dir may contain one level of sub-folders.
    Returns (None, '') if nothing usable is found.
    """
    candidates: list[Path] = []
    try:
        for p in source_dir.rglob('*'):
            if p.is_file() and not _is_ignored(p) and p.suffix.lower() in ALL_EXTENSIONS:
                candidates.append(p)
    except PermissionError:
        return None, ''

    if not candidates:
        return None, ''

    # Tier 1: preferred extensions
    preferred = [p for p in candidates if p.suffix.lower() in PREFERRED_EXTENSIONS]
    pool = preferred if preferred else candidates

    # Within pool, pick highest word-count
    scored = [(p, _word_count(p)) for p in pool]
    scored.sort(key=lambda x: x[1], reverse=True)

    best, wc = scored[0]
    if wc < MIN_WORD_COUNT:
        log.warning("best candidate %s has only %d words (< %d threshold)", best, wc, MIN_WORD_COUNT)

    text = _extract_plain(best)
    log.debug("selected %s (%d words)", best, wc)
    return best, text


def _extract_plain(path: Path) -> str:
    """Read file and return clean plain text (SRT timestamps stripped)."""
    try:
        raw = path.read_text(encoding='utf-8', errors='replace')
    except OSError as exc:
        log.error("cannot read %s: %s", path, exc)
        return ''
    if path.suffix.lower() == '.srt':
        raw = _strip_srt(raw)
    return raw.strip()
