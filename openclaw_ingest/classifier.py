"""12-axis categorisation classifier for OpenClaw@URANTiOS-ingest.

Implements `categorise_by_axes` per the Great Ingestion direction:
every ingested item should be sortable by 12 canonical axes —
project · claw · suite · doctrine_topic · technical_function ·
document_type · status · chronology · platform_source · host_device ·
authority_level · proof_state · implementation_vs_canon.

Pure rule-based + keyword matching. No embeddings (yet — future PR can
add embedding-based scoring for doctrine_topic via Cognee).

Every axis returns:
    {"value": <str | list[str]>,
     "confidence": <float 0.0-1.0>,
     "method": "rule" | "metadata" | "default" | "extension" | "pattern"}

Confidence is honest:
    1.0  — direct metadata or extension match
    0.7  — strong rule-based match (multiple keyword hits)
    0.5  — single keyword match
    0.3  — default fallback (no positive signal)

Downstream consumers (governance_check, export_urantipedia) can filter
low-confidence classifications for human review.

UrantiOS governed — Truth, Beauty, Goodness.
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

# ── Static registries ──────────────────────────────────────────────────

PROJECTS: dict[str, list[str]] = {
    "mircea-constellation": ["mircea-constellation", "constellation"],
    "URANTiOS":             ["urantios"],
    "UrantiPedia":          ["urantipedia", "urantiapedia"],
    "lobsterbot":           ["lobsterbot"],
    "phd-triune-monism":    ["phd-triune", "triune monism", "triune-monism", "phd"],
    "MelchizedekTruth":     ["melchizedektruth", "melchizedek truth"],
    "johnmark":             ["johnmark.io", "john mark"],
}

# Each claw → keyword variants (case-insensitive, whole-word matching).
CLAWS: dict[str, list[str]] = {
    "OpenClaw":         ["openclaw"],
    "NanoClaw":         ["nanoclaw"],
    "NemoClaw":         ["nemoclaw"],
    "Fireclaw":         ["fireclaw"],
    "LuciferiClaw":     ["lucifericlaw", "luciferiClaw", "luciferclaw"],
    "Paperclip":        ["paperclip"],
    "UrantiClaw":       [r"\buranticlaw\b"],
    "VisualUrantiClaw": ["visualuranticlaw", "visual uranticlaw"],
    "MemoryClaw":       ["memoryclaw"],
    "IndexClaw":        ["indexclaw"],
    "GateClaw":         ["gateclaw"],
    "RouteClaw":        ["routeclaw"],
    "JudgeClaw":        ["judgeclaw"],
    "LedgerClaw":       ["ledgerclaw"],
    "ShieldClaw":       ["shieldclaw"],
    "WatcherClaw":      ["watcherclaw"],
    "ArchiveClaw":      ["archiveclaw"],
    "ChannelClaw":      ["channelclaw"],
    "BuildClaw":        ["buildclaw"],
    "TestClaw":         ["testclaw"],
    "SyncClaw":         ["syncclaw"],
}

URANTI_SUITE_CLAWS: frozenset[str] = frozenset({
    "UrantiClaw", "VisualUrantiClaw", "LuciferiClaw",
})
OPERATIONAL_CLAWS: frozenset[str] = frozenset({
    "OpenClaw", "NanoClaw", "NemoClaw", "Fireclaw", "Paperclip",
    "MemoryClaw", "IndexClaw", "GateClaw", "RouteClaw", "JudgeClaw",
    "LedgerClaw", "ShieldClaw", "WatcherClaw", "ArchiveClaw",
    "ChannelClaw", "BuildClaw", "TestClaw", "SyncClaw", "LuciferiClaw",
})

# Document type by extension.
EXT_TO_DOCTYPE: dict[str, str] = {
    ".jsonl": "chat_log",
    ".json":  "structured_data",
    ".md":    "markdown_doc",
    ".py":    "python_code",
    ".js":    "javascript_code",
    ".ts":    "typescript_code",
    ".sh":    "shell_script",
    ".yaml":  "yaml_config",
    ".yml":   "yaml_config",
    ".toml":  "toml_config",
    ".html":  "html_doc",
    ".txt":   "text",
}

# Technical function patterns (multi-match → highest signal wins).
TECH_PATTERNS: list[tuple[str, re.Pattern[str], float]] = [
    ("code",          re.compile(r"^\s*(def |class |import |from \w+ import|function\s+\w+|const\s+\w+\s*=)", re.M), 0.7),
    ("shell",         re.compile(r"^#!/bin/(ba)?sh|^\s*(sudo |apt-get|systemctl |docker )", re.M), 0.7),
    ("config",        re.compile(r"^\s*(version:|services:|networks:|volumes:)\s*$|---\n.*:.*\n", re.M), 0.6),
    ("conversation",  re.compile(r'"role"\s*:\s*"(user|assistant|system)"|^(user|assistant|human):', re.I | re.M), 0.7),
    ("documentation", re.compile(r"^#{1,6}\s+\w|^\s*(\*|\-|\d+\.)\s+\w", re.M), 0.5),
    ("architecture",  re.compile(r"\b(architecture|topology|claw|suite|orchestrat|pipeline|integration)\b", re.I), 0.5),
    ("data",          re.compile(r"^\{.*\}\s*$|^\[.*\]\s*$", re.M | re.S), 0.5),
]

# Authority-level signals.
AUTHORITY_PATTERNS: list[tuple[str, re.Pattern[str], float]] = [
    ("canonical", re.compile(r"\b(canonical|canon|settled|locked|approved by mircea|father function)\b", re.I), 0.8),
    ("draft",     re.compile(r"\b(draft|tentative|proposed|preliminary|todo|wip)\b", re.I), 0.6),
    ("personal",  re.compile(r"\bdiary\b|\bjournal\b|\bnote to self\b", re.I), 0.6),
]

# Implementation vs canon vs idea vs draft.
IMPL_PATTERNS: list[tuple[str, re.Pattern[str], float]] = [
    ("canon",          re.compile(r"\b(canonical|definition|principle|rule|doctrine)\b", re.I), 0.6),
    ("implementation", re.compile(r"\b(deploy|install|build|run|exec|commit|push|merge)\b", re.I), 0.6),
    ("idea",           re.compile(r"\b(what if|maybe|could we|should we|perhaps|consider)\b", re.I), 0.5),
    ("draft",          re.compile(r"\b(draft|wip|brainstorm|exploring)\b", re.I), 0.6),
]

# Proof-state signals.
PROOF_PATTERNS: list[tuple[str, re.Pattern[str], float]] = [
    ("proven",  re.compile(r"\b(verified|proven|confirmed|sha256|tested end-to-end|smoke test passed)\b", re.I), 0.8),
    ("claimed", re.compile(r"\b(should|will|expected to|production-safe|ready)\b", re.I), 0.4),
    ("pending", re.compile(r"\b(pending|todo|tbd|not yet|unverified)\b", re.I), 0.6),
]

# Source platform signals (when metadata is missing).
SOURCE_PATTERNS: list[tuple[str, re.Pattern[str], float]] = [
    ("claude_code",  re.compile(r"claude.code|\.claude/|claude-code|anthropic", re.I), 0.7),
    ("chatgpt",      re.compile(r"chatgpt|openai|gpt-4|chat\.openai", re.I), 0.7),
    ("gemini",       re.compile(r"gemini|bard|google\s+ai", re.I), 0.7),
    ("grok",         re.compile(r"\bgrok\b|x\.ai", re.I), 0.7),
    ("telegram",     re.compile(r"telegram|@\w+_bot|tg-?bot", re.I), 0.6),
    ("obsidian",     re.compile(r"obsidian|\.md vault", re.I), 0.6),
]

# Stop-words for doctrine_topic keyword matching (don't match papers on these).
_STOPWORDS: frozenset[str] = frozenset({
    "the", "a", "an", "of", "and", "or", "in", "on", "at", "to", "for",
    "with", "by", "as", "is", "are", "was", "were", "be", "been", "being",
    "his", "her", "its", "their", "this", "that", "these", "those",
    "it", "of", "from", "up", "down", "out", "all", "any", "some",
})


# ── Paper title index (UrantiPedia, doctrine_topic axis) ──────────────
@dataclass
class PaperIndex:
    by_index: dict[int, str]                    # paper_index → title
    keyword_to_papers: dict[str, list[int]]     # keyword → [paper_index, ...]


_PAPER_INDEX: PaperIndex | None = None


def _load_paper_index() -> PaperIndex:
    """Load paper_titles.json (shipped with the module). Idempotent + cached."""
    global _PAPER_INDEX
    if _PAPER_INDEX is not None:
        return _PAPER_INDEX
    path = Path(__file__).parent / "paper_titles.json"
    if not path.exists():
        # Honest empty index — doctrine_topic axis becomes default.
        _PAPER_INDEX = PaperIndex({}, {})
        return _PAPER_INDEX
    data = json.loads(path.read_text())
    by_index: dict[int, str] = {}
    keyword_to_papers: dict[str, list[int]] = {}
    for entry in data.get("papers", []):
        # entry is [index, title] in compact form.
        idx, title = entry[0], entry[1]
        by_index[idx] = title
        # Build keyword reverse-index from title words.
        for raw in re.findall(r"[A-Za-z]{4,}", title.lower()):
            if raw in _STOPWORDS:
                continue
            keyword_to_papers.setdefault(raw, []).append(idx)
    _PAPER_INDEX = PaperIndex(by_index, keyword_to_papers)
    return _PAPER_INDEX


# ── Helpers ───────────────────────────────────────────────────────────
def _result(value: Any, confidence: float, method: str,
            **extra: Any) -> dict[str, Any]:
    out = {"value": value, "confidence": round(float(confidence), 2),
           "method": method}
    out.update(extra)
    return out


def _scan_keywords(text: str, registry: dict[str, list[str]]) -> list[str]:
    """Return registry keys whose any keyword appears (case-insensitive)
    as a whole-word match in `text`."""
    hits: list[str] = []
    text_lower = text.lower()
    for key, patterns in registry.items():
        for pat in patterns:
            # Allow regex strings (start with \\) or plain strings (escape).
            if pat.startswith("\\b"):
                if re.search(pat, text, re.I):
                    hits.append(key)
                    break
            else:
                # Whole-word match — wrap in \b...\b.
                if re.search(rf"\b{re.escape(pat)}\b", text_lower):
                    hits.append(key)
                    break
    return hits


def _strongest(text: str,
               patterns: list[tuple[str, re.Pattern[str], float]]
               ) -> tuple[str, float] | None:
    """Return (label, confidence) for the highest-scoring pattern that hits."""
    best: tuple[str, float] | None = None
    for label, pat, conf in patterns:
        if pat.search(text):
            if best is None or conf > best[1]:
                best = (label, conf)
    return best


# ── Per-axis classifiers ──────────────────────────────────────────────
def axis_project(text: str, metadata: dict) -> dict:
    if metadata.get("project"):
        return _result(metadata["project"], 1.0, "metadata")
    hits = _scan_keywords(text, PROJECTS)
    if not hits:
        return _result("unknown", 0.3, "default")
    if len(hits) == 1:
        return _result(hits[0], 0.7, "rule")
    return _result(hits, 0.7, "rule")


def axis_claw(text: str, metadata: dict) -> dict:
    if metadata.get("claw"):
        return _result(metadata["claw"], 1.0, "metadata")
    hits = _scan_keywords(text, CLAWS)
    if not hits:
        return _result([], 0.3, "default")
    return _result(hits, 0.7, "rule")


def axis_suite(claw_value: Any) -> dict:
    """Derived from the claw axis."""
    claws = claw_value if isinstance(claw_value, list) else [claw_value]
    suites: list[str] = []
    for c in claws:
        if c in URANTI_SUITE_CLAWS:
            suites.append("UrantiSuite")
        if c in OPERATIONAL_CLAWS:
            suites.append("operational")
    suites = sorted(set(suites))
    if not suites:
        return _result("unknown", 0.3, "default")
    return _result(suites if len(suites) > 1 else suites[0], 0.9, "derived")


def axis_doctrine_topic(text: str) -> dict:
    """Score against the 197-paper UrantiPedia title index.
    Returns up to top-3 papers by keyword-hit count, with scripture refs."""
    idx = _load_paper_index()
    if not idx.by_index:
        return _result([], 0.0, "default", note="paper_titles.json missing")
    text_words = set(re.findall(r"[a-z]{4,}", text.lower()))
    text_words -= _STOPWORDS
    scores: dict[int, int] = {}
    for w in text_words:
        for paper_idx in idx.keyword_to_papers.get(w, []):
            scores[paper_idx] = scores.get(paper_idx, 0) + 1
    if not scores:
        return _result([], 0.3, "default", note="no paper keyword matches")
    top = sorted(scores.items(), key=lambda kv: kv[1], reverse=True)[:3]
    matches = [{"paper": p, "title": idx.by_index[p], "hits": h}
               for p, h in top]
    # Confidence scales with hit count: 1 hit → 0.4, 3+ → 0.7.
    best_hits = top[0][1]
    conf = min(0.4 + 0.1 * (best_hits - 1), 0.7)
    return _result(matches, conf, "rule")


def axis_technical_function(text: str) -> dict:
    best = _strongest(text, TECH_PATTERNS)
    if best is None:
        return _result("narrative", 0.3, "default")
    return _result(best[0], best[1], "pattern")


def axis_document_type(filename: str | None, text: str) -> dict:
    if filename:
        ext = Path(filename).suffix.lower()
        if ext in EXT_TO_DOCTYPE:
            return _result(EXT_TO_DOCTYPE[ext], 1.0, "extension")
    # Fall back to content sniffing.
    head = text.lstrip()[:200]
    if head.startswith("{") or head.startswith("["):
        return _result("structured_data", 0.6, "pattern")
    if re.match(r"^#{1,6}\s+\w", head):
        return _result("markdown_doc", 0.6, "pattern")
    if re.match(r"^#!/", head):
        return _result("shell_script", 0.7, "pattern")
    return _result("text", 0.3, "default")


def axis_status() -> dict:
    """Trivially derived: the act of classifying makes it classified."""
    return _result("classified", 1.0, "derived")


def axis_chronology(text: str, metadata: dict) -> dict:
    """Extract ts from metadata, or first ISO/epoch timestamp in text."""
    candidate_ts: float | None = None
    if metadata.get("ts"):
        try:
            candidate_ts = float(metadata["ts"])
        except (TypeError, ValueError):
            pass
    if candidate_ts is None:
        m = re.search(r"\b(20\d{2}-\d{2}-\d{2}(?:T\d{2}:\d{2}:\d{2}[+-]?\d{0,4})?)\b", text)
        if m:
            try:
                dt = datetime.fromisoformat(m.group(1).replace("Z", "+00:00"))
                candidate_ts = dt.timestamp()
            except ValueError:
                pass
    if candidate_ts is None:
        return _result({"bucket": "unknown", "ts": None}, 0.3, "default")
    dt = datetime.fromtimestamp(candidate_ts, tz=timezone.utc)
    now = datetime.now(timezone.utc)
    delta = now - dt
    if delta < timedelta(days=1):
        bucket = "today"
    elif delta < timedelta(days=7):
        bucket = "this_week"
    elif delta < timedelta(days=30):
        bucket = "this_month"
    elif delta < timedelta(days=365):
        bucket = "this_year"
    else:
        bucket = "older"
    return _result({"bucket": bucket, "ts": candidate_ts,
                    "iso": dt.isoformat()}, 0.9, "extracted")


def axis_platform_source(metadata: dict, text: str) -> dict:
    if metadata.get("source"):
        return _result(metadata["source"], 1.0, "metadata")
    best = _strongest(text, SOURCE_PATTERNS)
    if best is None:
        return _result("unknown", 0.3, "default")
    return _result(best[0], best[1], "pattern")


def axis_host_device(platform_value: str, metadata: dict) -> dict:
    if metadata.get("host_device"):
        return _result(metadata["host_device"], 1.0, "metadata")
    mapping = {
        "claude_code": "imac_m4",
        "chatgpt":     "imac_m4",
        "gemini":      "imac_m4",
        "grok":        "imac_m4",
        "obsidian":    "imac_m4",
        "telegram":    "openclaw_hetzy",
    }
    if platform_value in mapping:
        return _result(mapping[platform_value], 0.6, "derived")
    return _result("unknown", 0.3, "default")


def axis_authority_level(text: str, metadata: dict) -> dict:
    if metadata.get("authority_level"):
        return _result(metadata["authority_level"], 1.0, "metadata")
    best = _strongest(text, AUTHORITY_PATTERNS)
    if best is None:
        return _result("personal", 0.3, "default")
    return _result(best[0], best[1], "pattern")


def axis_proof_state(text: str, metadata: dict) -> dict:
    if metadata.get("proof_state"):
        return _result(metadata["proof_state"], 1.0, "metadata")
    best = _strongest(text, PROOF_PATTERNS)
    if best is None:
        return _result("pending", 0.4, "default")
    return _result(best[0], best[1], "pattern")


def axis_implementation_vs_canon(text: str, metadata: dict) -> dict:
    if metadata.get("implementation_vs_canon"):
        return _result(metadata["implementation_vs_canon"], 1.0, "metadata")
    best = _strongest(text, IMPL_PATTERNS)
    if best is None:
        return _result("draft", 0.3, "default")
    return _result(best[0], best[1], "pattern")


# ── Public API ────────────────────────────────────────────────────────
def classify(text: str, metadata: dict | None = None,
             filename: str | None = None) -> dict[str, Any]:
    """Run all 12+ axes against `text` and return the full classification.

    Args:
        text: the content to classify.
        metadata: optional dict of pre-known fields (source, project, claw,
                  authority_level, etc.) — metadata always wins over inference.
        filename: optional filename — used for the document_type axis.

    Returns:
        {axis_name: {value, confidence, method, ...}, ...}
    """
    metadata = metadata or {}
    project       = axis_project(text, metadata)
    claw          = axis_claw(text, metadata)
    suite         = axis_suite(claw["value"])
    doctrine      = axis_doctrine_topic(text)
    technical     = axis_technical_function(text)
    document_type = axis_document_type(filename, text)
    status        = axis_status()
    chronology    = axis_chronology(text, metadata)
    platform      = axis_platform_source(metadata, text)
    host          = axis_host_device(platform["value"] if isinstance(platform["value"], str) else "", metadata)
    authority     = axis_authority_level(text, metadata)
    proof         = axis_proof_state(text, metadata)
    impl          = axis_implementation_vs_canon(text, metadata)

    return {
        "project":                project,
        "claw":                   claw,
        "suite":                  suite,
        "doctrine_topic":         doctrine,
        "technical_function":     technical,
        "document_type":          document_type,
        "status":                 status,
        "chronology":             chronology,
        "platform_source":        platform,
        "host_device":            host,
        "authority_level":        authority,
        "proof_state":            proof,
        "implementation_vs_canon": impl,
    }


def classify_file(path: str | Path,
                  metadata: dict | None = None) -> dict[str, Any]:
    """Convenience: classify a file's content. Returns classification +
    file-level fields (sha256, name, size)."""
    import hashlib
    p = Path(path)
    text = p.read_text(encoding="utf-8")
    sha = hashlib.sha256(text.encode("utf-8")).hexdigest()
    return {
        "file":   p.name,
        "size":   len(text),
        "sha256": sha,
        "axes":   classify(text, metadata=metadata, filename=p.name),
    }
