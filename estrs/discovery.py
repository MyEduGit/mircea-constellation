"""ESTRS — volume and sermon-folder discovery."""
from __future__ import annotations

import logging
from pathlib import Path
from typing import Iterator

from .config import (
    ASSEMBLYAI_PATTERN,
    MACWHISPER_PATTERN,
    SERMON_PATTERN,
    VOLUMES_ROOT,
)

log = logging.getLogger(__name__)


# ── Volume enumeration ────────────────────────────────────────────────────────

def iter_volumes() -> Iterator[Path]:
    """Yield every mounted volume directory under /Volumes."""
    if not VOLUMES_ROOT.exists():
        log.warning("/Volumes does not exist — no external SSD volumes found")
        return
    for vol in sorted(VOLUMES_ROOT.iterdir()):
        if vol.is_dir() and not vol.name.startswith('.'):
            yield vol


# ── Sermon folder discovery ───────────────────────────────────────────────────

def iter_sermon_folders(
    *search_roots: Path,
    max_depth: int = 8,
) -> Iterator[Path]:
    """Walk search_roots (defaults to all volumes) for C0001–C9999 folders."""
    roots = list(search_roots) if search_roots else list(iter_volumes())
    for root in roots:
        yield from _walk(root, depth=0, max_depth=max_depth)


def _walk(path: Path, depth: int, max_depth: int) -> Iterator[Path]:
    if depth > max_depth:
        return
    try:
        for child in sorted(path.iterdir()):
            if not child.is_dir():
                continue
            if SERMON_PATTERN.match(child.name):
                log.debug("found sermon folder: %s", child)
                yield child
            else:
                yield from _walk(child, depth + 1, max_depth)
    except PermissionError:
        log.debug("permission denied: %s", path)


# ── Source-directory detection ────────────────────────────────────────────────

def find_source_dirs(sermon_folder: Path) -> dict[str, Path | None]:
    """Return {'assemblyai': Path|None, 'macwhisper': Path|None}.

    Accepts fuzzy subfolder names (Assembly AI, assembly_ai, MacWhisper, …).
    If no dedicated subfolder is found, returns None for that source — the
    selector will then search the sermon folder root directly.
    """
    sources: dict[str, Path | None] = {'assemblyai': None, 'macwhisper': None}
    try:
        children = [c for c in sermon_folder.iterdir() if c.is_dir()]
    except PermissionError:
        return sources

    for child in children:
        name = child.name
        if ASSEMBLYAI_PATTERN.search(name) and sources['assemblyai'] is None:
            sources['assemblyai'] = child
            log.debug("assemblyai dir: %s", child)
        elif MACWHISPER_PATTERN.search(name) and sources['macwhisper'] is None:
            sources['macwhisper'] = child
            log.debug("macwhisper dir: %s", child)

    # If no dedicated sub-dir found, look for source-tagged files in the root.
    # A file like "assemblyai_transcript.txt" or "transcript_macwhisper.md"
    # counts as the source root for that engine.
    if sources['assemblyai'] is None or sources['macwhisper'] is None:
        try:
            root_files = [f for f in sermon_folder.iterdir() if f.is_file()]
        except PermissionError:
            root_files = []
        for f in root_files:
            name_lower = f.name.lower()
            if sources['assemblyai'] is None and ASSEMBLYAI_PATTERN.search(name_lower):
                sources['assemblyai'] = sermon_folder
                log.debug("assemblyai fallback to root (found file %s)", f.name)
            if sources['macwhisper'] is None and MACWHISPER_PATTERN.search(name_lower):
                sources['macwhisper'] = sermon_folder
                log.debug("macwhisper fallback to root (found file %s)", f.name)

    return sources


def sermon_folder_for_path(path: Path) -> Path | None:
    """Walk up from *path* to find the enclosing C0001–C9999 folder."""
    for parent in [path, *path.parents]:
        if SERMON_PATTERN.match(parent.name):
            return parent
    return None
