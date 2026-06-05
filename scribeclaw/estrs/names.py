"""
names.py — Detect uncertain proper nouns in Romanian Adventist sermon transcripts.

Strategy
--------
1. Tokenise text into capitalized multi-word phrases (2–4 words) that do NOT
   appear at the start of a sentence.
2. Filter out a built-in ~200-word Romanian/theological vocabulary.
3. Everything that remains is a NameCandidate flagged for human review.
4. Also flag: single capitalized tokens preceded by uncertain context words
   like "fratele", "sora", "pastorul", "doctorul" that are NOT in the known
   vocabulary — these may be personal names.
"""

from __future__ import annotations

import re
import logging
from dataclasses import dataclass, field
from typing import Sequence

logger = logging.getLogger(__name__)

# ──────────────────────────────────────────────────────────────────────────────
# Known Romanian / theological vocabulary — NOT flagged as uncertain names
# ──────────────────────────────────────────────────────────────────────────────

KNOWN_VOCABULARY: frozenset[str] = frozenset(
    {
        # Divine names & titles
        "Dumnezeu", "Hristos", "Iisus", "Iisus Hristos", "Isus", "Isus Hristos",
        "Domnul", "Tatăl", "Fiul", "Duhul Sfânt", "Duhul", "Mântuitorul",
        "Creatorul", "Judecătorul", "Mesia", "Emanuel",
        # Bible
        "Biblia", "Sfânta Scriptură", "Scriptura", "Cuvântul lui Dumnezeu",
        "Testamentul", "Vechiul Testament", "Noul Testament",
        # OT Books (Romanian)
        "Geneza", "Exodul", "Levitic", "Numeri", "Deuteronomul", "Iosua",
        "Judecători", "Rut", "Samuel", "Împărați", "Cronici", "Ezra", "Neemia",
        "Estera", "Iov", "Psalmi", "Proverbe", "Eclesiastul", "Cântarea",
        "Isaia", "Ieremia", "Plângerile", "Ezechiel", "Daniel", "Osea", "Ioel",
        "Amos", "Obadia", "Iona", "Mica", "Naum", "Habacuc", "Țefania",
        "Hagai", "Zaharia", "Maleahi",
        # NT Books (Romanian)
        "Matei", "Marcu", "Luca", "Ioan", "Faptele", "Faptele Apostolilor",
        "Romani", "Corinteni", "Galateni", "Efeseni", "Filipeni", "Coloseni",
        "Tesaloniceni", "Timotei", "Tit", "Filimon", "Evrei", "Iacov", "Petru",
        "Iuda", "Apocalipsa",
        # Bible characters
        "Avraam", "Isaac", "Iacob", "Iosif", "Moise", "Aaron", "Ilie", "Elisei",
        "David", "Solomon", "Ezechiel", "Neemia", "Estera", "Iov", "Pavel",
        "Petru", "Iacov", "Andrei", "Filip", "Bartolomeu", "Toma", "Matei",
        "Tadeu", "Simon", "Iuda", "Maria", "Marta", "Lazăr", "Nicodim",
        "Zaharia", "Elisabeta", "Ioan Botezătorul", "Pilat", "Caiafa", "Ana",
        "Ştefan", "Barnabas", "Timotei", "Tit", "Lidia", "Priscila", "Acuila",
        # Adventist figures
        "Ellen White", "Sora White", "James White", "Joseph Bates",
        "Hiram Edson", "William Miller", "Uriah Smith",
        # Reformers / theologians
        "Luther", "Martin Luther", "Calvin", "Jean Calvin", "Wesley",
        "John Wesley", "Zwingli", "Ulrich Zwingli", "Hus", "Jan Hus",
        "Wycliffe", "John Wycliffe", "Knox", "John Knox",
        # Key theological terms (Romanian)
        "adventist", "adventism", "adventistă", "adventistul",
        "protestant", "protestantism", "protestantă",
        "Reformațiunea", "Reforma", "Reformațiune",
        "catolic", "catolicism", "romano-catolic",
        "ortodox", "ortodoxie",
        "penticostal", "penticostalism",
        "baptist", "baptism",
        "evanghelic", "evangelism",
        "papă", "papalitate", "papist", "Vatican",
        "spiritism", "ocultism", "New Age",
        "Satana", "diavolul", "diavol", "demon", "demoni",
        "înger", "îngeri", "arhanghelul", "Mihail", "Gavril", "Lucifer",
        # Doctrinal / worship
        "Sabat", "Sabatul", "Sabatul Bibliei",
        "neprihănire", "sfințire", "mântuire", "pocăință", "credință",
        "botez", "botezul", "rugăciune", "profeție", "profet", "apostol",
        "biserică", "denominațiune", "denominațiuni",
        "sanctuarul", "judecata", "judecata de cercetare",
        "mileniu", "maranatha", "parouzie", "escatologie",
        "ispășire", "răscumpărare", "învierea", "învierea morților",
        "cer", "raiul", "iadul", "focul", "Gheena", "Hades",
        "a doua venire", "venirea", "revenirea",
        # Calendar / liturgy
        "Duminică", "Sâmbătă", "Vineri", "Paște", "Crăciun", "Rusalii",
        # Geographic (biblical)
        "Israel", "Ierusalim", "Babilon", "Egipt", "Canaan", "Iudeea",
        "Galileea", "Nazaret", "Betleem", "Capernaum", "Iordan",
        "Sinai", "Golgota", "Ghetsimani", "Sion", "Patmos",
        # Romanian church/ministry terms
        "pastorul", "pastori", "pastor",
        "Conferința", "Uniunea", "Diviziunea", "Asociația",
        "biserica locală", "departamentul",
        # Common titles not to flag
        "Fratele", "Sora", "Doctorul", "Profesorul",
    }
)

