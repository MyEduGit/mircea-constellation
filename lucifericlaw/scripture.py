"""Scripture loader — pulls canonical passages from URANTiOS.

LuciferiClaw doctrine is not invented by the engineer. Every adjudication
principle has a citation in The Urantia Book. This module loads the
canonical text from the URANTiOS repo (or a bundled fallback copy) so
the rules can quote scripture in every verdict.

Grounding papers:
    53 — The Lucifer Rebellion (the case study)
    54 — Problems of the Lucifer Rebellion (the procedure & the technique)
    45 — The Constellation Government (jurisdictional context)
    67 — The Planetary Rebellion (Caligastia: how an instance plays out)
"""
from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

# ── Source candidates, in priority order ───────────────────────────────
_CANDIDATE_ROOTS = [
    os.environ.get("URANTIOS_BOOK_DIR"),
    str(Path.home() / "URANTiOS" / "urantia-book"),
    str(Path.home() / "Code" / "URANTiOS" / "urantia-book"),
    "/home/user/URANTiOS/urantia-book",
    str(Path(__file__).parent / "scriptures"),  # bundled fallback
]

GROUNDING_PAPERS = {
    53: "The Lucifer Rebellion",
    54: "Problems of the Lucifer Rebellion",
    45: "The Constellation Government",
    67: "The Planetary Rebellion",
}


def find_book_root() -> Path | None:
    for c in _CANDIDATE_ROOTS:
        if not c:
            continue
        p = Path(c)
        if (p / "Doc053.json").exists():
            return p
    return None


def load_paper(paper_index: int) -> dict[str, Any] | None:
    """Load a single paper. Returns None if the source is unavailable."""
    root = find_book_root()
    if root is None:
        return None
    path = root / f"Doc{paper_index:03d}.json"
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text())
    except (OSError, json.JSONDecodeError):
        return None


def quote(par_ref: str) -> str | None:
    """Return the text of a paragraph by ref, e.g. '53:3.2'.

    par_ref format: 'PAPER:SECTION.PAR' — '53:3.2' = paper 53, section 3, par 2.
    Returns None if the source is unavailable.
    """
    try:
        paper_str, rest = par_ref.split(":", 1)
        paper_index = int(paper_str)
    except (ValueError, IndexError):
        return None
    paper = load_paper(paper_index)
    if not paper:
        return None
    for section in paper.get("sections", []):
        for par in section.get("pars", []):
            if par.get("par_ref") == par_ref:
                return par.get("par_content")
    return None


def section(section_ref: str) -> list[dict[str, str]] | None:
    """Return the paragraphs of a section, e.g. '53:3' returns the manifesto.

    Returns list of {"par_ref": ..., "par_content": ...} or None if missing.
    """
    try:
        paper_str, _ = section_ref.split(":", 1)
        paper_index = int(paper_str)
    except (ValueError, IndexError):
        return None
    paper = load_paper(paper_index)
    if not paper:
        return None
    for s in paper.get("sections", []):
        if s.get("section_ref") == section_ref:
            return [
                {"par_ref": p.get("par_ref"), "par_content": p.get("par_content")}
                for p in s.get("pars", [])
            ]
    return None


def doctrine_status() -> dict[str, Any]:
    """Report whether scripture is reachable. Truth: never claim more than proof."""
    root = find_book_root()
    if root is None:
        return {"available": False, "root": None,
                "papers_present": [], "missing": list(GROUNDING_PAPERS.keys())}
    present, missing = [], []
    for idx in GROUNDING_PAPERS:
        if (root / f"Doc{idx:03d}.json").exists():
            present.append(idx)
        else:
            missing.append(idx)
    return {"available": True, "root": str(root),
            "papers_present": present, "missing": missing}
