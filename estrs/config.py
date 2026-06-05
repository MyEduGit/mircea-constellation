"""ESTRS — configuration and shared constants."""
from __future__ import annotations

import re
from pathlib import Path

VERSION = "1.0.0"

# ── Folder discovery ──────────────────────────────────────────────────────────

SERMON_PATTERN = re.compile(r'^[Cc]\d{4}$')

ASSEMBLYAI_PATTERN = re.compile(r'assembly[\s_\-]?ai', re.IGNORECASE)
MACWHISPER_PATTERN = re.compile(r'mac[\s_\-]?whisper', re.IGNORECASE)

VOLUMES_ROOT = Path('/Volumes')

# ── File selection ────────────────────────────────────────────────────────────

PREFERRED_EXTENSIONS = ('.md', '.txt')
FALLBACK_EXTENSIONS = ('.srt',)
ALL_EXTENSIONS = PREFERRED_EXTENSIONS + FALLBACK_EXTENSIONS

IGNORE_PATTERN = re.compile(
    r'^(\.|~|.*\.tmp$|.*\.bak$|.*Thumbs\.db$|.*\.log$)',
    re.IGNORECASE,
)

MIN_WORD_COUNT = 30

# ── Output file names (written into each sermon folder) ───────────────────────

OUT_COMPARISON   = 'transcript_comparison.md'
OUT_NAMES        = 'name_resolution.md'
OUT_SCRIPTURE    = 'scripture_audit.md'
OUT_GATE         = 'publication_gate.md'
OUT_AUDIO_QUEUE  = 'audio_review_queue.md'
OUT_LOG          = 'automation_log.md'

# ── Watcher ──────────────────────────────────────────────────────────────────

# Seconds to wait after the last file event before processing
DEBOUNCE_SECONDS = 5.0
