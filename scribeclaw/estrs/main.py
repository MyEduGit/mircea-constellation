"""
main.py — CLI entry point for the ESTRS pipeline.

Usage
-----
    python -m estrs                              # scan /Volumes/* once
    python -m estrs --watch                      # daemon mode
    python -m estrs --sermon C0072               # process one sermon
    python -m estrs --volumes /Volumes/SSD1      # custom volume root
    python -m estrs --vault ~/Documents/Obsidian # set Obsidian vault

Automation log is written to:
    ~/Library/Logs/estrs/automation_log.md
(override with --log-dir)
"""

from __future__ import annotations

import argparse
import logging
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

# ──────────────────────────────────────────────────────────────────────────────
# Logging setup
# ──────────────────────────────────────────────────────────────────────────────

def _setup_logging(log_dir: Path, verbose: bool = False) -> Path:
    """Configure root logger and return the path to the log file."""
    log_dir.mkdir(parents=True, exist_ok=True)
    log_file = log_dir / "automation_log.md"

    level = logging.DEBUG if verbose else logging.INFO

    # File handler: writes structured log to Markdown file
    file_handler = logging.FileHandler(log_file, encoding="utf-8")
    file_handler.setLevel(level)
    file_handler.setFormatter(
        logging.Formatter("%(asctime)s | %(levelname)-8s | %(name)s | %(message)s")
    )

    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(level)
    console_handler.setFormatter(
        logging.Formatter("%(levelname)-8s %(name)s: %(message)s")
    )

    root = logging.getLogger()
    root.setLevel(level)
    root.addHandler(file_handler)
    root.addHandler(console_handler)

    return log_file


logger = logging.getLogger(__name__)


# ──────────────────────────────────────────────────────────────────────────────
# Core processing
# ──────────────────────────────────────────────────────────────────────────────

def process_sermon(
    sermon_folder_path: Path,
    obsidian_vault: Optional[Path] = None,
) -> None:
    """
    Run the full ESTRS QC pipeline on a single sermon folder.

    This function is also used as the watchdog callback.
    """
    from .discovery import _process_sermon_path, SERMON_CODE_RE

    # Accept either the sermon directory itself or a path inside it
    # (watcher may pass subdirectory paths)
    candidate = sermon_folder_path
    while candidate != candidate.parent:
        if SERMON_CODE_RE.fullmatch(candidate.name):
            break
        candidate = candidate.parent
    else:
        logger.warning("Cannot determine sermon root from path: %s", sermon_folder_path)
        return

    sermon = _process_sermon_path(candidate)
    if sermon is None:
        logger.warning("Path does not look like a sermon folder: %s", candidate)
        return

    logger.info("=" * 60)
    logger.info("Processing %s at %s", sermon.code, sermon.path)

    # ------------------------------------------------------------------
    # Comparison
    # ------------------------------------------------------------------
    comparison = None
    if sermon.has_both_sources():
        from .comparison import compare_files
        try:
            comparison = compare_files(
                sermon.assemblyai_transcript,
                sermon.macwhisper_transcript,
            )
            logger.info(
                "%s: comparison confidence = %.1f",
                sermon.code,
                comparison.confidence_score,
            )
        except Exception as exc:  # pylint: disable=broad-except
            logger.error("%s: comparison failed: %s", sermon.code, exc)

    # Choose the primary text for single-source analysis
    primary_text = ""
    if sermon.assemblyai_transcript:
        primary_text = sermon.assemblyai_transcript.read_text(encoding="utf-8", errors="replace")
    elif sermon.macwhisper_transcript:
        primary_text = sermon.macwhisper_transcript.read_text(encoding="utf-8", errors="replace")

    # ------------------------------------------------------------------
    # Name detection
    # ------------------------------------------------------------------
    from .names import detect_uncertain_names
    name_candidates = detect_uncertain_names(primary_text) if primary_text else []
    logger.info("%s: %d uncertain name(s)", sermon.code, len(name_candidates))

    # ------------------------------------------------------------------
    # Scripture extraction
    # ------------------------------------------------------------------
    from .scripture import extract_references, verify_format
    scripture_refs = extract_references(primary_text) if primary_text else []
    scripture_issues = verify_format(scripture_refs)
    logger.info(
        "%s: %d scripture ref(s), %d issue(s)",
        sermon.code,
        len(scripture_refs),
        len(scripture_issues),
    )

    # ------------------------------------------------------------------
    # Terminology audit
    # ------------------------------------------------------------------
    from .terminology import audit as term_audit
    term_flags = term_audit(primary_text) if primary_text else []
    logger.info("%s: %d terminology flag(s)", sermon.code, len(term_flags))

    # ------------------------------------------------------------------
    # Gate evaluation
    # ------------------------------------------------------------------
    from .gate import evaluate
    gate = evaluate(
        sermon=sermon,
        comparison=comparison,
        name_candidates=name_candidates,
        scripture_refs=scripture_refs,
        scripture_issues=scripture_issues,
        term_flags=term_flags,
    )
    logger.info("%s: gate = %s", sermon.code, gate.summary_line())

    # ------------------------------------------------------------------
    # Write reports
    # ------------------------------------------------------------------
    from .reports import write_all
    written = write_all(
        sermon=sermon,
        comparison=comparison,
        name_candidates=name_candidates,
        scripture_refs=scripture_refs,
        scripture_issues=scripture_issues,
        term_flags=term_flags,
        gate=gate,
    )
    logger.info("%s: wrote %d report file(s)", sermon.code, len(written))

    # ------------------------------------------------------------------
    # Obsidian index
    # ------------------------------------------------------------------
    from .obsidian import update_index
    update_index(sermon=sermon, gate=gate, obsidian_vault=obsidian_vault)

    logger.info("%s: DONE → %s", sermon.code, gate.status.value)


