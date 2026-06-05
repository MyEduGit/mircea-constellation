"""
reports.py — Write all QC Markdown report files for a sermon.

NEVER modifies or overwrites source transcripts.
Only writes to the six (or seven) generated report filenames listed below.

Report files produced
---------------------
  transcript_comparison.md
  name_resolution.md
  scripture_audit.md
  terminology_audit.md
  publication_gate.md
  audio_review_queue.md   (only when audio_review_queue is non-empty)
"""

from __future__ import annotations

import logging
import textwrap
from datetime import datetime, timezone
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .discovery import SermonFolder
    from .comparison import ComparisonResult
    from .names import NameCandidate
    from .scripture import ScriptureRef, FormatIssue
    from .terminology import TermFlag
    from .gate import GateResult

logger = logging.getLogger(__name__)

# ──────────────────────────────────────────────────────────────────────────────
# Safe output filenames (these are the ONLY files we ever write)
# ──────────────────────────────────────────────────────────────────────────────

REPORT_FILENAMES = {
    "comparison":    "transcript_comparison.md",
    "names":         "name_resolution.md",
    "scripture":     "scripture_audit.md",
    "terminology":   "terminology_audit.md",
    "gate":          "publication_gate.md",
    "audio_queue":   "audio_review_queue.md",
}

# Source transcript filenames that must never be written
_PROTECTED_EXTENSIONS = {".md", ".txt", ".srt"}


def _is_protected(path: Path) -> bool:
    """Return True if this path is likely a source transcript."""
    return path.name not in set(REPORT_FILENAMES.values())


def _now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _write_safe(path: Path, content: str) -> None:
    """Write *content* to *path*, refusing to overwrite protected source files."""
    # Guard: only allow writing our known report filenames
    if path.name not in set(REPORT_FILENAMES.values()):
        raise RuntimeError(
            f"SAFETY: Attempted to write to non-report file '{path}'. Aborting."
        )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    logger.info("Wrote report: %s", path)


def _header(sermon_code: str, title: str, source_files: list[str]) -> str:
    sources_yaml = "\n".join(f"  - {s}" for s in source_files) if source_files else "  - (none)"
    return (
        f"---\n"
        f"generated_at: {_now_iso()}\n"
        f"sermon_code: {sermon_code}\n"
        f"source_files:\n{sources_yaml}\n"
        f"---\n\n"
        f"# {title}\n\n"
    )


# ──────────────────────────────────────────────────────────────────────────────
# Individual report builders
# ──────────────────────────────────────────────────────────────────────────────

def _build_comparison_report(
    sermon: "SermonFolder",
    comparison: "ComparisonResult | None",
) -> str:
    sources = []
    if sermon.assemblyai_transcript:
        sources.append(str(sermon.assemblyai_transcript.relative_to(sermon.path.parent)))
    if sermon.macwhisper_transcript:
        sources.append(str(sermon.macwhisper_transcript.relative_to(sermon.path.parent)))

    body = _header(sermon.code, "Transcript Comparison", sources)

    if comparison is None:
        body += (
            "> **Note:** Only one source transcript was available. "
            "Cross-source comparison was skipped.\n"
        )
        return body

    body += f"## Summary\n\n"
    body += f"| Metric | Value |\n|--------|-------|\n"
    body += f"| Confidence Score | **{comparison.confidence_score:.1f} / 100** |\n"
    body += f"| Word Overlap | {comparison.word_overlap_pct * 100:.1f}% |\n"
    body += f"| Paragraph Pairs | {len(comparison.paragraph_diffs)} |\n"
    body += f"| AI Summary Used | {'Yes' if comparison.ai_used else 'No'} |\n\n"

    body += f"## Semantic Summary\n\n{comparison.ai_summary}\n\n"

    # Paragraph diff table (show only differing ones)
    differing = [pd for pd in comparison.paragraph_diffs if pd.similarity < 0.95]
    if differing:
        body += f"## Paragraph Differences ({len(differing)} differing)\n\n"
        for i, pd in enumerate(differing, 1):
            body += f"### Pair {i} — similarity {pd.similarity * 100:.1f}%\n\n"
            body += f"**AssemblyAI:**\n\n> {pd.para_a[:500]}\n\n"
            body += f"**MacWhisper:**\n\n> {pd.para_b[:500]}\n\n"
    else:
        body += "## Paragraph Differences\n\nNo significant paragraph-level differences.\n\n"

    # Unified diff (truncated)
    if comparison.line_diff:
        diff_preview = comparison.line_diff[:4000]
        if len(comparison.line_diff) > 4000:
            diff_preview += "\n\n… _(diff truncated — see full comparison tool)_\n"
        body += f"## Unified Diff\n\n```diff\n{diff_preview}\n```\n"
    else:
        body += "## Unified Diff\n\nTranscripts are identical.\n"

    return body


