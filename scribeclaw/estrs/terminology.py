"""
terminology.py — Flag Latin, medical, foreign, and theological-Latin terms in
Romanian Adventist sermon transcripts.

Also flags ALL-CAPS sequences of 3+ characters, which are common ASR artefacts
(e.g. missed acronyms, garbled words).

Categories
----------
LATIN              — classic Reformation slogans, liturgical Latin
THEOLOGICAL_LATIN  — Latin used in theology and church history
MEDICAL            — pharmaceutical / oncology terms (common in Dr. Geaboc's sermons
                     about faith and healing)
FOREIGN            — non-Romanian, non-Latin proper-noun terms (homeopathy etc.)
ALL_CAPS           — suspected ASR artefact
"""

from __future__ import annotations

import re
import logging
from dataclasses import dataclass
from enum import Enum
from pathlib import Path

logger = logging.getLogger(__name__)


class TermCategory(str, Enum):
    LATIN = "LATIN"
    THEOLOGICAL_LATIN = "THEOLOGICAL_LATIN"
    MEDICAL = "MEDICAL"
    FOREIGN = "FOREIGN"
    ALL_CAPS = "ALL_CAPS"


@dataclass
class TermFlag:
    term: str
    category: TermCategory
    context: str      # surrounding ~120 chars
    line_num: int


# ──────────────────────────────────────────────────────────────────────────────
# Built-in term lists
# ──────────────────────────────────────────────────────────────────────────────

_LATIN_TERMS: list[str] = [
    # Reformation slogans
    "Soli Deo Gloria",
    "Sola Scriptura",
    "sola fide",
    "sola gratia",
    "solus Christus",
    "solo Christo",
    "sola ecclesia",
    # Liturgical / classical
    "ad hominem",
    "ad hoc",
    "ex cathedra",
    "ex nihilo",
    "in absentia",
    "in memoriam",
    "per se",
    "sine qua non",
    "status quo",
    "vice versa",
    "mea culpa",
    "pater noster",
    "agnus dei",
    "Agnus Dei",
    "gloria in excelsis",
    "Gloria in Excelsis",
    "kyrie eleison",
    "credo",
    "Credo",
    "sanctus",
    "Sanctus",
    "fiat lux",
    "corpus christi",
    "Corpus Christi",
    "veni sancte spiritus",
    "veni Sancte Spiritus",
    "terra incognita",
    "tabula rasa",
]

_THEOLOGICAL_LATIN_TERMS: list[str] = [
    # Classic doctrinal terms
    "imputation",
    "imputatio",
    "propitiation",
    "propitiatio",
    "soteriology",
    "soteriologie",
    "eschatology",
    "pneumatology",
    "pneumatologie",
    "ecclesiology",
    "ecclesiologie",
    "hermeneutics",
    "hermeneutică",
    "exegesis",
    "exegeză",
    "perichoresis",
    "penal substitution",
    "substitutio",
    "ordo salutis",
    "theosis",
    "kenosis",
    "pericope",
    "pericocpă",
    "parousia",
    "parouzie",
    "adventus",
    "paroikia",
    "sensus plenior",
    "lectio divina",
    "Lectio Divina",
    "analogia entis",
    "analogia fidei",
    "communicatio idiomatum",
    "vestigia Trinitatis",
    "extra calvinisticum",
    # Church history
    "magisterium",
    "Magisterium",
    "infallibilitas",
    "ex opere operato",
    "lex orandi lex credendi",
    "anathema sit",
    "filioque",
    "Filioque",
    "homoousios",
    "homoiousios",
    "Nicaea",
    "Chalcedon",
]

_MEDICAL_TERMS: list[str] = [
    # Oncology / chemotherapy (common in Dr. Geaboc's apologetics against alternative medicine)
    "vincristina",
    "vinblastina",
    "vincristine",
    "vinblastine",
    "chimioterapie",
    "chimioterapia",
    "radioterapie",
    "radioterapia",
    "imunoterapie",
    "imunoterapia",
    "metastaza",
    "metastazare",
    "carcinoma",
    "carcinogen",
    "leucemie",
    "limfom",
    "melanom",
    "neoplasm",
    "oncologie",
    "oncolog",
    "biopsie",
    "histologie",
    "morfologie celulară",
    "celule canceroase",
    "ADN",
    "ARN",
    "cromozom",
    "gena",
    "mutație",
    "antibiotic",
    "cortizol",
    "adrenalina",
    "insulina",
    "glucoză",
    "hemoglobina",
    "trombocite",
    "leucocite",
    "eritrocite",
    "plasmă",
    "diagnostic",
    "prognostic",
    "simptome",
    "sindrom",
    "patologie",
    "anamneza",
    "protocol medical",
    # Homeopathy / alternative (common in critique)
    "homeopatie",
    "remediu homeopatic",
    "potentizare",
    "dilutie homeopatica",
    "miasm",
    "vitalism",
    "iridologie",
    "reflexoterapie",
    "acupunctură",
    "acupunctura",
    "ayurveda",
    "chakra",
    "chakre",
]

