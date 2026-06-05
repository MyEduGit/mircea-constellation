"""
scripture.py — Extract and validate Bible references from sermon transcripts.

Supports Romanian book names (Geneza, Exodul, …, Apocalipsa) and English
names (Genesis, Exodus, …, Revelation).

Reference patterns recognised
------------------------------
  Geneza 1:1            (standard chapter:verse)
  Geneza 1 versetul 1   (Romanian spoken form)
  Gen 1:1               (abbreviation)
  Revelation 22:20–21   (verse range)
  Ioan 3:16-17          (verse range with dash)
"""

from __future__ import annotations

import re
import logging
from dataclasses import dataclass, field
from typing import Sequence

logger = logging.getLogger(__name__)

# ──────────────────────────────────────────────────────────────────────────────
# Book tables
# ──────────────────────────────────────────────────────────────────────────────

# (Romanian name, English name, abbreviations, max_chapters, max_verses_per_chapter)
# max_verses is a rough upper bound used for sanity checking; 176 covers Psalm 119.
_BOOK_DATA: list[tuple[str, str, list[str], int, int]] = [
    # Old Testament
    ("Geneza",          "Genesis",          ["Gen"],              50,  57),
    ("Exodul",          "Exodus",           ["Ex", "Exo"],        40,  40),
    ("Levitic",         "Leviticus",        ["Lev"],              27,  34),
    ("Numeri",          "Numbers",          ["Num"],              36,  51),
    ("Deuteronomul",    "Deuteronomy",      ["Deut", "Deu"],      34,  29),
    ("Iosua",           "Joshua",           ["Ios", "Jos"],       24,  33),
    ("Judecători",      "Judges",           ["Jud"],              21,  31),
    ("Rut",             "Ruth",             ["Rut"],               4,  22),
    ("1 Samuel",        "1 Samuel",         ["1 Sam"],            31,  35),
    ("2 Samuel",        "2 Samuel",         ["2 Sam"],            24,  23),
    ("1 Împărați",      "1 Kings",          ["1 Imp", "1 Reg"],   22,  53),
    ("2 Împărați",      "2 Kings",          ["2 Imp", "2 Reg"],   25,  30),
    ("1 Cronici",       "1 Chronicles",     ["1 Cron", "1 Chr"],  29,  34),
    ("2 Cronici",       "2 Chronicles",     ["2 Cron", "2 Chr"],  36,  33),
    ("Ezra",            "Ezra",             ["Ezr"],              10,  44),
    ("Neemia",          "Nehemiah",         ["Neh"],              13,  27),
    ("Estera",          "Esther",           ["Est"],              10,  23),
    ("Iov",             "Job",              ["Iov"],              42,  34),
    ("Psalmi",          "Psalms",           ["Ps", "Psa"],       150, 176),
    ("Proverbe",        "Proverbs",         ["Prov", "Pro"],      31,  35),
    ("Eclesiastul",     "Ecclesiastes",     ["Ecl"],              12,  28),
    ("Cântarea",        "Song of Solomon",  ["Cant"],              8,  17),
    ("Isaia",           "Isaiah",           ["Is", "Isa"],        66,  22),
    ("Ieremia",         "Jeremiah",         ["Ier", "Jer"],       52,  22),
    ("Plângerile",      "Lamentations",     ["Plang", "Lam"],      5,  22),
    ("Ezechiel",        "Ezekiel",          ["Eze"],              48,  35),
    ("Daniel",          "Daniel",           ["Dan"],              12,  65),
    ("Osea",            "Hosea",            ["Os", "Hos"],        14,  15),
    ("Ioel",            "Joel",             ["Ioel", "Joel"],      3,  32),
    ("Amos",            "Amos",             ["Am"],               9,  15),
    ("Obadia",          "Obadiah",          ["Ob"],               1,  21),
    ("Iona",            "Jonah",            ["Iona", "Jon"],       4,  11),
    ("Mica",            "Micah",            ["Mica", "Mic"],       7,  20),
    ("Naum",            "Nahum",            ["Nah"],               3,  19),
    ("Habacuc",         "Habakkuk",         ["Hab"],               3,  20),
    ("Țefania",         "Zephaniah",        ["Tef", "Zep"],        3,  20),
    ("Hagai",           "Haggai",           ["Hag"],               2,  23),
    ("Zaharia",         "Zechariah",        ["Zah", "Zec"],       14,  21),
    ("Maleahi",         "Malachi",          ["Mal"],               4,   6),
    # New Testament
    ("Matei",           "Matthew",          ["Mat"],              28,  75),
    ("Marcu",           "Mark",             ["Mar"],              16,  78),
    ("Luca",            "Luke",             ["Luc"],              24,  80),
    ("Ioan",            "John",             ["In", "Jn"],         21,  25),
    ("Faptele",         "Acts",             ["Fapt", "Acts"],     28,  40),
    ("Romani",          "Romans",           ["Rom"],              16,  27),
    ("1 Corinteni",     "1 Corinthians",    ["1 Cor"],            16,  58),
    ("2 Corinteni",     "2 Corinthians",    ["2 Cor"],            13,  18),
    ("Galateni",        "Galatians",        ["Gal"],               6,  18),
    ("Efeseni",         "Ephesians",        ["Ef", "Eph"],         6,  33),
    ("Filipeni",        "Philippians",      ["Fil", "Phil"],       4,  23),
    ("Coloseni",        "Colossians",       ["Col"],               4,  18),
    ("1 Tesaloniceni",  "1 Thessalonians",  ["1 Tes", "1 Th"],     5,  28),
    ("2 Tesaloniceni",  "2 Thessalonians",  ["2 Tes", "2 Th"],     3,  17),
    ("1 Timotei",       "1 Timothy",        ["1 Tim"],             6,  22),
    ("2 Timotei",       "2 Timothy",        ["2 Tim"],             4,  22),
    ("Tit",             "Titus",            ["Tit"],               3,  15),
    ("Filimon",         "Philemon",         ["Filem", "Phm"],      1,  25),
    ("Evrei",           "Hebrews",          ["Ev", "Heb"],        13,  40),
    ("Iacov",           "James",            ["Iac", "Jas"],        5,  20),
    ("1 Petru",         "1 Peter",          ["1 Pet"],             5,  25),
    ("2 Petru",         "2 Peter",          ["2 Pet"],             3,  22),
    ("1 Ioan",          "1 John",           ["1 In", "1 Jn"],      5,  21),
    ("2 Ioan",          "2 John",           ["2 In", "2 Jn"],      1,  13),
    ("3 Ioan",          "3 John",           ["3 In", "3 Jn"],      1,  15),
    ("Iuda",            "Jude",             ["Iuda", "Jude"],      1,  25),
    ("Apocalipsa",      "Revelation",       ["Apoc", "Rev"],      22,  21),
]

