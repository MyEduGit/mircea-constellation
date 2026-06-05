"""
discovery.py — Locate sermon folders and transcript files on mounted volumes.

Scans /Volumes/* for directories matching C[0-9]{3,4} and locates AssemblyAI
and MacWhisper transcript files within them.
"""

from __future__ import annotations

import re
import logging
from dataclasses import dataclass, field
from pathlib import Path

logger = logging.getLogger(__name__)

# Regex: C followed by 3–4 digits (C001 through C9999)
SERMON_CODE_RE = re.compile(r"^C\d{3,4}$", re.IGNORECASE)

# Fuzzy name variants for each source
_ASSEMBLYAI_NAMES = {"assemblyai", "assembly_ai", "assembly ai", "assembly"}
_MACWHISPER_NAMES = {"macwhisper", "mac_whisper", "mac whisper", "macwhisper"}

# Transcript preference order
TRANSCRIPT_EXTENSIONS = [".md", ".txt", ".srt"]


@dataclass
class SermonFolder:
    """Represents a single sermon directory discovered on a volume."""

    path: Path
    code: str
    sources: dict[str, Path] = field(default_factory=dict)
    assemblyai_dir: Path | None = None
    macwhisper_dir: Path | None = None
    assemblyai_transcript: Path | None = None
    macwhisper_transcript: Path | None = None

    def __post_init__(self) -> None:
        self.code = self.code.upper()

    def has_both_sources(self) -> bool:
        return self.assemblyai_transcript is not None and self.macwhisper_transcript is not None

    def has_any_source(self) -> bool:
        return self.assemblyai_transcript is not None or self.macwhisper_transcript is not None

    def __repr__(self) -> str:
        ai = self.assemblyai_transcript.name if self.assemblyai_transcript else "—"
        mw = self.macwhisper_transcript.name if self.macwhisper_transcript else "—"
        return f"SermonFolder({self.code}, assemblyai={ai}, macwhisper={mw})"


def _normalise(name: str) -> str:
    """Lowercase and strip a directory name for fuzzy matching."""
    return name.lower().strip()


def _matches_source(dirname: str, candidates: set[str]) -> bool:
    """Return True if *dirname* matches any of the candidate source names."""
    norm = _normalise(dirname)
    # exact match
    if norm in candidates:
        return True
    # substring match (e.g. "AssemblyAI_output" contains "assemblyai")
    for c in candidates:
        if c in norm:
            return True
    return False


def select_transcript(directory: Path) -> Path | None:
    """
    Given a source subdirectory, pick the best transcript file.

    Preference order: .md > .txt > .srt
    Within each extension, prefer the file with the highest estimated word count
    (measured by reading the first 500 words).
    """
    if not directory.is_dir():
        return None

    candidates: dict[str, list[Path]] = {ext: [] for ext in TRANSCRIPT_EXTENSIONS}
    for f in directory.iterdir():
        if f.is_file() and f.suffix.lower() in TRANSCRIPT_EXTENSIONS:
            candidates[f.suffix.lower()].append(f)

    for ext in TRANSCRIPT_EXTENSIONS:
        files = candidates[ext]
        if not files:
            continue
        if len(files) == 1:
            return files[0]
        # Multiple files: pick highest word count
        return max(files, key=_estimate_word_count)

    return None


def _estimate_word_count(path: Path) -> int:
    """Read up to the first ~500 words from a file and count them."""
    try:
        with path.open("r", encoding="utf-8", errors="replace") as fh:
            # Read enough bytes to comfortably get 500 words
            chunk = fh.read(8192)
        words = chunk.split()
        return len(words[:500])
    except OSError as exc:
        logger.warning("Cannot read %s for word count: %s", path, exc)
        return 0


def _find_source_dirs(sermon_path: Path) -> tuple[Path | None, Path | None]:
    """
    Walk the immediate children of *sermon_path* and identify
    the AssemblyAI and MacWhisper subdirectories.
    """
    assemblyai_dir: Path | None = None
    macwhisper_dir: Path | None = None

    for child in sermon_path.iterdir():
        if not child.is_dir():
            continue
        name = child.name
        if assemblyai_dir is None and _matches_source(name, _ASSEMBLYAI_NAMES):
            assemblyai_dir = child
            logger.debug("Found AssemblyAI dir: %s", child)
        elif macwhisper_dir is None and _matches_source(name, _MACWHISPER_NAMES):
            macwhisper_dir = child
            logger.debug("Found MacWhisper dir: %s", child)

    return assemblyai_dir, macwhisper_dir


def _process_sermon_path(sermon_path: Path) -> SermonFolder | None:
    """Build a SermonFolder from a path that matches the sermon code pattern."""
    code = sermon_path.name
    if not SERMON_CODE_RE.match(code):
        return None

    ai_dir, mw_dir = _find_source_dirs(sermon_path)

    folder = SermonFolder(
        path=sermon_path,
        code=code,
        assemblyai_dir=ai_dir,
        macwhisper_dir=mw_dir,
    )

    if ai_dir is not None:
        folder.assemblyai_transcript = select_transcript(ai_dir)
        if folder.assemblyai_transcript:
            logger.info("%s: AssemblyAI → %s", code, folder.assemblyai_transcript.name)
        else:
            logger.warning("%s: AssemblyAI dir found but no transcript inside %s", code, ai_dir)

    if mw_dir is not None:
        folder.macwhisper_transcript = select_transcript(mw_dir)
        if folder.macwhisper_transcript:
            logger.info("%s: MacWhisper → %s", code, folder.macwhisper_transcript.name)
        else:
            logger.warning("%s: MacWhisper dir found but no transcript inside %s", code, mw_dir)

    return folder


def scan_volumes(volumes_root: Path | None = None) -> list[SermonFolder]:
    """
    Scan *volumes_root* (default: /Volumes) for sermon directories.

    Returns a list of SermonFolder objects, sorted by sermon code.
    Only directories matching C[0-9]{3,4} at ANY depth under a volume
    mount point are considered.  The search is two levels deep:
        /Volumes/<device>/<sermon_code>/
    to avoid traversing deeply into large drives.
    """
    if volumes_root is None:
        volumes_root = Path("/Volumes")

    if not volumes_root.exists():
        logger.warning("Volumes root %s does not exist — running on non-macOS?", volumes_root)
        return []

    found: list[SermonFolder] = []

    try:
        mounts = [m for m in volumes_root.iterdir() if m.is_dir()]
    except PermissionError as exc:
        logger.error("Cannot list %s: %s", volumes_root, exc)
        return []

    for mount in mounts:
        logger.debug("Scanning mount: %s", mount)
        try:
            for child in mount.iterdir():
                if not child.is_dir():
                    continue
                if SERMON_CODE_RE.match(child.name):
                    folder = _process_sermon_path(child)
                    if folder is not None:
                        found.append(folder)
        except PermissionError as exc:
            logger.warning("Skipping %s (permission denied): %s", mount, exc)
            continue

    found.sort(key=lambda sf: sf.code)
    logger.info("scan_volumes: found %d sermon folder(s) under %s", len(found), volumes_root)
    return found


def find_sermon_by_code(code: str, volumes_root: Path | None = None) -> SermonFolder | None:
    """Return the first SermonFolder matching *code*, or None."""
    target = code.upper()
    for folder in scan_volumes(volumes_root):
        if folder.code == target:
            return folder
    return None
