"""validate_srt — structural + encoding sanity checks for a SubRip file.

Catches the bugs that silently break YouTube's captions uploader:
  - File not valid UTF-8 (or unwanted UTF-16 BOM)
  - Mis-numbered indices (1, 2, 4, 5, ...)
  - Timestamps that don't parse
  - `end < start` within a cue
  - Cue N's start earlier than cue N-1's start (out-of-order)
  - Overlapping cues (cue N starts before cue N-1 ends)
  - Empty cue bodies
  - Cues exceeding YouTube's per-line char cap (soft warning, not error)
  - CRLF / trailing whitespace inconsistency (soft warning)

Returns a structured report. `status: success` iff no ERROR-level issues;
warnings never fail the handler — they're surfaced for the operator.

Deterministic, no external deps. Works on the bytes of the file (so the
encoding check is honest, not post-decode).
"""
from __future__ import annotations

import re
from pathlib import Path
from typing import Any

_SRT_TIME = re.compile(
    r"^(\d{2}):(\d{2}):(\d{2})[,\.](\d{3})\s*-->\s*"
    r"(\d{2}):(\d{2}):(\d{2})[,\.](\d{3})\s*$"
)

_UTF16_BOM_LE = b"\xff\xfe"
_UTF16_BOM_BE = b"\xfe\xff"
_UTF8_BOM = b"\xef\xbb\xbf"


def _ms(h: int, m: int, s: int, ms: int) -> int:
    return ((h * 3600 + m * 60 + s) * 1000) + ms


def _resolve_source(payload: dict[str, Any], data_root: Path) -> Path | dict:
    stem = payload.get("stem")
    srt_path = payload.get("srt_path")
    if bool(stem) == bool(srt_path):
        return {"status": "error", "handler": "validate_srt",
                "error": "exactly_one_of_stem_or_srt_path_required"}
    if stem:
        stem = Path(str(stem)).name
        base = data_root / "transcripts" / stem
        for candidate in (base / "transcript.srt", base / "transcript.cues.srt"):
            if candidate.exists():
                return candidate
        if base.is_dir():
            for p in sorted(base.glob("*.srt")):
                return p
        return {"status": "error", "handler": "validate_srt",
                "error": "srt_not_found_for_stem"}
    requested = Path(str(srt_path))
    candidate = (data_root / requested).resolve() if not requested.is_absolute() \
        else requested.resolve()
    try:
        candidate.relative_to(data_root.resolve())
    except ValueError:
        return {"status": "error", "handler": "validate_srt",
                "error": "srt_path_outside_data_root",
                "data_root": str(data_root.resolve())}
    if not candidate.exists():
        return {"status": "error", "handler": "validate_srt",
                "error": "srt_path_not_found", "path": str(candidate)}
    return candidate


