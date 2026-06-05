"""ESTRS — publication gate.

Evaluates all analysis results and emits a GateDecision:
  PASS                — no unresolved issues; ready for publication
  PASS_WITH_AUDIO_CHECK — only unresolved names remain; human spot-check needed
  BLOCKED             — major corruption / low confidence; do not publish

Decision criteria:
  BLOCKED if:
    - comparison confidence < 0.60  (major transcript divergence)
    - length skew > 0.50            (one transcript appears truncated)
    - no transcript found for either source

  PASS_WITH_AUDIO_CHECK if:
    - HIGH-confidence name candidates exist (unresolved unknown names)
    - terminology error patterns were flagged

  PASS otherwise.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum

from .comparison import ComparisonResult
from .names import NameCandidate
from .scripture import ScriptureAudit
from .terminology import TerminologyAudit


class GateStatus(str, Enum):
    PASS = 'PASS'
    PASS_WITH_AUDIO_CHECK = 'PASS_WITH_AUDIO_CHECK'
    BLOCKED = 'BLOCKED'


@dataclass
class GateDecision:
    status: GateStatus
    reasons: list[str] = field(default_factory=list)
    audio_check_items: list[str] = field(default_factory=list)
    recommendations: list[str] = field(default_factory=list)


def evaluate(
    comparison: ComparisonResult,
    names: list[NameCandidate],
    scripture: ScriptureAudit,
    terminology: TerminologyAudit,
    assemblyai_found: bool,
    macwhisper_found: bool,
) -> GateDecision:
    reasons: list[str] = []
    audio_items: list[str] = []
    recommendations: list[str] = []
    status = GateStatus.PASS

    # ── BLOCKED conditions ────────────────────────────────────────────────────

    if not assemblyai_found or not macwhisper_found:
        missing = []
        if not assemblyai_found:
            missing.append('AssemblyAI')
        if not macwhisper_found:
            missing.append('MacWhisper')
        reasons.append(f"Missing transcript(s): {', '.join(missing)}")
        status = GateStatus.BLOCKED

    if comparison.confidence < 0.60:
        reasons.append(
            f"Low transcript confidence ({comparison.confidence:.1%}) — "
            "major divergence between sources"
        )
        status = GateStatus.BLOCKED

    if comparison.length_skew > 0.50:
        reasons.append(
            f"Large word-count skew ({comparison.length_skew:.1%}) — "
            f"AssemblyAI={comparison.assemblyai_words} words, "
            f"MacWhisper={comparison.macwhisper_words} words"
        )
        status = GateStatus.BLOCKED

    # ── PASS_WITH_AUDIO_CHECK conditions (only when not already BLOCKED) ──────

    if status is not GateStatus.BLOCKED:
        high_names = [n for n in names if n.confidence in ('HIGH', 'MEDIUM')]
        if high_names:
            audio_items.append(
                f"{len(high_names)} uncertain name(s) require audio verification"
            )
            for n in high_names[:5]:
                audio_items.append(f'  • "{n.text}" (seen in: {", ".join(n.sources)})')
            if len(high_names) > 5:
                audio_items.append(f"  … and {len(high_names) - 5} more (see name_resolution.md)")
            status = GateStatus.PASS_WITH_AUDIO_CHECK

        if terminology.error_hits:
            audio_items.append(
                f"{len(terminology.error_hits)} likely transcription error(s) need review"
            )
            for e in terminology.error_hits[:3]:
                audio_items.append(f'  - found: "{e.pattern_found}" -> suggested: "{e.suggested_correction}"')
            status = GateStatus.PASS_WITH_AUDIO_CHECK

    # ── Recommendations ───────────────────────────────────────────────────────

    if scripture.format_warnings:
        recommendations.append("Standardise Bible reference formatting (see scripture_audit.md)")

    if comparison.char_similarity < 0.85 and status is not GateStatus.BLOCKED:
        recommendations.append(
            "Character similarity is below 85 % — consider a manual spot-check"
        )

    if status is GateStatus.PASS:
        reasons.append("All checks passed — no unresolved issues detected")

    return GateDecision(
        status=status,
        reasons=reasons,
        audio_check_items=audio_items,
        recommendations=recommendations,
    )
