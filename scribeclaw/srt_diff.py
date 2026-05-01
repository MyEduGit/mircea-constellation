"""srt_diff — cue-by-cue comparison of two SubRip files.

Typical use: compare `transcript.srt` against `transcript.clean.srt`
(after correct_ro_theological) to preview exactly what changed before
publishing. The .corrections.log already lists rule-driven changes but
it doesn't cover operator-manual edits; this handler catches both.

Alignment:
  - Prefer index-based: cues N-in-A vs N-in-B (fast, deterministic).
  - When cue counts differ, fall back to start-timestamp matching with
    a ±tolerance_ms window and label unmatched cues as added/removed.

Outputs (next to file A):
  <nameA>.vs.<nameB>.md     pretty diff for operator review
  <nameA>.vs.<nameB>.json   machine-readable changelist

Uses stdlib difflib for compact inline text diffs — no new deps.
"""
from __future__ import annotations

import difflib
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

_SRT_TIME = re.compile(
    r"^(\d{2}):(\d{2}):(\d{2})[,\.](\d{3})\s*-->\s*"
    r"(\d{2}):(\d{2}):(\d{2})[,\.](\d{3})\s*$"
)


@dataclass
class Cue:
    index: int
    start_ms: int
    end_ms: int
    text: str


def _ms(h: int, m: int, s: int, ms: int) -> int:
    return ((h * 3600 + m * 60 + s) * 1000) + ms


def _parse_srt(path: Path) -> list[Cue]:
    raw = path.read_bytes()
    if raw.startswith(b"\xef\xbb\xbf"):
        raw = raw[3:]
    text = raw.decode("utf-8", errors="replace").replace("\r\n", "\n")
    blocks = re.split(r"\n\s*\n", text.strip())
    cues: list[Cue] = []
    for b in blocks:
        lines = [ln for ln in b.split("\n") if ln != ""]
        if len(lines) < 2:
            continue
        if _SRT_TIME.match(lines[0]):
            idx = len(cues) + 1
            ts, body = lines[0], lines[1:]
        else:
            try:
                idx = int(lines[0].strip())
            except ValueError:
                idx = len(cues) + 1
            ts, body = (lines[1] if len(lines) > 1 else ""), lines[2:]
        m = _SRT_TIME.match(ts)
        if not m:
            continue
        sh, sm, ss, sms, eh, em, es, ems = (int(g) for g in m.groups())
        cues.append(Cue(
            index=idx,
            start_ms=_ms(sh, sm, ss, sms),
            end_ms=_ms(eh, em, es, ems),
            text="\n".join(body).strip(),
        ))
    return cues


def _fmt_ms(ms: int) -> str:
    s, ms = divmod(ms, 1000)
    m, s = divmod(s, 60)
    h, m = divmod(m, 60)
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


def _inline_diff(before: str, after: str) -> str:
    """Compact single-line diff suitable for embedding in a table cell."""
    sm = difflib.SequenceMatcher(None, before, after)
    parts: list[str] = []
    for tag, i1, i2, j1, j2 in sm.get_opcodes():
        if tag == "equal":
            parts.append(before[i1:i2])
        elif tag == "delete":
            parts.append(f"«-{before[i1:i2]}»")
        elif tag == "insert":
            parts.append(f"«+{after[j1:j2]}»")
        elif tag == "replace":
            parts.append(f"«-{before[i1:i2]}»«+{after[j1:j2]}»")
    return "".join(parts)


@dataclass
class Change:
    kind: str                # "text_changed" | "timing_shifted" | "added" | "removed"
    a_index: int | None
    b_index: int | None
    a_start_ms: int | None
    b_start_ms: int | None
    a_text: str
    b_text: str
    delta_ms: int | None


def _align_and_diff(a: list[Cue], b: list[Cue], *,
                    tolerance_ms: int) -> list[Change]:
    changes: list[Change] = []
    # Fast path: when cue counts match we align by index. That covers the
    # overwhelming majority of real operator use (correct_ro_theological
    # preserves cue count by contract).
    if len(a) == len(b):
        for ca, cb in zip(a, b):
            dt = cb.start_ms - ca.start_ms
            if ca.text != cb.text:
                changes.append(Change(
                    kind="text_changed",
                    a_index=ca.index, b_index=cb.index,
                    a_start_ms=ca.start_ms, b_start_ms=cb.start_ms,
                    a_text=ca.text, b_text=cb.text, delta_ms=dt,
                ))
            elif abs(dt) > tolerance_ms or (cb.end_ms - ca.end_ms) != dt:
                # Same text but timing drifted beyond tolerance.
                changes.append(Change(
                    kind="timing_shifted",
                    a_index=ca.index, b_index=cb.index,
                    a_start_ms=ca.start_ms, b_start_ms=cb.start_ms,
                    a_text=ca.text, b_text=cb.text, delta_ms=dt,
                ))
        return changes

    # Cue counts differ — align by closest start timestamp within tolerance.
    used_b: set[int] = set()
    for ca in a:
        best_j = -1
        best_dt = None
        for j, cb in enumerate(b):
            if j in used_b:
                continue
            dt = abs(cb.start_ms - ca.start_ms)
            if dt > tolerance_ms:
                continue
            if best_dt is None or dt < best_dt:
                best_dt, best_j = dt, j
        if best_j == -1:
            changes.append(Change(
                kind="removed",
                a_index=ca.index, b_index=None,
                a_start_ms=ca.start_ms, b_start_ms=None,
                a_text=ca.text, b_text="", delta_ms=None,
            ))
            continue
        cb = b[best_j]
        used_b.add(best_j)
        if ca.text != cb.text:
            changes.append(Change(
                kind="text_changed",
                a_index=ca.index, b_index=cb.index,
                a_start_ms=ca.start_ms, b_start_ms=cb.start_ms,
                a_text=ca.text, b_text=cb.text,
                delta_ms=cb.start_ms - ca.start_ms,
            ))
    for j, cb in enumerate(b):
        if j not in used_b:
            changes.append(Change(
                kind="added",
                a_index=None, b_index=cb.index,
                a_start_ms=None, b_start_ms=cb.start_ms,
                a_text="", b_text=cb.text, delta_ms=None,
            ))
    return changes