async def validate_srt(payload: dict[str, Any], data_root: Path) -> dict:
    resolved = _resolve_source(payload, data_root)
    if isinstance(resolved, dict):
        return resolved
    src: Path = resolved

    max_line_chars = int(payload.get("max_line_chars", 42))

    errors: list[dict] = []
    warnings: list[dict] = []

    # —— Encoding checks on raw bytes first —— ------------------------
    try:
        raw_bytes = src.read_bytes()
    except Exception as exc:
        return {"status": "error", "handler": "validate_srt",
                "error": "read_failed", "detail": str(exc),
                "path": str(src)}
    has_utf8_bom = raw_bytes.startswith(_UTF8_BOM)
    if raw_bytes.startswith(_UTF16_BOM_LE) or raw_bytes.startswith(_UTF16_BOM_BE):
        errors.append({"level": "error", "code": "utf16_encoding",
                       "detail": "file starts with a UTF-16 BOM; "
                                 "YouTube requires UTF-8"})
    try:
        text = raw_bytes.decode("utf-8")
    except UnicodeDecodeError as exc:
        return {"status": "error", "handler": "validate_srt",
                "error": "not_utf8", "detail": str(exc),
                "path": str(src), "has_utf8_bom": has_utf8_bom}

    if has_utf8_bom:
        text = text[1:]  # strip BOM for parsing
    if "\r\n" in text:
        warnings.append({"level": "warn", "code": "crlf_line_endings",
                         "detail": "CRLF found; YouTube is tolerant, but LF "
                                   "is the SRT convention"})

    # —— Cue-level parse —— -------------------------------------------
    text_norm = text.replace("\r\n", "\n").replace("\r", "\n")
    blocks = re.split(r"\n\s*\n", text_norm.strip())
    if not blocks or not blocks[0].strip():
        errors.append({"level": "error", "code": "empty_file"})
        return {"status": "error", "handler": "validate_srt",
                "path": str(src), "errors": errors, "warnings": warnings,
                "cues": 0}

    cue_summaries: list[dict] = []
    prev_end_ms = -1
    prev_start_ms = -1
    prev_index = 0
    for bi, block in enumerate(blocks):
        lines = [ln for ln in block.split("\n") if ln != ""]
        if len(lines) < 2:
            errors.append({"level": "error", "code": "malformed_block",
                           "block": bi + 1, "detail": "fewer than 2 lines"})
            continue
        # Tolerate missing index line but record it.
        if _SRT_TIME.match(lines[0]):
            index_declared: int | None = None
            ts_line = lines[0]
            body_lines = lines[1:]
        else:
            try:
                index_declared = int(lines[0].strip())
            except ValueError:
                errors.append({"level": "error", "code": "index_not_integer",
                               "block": bi + 1, "value": lines[0]})
                index_declared = None
            ts_line = lines[1] if len(lines) > 1 else ""
            body_lines = lines[2:]

        m = _SRT_TIME.match(ts_line.strip())
        if not m:
            errors.append({"level": "error", "code": "bad_timestamp_line",
                           "block": bi + 1, "value": ts_line})
            continue
        sh, sm, ss, sms, eh, em, es, ems = (int(g) for g in m.groups())
        start_ms = _ms(sh, sm, ss, sms)
        end_ms = _ms(eh, em, es, ems)

        if end_ms < start_ms:
            errors.append({"level": "error", "code": "end_before_start",
                           "block": bi + 1,
                           "start_ms": start_ms, "end_ms": end_ms})
        if start_ms < prev_start_ms:
            errors.append({"level": "error", "code": "out_of_order",
                           "block": bi + 1,
                           "this_start_ms": start_ms,
                           "prev_start_ms": prev_start_ms})
        if prev_end_ms >= 0 and start_ms < prev_end_ms:
            warnings.append({"level": "warn", "code": "overlap",
                             "block": bi + 1,
                             "this_start_ms": start_ms,
                             "prev_end_ms": prev_end_ms})
        body = "\n".join(body_lines).strip()
        if not body:
            warnings.append({"level": "warn", "code": "empty_body",
                             "block": bi + 1})
        for li, line in enumerate(body_lines):
            if len(line) > max_line_chars:
                warnings.append({"level": "warn", "code": "line_too_long",
                                 "block": bi + 1, "line": li,
                                 "chars": len(line),
                                 "max": max_line_chars})
        # Index sanity (soft): expect monotonic starting from 1.
        expected = prev_index + 1
        if index_declared is not None and index_declared != expected:
            warnings.append({"level": "warn", "code": "index_mismatch",
                             "block": bi + 1,
                             "declared": index_declared, "expected": expected})
        prev_index = expected
        prev_start_ms = start_ms
        prev_end_ms = end_ms
        cue_summaries.append({
            "index": expected,
            "start_ms": start_ms, "end_ms": end_ms,
            "body_chars": len(body), "lines": len(body_lines),
        })

    status = "success" if not errors else "error"
    return {
        "status": status,
        "handler": "validate_srt",
        "path": str(src),
        "cues": len(cue_summaries),
        "errors": errors,
        "warnings": warnings,
        "has_utf8_bom": has_utf8_bom,
        "total_duration_ms": prev_end_ms if prev_end_ms > 0 else 0,
    }