_FOREIGN_TERMS: list[str] = [
    # Homeopathy founders / associated names
    "Hahnemann",
    "Samuel Hahnemann",
    "Paracelsus",
    "Rudolf Steiner",
    "anthroposofie",
    "Waldorf",
    "Christian Science",
    "Mary Baker Eddy",
    # New Age / occult
    "New Age",
    "karma",
    "dharma",
    "nirvana",
    "reincarnare",
    "reîncarnare",
    "chakra",
    "mantra",
    "yoga",
    "meditație transcendentală",
    "transcendental",
    "shamanism",
    "șamanism",
    "wicca",
    "Wicca",
    "druidism",
    "kabbalah",
    "Kabbalah",
    "feng shui",
    "astrology",
    "astrologie",
    "horoscop",
    # Specific sects / movements critiqued
    "Jehovah's Witnesses",
    "Martorii lui Iehova",
    "Iehova",
    "Mormons",
    "mormoni",
    "Scientology",
    "Scientologie",
    "Freemasonry",
    "francmasonerie",
    "Illuminati",
    # Cultural / non-Romanian theological terms
    "Koran",
    "Quran",
    "Coran",
    "Jihad",
    "halal",
    "bar mitzva",
    "Torah",
    "Talmud",
    "Mishna",
    "kabbalah",
    "Yom Kippur",
    "Rosh Hashanah",
    "Ramadan",
]


# ──────────────────────────────────────────────────────────────────────────────
# Pre-compile term → category lookup
# ──────────────────────────────────────────────────────────────────────────────

def _build_term_patterns() -> list[tuple[re.Pattern, TermCategory]]:
    """Build a list of (compiled_pattern, category) tuples."""
    pairs: list[tuple[re.Pattern, TermCategory]] = []
    mapping: list[tuple[list[str], TermCategory]] = [
        (_LATIN_TERMS,             TermCategory.LATIN),
        (_THEOLOGICAL_LATIN_TERMS, TermCategory.THEOLOGICAL_LATIN),
        (_MEDICAL_TERMS,           TermCategory.MEDICAL),
        (_FOREIGN_TERMS,           TermCategory.FOREIGN),
    ]
    for terms, category in mapping:
        for term in terms:
            # Word-boundary aware, case-insensitive
            pat = re.compile(r"\b" + re.escape(term) + r"\b", re.IGNORECASE | re.UNICODE)
            pairs.append((pat, category))
    return pairs


_TERM_PATTERNS: list[tuple[re.Pattern, TermCategory]] = _build_term_patterns()

# ALL-CAPS sequence: 3+ uppercase letters (ignoring common abbreviations ≤2 chars)
_ALL_CAPS_RE = re.compile(r"\b([A-ZĂÂÎȘȚ]{3,})\b", re.UNICODE)

# Well-known Romanian/biblical abbreviations to exclude from ALL_CAPS flagging
_CAPS_WHITELIST: frozenset[str] = frozenset(
    {
        "ADN", "ARN", "SDA", "KJV", "NIV", "ESV", "NTR", "VDCC", "GBV",
        "SUA", "UE", "OMS", "ONU", "NATO", "EU", "USA", "BBC", "CNN",
        "ISBN", "URL", "PDF", "HTML", "XML", "JSON", "API",
    }
)


# ──────────────────────────────────────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────────────────────────────────────

def _get_context(text: str, start: int, end: int, window: int = 120) -> str:
    ctx_start = max(0, start - window // 2)
    ctx_end = min(len(text), end + window // 2)
    return text[ctx_start:ctx_end].replace("\n", " ").strip()


def _get_line_number(text: str, char_pos: int) -> int:
    return text[:char_pos].count("\n") + 1


# ──────────────────────────────────────────────────────────────────────────────
# Public API
# ──────────────────────────────────────────────────────────────────────────────

def audit(text: str) -> list[TermFlag]:
    """
    Scan *text* for terminology flags.

    Returns a list of TermFlag objects (one per match), sorted by line number.
    Duplicate spans are deduplicated — if a term matches multiple categories the
    highest-priority one wins (LATIN > THEOLOGICAL_LATIN > MEDICAL > FOREIGN).
    """
    flags: list[TermFlag] = []
    seen_spans: set[tuple[int, int]] = set()

    # Categorical term matching
    for pattern, category in _TERM_PATTERNS:
        for m in pattern.finditer(text):
            span = (m.start(), m.end())
            if span in seen_spans:
                continue
            seen_spans.add(span)
            flags.append(
                TermFlag(
                    term=m.group(0),
                    category=category,
                    context=_get_context(text, m.start(), m.end()),
                    line_num=_get_line_number(text, m.start()),
                )
            )

    # ALL_CAPS check
    for m in _ALL_CAPS_RE.finditer(text):
        word = m.group(1)
        if word in _CAPS_WHITELIST:
            continue
        span = (m.start(), m.end())
        if span in seen_spans:
            continue
        seen_spans.add(span)
        flags.append(
            TermFlag(
                term=word,
                category=TermCategory.ALL_CAPS,
                context=_get_context(text, m.start(), m.end()),
                line_num=_get_line_number(text, m.start()),
            )
        )

    flags.sort(key=lambda f: f.line_num)
    return flags


def summarise(flags: list[TermFlag]) -> dict[str, int]:
    """Return a count of flags per category."""
    counts: dict[str, int] = {c.value: 0 for c in TermCategory}
    for f in flags:
        counts[f.category.value] += 1
    return counts
