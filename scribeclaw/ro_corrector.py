"""correct_ro_theological — deterministic ASR-error corrector for
Romanian theological/liturgical transcripts.

Does NOT call an LLM. Every correction is a documented rule with a
confidence score. Rules below `min_confidence_auto_fix` (default 0.85)
are surfaced as flags instead of being applied, so the operator can
spot-check against audio before committing.

Inputs:
  stem        (str, optional): transcript stem. When present, the
                               handler prefers /data/transcripts/<stem>/
                               transcript.cues.srt, falls back to
                               transcript.srt.
  srt_path    (str, optional): explicit path, resolved under DATA_ROOT.

Exactly one of `stem` or `srt_path` is required.

Outputs (next to the source SRT):
  <name>.clean.srt          — corrected SRT, identical timings, UTF-8
                              (BOM added by default for YouTube Studio).
  <name>.corrections.log    — pretty per-cue audit: original, change,
                              rule_id, confidence, flag reason.
  <name>.corrections.json   — structured audit log (machine-readable).

The result payload surfaces counts, flagged cues (with suggested
replacements and confidence scores), and the absolute path of every
output.
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

_HARD_BREAK = re.compile(r"(?<=[.!?])\s+(?=[A-ZĂÂÎȘȚ])")
_SRT_TIME = re.compile(
    r"(\d{2}):(\d{2}):(\d{2})[,\.](\d{3})\s*-->\s*"
    r"(\d{2}):(\d{2}):(\d{2})[,\.](\d{3})"
)


# ──────────────────────────────────────────────────────────────────────
# RULE LIBRARY — deterministic, documented, versioned.
# Every rule carries:
#   id          : stable identifier (for evidence logs)
#   category    : grouping (reporting only)
#   pattern     : compiled regex applied against cue text
#   replacement : substitution string (supports \1..\9 backrefs)
#   confidence  : 0.0-1.0; below min_confidence_auto_fix → flag-only
#   rationale   : human-readable reason
#   context_*   : optional before/after context substrings (case-
#                 insensitive); when supplied the rule only fires when
#                 at least one context cue matches within ± window.
# ──────────────────────────────────────────────────────────────────────
@dataclass(frozen=True)
class Rule:
    id: str
    category: str
    pattern: re.Pattern
    replacement: str
    confidence: float
    rationale: str
    context_before: tuple[str, ...] = ()
    context_after: tuple[str, ...] = ()


def _wb(word: str) -> re.Pattern:
    """Word-boundary regex that also respects Romanian diacritics.

    \\b is ASCII-only in Python's re; we build an explicit
    non-letter boundary to avoid matching mid-word."""
    body = re.escape(word)
    return re.compile(r"(?<![A-Za-zĂÂÎȘȚăâîșț])" + body + r"(?![A-Za-zĂÂÎȘȚăâîșț])")


# The library. Keep it small, explicit, and documented — additions
# should come via an operator-supplied overlay (library_path), not
# silently shipping patterns that change the canonical corpus.
BUILTIN_RULES: tuple[Rule, ...] = (
    # —— English/Romanian spelling bleed ────────────────────────────
    Rule("spell.humana_romanian",  "spelling",
         _wb("humană"),   "umană",    0.98,
         "Romanian word is 'umană' (fem. of 'uman'); 'humană' is English/Latinate bleed-through."),
    Rule("spell.humanitatea",      "spelling",
         _wb("Humanitatea"), "Umanitatea", 0.98,
         "Capitalised spelling-bleed variant."),
    Rule("spell.humanitate_any_case", "spelling",
         re.compile(r"(?<![A-Za-zĂÂÎȘȚăâîșț])[Hh]umanitat"), "Umanitat",  0.96,
         "Covers Humanitate/humanitate forms — always no H in Romanian."),
    Rule("spell.humanitar",        "spelling",
         _wb("humanitar"), "umanitar", 0.97,
         "'Humanitar' is spelling bleed; Romanian spells this without H."),

    # —— Apostle / Epistle proper nouns ─────────────────────────────
    Rule("proper.apostolul_pavel", "proper-noun",
         re.compile(r"(?<![A-Za-zĂÂÎȘȚăâîșț])[Pp]ostul\s+Pavel"),
         "Apostolul Pavel",        0.95,
         "'Postul Pavel' is ASR artefact for 'Apostolul Pavel' (the Apostle Paul)."),
    Rule("proper.apostolul_lui_pavel", "proper-noun",
         re.compile(r"(?<![A-Za-zĂÂÎȘȚăâîșț])[Pp]ostul\s+lui\s+Pavel"),
         "Apostolul Pavel",        0.93,
         "Genitive variant of the same ASR artefact."),
    Rule("proper.epistola_pavel",   "proper-noun",
         re.compile(r"(?<![A-Za-zĂÂÎȘȚăâîșț])Episodul\s+al\s+Pavelului"),
         "Epistola lui Pavel",     0.92,
         "'Episodul al Pavelului' → 'Epistola lui Pavel' (Paul's letter)."),

    # —— Biblical / liturgical Romanian vocabulary ──────────────────
    Rule("biblical.capetenia",     "biblical-vocab",
         _wb("căpătenia"),  "căpetenia", 0.94,
         "'Căpătenia' is mispronunciation of 'căpetenia' (chief/head)."),
    Rule("biblical.desavarsirea",  "biblical-vocab",
         re.compile(
             r"(?<![A-Za-zĂÂÎȘȚăâîșț])(D|d)esărbășirea(?![A-Za-zĂÂÎȘȚăâîșț])"
         ),
         r"\1esăvârșirea", 0.92,
         "ASR garble of 'desăvârșirea' (perfection) — case-preserving."),
    Rule("biblical.neprihanirea",  "biblical-vocab",
         _wb("neprivenirea"), "neprihănirea", 0.95,
         "'Neprihănirea' (righteousness) — Cornilescu register."),
    Rule("biblical.s_a_smerit",    "biblical-vocab",
         re.compile(r"(?<![A-Za-zĂÂÎȘȚăâîșț])s-a\s+ominit"),
         "s-a smerit",             0.93,
         "Philippians 2 context — 's-a smerit' (He humbled Himself)."),
    Rule("biblical.scara_lui_iacov", "biblical-vocab",
         re.compile(r"(?<![A-Za-zĂÂÎȘȚăâîșț])scală(\s+(?:lui\s+)?Iacov)?"),
         "scara\\1",               0.90,
         "Genesis 28 — 'scara lui Iacov' (Jacob's ladder)."),
    Rule("biblical.mantuitor",     "biblical-vocab",
         _wb("mântuitor"), "Mântuitor", 0.80,
         "Proper noun when referring to Christ; capitalised in context."),

    # —— ASR artefacts / miscellaneous ──────────────────────────────
    Rule("asr.datatoare",          "asr-artifact",
         _wb("dătoare"),   "dătătoare", 0.88,
         "Whisper drops a syllable; 'dătătoare' (giving) is correct form."),
    Rule("asr.iubire",             "asr-artifact",
         _wb("iubiruință"), "iubire",   0.86,
         "Nonce word; 'iubire' (love) is the theological baseline."),
    Rule("asr.finitul",            "philosophical",
         _wb("Finidul"),   "Finitul",   0.90,
         "'Finitul' (the Finite) — contrasted with Infinitul."),

    # —— Grammar (gender / case) ────────────────────────────────────
    Rule("grammar.acelasi_credinte", "grammar",
         re.compile(r"(?<![A-Za-zĂÂÎȘȚăâîșț])aceiași\s+credințe"),
         "aceleași credințe",      0.92,
         "Feminine plural needs 'aceleași', not 'aceiași'."),

    # —— Context-conditional ────────────────────────────────────────
    # Confidence 0.70 → flag-only by default; operator can lower threshold.
    Rule("context.ellen_white_from_solaoide", "proper-noun",
         _wb("Solaoide"), "Ellen White", 0.70,
         "Likely 'Ellen White' when surrounded by Christology context.",
         context_before=("hristos", "lumina lumii", "desire of ages"),
         context_after=("hristos", "lumina lumii", "desire of ages")),
)


# ──────────────────────────────────────────────────────────────────────
# SRT parsing / serialization (no external deps).
# ──────────────────────────────────────────────────────────────────────
@dataclass
class Cue:
    index: int
    timestamp: str           # the full "HH:MM:SS,mmm --> HH:MM:SS,mmm" line
    text: str                # cue body (may contain internal newlines)


def _parse_srt(content: str) -> list[Cue]:
    # Strip UTF-8 BOM if present — we'll add one on write if requested.
    if content.startswith("\ufeff"):
        content = content[1:]
    # Normalise Windows/Mac line endings.
    content = content.replace("\r\n", "\n").replace("\r", "\n")

    cues: list[Cue] = []
    blocks = re.split(r"\n\s*\n", content.strip())
    for block in blocks:
        lines = [l for l in block.split("\n") if l != ""]
        if len(lines) < 2:
            continue
        # Tolerate missing index line.
        if _SRT_TIME.search(lines[0]):
            ts_line = lines[0]
            text_lines = lines[1:]
            idx = len(cues) + 1
        else:
            try:
                idx = int(lines[0].strip())
            except ValueError:
                idx = len(cues) + 1
            ts_line = lines[1] if len(lines) > 1 else ""
            text_lines = lines[2:]
        if not _SRT_TIME.search(ts_line):
            continue
        cues.append(Cue(index=idx, timestamp=ts_line.strip(),
                        text="\n".join(text_lines)))
    return cues


def _serialize_srt(cues: list[Cue], write_bom: bool) -> str:
    parts: list[str] = []
    for i, c in enumerate(cues, start=1):
        parts.append(str(i))
        parts.append(c.timestamp)
        parts.append(c.text)
        parts.append("")  # blank separator
    body = "\n".join(parts).rstrip() + "\n"
    return ("\ufeff" + body) if write_bom else body


# ──────────────────────────────────────────────────────────────────────
# Correction engine
# ──────────────────────────────────────────────────────────────────────
@dataclass
class Correction:
    cue_index: int
    rule_id: str
    category: str
    before: str
    after: str
    confidence: float
    rationale: str
    applied: bool
    flag_reason: str | None = None
    snippet_before: str = ""
    snippet_after: str = ""


def _context_matches(cues: list[Cue], idx: int, window: int,
                     tokens_before: tuple[str, ...],
                     tokens_after: tuple[str, ...]) -> bool:
    """Return True iff a context-conditional rule's preconditions hold.

    Rule fires when:
      - there are no context requirements at all, OR
      - any context token appears in the current cue, OR
      - a tokens_before term appears in one of the `window` preceding
        cues, OR
      - a tokens_after term appears in one of the `window` following
        cues.

    The current-cue check is what lets a single-cue mention like
    'Solaoide a scris despre Hristos, lumina lumii' trigger the
    Ellen White flag without needing extra cues around it."""
    if not tokens_before and not tokens_after:
        return True
    lows = [c.text.lower() for c in cues]
    all_tokens = tokens_before + tokens_after
    if any(tok in lows[idx] for tok in all_tokens):
        return True
    if tokens_before:
        for j in range(max(0, idx - window), idx):
            if any(tok in lows[j] for tok in tokens_before):
                return True
    if tokens_after:
        for j in range(idx + 1, min(len(cues), idx + window + 1)):
            if any(tok in lows[j] for tok in tokens_after):
                return True
    return False


def _apply_rules(cues: list[Cue], rules: tuple[Rule, ...], *,
                 context_window: int,
                 min_confidence_auto_fix: float) -> list[Correction]:
    out: list[Correction] = []
    for i, cue in enumerate(cues):
        for rule in rules:
            if rule.context_before or rule.context_after:
                if not _context_matches(cues, i, context_window,
                                        rule.context_before, rule.context_after):
                    continue
            matches = list(rule.pattern.finditer(cue.text))
            if not matches:
                continue
            # Build the replacement text once per cue per rule.
            new_text = rule.pattern.sub(rule.replacement, cue.text)
            if new_text == cue.text:
                continue  # replacement equals original (no-op)
            applied = rule.confidence >= min_confidence_auto_fix
            flag_reason = None if applied else (
                f"confidence {rule.confidence:.2f} below threshold "
                f"{min_confidence_auto_fix:.2f}"
            )
            out.append(Correction(
                cue_index=cue.index,
                rule_id=rule.id,
                category=rule.category,
                before=matches[0].group(0),
                after=rule.pattern.sub(rule.replacement, matches[0].group(0)),
                confidence=rule.confidence,
                rationale=rule.rationale,
                applied=applied,
                flag_reason=flag_reason,
                snippet_before=cue.text,
                snippet_after=new_text,
            ))
            if applied:
                cue.text = new_text
    return out


def _load_overlay(path: Path) -> tuple[Rule, ...]:
    """Load operator-supplied rule overlay from JSON.

    Each entry: {id, category, pattern, replacement, confidence,
                 rationale, context_before?: [...], context_after?: [...],
                 flags?: "i"}  (flags="i" → IGNORECASE)
    """
    if not path.exists():
        return ()
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        raise ValueError(f"library_path parse error: {exc}") from exc
    if not isinstance(data, list):
        raise ValueError("library_path must be a JSON array of rule objects")
    built: list[Rule] = []
    for i, r in enumerate(data):
        try:
            flags = re.IGNORECASE if r.get("flags") == "i" else 0
            built.append(Rule(
                id=str(r["id"]),
                category=str(r.get("category", "operator-overlay")),
                pattern=re.compile(r["pattern"], flags),
                replacement=str(r["replacement"]),
                confidence=float(r.get("confidence", 0.9)),
                rationale=str(r.get("rationale", "operator overlay rule")),
                context_before=tuple(s.lower() for s in r.get("context_before", [])),
                context_after=tuple(s.lower() for s in r.get("context_after", [])),
            ))
        except Exception as exc:
            raise ValueError(f"overlay rule #{i} invalid: {exc}") from exc
    return tuple(built)


def _resolve_source(payload: dict[str, Any], data_root: Path) -> Path | dict:
    stem = payload.get("stem")
    srt_path = payload.get("srt_path")
    if bool(stem) == bool(srt_path):
        return {"status": "error", "handler": "correct_ro_theological",
                "error": "exactly_one_of_stem_or_srt_path_required"}
    if stem:
        stem = Path(str(stem)).name
        base = data_root / "transcripts" / stem
        for candidate in (base / "transcript.cues.srt", base / "transcript.srt"):
            if candidate.exists():
                return candidate
        return {"status": "error", "handler": "correct_ro_theological",
                "error": "srt_not_found_for_stem",
                "searched": [str(base / "transcript.cues.srt"),
                             str(base / "transcript.srt")]}
    # srt_path: resolve under DATA_ROOT to prevent traversal.
    requested = Path(str(srt_path))
    candidate = (data_root / requested).resolve() if not requested.is_absolute() \
        else requested.resolve()
    root_resolved = data_root.resolve()
    try:
        candidate.relative_to(root_resolved)
    except ValueError:
        return {"status": "error", "handler": "correct_ro_theological",
                "error": "srt_path_outside_data_root",
                "data_root": str(root_resolved)}
    if not candidate.exists():
        return {"status": "error", "handler": "correct_ro_theological",
                "error": "srt_path_not_found", "path": str(candidate)}
    return candidate


async def correct_ro_theological(payload: dict[str, Any], data_root: Path) -> dict:
    """Apply RO theological ASR corrections. Determinstic, no LLM."""
    resolved = _resolve_source(payload, data_root)
    if isinstance(resolved, dict):
        return resolved
    src: Path = resolved

    context_window = int(payload.get("context_window", 2))
    min_conf = float(payload.get("min_confidence_auto_fix", 0.85))
    write_bom = bool(payload.get("output_bom", True))

    overlay_path = payload.get("library_path")
    overlay_rules: tuple[Rule, ...] = ()
    if overlay_path:
        try:
            overlay_rules = _load_overlay(Path(str(overlay_path)))
        except ValueError as exc:
            return {"status": "error", "handler": "correct_ro_theological",
                    "error": "overlay_invalid", "detail": str(exc)}

    try:
        raw = src.read_text(encoding="utf-8")
    except Exception as exc:
        return {"status": "error", "handler": "correct_ro_theological",
                "error": "read_failed", "detail": str(exc), "path": str(src)}

    cues = _parse_srt(raw)
    if not cues:
        return {"status": "error", "handler": "correct_ro_theological",
                "error": "no_cues_parsed", "path": str(src),
                "hint": "file may not be a valid SRT"}

    original_texts = [c.text for c in cues]  # for the log
    corrections = _apply_rules(
        cues, BUILTIN_RULES + overlay_rules,
        context_window=context_window,
        min_confidence_auto_fix=min_conf,
    )

    applied_count = sum(1 for c in corrections if c.applied)
    flagged = [c for c in corrections if not c.applied]

    clean_path = src.with_name(src.stem + ".clean" + src.suffix)
    log_path = src.with_name(src.stem + ".corrections.log")
    json_path = src.with_name(src.stem + ".corrections.json")

    clean_path.write_text(_serialize_srt(cues, write_bom=write_bom),
                          encoding="utf-8")

    # Human-readable audit.
    log_lines: list[str] = [
        f"# corrections audit for {src.name}",
        f"# rules: builtin={len(BUILTIN_RULES)} overlay={len(overlay_rules)}",
        f"# cues: {len(cues)} · applied: {applied_count} · flagged: {len(flagged)}",
        f"# min_confidence_auto_fix: {min_conf}",
        "",
    ]
    for c in corrections:
        status = "APPLIED" if c.applied else "FLAGGED"
        log_lines.append(
            f"cue {c.cue_index:>4} [{status}] {c.rule_id} ({c.category}) "
            f"conf={c.confidence:.2f}"
        )
        log_lines.append(f"    — {c.rationale}")
        log_lines.append(f"    - {c.before!r}")
        log_lines.append(f"    + {c.after!r}")
        if c.flag_reason:
            log_lines.append(f"    ! {c.flag_reason}")
        log_lines.append("")
    log_path.write_text("\n".join(log_lines), encoding="utf-8")

    # Machine-readable audit.
    json_path.write_text(json.dumps({
        "source": str(src),
        "clean": str(clean_path),
        "cues": len(cues),
        "applied_count": applied_count,
        "flagged_count": len(flagged),
        "min_confidence_auto_fix": min_conf,
        "corrections": [
            {
                "cue": c.cue_index, "rule_id": c.rule_id, "category": c.category,
                "before": c.before, "after": c.after,
                "confidence": c.confidence, "rationale": c.rationale,
                "applied": c.applied, "flag_reason": c.flag_reason,
            }
            for c in corrections
        ],
    }, ensure_ascii=False, indent=2), encoding="utf-8")

    # Summarise flags by cue for the dashboard / operator.
    flag_digest = [
        {
            "cue": c.cue_index,
            "rule_id": c.rule_id,
            "suggested": c.after,
            "current": c.before,
            "confidence": c.confidence,
            "rationale": c.rationale,
        }
        for c in sorted(flagged, key=lambda x: -x.confidence)
    ]

    return {
        "status": "success",
        "handler": "correct_ro_theological",
        "source": str(src),
        "clean": str(clean_path),
        "log": str(log_path),
        "json_audit": str(json_path),
        "cues": len(cues),
        "applied_count": applied_count,
        "flagged_count": len(flagged),
        "flags": flag_digest,
        "unchanged_cue_count": sum(
            1 for i, c in enumerate(cues) if c.text == original_texts[i]
        ),
        "rules_total": len(BUILTIN_RULES) + len(overlay_rules),
    }
