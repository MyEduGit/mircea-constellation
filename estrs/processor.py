"""ESTRS — sermon folder processor.

Orchestrates the full pipeline for a single sermon folder:
  1. Discover source directories (AssemblyAI / MacWhisper)
  2. Select best transcript from each source
  3. Compare transcripts
  4. Detect uncertain names
  5. Audit scripture references
  6. Audit terminology
  7. Evaluate publication gate
  8. Write all reports
  9. Append automation log

Returns a ProcessResult summarising what happened.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from pathlib import Path

from .comparison import compare
from .config import OUT_GATE
from .discovery import find_source_dirs
from .gate import GateDecision, GateStatus, evaluate
from .names import detect_names
from .reporter import (
    append_log,
    write_audio_queue,
    write_comparison,
    write_gate,
    write_names,
    write_scripture,
)
from .scripture import audit_scripture
from .selector import select_transcript
from .terminology import audit_terminology

log = logging.getLogger(__name__)


@dataclass
class ProcessResult:
    sermon_id: str
    folder: Path
    assemblyai_file: Path | None
    macwhisper_file: Path | None
    gate_status: GateStatus
    errors: list[str] = field(default_factory=list)
    skipped: bool = False
    skip_reason: str = ''


def process_sermon(folder: Path, force: bool = False) -> ProcessResult:
    """Run the full ESTRS pipeline on *folder*.

    If reports already exist and *force* is False, skip processing.
    """
    sermon_id = folder.name
    log.info("processing %s", sermon_id)

    result = ProcessResult(
        sermon_id=sermon_id,
        folder=folder,
        assemblyai_file=None,
        macwhisper_file=None,
        gate_status=GateStatus.BLOCKED,
    )

    # Skip if already processed (gate file exists) unless forced
    if not force and (folder / OUT_GATE).exists():
        log.debug("%s already processed — skipping (use force=True to reprocess)", sermon_id)
        result.skipped = True
        result.skip_reason = 'already processed'
        # Recover gate status from existing file
        try:
            content = (folder / OUT_GATE).read_text(encoding='utf-8')
            for status in GateStatus:
                if status.value in content:
                    result.gate_status = status
                    break
        except OSError:
            pass
        return result

    # ── Step 1: discover source directories ──────────────────────────────────
    sources = find_source_dirs(folder)
    ai_dir = sources['assemblyai']
    mw_dir = sources['macwhisper']

    # ── Step 2: select transcripts ───────────────────────────────────────────
    ai_file, ai_text = select_transcript(ai_dir) if ai_dir else (None, '')
    mw_file, mw_text = select_transcript(mw_dir) if mw_dir else (None, '')

    result.assemblyai_file = ai_file
    result.macwhisper_file = mw_file

    ai_found = bool(ai_text.strip())
    mw_found = bool(mw_text.strip())

    log.info(
        "%s — AI file: %s (%d words), MW file: %s (%d words)",
        sermon_id,
        ai_file.name if ai_file else 'NONE',
        len(ai_text.split()),
        mw_file.name if mw_file else 'NONE',
        len(mw_text.split()),
    )

    # Use empty strings if a source is missing so downstream still runs
    ai_text_safe = ai_text or ''
    mw_text_safe = mw_text or ''

    # ── Step 3: compare transcripts ───────────────────────────────────────────
    comparison = compare(
        ai_text_safe, mw_text_safe,
        assemblyai_path=ai_file,
        macwhisper_path=mw_file,
    )

    # ── Step 4: detect uncertain names ────────────────────────────────────────
    names = detect_names(ai_text_safe, mw_text_safe)

    # ── Step 5: audit scripture references ────────────────────────────────────
    scripture = audit_scripture(ai_text_safe, mw_text_safe)

    # ── Step 6: audit terminology ─────────────────────────────────────────────
    terminology = audit_terminology(ai_text_safe, mw_text_safe)

    # ── Step 7: evaluate publication gate ─────────────────────────────────────
    gate = evaluate(
        comparison=comparison,
        names=names,
        scripture=scripture,
        terminology=terminology,
        assemblyai_found=ai_found,
        macwhisper_found=mw_found,
    )
    result.gate_status = gate.status

    # ── Step 8: write all reports ─────────────────────────────────────────────
    try:
        write_comparison(folder, comparison)
        write_names(folder, names)
        write_scripture(folder, scripture, terminology)
        write_gate(folder, gate, sermon_id=sermon_id)
        write_audio_queue(folder, names, terminology.error_hits)
    except Exception as exc:
        log.exception("report writing failed for %s", sermon_id)
        result.errors.append(str(exc))

    # ── Step 9: append automation log ────────────────────────────────────────
    files_found = {
        'assemblyai': str(ai_file) if ai_file else None,
        'macwhisper': str(mw_file) if mw_file else None,
    }
    notes_parts = []
    if names:
        notes_parts.append(f"{len(names)} uncertain names")
    if scripture.total_count:
        notes_parts.append(f"{scripture.total_count} scripture refs")
    if terminology.error_hits:
        notes_parts.append(f"{len(terminology.error_hits)} term errors")
    notes = '; '.join(notes_parts)

    append_log(folder, sermon_id, gate.status.value, files_found, notes=notes)

    log.info("%s — gate: %s", sermon_id, gate.status.value)
    return result