def _build_name_resolution_report(
    sermon: "SermonFolder",
    name_candidates: "list[NameCandidate]",
) -> str:
    sources = []
    if sermon.assemblyai_transcript:
        sources.append(sermon.assemblyai_transcript.name)
    if sermon.macwhisper_transcript:
        sources.append(sermon.macwhisper_transcript.name)

    body = _header(sermon.code, "Name Resolution", sources)

    if not name_candidates:
        body += "_No uncertain proper nouns detected. All names resolved._\n"
        return body

    body += (
        f"**{len(name_candidates)} uncertain proper noun(s) detected** for human review.\n\n"
        f"| # | Phrase | Line | Confidence | Context |\n"
        f"|---|--------|------|------------|---------|\n"
    )
    for i, nc in enumerate(name_candidates, 1):
        ctx = nc.context.replace("|", "\\|")[:80]
        body += (
            f"| {i} | `{nc.phrase}` | {nc.line_num} | "
            f"{nc.confidence * 100:.0f}% | {ctx} |\n"
        )

    body += (
        "\n> **Action required:** Verify each phrase against the original audio. "
        "Update `audio_review_queue.md` after resolution.\n"
    )
    return body


def _build_scripture_audit_report(
    sermon: "SermonFolder",
    refs: "list[ScriptureRef]",
    issues: "list[FormatIssue]",
) -> str:
    sources = []
    if sermon.assemblyai_transcript:
        sources.append(sermon.assemblyai_transcript.name)
    if sermon.macwhisper_transcript:
        sources.append(sermon.macwhisper_transcript.name)

    body = _header(sermon.code, "Scripture Audit", sources)
    body += f"**References found:** {len(refs)}  \n"
    body += f"**Format issues:** {len(issues)}\n\n"

    if refs:
        body += "## References\n\n"
        body += "| # | Book | Ch | Verse | Raw Text | Line |\n"
        body += "|---|------|----|-------|----------|------|\n"
        for i, r in enumerate(refs, 1):
            vs = f"{r.verse_start}" if r.verse_end is None else f"{r.verse_start}–{r.verse_end}"
            raw = r.raw_text.replace("|", "\\|")
            body += f"| {i} | {r.book} | {r.chapter} | {vs} | `{raw}` | {r.line_num} |\n"
        body += "\n"

    if issues:
        body += "## Format Issues\n\n"
        for issue in issues:
            body += f"- **Line {issue.ref.line_num}** — `{issue.ref.raw_text}`: {issue.issue}\n"
        body += "\n"
    else:
        body += "## Format Issues\n\n_No format issues detected._\n"

    return body


def _build_terminology_audit_report(
    sermon: "SermonFolder",
    term_flags: "list[TermFlag]",
) -> str:
    sources = []
    if sermon.assemblyai_transcript:
        sources.append(sermon.assemblyai_transcript.name)
    if sermon.macwhisper_transcript:
        sources.append(sermon.macwhisper_transcript.name)

    body = _header(sermon.code, "Terminology Audit", sources)
    body += f"**Total flags:** {len(term_flags)}\n\n"

    if not term_flags:
        body += "_No terminology flags detected._\n"
        return body

    # Group by category
    from .terminology import TermCategory
    categories = list(TermCategory)
    for cat in categories:
        cat_flags = [f for f in term_flags if f.category == cat]
        if not cat_flags:
            continue
        body += f"## {cat.value} ({len(cat_flags)})\n\n"
        body += "| # | Term | Line | Context |\n|---|------|------|---------|\n"
        for i, f in enumerate(cat_flags, 1):
            ctx = f.context.replace("|", "\\|")[:80]
            body += f"| {i} | `{f.term}` | {f.line_num} | {ctx} |\n"
        body += "\n"

    return body