def process_all_volumes(
    volumes_root: Optional[Path],
    obsidian_vault: Optional[Path],
) -> int:
    """Scan all volumes and process every sermon found. Returns count processed."""
    from .discovery import scan_volumes

    sermons = scan_volumes(volumes_root)
    if not sermons:
        logger.info("No sermon folders found under %s.", volumes_root or "/Volumes")
        return 0

    logger.info("Found %d sermon folder(s). Processing…", len(sermons))
    count = 0
    for sermon in sermons:
        try:
            process_sermon(sermon.path, obsidian_vault=obsidian_vault)
            count += 1
        except Exception as exc:  # pylint: disable=broad-except
            logger.error("Failed to process %s: %s", sermon.code, exc, exc_info=True)

    return count


# ──────────────────────────────────────────────────────────────────────────────
# CLI
# ──────────────────────────────────────────────────────────────────────────────

def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="estrs",
        description=(
            "ESTRS — Eternal Sermon Transcript Reconciliation System\n"
            "Automated QC for Dr. Emanoil Geaboc's Romanian Adventist sermon transcripts."
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    p.add_argument(
        "--watch",
        action="store_true",
        help="Start a filesystem watcher daemon instead of a one-shot scan.",
    )
    p.add_argument(
        "--sermon",
        metavar="CODE",
        help="Process a single sermon by code (e.g. C0072).",
    )
    p.add_argument(
        "--volumes",
        metavar="PATH",
        type=Path,
        default=None,
        help="Override default /Volumes/* scan root.",
    )
    p.add_argument(
        "--vault",
        metavar="PATH",
        type=Path,
        default=None,
        help="Path to the Obsidian vault root.",
    )
    p.add_argument(
        "--log-dir",
        metavar="PATH",
        type=Path,
        default=Path.home() / "Library" / "Logs" / "estrs",
        help="Directory for automation_log.md (default: ~/Library/Logs/estrs).",
    )
    p.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Enable DEBUG-level logging.",
    )
    return p


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)

    log_file = _setup_logging(args.log_dir, verbose=args.verbose)
    logger.info(
        "ESTRS starting at %s | log → %s",
        datetime.now(timezone.utc).isoformat(),
        log_file,
    )

    # ── Single sermon mode ──────────────────────────────────────────
    if args.sermon:
        from .discovery import find_sermon_by_code
        sermon = find_sermon_by_code(args.sermon, args.volumes)
        if sermon is None:
            logger.error(
                "Sermon %s not found under %s.", args.sermon, args.volumes or "/Volumes"
            )
            return 1
        try:
            process_sermon(sermon.path, obsidian_vault=args.vault)
        except Exception as exc:  # pylint: disable=broad-except
            logger.error("Failed: %s", exc, exc_info=True)
            return 1
        return 0

    # ── Watch mode ──────────────────────────────────────────────────
    if args.watch:
        logger.info("Starting watcher daemon on %s…", args.volumes or "/Volumes")

        def _callback(sermon_path: Path) -> None:
            try:
                process_sermon(sermon_path, obsidian_vault=args.vault)
            except Exception as exc:  # pylint: disable=broad-except
                logger.error("Watcher callback error: %s", exc, exc_info=True)

        from .watcher import start_watcher
        start_watcher(callback=_callback, volumes_root=args.volumes, block=True)
        return 0

    # ── One-shot scan mode ─────────────────────────────────────────
    count = process_all_volumes(
        volumes_root=args.volumes,
        obsidian_vault=args.vault,
    )
    logger.info("One-shot scan complete. Processed %d sermon(s).", count)
    return 0


if __name__ == "__main__":
    sys.exit(main())