# Build lookup: any alias → (canonical_romanian, max_chapters, max_verses)
@dataclass
class _BookInfo:
    romanian: str
    english: str
    max_chapters: int
    max_verses: int

_BOOK_LOOKUP: dict[str, _BookInfo] = {}

for _ro, _en, _abbrs, _mc, _mv in _BOOK_DATA:
    _info = _BookInfo(romanian=_ro, english=_en, max_chapters=_mc, max_verses=_mv)
    for _name in [_ro, _en] + _abbrs:
        _BOOK_LOOKUP[_name.lower()] = _info
        # also map without leading digit space for multi-word books like "1 Samuel"
        _BOOK_LOOKUP[_name.lower().replace(" ", "")] = _info


# ──────────────────────────────────────────────────────────────────────────────
# Data classes
# ──────────────────────────────────────────────────────────────────────────────

@dataclass
class ScriptureRef:
    book: str           # canonical Romanian book name
    chapter: int
    verse_start: int
    verse_end: int | None  # None if not a range
    raw_text: str          # as found in source
    line_num: int


@dataclass
class FormatIssue:
    ref: ScriptureRef
    issue: str  # human-readable description


# ──────────────────────────────────────────────────────────────────────────────
# Regex construction
# ──────────────────────────────────────────────────────────────────────────────

def _build_book_pattern() -> str:
    """Build an alternation of all known book names and abbreviations, longest first."""
    all_names: list[str] = []
    for ro, en, abbrs, _mc, _mv in _BOOK_DATA:
        all_names.append(ro)
        all_names.append(en)
        all_names.extend(abbrs)
    # Sort longest first to ensure greedy matching of "1 Corinteni" before "1"
    all_names.sort(key=len, reverse=True)
    return "|".join(re.escape(n) for n in all_names)


