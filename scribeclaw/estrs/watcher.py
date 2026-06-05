"""
watcher.py — Watchdog-based filesystem watcher for /Volumes/*.

Watches all mounted volumes for:
  - New directories matching C[0-9]{3,4}
  - New .md / .txt / .srt files inside a C0* sermon folder

Debounce: waits 5 seconds after the last relevant event before triggering
processing to avoid running on partial writes.

Usage (via main.py):
    from estrs.watcher import start_watcher
    start_watcher(callback=process_sermon, volumes_root=Path("/Volumes"))
"""

from __future__ import annotations

import logging
import re
import threading
from pathlib import Path
from typing import Callable

logger = logging.getLogger(__name__)

SERMON_CODE_RE = re.compile(r"C\d{3,4}", re.IGNORECASE)
TRANSCRIPT_SUFFIXES = {".md", ".txt", ".srt"}
DEBOUNCE_SECONDS = 5.0


def _find_sermon_root(path: Path) -> Path | None:
    """
    Walk up from *path* until we find a directory matching the sermon code pattern.
    Returns None if no such parent exists within the volumes structure.
    """
    current = path if path.is_dir() else path.parent
    # Walk up at most 4 levels to stay within volumes
    for _ in range(4):
        if SERMON_CODE_RE.fullmatch(current.name):
            return current
        parent = current.parent
        if parent == current:
            break
        current = parent
    return None


class _SermonEventHandler:
    """
    Implements watchdog EventHandler interface manually so we can import
    watchdog lazily and give a helpful error if it's missing.
    """

    def __init__(
        self,
        callback: Callable[[Path], None],
        volumes_root: Path,
    ) -> None:
        self._callback = callback
        self._volumes_root = volumes_root
        self._pending: dict[Path, threading.Timer] = {}
        self._lock = threading.Lock()

    # watchdog calls dispatch() for all events
    def dispatch(self, event: object) -> None:
        self.on_any_event(event)

    def on_any_event(self, event: object) -> None:
        try:
            src = Path(getattr(event, "src_path", ""))
        except Exception:
            return

        # Only care about transcript files or C0* directories
        is_relevant = False

        if src.is_dir() and SERMON_CODE_RE.fullmatch(src.name):
            is_relevant = True
        elif src.suffix.lower() in TRANSCRIPT_SUFFIXES:
            # Check if it lives inside a sermon folder
            if _find_sermon_root(src) is not None:
                is_relevant = True

        if not is_relevant:
            return

        sermon_root = _find_sermon_root(src)
        if sermon_root is None:
            return

        self._schedule(sermon_root)

    def _schedule(self, sermon_root: Path) -> None:
        """Debounce: reset timer each time an event fires for the same folder."""
        with self._lock:
            existing = self._pending.get(sermon_root)
            if existing is not None:
                existing.cancel()
            t = threading.Timer(
                DEBOUNCE_SECONDS,
                self._fire,
                args=(sermon_root,),
            )
            self._pending[sermon_root] = t
            t.daemon = True
            t.start()
        logger.debug("Scheduled processing for %s in %.0fs", sermon_root, DEBOUNCE_SECONDS)

    def _fire(self, sermon_root: Path) -> None:
        with self._lock:
            self._pending.pop(sermon_root, None)
        logger.info("Debounce elapsed; processing sermon at %s", sermon_root)
        try:
            self._callback(sermon_root)
        except Exception as exc:  # pylint: disable=broad-except
            logger.error("Error processing %s: %s", sermon_root, exc, exc_info=True)


def start_watcher(
    callback: Callable[[Path], None],
    volumes_root: Path | None = None,
    block: bool = True,
) -> object:
    """
    Start watching *volumes_root* (default: /Volumes) for sermon changes.

    Parameters
    ----------
    callback:
        Called with the sermon folder Path whenever a change is detected.
    volumes_root:
        Root directory to watch.  Defaults to /Volumes.
    block:
        If True, block the calling thread (run the observer loop).
        If False, start the observer in a background thread and return it.

    Returns
    -------
    The watchdog Observer instance (useful for stopping it in tests).

    Raises
    ------
    SystemExit if watchdog is not installed.
    """
    try:
        from watchdog.observers import Observer  # type: ignore[import]
        from watchdog.events import FileSystemEventHandler  # type: ignore[import]
    except ImportError:
        print(
            "\n[ESTRS] The 'watchdog' package is required for --watch mode.\n"
            "Install it with:\n\n"
            "    pip install watchdog\n"
        )
        raise SystemExit(1)

    if volumes_root is None:
        volumes_root = Path("/Volumes")

    if not volumes_root.exists():
        logger.warning(
            "Volumes root '%s' does not exist. Watcher may not detect any events.",
            volumes_root,
        )

    # Wrap our handler to satisfy watchdog's EventHandler base class
    class _Handler(FileSystemEventHandler):
        def __init__(self, inner: _SermonEventHandler) -> None:
            super().__init__()
            self._inner = inner

        def on_any_event(self, event: object) -> None:
            self._inner.on_any_event(event)

    inner = _SermonEventHandler(callback=callback, volumes_root=volumes_root)
    handler = _Handler(inner)

    observer = Observer()
    observer.schedule(handler, str(volumes_root), recursive=True)
    observer.start()

    logger.info(
        "ESTRS watcher started on %s (debounce=%.0fs)",
        volumes_root,
        DEBOUNCE_SECONDS,
    )

    if not block:
        return observer

    try:
        import time
        while observer.is_alive():
            time.sleep(1)
    except KeyboardInterrupt:
        logger.info("Watcher interrupted by user.")
    finally:
        observer.stop()
        observer.join()
        logger.info("ESTRS watcher stopped.")

    return observer
