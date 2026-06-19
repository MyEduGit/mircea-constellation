"""ESTRS — main entry point.

Usage:
  python -m estrs                     # scan all volumes once
  python -m estrs --watch             # start persistent watcher
  python -m estrs --folder /path/C0001  # process a specific folder
  python -m estrs --all --force       # rescan everything, overwrite existing
  python -m estrs --root /path        # scan a specific root
"""
from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

from . import VERSION
from .config import VOLUMES_ROOT
from .discovery import iter_sermon_folders
from .processor import process_sermon

log = logging.getLogger('estrs')


def _configure_logging(verbose: bool) -> None:
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format='%(asctime)s | %(levelname)-8s | %(name)s | %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S',
    )


def cmd_scan(roots: list[Path], force: bool) -> int:
    folders = list(iter_sermon_folders(*roots))
    if not folders:
        log.warning("no sermon folders (C0001…C9999) found in %s",
                    ', '.join(str(r) for r in roots))
        return 0

    log.info("found %d sermon folder(s)", len(folders))
    ok = skipped = failed = 0
    for folder in folders:
        try:
            res = process_sermon(folder, force=force)
            if res.skipped:
                skipped += 1
            else:
                ok += 1
        except Exception as exc:
            log.error("FAILED %s: %s", folder, exc)
            failed += 1

    log.info("scan complete — processed=%d skipped=%d failed=%d", ok, skipped, failed)
    return 0 if failed == 0 else 1


def cmd_folder(folder: Path, force: bool) -> int:
    if not folder.is_dir():
        log.error("not a directory: %s", folder)
        return 2
    result = process_sermon(folder, force=force)
    print(f"\nSermon:  {result.sermon_id}")
    print(f"Gate:    {result.gate_status.value}")
    if result.assemblyai_file:
        print(f"AI:      {result.assemblyai_file.name}")
    if result.macwhisper_file:
        print(f"MW:      {result.macwhisper_file.name}")
    if result.errors:
        print(f"Errors:  {'; '.join(result.errors)}")
    return 0


def cmd_watch(roots: list[Path], force: bool) -> int:
    from .watcher import Watcher

    def _on_sermon(folder: Path) -> None:
        try:
            result = process_sermon(folder, force=force)
            log.info("auto-processed %s → %s", result.sermon_id, result.gate_status.value)
        except Exception:
            log.exception("auto-processing failed for %s", folder)

    watcher = Watcher(on_sermon=_on_sermon, watch_roots=roots)
    watcher.start()

    # Run a one-shot scan first so existing unprocessed folders get handled
    log.info("running initial scan before entering watch mode…")
    existing = list(iter_sermon_folders(*roots))
    for folder in existing:
        _on_sermon(folder)

    log.info("entering watch mode — press Ctrl-C to stop")
    watcher.join()
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog='python -m estrs',
        description=f'ESTRS v{VERSION} — Eternal Sermon Transcript Reconciliation System',
    )
    p.add_argument('--version', action='version', version=f'ESTRS {VERSION}')
    p.add_argument('-v', '--verbose', action='store_true', help='debug logging')
    p.add_argument(
        '--root', metavar='DIR', action='append', dest='roots',
        help='search root (default: all /Volumes/* mounts); repeatable',
    )
    p.add_argument(
        '--folder', metavar='DIR',
        help='process a single sermon folder (C0001-style)',
    )
    p.add_argument(
        '--watch', action='store_true',
        help='start persistent watcher (runs forever)',
    )
    p.add_argument(
        '--force', action='store_true',
        help='reprocess even if reports already exist',
    )
    return p


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    _configure_logging(args.verbose)

    log.info("ESTRS v%s starting", VERSION)

    roots: list[Path] = []
    if args.roots:
        roots = [Path(r) for r in args.roots]
    elif VOLUMES_ROOT.exists():
        roots = [v for v in sorted(VOLUMES_ROOT.iterdir())
                 if v.is_dir() and not v.name.startswith('.')]
    if not roots:
        log.warning("/Volumes not found; using current directory as search root")
        roots = [Path.cwd()]

    if args.folder:
        return cmd_folder(Path(args.folder), force=args.force)
    if args.watch:
        return cmd_watch(roots, force=args.force)
    return cmd_scan(roots, force=args.force)


if __name__ == '__main__':
    sys.exit(main())
