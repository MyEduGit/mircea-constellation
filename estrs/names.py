"""ESTRS — uncertain-name detection.

Scans transcript text for capitalized phrases that are NOT at the start of a
sentence and do not appear in a known-good word list.  Flags candidates as:
  HIGH    — unknown; both transcripts agree on the spelling
  MEDIUM  — unknown; transcripts disagree on the spelling
  LOW     — likely false positive (short word, common pattern)

Designed for Romanian-language sermons by Dr. Emanoil Geaboc.  The known-good
list includes common Romanian words, biblical names, standard theological terms,
and Romanian diacritics variants.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import NamedTuple

# ── Known-good corpus ─────────────────────────────────────────────────────────

# Words here are NEVER flagged regardless of capitalisation
_KNOWN: frozenset[str] = frozenset({
    # Romanian common nouns / pronouns often capitalised mid-sentence
    'Dumnezeu', 'Doamne', 'Domnul', 'Domnului', 'Isus', 'Hristos', 'Cristos',
    'Iisus', 'Tatăl', 'Duhul', 'Sfântul', 'Sfânt', 'Biblia', 'Scriptura',
    'Scripturile', 'Evanghelia', 'Legea', 'Prorocul', 'Psalmii', 'Psalmul',
    'Psalmistul', 'Apostolul', 'Apostolii', 'Proorocul',

    # Biblical proper names (common in sermons)
    'Avraam', 'Isaac', 'Iacob', 'Iosif', 'Moise', 'Aaron', 'Iosua', 'Ghedeon',
    'Samuel', 'Saul', 'David', 'Solomon', 'Ilie', 'Elisei', 'Isaia', 'Ieremia',
    'Ezechiel', 'Daniel', 'Osea', 'Ioel', 'Amos', 'Iona', 'Mica', 'Naum',
    'Habacuc', 'Zaharia', 'Maleahi', 'Ioan', 'Petru', 'Pavel', 'Iacov',
    'Andrei', 'Filip', 'Toma', 'Matei', 'Marcu', 'Luca', 'Iuda', 'Barnaba',
    'Timotei', 'Tit', 'Silas', 'Ştefan', 'Stefan', 'Apollos', 'Priscila',
    'Aquila', 'Lidia', 'Maria', 'Marta', 'Lazăr', 'Lazar', 'Nicodim',
    'Zaccheu', 'Zacheu', 'Pilat', 'Irod', 'Herode', 'Gamaliel', 'Caiafa',
    'Ana', 'Elisabeta', 'Zaharia', 'Simeon', 'Solomonida',

    # English biblical names (may appear in mixed text)
    'Abraham', 'Isaiah', 'Jeremiah', 'Ezekiel', 'Nehemiah', 'Zechariah',
    'Matthew', 'Mark', 'Luke', 'John', 'Peter', 'Paul', 'James', 'Judas',
    'Thomas', 'Philip', 'Andrew', 'Barnabas', 'Timothy', 'Titus', 'Stephen',
    'Lydia', 'Priscilla', 'Aquila', 'Mary', 'Martha', 'Lazarus', 'Nicodemus',
    'Zacchaeus', 'Pilate', 'Herod', 'Caiaphas', 'Simeon', 'Gamaliel',

    # Common theologians cited in sermons
    'Calvin', 'Luther', 'Wesley', 'Spurgeon', 'Whitefield', 'Bunyan',
    'Augustine', 'Augustin', 'Chrysostom', 'Origen', 'Tertullian', 'Aquinas',
    'Anselm', 'Zwingli', 'Knox', 'Owen', 'Baxter', 'Edwards', 'Warfield',
    'Machen', 'Packer', 'Stott', 'Kuyper', 'Berkhof', 'Hodge', 'Chafer',
    'Ryle', 'Tozer', 'Lloyd-Jones', 'Pink', 'Schaeffer', 'Sproul',
    'MacArthur', 'Piper', 'Keller', 'Dever',

    # All Bible book names (English + Romanian) — must not be flagged as uncertain
    'Genesis', 'Geneza', 'Exodus', 'Exodul', 'Leviticus', 'Leviticul',
    'Numbers', 'Numeri', 'Deuteronomy', 'Deuteronomul', 'Joshua', 'Iosua',
    'Judges', 'Judecători', 'Ruth', 'Rut', 'Samuel', 'Regi', 'Cronici',
    'Ezra', 'Nehemiah', 'Neemia', 'Esther', 'Estera', 'Job', 'Iov',
    'Psalms', 'Psalm', 'Psalmi', 'Psalmii', 'Psalmul', 'Proverbs', 'Proverbe',
    'Ecclesiastes', 'Eclesiastul', 'Isaiah', 'Isaia', 'Jeremiah', 'Ieremia',
    'Lamentations', 'Plângerile', 'Ezekiel', 'Ezechiel', 'Daniel',
    'Hosea', 'Osea', 'Joel', 'Ioel', 'Amos', 'Obadiah', 'Jonah', 'Iona',
    'Micah', 'Mica', 'Nahum', 'Naum', 'Habakkuk', 'Habacuc',
    'Zephaniah', 'Haggai', 'Zechariah', 'Zaharia', 'Malachi', 'Maleahi',
    'Matthew', 'Matei', 'Mark', 'Marcu', 'Luke', 'Luca', 'John', 'Ioan',
    'Acts', 'Faptele', 'Romans', 'Romani', 'Corinthians', 'Corinteni',
    'Galatians', 'Galateni', 'Ephesians', 'Efeseni', 'Philippians', 'Filipeni',
    'Colossians', 'Coloseni', 'Thessalonians', 'Tesaloniceni',
    'Timothy', 'Timotei', 'Titus', 'Tit', 'Philemon', 'Filimon',
    'Hebrews', 'Evrei', 'James', 'Iacov', 'Peter', 'Petru',
    'Revelation', 'Apocalipsa',

    # Romanian places / countries frequently named
    'România', 'Romania', 'Israel', 'Ierusalim', 'Jerusalem', 'Iuda',
    'Galileea', 'Samaria', 'Babilon', 'Egipt', 'Canaan', 'Nazaret',
    'Betleem', 'Betania', 'Ierihon', 'Corint', 'Efes', 'Antiohia',
    'Roma', 'Atena',

    # Days / months (Romanian capitalises these)
    'Luni', 'Marți', 'Miercuri', 'Joi', 'Vineri', 'Sâmbătă', 'Duminică',
    'Ianuarie', 'Februarie', 'Martie', 'Aprilie', 'Mai', 'Iunie',
    'Iulie', 'August', 'Septembrie', 'Octombrie', 'Noiembrie', 'Decembrie',

    # Common Latin titles appearing in sermons
    'Soli', 'Deo', 'Gloria', 'Gratia', 'Dei', 'Solus', 'Christus',

    # Hahnemann and other known terms
    'Hahnemann', 'Ritalin',
})

# Lowercase-normalised version for fast lookup
_KNOWN_LOWER: frozenset[str] = frozenset(w.lower() for w in _KNOWN)

# ── Patterns ──────────────────────────────────────────────────────────────────

_SENTENCE_END = re.compile(r'[.!?…]\s*$')
_CAPITALISED_WORD = re.compile(r'\b([A-ZĂÂÎȘȚŞŢ][a-zăâîșțşţ]{2,})\b')
_MULTI_WORD_CAP = re.compile(
    r'\b([A-ZĂÂÎȘȚŞŢ][a-zăâîșțşţ]{1,}(?:\s+[A-ZĂÂÎȘȚŞŢ][a-zăâîșțşţ]{1,}){1,3})\b'
)

# ── Data types ────────────────────────────────────────────────────────────────

@dataclass
class NameCandidate:
    text: str
    locations: list[tuple[int, int]] = field(default_factory=list)  # (line_no, char_pos)
    contexts: list[str] = field(default_factory=list)               # surrounding text
    sources: list[str] = field(default_factory=list)                # 'assemblyai' / 'macwhisper'
    confidence: str = 'MEDIUM'   # HIGH / MEDIUM / LOW
    note: str = ''


# ── Detection ─────────────────────────────────────────────────────────────────

def _is_sentence_start(line: str, pos: int) -> bool:
    """Return True if pos falls at the very start of a sentence."""
    before = line[:pos].rstrip()
    return (not before) or bool(_SENTENCE_END.search(before))


def _extract_candidates(text: str, source_label: str) -> dict[str, NameCandidate]:
    """Extract uncertain capitalised names from *text*."""
    candidates: dict[str, NameCandidate] = {}

    lines = text.splitlines()
    for line_no, line in enumerate(lines, start=1):
        # Multi-word capitalized phrases take priority
        for m in _MULTI_WORD_CAP.finditer(line):
            phrase = m.group(1)
            if all(w.lower() in _KNOWN_LOWER for w in phrase.split()):
                continue
            if _is_sentence_start(line, m.start()):
                continue
            key = phrase.lower()
            if key not in candidates:
                candidates[key] = NameCandidate(text=phrase)
            c = candidates[key]
            c.locations.append((line_no, m.start()))
            c.contexts.append(_context(lines, line_no - 1, m.start(), m.end()))
            if source_label not in c.sources:
                c.sources.append(source_label)

        # Single-word capitalised tokens
        for m in _CAPITALISED_WORD.finditer(line):
            word = m.group(1)
            if word.lower() in _KNOWN_LOWER:
                continue
            if _is_sentence_start(line, m.start()):
                continue
            key = word.lower()
            if key in candidates:
                continue  # already captured by multi-word pass
            if len(word) <= 3:
                continue  # ignore very short tokens
            candidates[key] = NameCandidate(
                text=word,
                locations=[(line_no, m.start())],
                contexts=[_context(lines, line_no - 1, m.start(), m.end())],
                sources=[source_label],
            )

    return candidates


def _context(lines: list[str], idx: int, start: int, end: int, radius: int = 60) -> str:
    line = lines[idx] if idx < len(lines) else ''
    before = line[max(0, start - radius):start].strip()
    after  = line[end:end + radius].strip()
    word   = line[start:end]
    return f"…{before} **{word}** {after}…".strip()


def detect_names(assemblyai_text: str, macwhisper_text: str) -> list[NameCandidate]:
    """Merge uncertain names from both transcripts, rate confidence."""
    a_cands = _extract_candidates(assemblyai_text, 'assemblyai')
    m_cands = _extract_candidates(macwhisper_text, 'macwhisper')

    merged: dict[str, NameCandidate] = {}

    for key, cand in a_cands.items():
        merged[key] = cand

    for key, cand in m_cands.items():
        if key in merged:
            existing = merged[key]
            existing.locations.extend(cand.locations)
            existing.contexts.extend(cand.contexts)
            for s in cand.sources:
                if s not in existing.sources:
                    existing.sources.append(s)
        else:
            merged[key] = cand

    # Rate confidence
    for key, cand in merged.items():
        both_sources = len(cand.sources) == 2
        if both_sources and len(cand.locations) >= 3:
            cand.confidence = 'HIGH'
        elif both_sources:
            cand.confidence = 'MEDIUM'
        else:
            cand.confidence = 'LOW'

    return sorted(merged.values(), key=lambda c: c.confidence)
