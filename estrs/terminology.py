"""ESTRS — terminology audit.

Checks for:
  1. Known Latin phrases (theological / liturgical)
  2. Medical / pharmaceutical terms (context: Dr. Geaboc sermons on illness)
  3. Foreign words / homeopathy terminology
  4. Likely transcription errors (phonetic confusions common in Romanian ASR)

Returns a TerminologyAudit with flagged items and context.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field

# ── Term catalogs ─────────────────────────────────────────────────────────────

# (display_term, category, notes)
_KNOWN_TERMS: list[tuple[str, str, str]] = [
    # Latin — theological
    ('Soli Deo Gloria',     'Latin',   'To God alone be the glory'),
    ('Sola Scriptura',      'Latin',   'Scripture alone'),
    ('Sola Fide',           'Latin',   'By faith alone'),
    ('Sola Gratia',         'Latin',   'By grace alone'),
    ('Solus Christus',      'Latin',   'Through Christ alone'),
    ('Coram Deo',           'Latin',   'Before the face of God'),
    ('Imago Dei',           'Latin',   'Image of God'),
    ('Sub specie aeternitatis', 'Latin', 'Under the aspect of eternity'),
    ('Dei Gratia',          'Latin',   'By the grace of God'),
    ('Gloria in Excelsis',  'Latin',   'Glory in the highest'),
    ('Agnus Dei',           'Latin',   'Lamb of God'),
    ('Vox Dei',             'Latin',   'Voice of God'),
    ('Deus Vult',           'Latin',   'God wills it'),
    ('Ex nihilo',           'Latin',   'Out of nothing'),
    ('Ad Gloriam Dei',      'Latin',   'To the glory of God'),
    ('Ecce Homo',           'Latin',   'Behold the man'),
    ('Laus Deo',            'Latin',   'Praise be to God'),
    ('Magnificat',          'Latin',   'Mary\'s hymn of praise'),
    ('Kyrie Eleison',       'Greek/Liturgical', 'Lord have mercy'),
    ('Maranatha',           'Aramaic', 'Come, Lord'),
    ('Hallelujah',          'Hebrew',  'Praise the Lord'),
    ('Selah',               'Hebrew',  'Pause / lift up (Psalms)'),
    ('Amen',                'Hebrew',  'So be it'),
    ('Hosanna',             'Hebrew',  'Save now'),
    ('Abba',                'Aramaic', 'Father'),

    # Medical / oncology (common in sermons about illness / healing)
    ('vincristina',         'Medical', 'Vinca alkaloid chemotherapy agent'),
    ('vinblastina',         'Medical', 'Vinca alkaloid chemotherapy agent'),
    ('vincristine',         'Medical', 'English form of vincristina'),
    ('vinblastine',         'Medical', 'English form of vinblastina'),
    ('metastaza',           'Medical', 'Romanian: metastasis'),
    ('metastasis',          'Medical', 'Spread of cancer'),
    ('chimioterapie',       'Medical', 'Romanian: chemotherapy'),
    ('chemotherapy',        'Medical', 'Cancer treatment'),
    ('radioterapie',        'Medical', 'Romanian: radiotherapy'),
    ('leucemie',            'Medical', 'Romanian: leukemia'),
    ('limfom',              'Medical', 'Romanian: lymphoma'),
    ('oncologie',           'Medical', 'Romanian: oncology'),
    ('biopsie',             'Medical', 'Romanian: biopsy'),

    # Homeopathy / alternative medicine
    ('Hahnemann',           'Homeopathy', 'Samuel Hahnemann, founder of homeopathy'),
    ('homeopatie',          'Homeopathy', 'Romanian: homeopathy'),
    ('homeopathy',          'Homeopathy', 'Alternative medicine system'),

    # Ritalin (may appear in sermons on mental health)
    ('Ritalin',             'Medical', 'Methylphenidate — ADHD medication'),
    ('metilfenidat',        'Medical', 'Romanian: methylphenidate'),

    # German names often cited
    ('Niebuhr',             'Theology', 'Reinhold Niebuhr — theologian'),
    ('Bonhoeffer',          'Theology', 'Dietrich Bonhoeffer — theologian/martyr'),
    ('Kierkegaard',         'Philosophy', 'Danish philosopher'),
    ('Dostoievski',         'Literature', 'Romanian: Dostoevsky'),
    ('Dostoevsky',          'Literature', 'Russian novelist'),
    ('Soljenițin',          'Literature', 'Romanian: Solzhenitsyn'),
    ('Solzhenitsyn',        'Literature', 'Russian novelist / dissident'),
]

# Build pattern: case-insensitive search for each term
_TERM_PATTERNS: list[tuple[re.Pattern, str, str, str]] = []
for _term, _cat, _note in _KNOWN_TERMS:
    _pat = re.compile(r'\b' + re.escape(_term) + r'\b', re.IGNORECASE | re.UNICODE)
    _TERM_PATTERNS.append((_pat, _term, _cat, _note))

# ── Likely transcription error patterns ───────────────────────────────────────
# Romanian ASR often confuses these phoneme pairs

_ERROR_PATTERNS: list[tuple[re.Pattern, str, str]] = [
    # ș (sh-sound) written as s
    (re.compile(r'\bcrestina\b', re.IGNORECASE), 'creștina',  'ASR: ș→s confusion'),
    (re.compile(r'\bcrestin\b',  re.IGNORECASE), 'creștin',   'ASR: ș→s confusion'),
    (re.compile(r'\bsfinta\b',   re.IGNORECASE), 'sfânta',    'ASR: â missing'),
    (re.compile(r'\bpamant\b',   re.IGNORECASE), 'pământ',    'ASR: â missing'),
    (re.compile(r'\bmantuit\b',  re.IGNORECASE), 'mântuit',   'ASR: â missing'),
    # Common ASR mishearing
    (re.compile(r'\binimile\b',  re.IGNORECASE), 'inimile',   'verify: hearts (pl)'),
]

# ── Data types ────────────────────────────────────────────────────────────────

@dataclass
class TermHit:
    term: str
    category: str
    note: str
    occurrences: list[tuple[str, int, str]] = field(default_factory=list)
    # Each occurrence: (source_label, line_no, context_snippet)


@dataclass
class ErrorHit:
    pattern_found: str
    suggested_correction: str
    reason: str
    occurrences: list[tuple[str, int, str]] = field(default_factory=list)


@dataclass
class TerminologyAudit:
    term_hits: list[TermHit] = field(default_factory=list)
    error_hits: list[ErrorHit] = field(default_factory=list)
    total_terms_found: int = 0
    total_errors_flagged: int = 0


# ── Audit logic ───────────────────────────────────────────────────────────────

def _scan_text(text: str, source: str,
               hits: dict[str, TermHit],
               errors: dict[str, ErrorHit]) -> None:
    lines = text.splitlines()
    for line_no, line in enumerate(lines, start=1):
        ctx = line.strip()[:120]

        for pat, term, cat, note in _TERM_PATTERNS:
            if pat.search(line):
                if term not in hits:
                    hits[term] = TermHit(term=term, category=cat, note=note)
                hits[term].occurrences.append((source, line_no, ctx))

        for pat, correction, reason in _ERROR_PATTERNS:
            m = pat.search(line)
            if m:
                found = m.group(0)
                key = found.lower()
                if key not in errors:
                    errors[key] = ErrorHit(
                        pattern_found=found,
                        suggested_correction=correction,
                        reason=reason,
                    )
                errors[key].occurrences.append((source, line_no, ctx))


def audit_terminology(assemblyai_text: str, macwhisper_text: str) -> TerminologyAudit:
    hits: dict[str, TermHit] = {}
    errors: dict[str, ErrorHit] = {}

    _scan_text(assemblyai_text, 'assemblyai', hits, errors)
    _scan_text(macwhisper_text, 'macwhisper', hits, errors)

    return TerminologyAudit(
        term_hits=sorted(hits.values(), key=lambda h: h.category),
        error_hits=list(errors.values()),
        total_terms_found=len(hits),
        total_errors_flagged=len(errors),
    )