def _render_md(a: Path, b: Path, a_count: int, b_count: int,
               changes: list[Change]) -> str:
    counts: dict[str, int] = {}
    for c in changes:
        counts[c.kind] = counts.get(c.kind, 0) + 1

    lines: list[str] = [
        f"# SRT diff — `{a.name}` vs `{b.name}`",
        "",
        f"- A: `{a}` ({a_count} cues)",
        f"- B: `{b}` ({b_count} cues)",
        f"- Changes: text_changed={counts.get('text_changed', 0)} · "
        f"timing_shifted={counts.get('timing_shifted', 0)} · "
        f"added={counts.get('added', 0)} · "
        f"removed={counts.get('removed', 0)}",
        "",
        "| A idx | B idx | @time | kind | diff |",
        "|---:|---:|---|---|---|",
    ]
    for c in changes:
        when = _fmt_ms(c.a_start_ms if c.a_start_ms is not None else (c.b_start_ms or 0))
        if c.kind == "text_changed":
            cell = _inline_diff(c.a_text, c.b_text)
        elif c.kind == "timing_shifted":
            cell = f"Δ={c.delta_ms}ms (text unchanged)"
        elif c.kind == "added":
            cell = f"«+{c.b_text}»"
        else:  # removed
            cell = f"«-{c.a_text}»"
        # Pipe-escape for markdown-table safety.
        cell = cell.replace("|", "\\|").replace("\n", " ⏎ ")
        lines.append(
            f"| {c.a_index if c.a_index is not None else '—'} "
            f"| {c.b_index if c.b_index is not None else '—'} "
            f"| `{when}` | {c.kind} | {cell} |"
        )
    lines.append("")
    return "\n".join(lines)


def _safe_resolve(data_root: Path, rel: str) -> Path | dict:
    requested = Path(str(rel))
    candidate = (data_root / requested).resolve() if not requested.is_absolute() \
        else requested.resolve()
    try:
        candidate.relative_to(data_root.resolve())
    except ValueError:
        return {"status": "error", "handler": "srt_diff",
                "error": "path_outside_data_root",
                "data_root": str(data_root.resolve()),
                "given": str(rel)}
    if not candidate.exists():
        return {"status": "error", "handler": "srt_diff",
                "error": "srt_path_not_found", "path": str(candidate)}
    return candidate


async def srt_diff(payload: dict[str, Any], data_root: Path) -> dict:
    """Diff two SRT files cue-by-cue.

    Payload:
      a             (str, required): path under DATA_ROOT (or absolute
                                     under DATA_ROOT) to the "before" SRT
      b             (str, required): the "after" SRT
      tolerance_ms  (int, optional): max start-ms drift classed as
                                     timing_shifted, not text_changed;
                                     default 50
    """
    a_raw = payload.get("a")
    b_raw = payload.get("b")
    if not a_raw or not b_raw:
        return {"status": "error", "handler": "srt_diff",
                "error": "a_and_b_required"}
    resolved_a = _safe_resolve(data_root, a_raw)
    if isinstance(resolved_a, dict):
        return resolved_a
    resolved_b = _safe_resolve(data_root, b_raw)
    if isinstance(resolved_b, dict):
        return resolved_b
    a_path: Path = resolved_a
    b_path: Path = resolved_b
    tolerance_ms = int(payload.get("tolerance_ms", 50))

    try:
        a_cues = _parse_srt(a_path)
        b_cues = _parse_srt(b_path)
    except Exception as exc:
        return {"status": "error", "handler": "srt_diff",
                "error": "parse_failed", "detail": str(exc)}
    if not a_cues or not b_cues:
        return {"status": "error", "handler": "srt_diff",
                "error": "empty_srt",
                "a_cues": len(a_cues), "b_cues": len(b_cues)}

    changes = _align_and_diff(a_cues, b_cues, tolerance_ms=tolerance_ms)

    md = _render_md(a_path, b_path, len(a_cues), len(b_cues), changes)
    md_path = a_path.with_name(f"{a_path.stem}.vs.{b_path.stem}.md")
    json_path = a_path.with_name(f"{a_path.stem}.vs.{b_path.stem}.json")
    md_path.write_text(md, encoding="utf-8")

    json_path.write_text(json.dumps({
        "a": str(a_path), "b": str(b_path),
        "a_cues": len(a_cues), "b_cues": len(b_cues),
        "tolerance_ms": tolerance_ms,
        "changes": [
            {
                "kind": c.kind, "a_index": c.a_index, "b_index": c.b_index,
                "a_start_ms": c.a_start_ms, "b_start_ms": c.b_start_ms,
                "a_text": c.a_text, "b_text": c.b_text,
                "delta_ms": c.delta_ms,
            }
            for c in changes
        ],
    }, ensure_ascii=False, indent=2), encoding="utf-8")

    kinds: dict[str, int] = {}
    for c in changes:
        kinds[c.kind] = kinds.get(c.kind, 0) + 1

    return {
        "status": "success",
        "handler": "srt_diff",
        "a": str(a_path),
        "b": str(b_path),
        "a_cues": len(a_cues),
        "b_cues": len(b_cues),
        "changes_total": len(changes),
        "changes_by_kind": kinds,
        "outputs": [str(md_path), str(json_path)],
    }