def _build_gate_report(
    sermon: "SermonFolder",
    gate: "GateResult",
    comparison: "ComparisonResult | None",
) -> str:
    sources = []
    if sermon.assemblyai_transcript:
        sources.append(sermon.assemblyai_transcript.name)
    if sermon.macwhisper_transcript:
        sources.append(sermon.macwhisper_transcript.name)

    body = _header(sermon.code, "Publication Gate", sources)
    status_emoji = {"PASS": "✅", "PASS_WITH_AUDIO_CHECK": "⚠️", "BLOCKED": "🚫"}.get(
        gate.status.value, "❓"
    )
    body += f"## Status: {status_emoji} `{gate.status.value}`\n\n"

    if comparison:
        body += f"**Confidence score:** {comparison.confidence_score:.1f} / 100\n\n"

    if gate.reasons:
        body += "## Reasons\n\n"
        for r in gate.reasons:
            body += f"- {r}\n"
        body += "\n"

    if gate.warnings:
        body += "## Warnings\n\n"
        for w in gate.warnings:
            body += f"- ⚠️ {w}\n"
        body += "\n"

    if gate.audio_review_queue:
        body += (
            f"## Audio Review Required\n\n"
            f"{len(gate.audio_review_queue)} uncertain name(s) must be verified. "
            "See `audio_review_queue.md`.\n\n"
        )

    body += "## Checklist\n\n"
    items = [
        ("Both source transcripts present", sermon.has_both_sources()),
        ("Confidence ≥ 60", comparison is not None and comparison.confidence_score >= 60),
        ("No uncertain names pending", len(gate.audio_review_queue) == 0),
        ("Gate status not BLOCKED", not gate.is_blocked()),
    ]
    for label, ok in items:
        mark = "x" if ok else " "
        body += f"- [{mark}] {label}\n"

    return body


def _build_audio_queue_report(
    sermon: "SermonFolder",
    gate: "GateResult",
) -> str:
    body = _header(sermon.code, "Audio Review Queue", [])
    body += (
        f"**{len(gate.audio_review_queue)} item(s) require verification against the original audio.**\n\n"
        "For each item, listen to the corresponding passage and confirm or correct the transcribed phrase.\n\n"
    )
    body += "| # | Phrase | Line | Context | Resolved? | Correction |\n"
    body += "|---|--------|------|---------|-----------|------------|\n"
    for i, nc in enumerate(gate.audio_review_queue, 1):
        ctx = nc.context.replace("|", "\\|")[:80]
        body += f"| {i} | `{nc.phrase}` | {nc.line_num} | {ctx} | ☐ | |\n"
    body += (
        "\n"
        "> Fill in the **Resolved?** column (✓ / ✗) and add the **Correction** "
        "if the name was transcribed incorrectly.\n"
    )
    return body


# ──────────────────────────────────────────────────────────────────────────────
# Public API
# ──────────────────────────────────────────────────────────────────────────────

def write_all(
    sermon: "SermonFolder",
    comparison: "ComparisonResult | None",
    name_candidates: "list[NameCandidate]",
    scripture_refs: "list[ScriptureRef]",
    scripture_issues: "list[FormatIssue]",
    term_flags: "list[TermFlag]",
    gate: "GateResult",
) -> list[Path]:
    """
    Write all QC report files to *sermon.path*.

    Returns a list of Path objects for the files that were written.
    Never touches source transcript files.
    """
    written: list[Path] = []
    base = sermon.path

    reports = {
        "comparison":  _build_comparison_report(sermon, comparison),
        "names":       _build_name_resolution_report(sermon, name_candidates),
        "scripture":   _build_scripture_audit_report(sermon, scripture_refs, scripture_issues),
        "terminology": _build_terminology_audit_report(sermon, term_flags),
        "gate":        _build_gate_report(sermon, gate, comparison),
    }

    for key, content in reports.items():
        out_path = base / REPORT_FILENAMES[key]
        _write_safe(out_path, content)
        written.append(out_path)

    # Audio queue only written when needed
    if gate.audio_review_queue:
        out_path = base / REPORT_FILENAMES["audio_queue"]
        _write_safe(out_path, _build_audio_queue_report(sermon, gate))
        written.append(out_path)

    return written
