"""
comparison.py — Structural and semantic comparison between two transcripts.

Computes unified diff, word overlap, paragraph-level similarity, and an
overall confidence score (0–100).  If ANTHROPIC_API_KEY is present, a
claude-haiku call adds a brief semantic summary of the discrepancies.
"""

from __future__ import annotations

import difflib
import logging
import os
import re
import textwrap
from dataclasses import dataclass, field
from pathlib import Path

logger = logging.getLogger(__name__)


@dataclass
class ParagraphDiff:
    para_a: str
    para_b: str
    similarity: float  # 0.0 – 1.0


@dataclass
class ComparisonResult:
    """Full comparison between two transcript texts."""

    line_diff: str  # unified diff as a single string
    word_overlap_pct: float  # 0.0 – 1.0
    paragraph_diffs: list[ParagraphDiff] = field(default_factory=list)
    confidence_score: float = 0.0  # 0 – 100
    ai_summary: str = ""  # populated only if ANTHROPIC_API_KEY is set
    ai_used: bool = False

    def is_high_confidence(self) -> bool:
        return self.confidence_score >= 80

    def is_corrupted(self) -> bool:
        return self.confidence_score < 40


# ──────────────────────────────────────────────────────────
# Text normalisation helpers
# ──────────────────────────────────────────────────────────

def _clean_text(text: str) -> str:
    """Strip SRT timestamps and leading/trailing whitespace."""
    # Remove SRT sequence numbers and timestamps
    text = re.sub(r"^\d+\s*$", "", text, flags=re.MULTILINE)
    text = re.sub(
        r"\d{2}:\d{2}:\d{2}[,\.]\d{3}\s*-->\s*\d{2}:\d{2}:\d{2}[,\.]\d{3}",
        "",
        text,
    )
    # Collapse extra blank lines
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def _tokenise_words(text: str) -> list[str]:
    return re.findall(r"\b\w+\b", text.lower())


def _split_paragraphs(text: str) -> list[str]:
    """Split on blank lines; each paragraph is non-empty stripped."""
    paras = re.split(r"\n{2,}", text)
    return [p.strip() for p in paras if p.strip()]


# ──────────────────────────────────────────────────────────
# Core metrics
# ──────────────────────────────────────────────────────────

def _compute_word_overlap(text_a: str, text_b: str) -> float:
    words_a = set(_tokenise_words(text_a))
    words_b = set(_tokenise_words(text_b))
    if not words_a and not words_b:
        return 1.0
    if not words_a or not words_b:
        return 0.0
    intersection = words_a & words_b
    union = words_a | words_b
    return len(intersection) / len(union)


def _compute_line_diff(text_a: str, text_b: str) -> str:
    lines_a = text_a.splitlines(keepends=True)
    lines_b = text_b.splitlines(keepends=True)
    diff = difflib.unified_diff(
        lines_a, lines_b, fromfile="assemblyai", tofile="macwhisper", lineterm=""
    )
    return "".join(diff)


def _compute_paragraph_diffs(text_a: str, text_b: str) -> list[ParagraphDiff]:
    paras_a = _split_paragraphs(text_a)
    paras_b = _split_paragraphs(text_b)

    # Align by index up to the shorter length, then append extras
    length = max(len(paras_a), len(paras_b))
    results: list[ParagraphDiff] = []

    for i in range(length):
        pa = paras_a[i] if i < len(paras_a) else ""
        pb = paras_b[i] if i < len(paras_b) else ""
        sim = difflib.SequenceMatcher(None, pa.lower(), pb.lower()).ratio()
        results.append(ParagraphDiff(para_a=pa, para_b=pb, similarity=sim))

    return results


def _compute_confidence(word_overlap: float, para_diffs: list[ParagraphDiff]) -> float:
    """
    Blend word-level Jaccard overlap with mean paragraph similarity.

    confidence = 0.4 * word_overlap + 0.6 * mean_para_sim  → scaled 0–100
    """
    if para_diffs:
        mean_para_sim = sum(pd.similarity for pd in para_diffs) / len(para_diffs)
    else:
        mean_para_sim = word_overlap  # fallback when no paragraphs

    raw = 0.40 * word_overlap + 0.60 * mean_para_sim
    return round(raw * 100, 1)


# ──────────────────────────────────────────────────────────
# Optional AI semantic summary
# ──────────────────────────────────────────────────────────

def _try_ai_summary(text_a: str, text_b: str, confidence: float) -> str:
    """
    Call claude-haiku to produce a brief semantic summary of differences.
    Returns an empty string if the API key is absent or the call fails.
    """
    api_key = os.environ.get("ANTHROPIC_API_KEY", "")
    if not api_key:
        return ""

    try:
        import anthropic  # type: ignore[import]
    except ImportError:
        logger.warning("anthropic package not installed; skipping AI summary")
        return ""

    # Truncate to avoid large token bills
    excerpt_a = textwrap.shorten(text_a, width=2000, placeholder="…")
    excerpt_b = textwrap.shorten(text_b, width=2000, placeholder="…")

    prompt = (
        f"You are a theological transcript QC assistant for Romanian Adventist sermons.\n\n"
        f"Two ASR transcripts of the same sermon have been compared.\n"
        f"Confidence score: {confidence}/100.\n\n"
        f"TRANSCRIPT A (AssemblyAI — excerpt):\n{excerpt_a}\n\n"
        f"TRANSCRIPT B (MacWhisper — excerpt):\n{excerpt_b}\n\n"
        f"In 3–5 sentences, summarise the key semantic differences between the two transcripts. "
        f"Focus on theological terminology, proper nouns, and any passages that diverge significantly."
    )

    try:
        client = anthropic.Anthropic(api_key=api_key)
        message = client.messages.create(
            model="claude-haiku-4-5",
            max_tokens=512,
            messages=[{"role": "user", "content": prompt}],
        )
        return message.content[0].text.strip()
    except Exception as exc:  # pylint: disable=broad-except
        logger.warning("AI summary call failed: %s", exc)
        return ""


# ──────────────────────────────────────────────────────────
# Public API
# ──────────────────────────────────────────────────────────

def compare(text_a: str, text_b: str) -> ComparisonResult:
    """
    Compare two transcript texts and return a ComparisonResult.

    Parameters
    ----------
    text_a:
        AssemblyAI transcript text.
    text_b:
        MacWhisper transcript text.
    """
    clean_a = _clean_text(text_a)
    clean_b = _clean_text(text_b)

    line_diff = _compute_line_diff(clean_a, clean_b)
    word_overlap = _compute_word_overlap(clean_a, clean_b)
    para_diffs = _compute_paragraph_diffs(clean_a, clean_b)
    confidence = _compute_confidence(word_overlap, para_diffs)

    ai_summary = _try_ai_summary(clean_a, clean_b, confidence)
    ai_used = bool(ai_summary)
    if not ai_used:
        ai_summary = (
            "_AI semantic summary skipped — ANTHROPIC_API_KEY not set or call failed._"
        )

    return ComparisonResult(
        line_diff=line_diff,
        word_overlap_pct=word_overlap,
        paragraph_diffs=para_diffs,
        confidence_score=confidence,
        ai_summary=ai_summary,
        ai_used=ai_used,
    )


def compare_files(path_a: Path, path_b: Path) -> ComparisonResult:
    """Convenience wrapper: read two files then call compare()."""
    text_a = path_a.read_text(encoding="utf-8", errors="replace")
    text_b = path_b.read_text(encoding="utf-8", errors="replace")
    return compare(text_a, text_b)
