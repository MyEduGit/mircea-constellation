"""ESTRS — transcript comparison engine.

Produces a structured diff between an AssemblyAI transcript and a
MacWhisper transcript, computing:
  - character-level similarity ratio (difflib)
  - paragraph-level delta
  - line-level diff blocks
  - overall confidence score

Output is a ComparisonResult dataclass ready for the reporter.
"""
from __future__ import annotations

import difflib
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import NamedTuple


# ── Helpers ───────────────────────────────────────────────────────────────────

def _normalise(text: str) -> str:
    """Collapse whitespace, strip leading/trailing."""
    return re.sub(r'\s+', ' ', text).strip()


def _to_paragraphs(text: str) -> list[str]:
    """Split on blank lines; return non-empty paragraphs."""
    blocks = re.split(r'\n\s*\n', text)
    return [_normalise(b) for b in blocks if b.strip()]


def _to_lines(text: str) -> list[str]:
    return [ln.rstrip() for ln in text.splitlines()]


def _similarity(a: str, b: str) -> float:
    if not a and not b:
        return 1.0
    return difflib.SequenceMatcher(None, a, b).ratio()


# ── Data types ────────────────────────────────────────────────────────────────

class DiffBlock(NamedTuple):
    tag: str          # 'equal' | 'replace' | 'insert' | 'delete'
    a_start: int
    a_end: int
    b_start: int
    b_end: int
    a_lines: list[str]
    b_lines: list[str]


@dataclass
class ComparisonResult:
    assemblyai_path: Path | None
    macwhisper_path: Path | None
    assemblyai_words: int
    macwhisper_words: int
    char_similarity: float          # 0–1
    paragraph_similarity: float     # 0–1
    line_diff_blocks: list[DiffBlock]
    differing_block_count: int
    confidence: float               # 0–1  derived
    length_skew: float              # |wc_a - wc_b| / max(wc_a, wc_b)
    summary_lines: list[str] = field(default_factory=list)

    @property
    def status(self) -> str:
        if self.confidence >= 0.92:
            return 'HIGH'
        if self.confidence >= 0.75:
            return 'MEDIUM'
        return 'LOW'


# ── Comparison logic ──────────────────────────────────────────────────────────

def compare(assemblyai_text: str, macwhisper_text: str,
            assemblyai_path: Path | None = None,
            macwhisper_path: Path | None = None) -> ComparisonResult:

    wc_a = len(assemblyai_text.split())
    wc_b = len(macwhisper_text.split())

    char_sim = _similarity(assemblyai_text, macwhisper_text)

    paras_a = _to_paragraphs(assemblyai_text)
    paras_b = _to_paragraphs(macwhisper_text)
    para_sim = _similarity('\n'.join(paras_a), '\n'.join(paras_b))

    lines_a = _to_lines(assemblyai_text)
    lines_b = _to_lines(macwhisper_text)

    matcher = difflib.SequenceMatcher(None, lines_a, lines_b, autojunk=False)
    blocks: list[DiffBlock] = []
    diff_count = 0
    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        blocks.append(DiffBlock(
            tag=tag,
            a_start=i1, a_end=i2,
            b_start=j1, b_end=j2,
            a_lines=lines_a[i1:i2],
            b_lines=lines_b[j1:j2],
        ))
        if tag != 'equal':
            diff_count += 1

    max_wc = max(wc_a, wc_b, 1)
    length_skew = abs(wc_a - wc_b) / max_wc

    # Confidence: weighted combo of similarity metrics, penalised by length skew
    raw_conf = (char_sim * 0.5 + para_sim * 0.3 + (1 - length_skew) * 0.2)
    confidence = max(0.0, min(1.0, raw_conf))

    summary = _build_summary(wc_a, wc_b, char_sim, para_sim,
                             diff_count, confidence, length_skew)

    return ComparisonResult(
        assemblyai_path=assemblyai_path,
        macwhisper_path=macwhisper_path,
        assemblyai_words=wc_a,
        macwhisper_words=wc_b,
        char_similarity=char_sim,
        paragraph_similarity=para_sim,
        line_diff_blocks=blocks,
        differing_block_count=diff_count,
        confidence=confidence,
        length_skew=length_skew,
        summary_lines=summary,
    )


def _build_summary(wc_a: int, wc_b: int, char_sim: float, para_sim: float,
                   diff_count: int, confidence: float, skew: float) -> list[str]:
    lines = [
        f"- AssemblyAI word count: **{wc_a}**",
        f"- MacWhisper word count: **{wc_b}**",
        f"- Length skew: **{skew:.1%}**",
        f"- Character similarity: **{char_sim:.1%}**",
        f"- Paragraph similarity: **{para_sim:.1%}**",
        f"- Differing line blocks: **{diff_count}**",
        f"- Overall confidence: **{confidence:.1%}**",
    ]
    if skew > 0.4:
        lines.append("⚠️  Large length difference — one transcript may be incomplete.")
    if char_sim < 0.6:
        lines.append("⚠️  Low character similarity — significant divergence detected.")
    return lines