_BOOK_PAT = _build_book_pattern()

# Full reference patterns
#   Pattern 1: "Geneza 1:2"  or "Geneza 1:2-3"  or "Geneza 1:2–3"
_REF_COLON = re.compile(
    r"(?P<book>" + _BOOK_PAT + r")"
    r"\s+(?P<chapter>\d{1,3})"
    r"[:\s](?P<verse>\d{1,3})"
    r"(?:[–\-](?P<verse_end>\d{1,3}))?",
    re.IGNORECASE | re.UNICODE,
)

# Pattern 2: "Geneza capitolul 1 versetul 2" (spoken Romanian)
_REF_SPOKEN = re.compile(
    r"(?P<book>" + _BOOK_PAT + r")"
    r"\s+(?:capitolul\s+)?(?P<chapter>\d{1,3})"
    r"\s+versetul\s+(?P<verse>\d{1,3})"
    r"(?:\s*[–\-]\s*(?P<verse_end>\d{1,3}))?",
    re.IGNORECASE | re.UNICODE,
)


def _get_line_number(text: str, char_pos: int) -> int:
    return text[:char_pos].count("\n") + 1


def _resolve_book(raw: str) -> _BookInfo | None:
    key = raw.strip().lower().replace(" ", "")
    return _BOOK_LOOKUP.get(key) or _BOOK_LOOKUP.get(raw.strip().lower())


def _match_to_ref(m: re.Match, text: str) -> ScriptureRef | None:
    raw_book = m.group("book")
    info = _resolve_book(raw_book)
    if info is None:
        return None
    try:
        chapter = int(m.group("chapter"))
        verse = int(m.group("verse"))
    except (TypeError, ValueError):
        return None
    verse_end_raw = m.groupdict().get("verse_end")
    verse_end = int(verse_end_raw) if verse_end_raw else None
    return ScriptureRef(
        book=info.romanian,
        chapter=chapter,
        verse_start=verse,
        verse_end=verse_end,
        raw_text=m.group(0),
        line_num=_get_line_number(text, m.start()),
    )


# ──────────────────────────────────────────────────────────────────────────────
# Public API
# ──────────────────────────────────────────────────────────────────────────────

def extract_references(text: str) -> list[ScriptureRef]:
    """
    Extract all Bible references from *text*.

    Returns a list of ScriptureRef objects sorted by line number.
    Both Romanian and English book names are recognised.
    """
    refs: list[ScriptureRef] = []
    seen_spans: set[tuple[int, int]] = set()

    for pattern in (_REF_SPOKEN, _REF_COLON):
        for m in pattern.finditer(text):
            span = (m.start(), m.end())
            if span in seen_spans:
                continue
            ref = _match_to_ref(m, text)
            if ref is not None:
                refs.append(ref)
                seen_spans.add(span)

    refs.sort(key=lambda r: r.line_num)
    return refs


def verify_format(refs: list[ScriptureRef]) -> list[FormatIssue]:
    """
    Check each ScriptureRef for plausible chapter/verse numbers.

    Returns a list of FormatIssue for any references that appear out of range.
    """
    issues: list[FormatIssue] = []
    for ref in refs:
        info = _resolve_book(ref.book)
        if info is None:
            issues.append(FormatIssue(ref=ref, issue=f"Unknown book: '{ref.book}'"))
            continue
        if ref.chapter < 1 or ref.chapter > info.max_chapters:
            issues.append(
                FormatIssue(
                    ref=ref,
                    issue=(
                        f"{ref.book} has {info.max_chapters} chapters; "
                        f"chapter {ref.chapter} is out of range"
                    ),
                )
            )
        if ref.verse_start < 1 or ref.verse_start > info.max_verses:
            issues.append(
                FormatIssue(
                    ref=ref,
                    issue=(
                        f"Verse {ref.verse_start} may be out of range for {ref.book} "
                        f"(max ~{info.max_verses})"
                    ),
                )
            )
        if ref.verse_end is not None and ref.verse_end < ref.verse_start:
            issues.append(
                FormatIssue(
                    ref=ref,
                    issue=(
                        f"Verse range end ({ref.verse_end}) is less than start "
                        f"({ref.verse_start})"
                    ),
                )
            )
    return issues
