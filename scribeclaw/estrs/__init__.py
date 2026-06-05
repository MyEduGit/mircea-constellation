"""
ESTRS — Eternal Sermon Transcript Reconciliation System
========================================================
A macOS filesystem automation tool for Dr. Emanoil Geaboc's
Romanian Adventist sermon transcript QC pipeline.

Usage:
    python -m estrs                      # scan volumes once
    python -m estrs --watch              # daemon mode
    python -m estrs --sermon C0072       # single sermon
"""

__version__ = "0.1.0"
__author__ = "ESTRS"

from .discovery import SermonFolder, scan_volumes, select_transcript
from .comparison import ComparisonResult, compare
from .names import NameCandidate, detect_uncertain_names
from .scripture import ScriptureRef, FormatIssue, extract_references, verify_format
from .terminology import TermFlag, audit
from .gate import GateResult, GateStatus, evaluate
from .reports import write_all
from .obsidian import update_index

__all__ = [
    "SermonFolder",
    "scan_volumes",
    "select_transcript",
    "ComparisonResult",
    "compare",
    "NameCandidate",
    "detect_uncertain_names",
    "ScriptureRef",
    "FormatIssue",
    "extract_references",
    "verify_format",
    "TermFlag",
    "audit",
    "GateResult",
    "GateStatus",
    "evaluate",
    "write_all",
    "update_index",
]
