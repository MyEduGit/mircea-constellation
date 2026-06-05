"""ESTRS — filesystem watcher daemon.

Monitors /Volumes/* (or any provided roots) for new sermon folders and new
transcript files.  Uses the *watchdog* library with FSEventsObserver on macOS
and InotifyObserver on Linux; falls back to PollingObserver everywhere else.

Debouncing:  file-system events are batched.  The sermon folder is only
processed once all activity has settled for DEBOUNCE_SECONDS.

Safety:  the watcher is entirely read-only on source files.
"""
from __future__ import annotations

import logging
import threading
import time
from pathlib import Path
from typing import Callable

from .config import (
    ALL_EXTENSIONS,
    DEBOUNCE_SECONDS,
    VOLUMES_ROOT,
)
from .discovery import sermon_folder_for_path

log = logging.getLogger(__name__)

# ── Observer selection ────────────────────────────────────────────────────────

def _make_observer():
    try:
        import watchdog.observers.fsevents as _fse  # macOS
        log.info("using FSEventsObserver (macOS)")
        return _fse.Observer()
    except (ImportError, AttributeError):
        pass
    try:
        import watchdog.observers.inotify as _ino  # Linux
        log.info("using InotifyObserver (Linux)")
        return _ino.InotifyObserver()
    except (ImportError, AttributeError):
        pass
    from watchdog.observers.polling import PollingObserver
    log.info("using PollingObserver (fallback)")
    return PollingObserver()


# ── Debounce manager ──────────────────────────────────────────────────────────

class _Debouncer:
    """Accumulates event paths; fires callback after a quiet period."""

    def __init__(self, callback: Callable[[Path], None], delay: float = DEBOUNCE_SECONDS):
        self._callback = callback
        self._delay = delay
        self._lock = threading.Lock()
        self._timers: dict[Path, threading.Timer] = {}

    def trigger(self, sermon_folder: Path) -> None:
        with self._lock:
            existing = self._timers.get(sermon_folder)
            if existing:
                existing.cancel()
            timer = threading.Timer(self._delay, self._fire, args=[sermon_folder])
            self._timers[sermon_folder] = timer
            timer.start()

    def _fire(self, sermon_folder: Path) -> None:
        with self._lock:
            self._timers.pop(sermon_folder, None)
        try:
            self._callback(sermon_folder)
        except Exception:
            log.exception("error processing %s", sermon_folder)


# ── Watchdog event handler ────────────────────────────────────────────────────

def _make_handler(debouncer: '_Debouncer'):
    from watchdog.events import FileSystemEventHandler

    class _Handler(FileSystemEventHandler):
        def on_created(self, event):
            self._handle(Path(event.src_path))

        def on_modified(self, event):
            self._handle(Path(event.src_path))

        def on_moved(self, event):
            self._handle(Path(event.dest_path))

        def _handle(self, path: Path) -> None:
            # Only care about transcript-extension files
            if path.is_dir():
                # New directory — check if it's a sermon folder itself
                from .discovery import SERMON_PATTERN
                from .config import SERMON_PATTERN as _SP  # noqa: F401
                from .discovery import SERMON_PATTERN as SP
                if SP.match(path.name):
                    debouncer.trigger(path)
                return
            if path.suffix.lower() not in ALL_EXTENSIONS:
                return
            sermon = sermon_folder_for_path(path)
            if sermon:
                log.debug("event on %s → sermon %s", path.name, sermon.name)
                debouncer.trigger(sermon)

    return _Handler()


# ── Public API ────────────────────────────────────────────────────────────────

class Watcher:
    """Persistent filesystem watcher for ESTRS.

    Usage::

        from estrs.watcher import Watcher
        from estrs.processor import process_sermon

        w = Watcher(on_sermon=process_sermon)
        w.start()          # non-blocking; spawns background threads
        w.join()           # block forever (Ctrl-C to stop)
    """

    def __init__(
        self,
        on_sermon: Callable[[Path], None],
        *,
        watch_roots: list[Path] | None = None,
        debounce_seconds: float = DEBOUNCE_SECONDS,
    ):
        self._on_sermon = on_sermon
        self._roots = watch_roots or _default_roots()
        self._debounce_sec = debounce_seconds
        self._observer = None
        self._stop_event = threading.Event()

    def start(self) -> None:
        try:
            from watchdog.observers import Observer as _Obs  # noqa: F401
        except ImportError:
            log.error(
                "watchdog is not installed. "
                "Run: pip install watchdog  — then restart ESTRS."
            )
            return

        debouncer = _Debouncer(self._on_sermon, self._debounce_sec)
        handler = _make_handler(debouncer)

        self._observer = _make_observer()
        for root in self._roots:
            if root.exists():
                self._observer.schedule(handler, str(root), recursive=True)
                log.info("watching %s", root)
            else:
                log.warning("watch root does not exist: %s", root)

        self._observer.start()
        log.info("ESTRS watcher started (debounce=%.1fs)", self._debounce_sec)

    def stop(self) -> None:
        self._stop_event.set()
        if self._observer:
            self._observer.stop()
            self._observer.join()
        log.info("ESTRS watcher stopped")

    def join(self) -> None:
        """Block until Ctrl-C or stop() is called."""
        try:
            while not self._stop_event.is_set():
                time.sleep(1)
        except KeyboardInterrupt:
            log.info("keyboard interrupt — shutting down")
        finally:
            self.stop()


def _default_roots() -> list[Path]:
    """Return volumes to watch.  Prefers /Volumes/* on macOS; falls back to /."""
    roots: list[Path] = []
    if VOLUMES_ROOT.exists():
        for vol in sorted(VOLUMES_ROOT.iterdir()):
            if vol.is_dir() and not vol.name.startswith('.'):
                roots.append(vol)
    if not roots:
        # Development / Linux fallback
        roots = [Path('/')]
    return roots
