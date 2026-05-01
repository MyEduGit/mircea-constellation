"""strip_speaker_labels — remove "Speaker N:" prefixes from an SRT.

YouTube's auto-captions inject diarisation labels like "Speaker 1:" on
every cue, even for monologue content. When those get saved as a CC
track, every subtitle line visible to viewers starts with a noisy
"Speaker 1:" prefix. This handler removes them.

Scope is narrow:
  - Only matches known speaker-label shapes at the START of a cue line.
  - Does NOT touch in-body text, punctuation, or timings.
  - Does NOT remove anything if no known shape matches — errs on the
    side of preserving operator content.

Deterministic, idempotent: running twice on the same file yields the
same output. No external dependencies.

Patterns recognised (case-insensitive, locale-aware):
  Speaker 1:          Speaker A:           SPEAKER_00:
  [Speaker 1]         (Speaker 2)          - Speaker 3:
  Vorbitor 1:         Persoana 2:          Narator:

Input payload:
  stem       (str, optional): prefers /data/transcripts/<stem>/
                              transcript.srt, falls back to any .srt
                              directly under that dir.
  srt_path   (str, optional): explicit path under DATA_ROOT.

Exactly one of `stem` or `srt_path` is required.

Output (next to source):
  <name>.nolabels.srt    — stripped copy
  <name>.nolabels.json   — audit report with per-cue removal log
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

_SRT_TIME = re.compile(
    r"(\d{2}):(\d{2}):(\d{2})[,\.](\d{3})\s*-->\s*"
    r"(\d{2}):(\d{2}):(\d{2})[,\.](\d{3})"
)


# Order matters: the most specific shapes go first. Each pattern only
# matches at the START of a stripped line (after any leading dash /
# bullet / quote marker).
_LEADING_JUNK = r"[-–—>•·]?\s*"

_LABEL_PATTERNS: tuple[tuple[str, re.Pattern], ...] = (
    # Bracketed: [Speaker 1], (Speaker 2), <Speaker A>
    ("bracket",
     re.compile(
         r"^" + _LEADING_JUNK +
         r"[\[\(\<]\s*(?:Speaker|SPEAKER|Vorbitor|Persoana|Narator)"
         r"(?:[\s_]?[A-Z0-9]+)?\s*[\]\)\>]\s*[:\-]?\s*",
         re.IGNORECASE,
     )),
    # Bare: Speaker 1:, SPEAKER_00:, Vorbitor 2:, Narator:
    ("bare",
     re.compile(
         r"^" + _LEADING_JUNK +
         r"(?:Speaker|SPEAKER|Vorbitor|Persoana|Narator)"
         r"(?:[\s_]?[A-Z0-9]+)?\s*:\s*",
         re.IGNORECASE,
     )),
)


@dataclass
class Cue:
    index: int
    timestamp: str
    lines: list[str]  # preserve multi-line SRT cues


@dataclass
class Removal:
    cue: int
    line: int
    pattern: str
    before: str
    after: str


def _parse_srt(content: str) -> list[Cue]:
    if content.startswith("\ufeff"):
        content = content[1:]
    content = content.replace("\r\n", "\n").replace("\r", "\n")
    blocks = re.split(r"\n\s*\n", content.strip())
    cues: list[Cue] = []
    for block in blocks:
        lines = [ln for ln in block.split("\n") if ln != ""]
        if len(lines) < 2:
            continue
        if _SRT_TIME.search(lines[0]):
            ts_line = lines[0]
            text_lines = lines[1:]
            idx = len(cues) + 1
        else:
            try:
                idx = int(lines[0].strip())
            except ValueError:
                idx = len(cues) + 1
            ts_line = lines[1] if len(lines) > 1 else ""
            text_lines = lines[2:]
        if not _SRT_TIME.search(ts_line):
            continue
        cues.append(Cue(index=idx, timestamp=ts_line.strip(),
                        lines=list(text_lines)))
    return cues


def _serialize_srt(cues: list[Cue], write_bom: bool) -> str:
    parts: list[str] = []
    for i, c in enumerate(cues, start=1):
        parts.append(str(i))
        parts.append(c.timestamp)
        parts.extend(c.lines)
        parts.append("")
    body = "\n".join(parts).rstrip() + "\n"
    return ("\ufeff" + body) if write_bom else body


def _strip_line(line: str) -> tuple[str, str | None]:
    """Apply patterns in order; return (cleaned, pattern_name_if_matched)."""
    for name, pat in _LABEL_PATTERNS:
        m = pat.match(line)
        if m:
            return line[m.end():].lstrip(), name
    return line, None


def _resolve_source(payload: dict[str, Any], data_root: Path) -> Path | dict:
    stem = payload.get("stem")
    srt_path = payload.get("srt_path")
    if bool(stem) == bool(srt_path):
        return {"status": "error", "handler": "strip_speaker_labels",
                "error": "exactly_one_of_stem_or_srt_path_required"}
    if stem:
        stem = Path(str(stem)).name
        base = data_root / "transcripts" / stem
        for candidate in (base / "transcript.srt", base / "transcript.cues.srt"):
            if candidate.exists():
                return candidate
        # Fall back to any *.srt under the stem directory; pick first
        # deterministically.
        if base.is_dir():
            for p in sorted(base.glob("*.srt")):
                return p
        return {"status": "error", "handler": "strip_speaker_labels",
                "error": "srt_not_found_for_stem",
                "searched": [str(base / "transcript.srt"),
                             str(base / "transcript.cues.srt")]}
    requested = Path(str(srt_path))
    candidate = (data_root / requested).resolve() if not requested.is_absolute() \
        else requested.resolve()
    try:
        candidate.relative_to(data_root.resolve())
    except ValueError:
        return {"status": "error", "handler": "strip_speaker_labels",
                "error": "srt_path_outside_data_root",
                "data_root": str(data_root.resolve())}
    if not candidate.exists():
        return {"status": "error", "handler": "strip_speaker_labels",
                "error": "srt_path_not_found", "path": str(candidate)}
    return candidate


async def strip_speaker_labels(payload: dict[str, Any], data_root: Path) -> dict:
    resolved = _resolve_source(payload, data_root)
    if isinstance(resolved, dict):
        return resolved
    src: Path = resolved

    write_bom = bool(payload.get("output_bom", True))

    try:
        raw = src.read_text(encoding="utf-8")
    except Exception as exc:
        return {"status": "error", "handler": "strip_speaker_labels",
                "error": "read_failed", "detail": str(exc), "path": str(src)}

    cues = _parse_srt(raw)
    if not cues:
        return {"status": "error", "handler": "strip_speaker_labels",
                "error": "no_cues_parsed", "path": str(src)}

    removals: list[Removal] = []
    cues_touched = 0
    for cue in cues:
        any_change = False
        # Whole-cue label on line 0 that leaves the rest of the cue
        # empty — drop it entirely rather than leaving a blank line
        # that would display as a flicker.
        new_lines: list[str] = []
        for li, line in enumerate(cue.lines):
            cleaned, pat = _strip_line(line)
            if pat is not None:
                removals.append(Removal(
                    cue=cue.index, line=li,
                    pattern=pat, before=line, after=cleaned,
                ))
                any_change = True
            if cleaned.strip() or new_lines:
                # Keep the line if non-blank OR we've already kept an
                # earlier line (preserves multi-line cue structure).
                new_lines.append(cleaned)
        if not new_lines:
            # Edge case: the entire cue was just a label. Keep the cue
            # but with a single blank to preserve count + timing.
            new_lines = [""]
        cue.lines = new_lines
        if any_change:
            cues_touched += 1

    clean_path = src.with_name(src.stem + ".nolabels" + src.suffix)
    json_path = src.with_name(src.stem + ".nolabels.json")

    clean_path.write_text(_serialize_srt(cues, write_bom=write_bom),
                          encoding="utf-8")
    json_path.write_text(json.dumps({
        "source": str(src),
        "clean": str(clean_path),
        "cues": len(cues),
        "cues_touched": cues_touched,
        "removals": [
            {"cue": r.cue, "line": r.line, "pattern": r.pattern,
             "before": r.before, "after": r.after}
            for r in removals
        ],
    }, ensure_ascii=False, indent=2), encoding="utf-8")

    return {
        "status": "success",
        "handler": "strip_speaker_labels",
        "source": str(src),
        "clean": str(clean_path),
        "json_audit": str(json_path),
        "cues": len(cues),
        "cues_touched": cues_touched,
        "removals_count": len(removals),
    }