# Lowercase version for case-insensitive lookup
_KNOWN_LOWER: frozenset[str] = frozenset(t.lower() for t in KNOWN_VOCABULARY)

# Context words that may precede personal names (Romanian)
_NAME_CONTEXT_WORDS = frozenset(
    {
        "fratele", "sora", "pastorul", "doctorul", "profesorul",
        "domnul", "doamna", "dl", "dna", "dr",
    }
)


# ──────────────────────────────────────────────────────────────────────────────
# Data classes
# ──────────────────────────────────────────────────────────────────────────────

@dataclass
class NameCandidate:
    """A possibly-uncertain proper noun found in the transcript."""

    phrase: str          # the raw phrase as found
    context: str         # surrounding sentence context (up to ~120 chars)
    line_num: int        # 1-based line number where phrase starts
    confidence: float    # 0.0–1.0: how confident we are it IS uncertain
                         # (1.0 = very likely an unresolved name)


# ──────────────────────────────────────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────────────────────────────────────

def _is_sentence_start(text: str, match_start: int) -> bool:
    """Return True if the character at match_start follows a sentence boundary."""
    preceding = text[:match_start].rstrip()
    if not preceding:
        return True  # very start of text
    last_char = preceding[-1]
    return last_char in ".!?\n"


def _get_context(text: str, start: int, end: int, window: int = 120) -> str:
    """Extract a context window around [start:end]."""
    ctx_start = max(0, start - window // 2)
    ctx_end = min(len(text), end + window // 2)
    snippet = text[ctx_start:ctx_end].replace("\n", " ").strip()
    return snippet


def _phrase_is_known(phrase: str) -> bool:
    """Return True if the phrase (or any sub-phrase) is in the known vocabulary."""
    lower = phrase.lower().strip()
    if lower in _KNOWN_LOWER:
        return True
    # Check each individual token
    for token in lower.split():
        if token in _KNOWN_LOWER:
            return True
    return False


def _get_line_number(text: str, char_pos: int) -> int:
    """Return the 1-based line number for a character position in *text*."""
    return text[:char_pos].count("\n") + 1


# ──────────────────────────────────────────────────────────────────────────────
# Multi-word capitalized phrase detection
# ──────────────────────────────────────────────────────────────────────────────

# Matches 2–4 consecutive Capitalized_Words (allows hyphens and Romanian diacritics)
_CAPITALIZED_WORD = r"[A-ZĂÂÎȘȚ][a-zA-ZăâîșțĂÂÎȘȚ\-]+"
_MULTI_WORD_RE = re.compile(
    r"(?<!\.\s)(?<![!?]\s)\b("
    + _CAPITALIZED_WORD
    + r"(?:\s+"
    + _CAPITALIZED_WORD
    + r"){1,3})\b"
)

# Matches a single capitalized word that follows a title/context word
_TITLE_NAME_RE = re.compile(
    r"\b(?P<title>"
    + "|".join(re.escape(w) for w in _NAME_CONTEXT_WORDS)
    + r")\s+(?P<name>[A-ZĂÂÎȘȚ][a-zA-ZăâîșțĂÂÎȘȚ\-]+)\b",
    re.IGNORECASE,
)


def _extract_multi_word_candidates(text: str) -> list[NameCandidate]:
    """Find 2–4-word capitalized phrases not at sentence start."""
    results: list[NameCandidate] = []
    for m in _MULTI_WORD_RE.finditer(text):
        phrase = m.group(1)
        if _is_sentence_start(text, m.start()):
            continue
        if _phrase_is_known(phrase):
            continue
        context = _get_context(text, m.start(), m.end())
        line_num = _get_line_number(text, m.start())
        results.append(
            NameCandidate(
                phrase=phrase,
                context=context,
                line_num=line_num,
                confidence=0.8,
            )
        )
    return results


def _extract_title_preceded_names(text: str) -> list[NameCandidate]:
    """Find 'fratele X', 'pastorul Y' style names."""
    results: list[NameCandidate] = []
    for m in _TITLE_NAME_RE.finditer(text):
        name = m.group("name")
        if _phrase_is_known(name):
            continue
        context = _get_context(text, m.start(), m.end())
        line_num = _get_line_number(text, m.start())
        results.append(
            NameCandidate(
                phrase=m.group(0),
                context=context,
                line_num=line_num,
                confidence=0.9,
            )
        )
    return results


def _deduplicate(candidates: list[NameCandidate]) -> list[NameCandidate]:
    """Remove duplicate phrases (case-insensitive), keeping highest confidence."""
    seen: dict[str, NameCandidate] = {}
    for c in candidates:
        key = c.phrase.lower().strip()
        if key not in seen or c.confidence > seen[key].confidence:
            seen[key] = c
    return sorted(seen.values(), key=lambda c: c.line_num)


# ──────────────────────────────────────────────────────────────────────────────
# Public API
# ──────────────────────────────────────────────────────────────────────────────

def detect_uncertain_names(text: str) -> list[NameCandidate]:
    """
    Detect uncertain proper nouns in *text*.

    Returns a deduplicated list of NameCandidate objects sorted by line number.
    Only flags phrases not already in the built-in Romanian/theological
    vocabulary (~200 entries).
    """
    candidates: list[NameCandidate] = []
    candidates.extend(_extract_multi_word_candidates(text))
    candidates.extend(_extract_title_preceded_names(text))
    return _deduplicate(candidates)
