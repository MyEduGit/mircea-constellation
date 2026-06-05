"""
gate.py — Publication gate evaluator.

Combines the outputs of all QC modules and produces a GateResult with one of
three statuses:

  PASS                  — no issues; transcript is ready for publication
  PASS_WITH_AUDIO_CHECK — unresolved uncertain names; needs human audio review
  BLOCKED               — low confidence score or major corruption detected

The gate also populates an audio_review_queue: the set of NameCandidates that
need to be verified against the original audio before the sermon can be cleared.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .discovery import SermonFolder
    from .comparison import ComparisonResult
    from .names import NameCandidate
    from .scripture import ScriptureRef, FormatIssue
    from .terminology import TermFlag

logger = logging.getLogger(__name__)


class GateStatus(str, Enum):
    PASS = "PASS"
    PASS_WITH_AUDIO_CHECK = "PASS_WITH_AUDIO_CHECK"
    BLOCKED = "BLOCKED"


@dataclass
class GateResult:
    status: GateStatus
    reasons: list[str] = field(default_factory=list)
    audio_review_queue: list["NameCandidate"] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    def is_blocked(self) -> bool:
        return self.status == GateStatus.BLOCKED

    def needs_audio_check(self) -> bool:
        return self.status == GateStatus.PASS_WITH_AUDIO_CHECK

    def summary_line(self) -> str:
        extras = ""
        if self.audio_review_queue:
            extras = f" ({len(self.audio_review_queue)} names pending)"
        return f"{self.status.value}{extras}"


# ──────────────────────────────────────────────────────────────────────────────
# Thresholds (easy to adjust in one place)
# ──────────────────────────────────────────────────────────────────────────────

CONFIDENCE_BLOCK_THRESHOLD = 60      # below this → BLOCKED
CONFIDENCE_WARN_THRESHOLD  = 75      # below this → add a warning
ALL_CAPS_BLOCK_THRESHOLD   = 20      # more than N all-caps flags → BLOCKED (corruption signal)
SCRIPTURE_ISSUE_WARN_LIMIT = 5       # more than N scripture format issues → warning


# ──────────────────────────────────────────────────────────────────────────────
# Public API
# ──────────────────────────────────────────────────────────────────────────────

def evaluate(
    sermon: "SermonFolder",
    comparison: "ComparisonResult | None",
    name_candidates: "list[NameCandidate]",
    scripture_refs: "list[ScriptureRef]",
    scripture_issues: "list[FormatIssue]",
    term_flags: "list[TermFlag]",
) -> GateResult:
    """
    Evaluate all QC results and return a GateResult.

    Parameters
    ----------
    sermon:
        The SermonFolder being evaluated.
    comparison:
        ComparisonResult from comparison.compare(), or None if only one
        source transcript is available.
    name_candidates:
        Uncertain proper nouns from names.detect_uncertain_names().
    scripture_refs:
        Extracted Bible references.
    scripture_issues:
        Format issues from scripture.verify_format().
    term_flags:
        Terminology flags from terminology.audit().
    """
    reasons: list[str] = []
    warnings: list[str] = []
    blocked = False

    # ------------------------------------------------------------------
    # 1. Missing source transcripts
    # ------------------------------------------------------------------
    if not sermon.has_any_source():
        reasons.append("No transcript files found in sermon folder.")
        blocked = True

    if not sermon.has_both_sources():
        missing = []
        if sermon.assemblyai_transcript is None:
            missing.append("AssemblyAI")
        if sermon.macwhisper_transcript is None:
            missing.append("MacWhisper")
        warnings.append(
            f"Only one source transcript available (missing: {', '.join(missing)}). "
            "Cross-source comparison not possible."
        )

    # ------------------------------------------------------------------
    # 2. Comparison confidence
    # ------------------------------------------------------------------
    if comparison is not None:
        if comparison.confidence_score < CONFIDENCE_BLOCK_THRESHOLD:
            reasons.append(
                f"Transcript confidence score {comparison.confidence_score:.1f}/100 "
                f"is below the block threshold of {CONFIDENCE_BLOCK_THRESHOLD}."
            )
            blocked = True
        elif comparison.confidence_score < CONFIDENCE_WARN_THRESHOLD:
            warnings.append(
                f"Transcript confidence score {comparison.confidence_score:.1f}/100 "
                f"is below the ideal threshold of {CONFIDENCE_WARN_THRESHOLD}."
            )
        if comparison.is_corrupted():
            reasons.append(
                "Comparison indicates possible transcript corruption (very low similarity)."
            )
            blocked = True

    # ------------------------------------------------------------------
    # 3. ALL_CAPS artefacts (possible major ASR corruption)
    # ------------------------------------------------------------------
    from .terminology import TermCategory  # local import to avoid circularity
    caps_flags = [f for f in term_flags if f.category == TermCategory.ALL_CAPS]
    if len(caps_flags) > ALL_CAPS_BLOCK_THRESHOLD:
        reasons.append(
            f"Detected {len(caps_flags)} ALL-CAPS sequences (threshold: "
            f"{ALL_CAPS_BLOCK_THRESHOLD}), suggesting major ASR artefacts or "
            "transcript corruption."
        )
        blocked = True
    elif caps_flags:
        warnings.append(f"{len(caps_flags)} ALL-CAPS sequence(s) detected — possible ASR artefacts.")

    # ------------------------------------------------------------------
    # 4. Scripture format issues
    # ------------------------------------------------------------------
    if len(scripture_issues) > SCRIPTURE_ISSUE_WARN_LIMIT:
        warnings.append(
            f"{len(scripture_issues)} Bible reference format issue(s) detected. "
            "Review scripture_audit.md."
        )
    elif scripture_issues:
        warnings.append(
            f"{len(scripture_issues)} minor Bible reference format issue(s) detected."
        )

    # ------------------------------------------------------------------
    # 5. Uncertain names → audio review queue
    # ------------------------------------------------------------------
    audio_queue: list["NameCandidate"] = []
    if name_candidates:
        audio_queue = name_candidates
        logger.info(
            "%s: %d uncertain name(s) queued for audio review",
            sermon.code,
            len(audio_queue),
        )

    # ------------------------------------------------------------------
    # 6. Terminology flags — just warnings, not blockers
    # ------------------------------------------------------------------
    non_caps = [f for f in term_flags if f.category != TermCategory.ALL_CAPS]
    if non_caps:
        cat_counts: dict[str, int] = {}
        for f in non_caps:
            cat_counts[f.category.value] = cat_counts.get(f.category.value, 0) + 1
        summary = ", ".join(f"{v} {k}" for k, v in cat_counts.items())
        warnings.append(f"Terminology flags: {summary}. Review terminology_audit.md.")

    # ------------------------------------------------------------------
    # 7. Determine final status
    # ------------------------------------------------------------------
    if blocked:
        status = GateStatus.BLOCKED
    elif audio_queue:
        status = GateStatus.PASS_WITH_AUDIO_CHECK
        reasons.append(
            f"{len(audio_queue)} uncertain proper noun(s) require audio verification "
            "before final publication."
        )
    else:
        status = GateStatus.PASS
        if not reasons:
            reasons.append("All automated checks passed.")

    result = GateResult(
        status=status,
        reasons=reasons,
        audio_review_queue=audio_queue,
        warnings=warnings,
    )
    logger.info("%s gate result: %s", sermon.code, result.summary_line())
    return result
