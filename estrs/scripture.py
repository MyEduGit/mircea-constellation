"""ESTRS — Bible-reference extraction and audit.

Finds references of the form:
  Genesis 1:1            (English)
  Geneza 1:1             (Romanian)
  Gen. 1:1               (abbreviated)
  Ioan 3:16              (Romanian NT)
  1 Corinteni 13:4-7     (Romanian with chapter range)
  Revelation 22:20

Emits a ScriptureAudit with:
  - all references found
  - books cited
  - format-consistency warnings
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field

# ── Book name table ───────────────────────────────────────────────────────────

# Maps canonical English name → list of accepted surface forms (English + Romanian)
BOOK_ALIASES: dict[str, list[str]] = {
    'Genesis':         ['Genesis', 'Geneza', 'Gen'],
    'Exodus':          ['Exodus', 'Exodul', 'Ex'],
    'Leviticus':       ['Leviticus', 'Leviticul', 'Lev'],
    'Numbers':         ['Numbers', 'Numeri', 'Num'],
    'Deuteronomy':     ['Deuteronomy', 'Deuteronomul', 'Deut'],
    'Joshua':          ['Joshua', 'Iosua', 'Ios'],
    'Judges':          ['Judges', 'Judecători', 'Jud'],
    'Ruth':            ['Ruth', 'Rut'],
    '1 Samuel':        ['1 Samuel', '1Samuel', '1Sam', '1 Sam'],
    '2 Samuel':        ['2 Samuel', '2Samuel', '2Sam', '2 Sam'],
    '1 Kings':         ['1 Kings', '1Kings', '1 Regi', '1Regi'],
    '2 Kings':         ['2 Kings', '2Kings', '2 Regi', '2Regi'],
    '1 Chronicles':    ['1 Chronicles', '1 Cronici', '1Cronici'],
    '2 Chronicles':    ['2 Chronicles', '2 Cronici', '2Cronici'],
    'Ezra':            ['Ezra', 'Ezra'],
    'Nehemiah':        ['Nehemiah', 'Neemia'],
    'Esther':          ['Esther', 'Estera'],
    'Job':             ['Job', 'Iov'],
    'Psalms':          ['Psalms', 'Psalm', 'Psalmii', 'Psalmul', 'Ps'],
    'Proverbs':        ['Proverbs', 'Proverbe', 'Prov'],
    'Ecclesiastes':    ['Ecclesiastes', 'Eclesiastul', 'Ecl'],
    'Song of Songs':   ['Song of Songs', 'Song of Solomon', 'Cântarea Cântărilor', 'Cânt'],
    'Isaiah':          ['Isaiah', 'Isaia', 'Is'],
    'Jeremiah':        ['Jeremiah', 'Ieremia', 'Ier'],
    'Lamentations':    ['Lamentations', 'Plângerile', 'Plâng'],
    'Ezekiel':         ['Ezekiel', 'Ezechiel', 'Ez'],
    'Daniel':          ['Daniel', 'Dan'],
    'Hosea':           ['Hosea', 'Osea', 'Os'],
    'Joel':            ['Joel', 'Ioel'],
    'Amos':            ['Amos'],
    'Obadiah':         ['Obadiah', 'Obadia'],
    'Jonah':           ['Jonah', 'Iona'],
    'Micah':           ['Micah', 'Mica'],
    'Nahum':           ['Nahum', 'Naum'],
    'Habakkuk':        ['Habakkuk', 'Habacuc'],
    'Zephaniah':       ['Zephaniah', 'Țefania'],
    'Haggai':          ['Haggai', 'Hagai'],
    'Zechariah':       ['Zechariah', 'Zaharia'],
    'Malachi':         ['Malachi', 'Maleahi'],
    'Matthew':         ['Matthew', 'Matei', 'Mat'],
    'Mark':            ['Mark', 'Marcu'],
    'Luke':            ['Luke', 'Luca'],
    'John':            ['John', 'Ioan'],
    'Acts':            ['Acts', 'Faptele Apostolilor', 'Faptele', 'FA'],
    'Romans':          ['Romans', 'Romani', 'Rom'],
    '1 Corinthians':   ['1 Corinthians', '1 Corinteni', '1Cor'],
    '2 Corinthians':   ['2 Corinthians', '2 Corinteni', '2Cor'],
    'Galatians':       ['Galatians', 'Galateni', 'Gal'],
    'Ephesians':       ['Ephesians', 'Efeseni', 'Ef'],
    'Philippians':     ['Philippians', 'Filipeni', 'Fil'],
    'Colossians':      ['Colossians', 'Coloseni', 'Col'],
    '1 Thessalonians': ['1 Thessalonians', '1 Tesaloniceni', '1Tes'],
    '2 Thessalonians': ['2 Thessalonians', '2 Tesaloniceni', '2Tes'],
    '1 Timothy':       ['1 Timothy', '1 Timotei', '1Tim'],
    '2 Timothy':       ['2 Timothy', '2 Timotei', '2Tim'],
    'Titus':           ['Titus', 'Tit'],
    'Philemon':        ['Philemon', 'Filimon'],
    'Hebrews':         ['Hebrews', 'Evrei', 'Evr'],
    'James':           ['James', 'Iacov', 'Iac'],
    '1 Peter':         ['1 Peter', '1 Petru', '1Pet'],
    '2 Peter':         ['2 Peter', '2 Petru', '2Pet'],
    '1 John':          ['1 John', '1 Ioan', '1In'],
    '2 John':          ['2 John', '2 Ioan', '2In'],
    '3 John':          ['3 John', '3 Ioan', '3In'],
    'Jude':            ['Jude', 'Iuda'],
    'Revelation':      ['Revelation', 'Apocalipsa', 'Apoc', 'Rev'],
}

# Build reverse lookup: surface → canonical
_SURFACE_TO_BOOK: dict[str, str] = {}
for canonical, surfaces in BOOK_ALIASES.items():
    for s in surfaces:
        _SURFACE_TO_BOOK[s] = canonical

# Pattern: optional number prefix + book name + space + chapter(:verse)?
_all_surfaces = sorted(_SURFACE_TO_BOOK.keys(), key=len, reverse=True)
_book_alt = '|'.join(re.escape(s) for s in _all_surfaces)
_REF_PATTERN = re.compile(
    r'\b(?:(\d)\s+)?(' + _book_alt + r')\.?\s+(\d{1,3})(?::(\d{1,3})(?:-(\d{1,3}))?)?',
    re.UNICODE,
)

# ── Data types ────────────────────────────────────────────────────────────────

@dataclass
class ScriptureRef:
    raw: str
    canonical_book: str
    chapter: int
    verse_start: int | None
    verse_end: int | None
    line_no: int
    source: str


@dataclass
class ScriptureAudit:
    refs: list[ScriptureRef] = field(default_factory=list)
    books_cited: list[str] = field(default_factory=list)
    format_warnings: list[str] = field(default_factory=list)
    total_count: int = 0


# ── Extraction ────────────────────────────────────────────────────────────────

def _extract_refs(text: str, source: str) -> list[ScriptureRef]:
    refs: list[ScriptureRef] = []
    for line_no, line in enumerate(text.splitlines(), start=1):
        for m in _REF_PATTERN.finditer(line):
            prefix_num = m.group(1)  # '1', '2', '3' for numbered books
            book_surface = m.group(2)
            chapter = int(m.group(3))
            verse_start = int(m.group(4)) if m.group(4) else None
            verse_end   = int(m.group(5)) if m.group(5) else None

            # Reconstruct the surface key for lookup
            lookup_key = f"{prefix_num} {book_surface}" if prefix_num else book_surface
            canonical = _SURFACE_TO_BOOK.get(lookup_key) or _SURFACE_TO_BOOK.get(book_surface)
            if not canonical:
                continue

            refs.append(ScriptureRef(
                raw=m.group(0),
                canonical_book=canonical,
                chapter=chapter,
                verse_start=verse_start,
                verse_end=verse_end,
                line_no=line_no,
                source=source,
            ))
    return refs


def _check_format_consistency(refs: list[ScriptureRef]) -> list[str]:
    warnings: list[str] = []
    # Check for same book cited in different surface forms
    surface_map: dict[str, set[str]] = {}
    for r in refs:
        canon = r.canonical_book
        surface = r.raw.split()[0] if r.raw else ''
        if canon not in surface_map:
            surface_map[canon] = set()
        surface_map[canon].add(surface)
    for book, surfaces in surface_map.items():
        if len(surfaces) > 1:
            warnings.append(
                f"'{book}' cited in {len(surfaces)} different surface forms: "
                + ', '.join(f'"{s}"' for s in sorted(surfaces))
            )
    return warnings


def audit_scripture(assemblyai_text: str, macwhisper_text: str) -> ScriptureAudit:
    refs_a = _extract_refs(assemblyai_text, 'assemblyai')
    refs_m = _extract_refs(macwhisper_text, 'macwhisper')
    all_refs = refs_a + refs_m

    books = sorted(set(r.canonical_book for r in all_refs))
    warnings = _check_format_consistency(all_refs)

    # Warn if a reference appears in only one transcript
    a_set = {(r.canonical_book, r.chapter, r.verse_start) for r in refs_a}
    m_set = {(r.canonical_book, r.chapter, r.verse_start) for r in refs_m}
    only_in_a = a_set - m_set
    only_in_m = m_set - a_set
    for ref in sorted(only_in_a):
        warnings.append(f"Reference {ref} found only in AssemblyAI transcript")
    for ref in sorted(only_in_m):
        warnings.append(f"Reference {ref} found only in MacWhisper transcript")

    return ScriptureAudit(
        refs=all_refs,
        books_cited=books,
        format_warnings=warnings,
        total_count=len(all_refs),
    )
