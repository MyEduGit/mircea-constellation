#!/usr/bin/env python3
"""
ingest_amep.py — Cognee ingest for the AMEP AI Literacy Manual

Ingests all 26 markdown files from the amep-ai-literacy/ tree into
Cognee under the DATASET_AMEP dataset, tagging each node with:
  - book:student | book:teacher | book:both
  - module:<n> (for module files)
  - type:<module|glossary|appendix|front-matter>
  - cefr:<level> (one tag per CEFR level)

Usage (from repo root):
    python3 -m amep-ai-literacy.ingest_amep
    python3 amep-ai-literacy/ingest_amep.py
    python3 amep-ai-literacy/ingest_amep.py --dry-run

Requires cognee_config.py to be on PYTHONPATH (it lives at repo root).
Activate the Cognee venv first:
    source ~/.cognee-env/bin/activate

UrantiOS governed — Truth, Beauty, Goodness.
"""
from __future__ import annotations

import argparse
import asyncio
import hashlib
import sys
from pathlib import Path

# ── Path setup ────────────────────────────────────────────────────────────────
REPO_ROOT = Path(__file__).resolve().parent.parent
AMEP_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(REPO_ROOT))

# ── File manifest — 26 files, explicit and auditable ─────────────────────────
# Each entry: (relative_path, book, type, module_num_or_None, [cefr_levels])
MANIFEST: list[tuple[str, str, str, int | None, list[str]]] = [
    # Front matter
    ("00-front-matter.md", "both", "front-matter", None, ["Pre-A1", "A1", "A2", "B1"]),
    # Student Book
    ("student-book/S-01-what-is-ai.md",          "student", "module",  1,    ["Pre-A1", "A1"]),
    ("student-book/S-02-opening-claude.md",       "student", "module",  2,    ["A1"]),
    ("student-book/S-03-voice-mode.md",           "student", "module",  3,    ["A1"]),
    ("student-book/S-04-english-practice.md",     "student", "module",  4,    ["A2"]),
    ("student-book/S-05-real-life.md",            "student", "module",  5,    ["A2"]),
    ("student-book/S-06-web-search.md",           "student", "module",  6,    ["A2", "B1"]),
    ("student-book/S-07-claude-chrome.md",        "student", "module",  7,    ["B1"]),
    ("student-book/S-08-cowork.md",               "student", "module",  8,    ["B1"]),
    ("student-book/S-09-claude-code-optional.md", "student", "module",  9,    ["B1"]),
    ("student-book/S-10-ethics-privacy-future.md","student", "module",  10,   ["Pre-A1", "A1", "A2", "B1"]),
    ("student-book/S-glossary.md",                "student", "glossary",None, ["Pre-A1", "A1", "A2", "B1"]),
    # Teacher's Book
    ("teacher-book/T-01-what-is-ai.md",           "teacher", "module",  1,    ["Pre-A1", "A1"]),
    ("teacher-book/T-02-opening-claude.md",        "teacher", "module",  2,    ["A1"]),
    ("teacher-book/T-03-voice-mode.md",            "teacher", "module",  3,    ["A1"]),
    ("teacher-book/T-04-english-practice.md",      "teacher", "module",  4,    ["A2"]),
    ("teacher-book/T-05-real-life.md",             "teacher", "module",  5,    ["A2"]),
    ("teacher-book/T-06-web-search.md",            "teacher", "module",  6,    ["A2", "B1"]),
    ("teacher-book/T-07-claude-chrome.md",         "teacher", "module",  7,    ["B1"]),
    ("teacher-book/T-08-cowork.md",                "teacher", "module",  8,    ["B1"]),
    ("teacher-book/T-09-claude-code-optional.md",  "teacher", "module",  9,    ["B1"]),
    ("teacher-book/T-10-ethics-privacy-future.md", "teacher", "module",  10,   ["Pre-A1", "A1", "A2", "B1"]),
    # Appendices
    ("appendices/appendix-A-pd-primer.md",         "teacher", "appendix",None, ["Pre-A1", "A1", "A2", "B1"]),
    ("appendices/appendix-B-teacher-faq.md",       "teacher", "appendix",None, ["Pre-A1", "A1", "A2", "B1"]),
    ("appendices/appendix-C-cheat-sheets.md",      "both",    "appendix",None, ["Pre-A1", "A1", "A2", "B1"]),
    ("appendices/appendix-D-worksheets.md",        "both",    "appendix",None, ["Pre-A1", "A1", "A2", "B1"]),
]

assert len(MANIFEST) == 26, f"Expected 26 files, got {len(MANIFEST)}"


def _node_set(
    path: str,
    book: str,
    doc_type: str,
    module: int | None,
    cefr: list[str],
    sha: str,
) -> list[str]:
    tags = [
        "source:amep_ai_literacy",
        f"book:{book}",
        f"type:{doc_type}",
        f"sha256:{sha}",
        f"file:{Path(path).name}",
    ]
    if module is not None:
        tags.append(f"module:{module}")
    for level in cefr:
        tags.append(f"cefr:{level}")
    return tags


async def ingest(dry_run: bool = False) -> dict:
    import cognee
    import cognee_config

    cfg = cognee_config.init(verbose=True)
    dataset = cognee_config.DATASET_AMEP

    results = {"ingested": 0, "skipped": 0, "errors": [], "dataset": dataset}

    for rel_path, book, doc_type, module, cefr in MANIFEST:
        full_path = AMEP_ROOT / rel_path
        if not full_path.exists():
            results["errors"].append({"file": rel_path, "error": "file_not_found"})
            print(f"  MISSING: {rel_path}")
            continue

        content = full_path.read_text(encoding="utf-8")
        sha = hashlib.sha256(content.encode("utf-8")).hexdigest()
        node_set = _node_set(rel_path, book, doc_type, module, cefr, sha)

        label = f"{rel_path} ({doc_type}, book={book})"
        if dry_run:
            print(f"  [DRY-RUN] would ingest: {label}")
            print(f"    sha256={sha[:12]}  nodes={node_set[:4]}...")
            results["ingested"] += 1
            continue

        try:
            await cognee.add(content, dataset_name=dataset, node_set=node_set)
            print(f"  OK: {label}")
            results["ingested"] += 1
        except Exception as exc:
            results["errors"].append({"file": rel_path, "error": str(exc)})
            print(f"  ERROR: {label} — {exc}")

    return results


def main() -> int:
    parser = argparse.ArgumentParser(
        prog="ingest_amep",
        description="Ingest the AMEP AI Literacy Manual into Cognee.",
    )
    parser.add_argument(
        "--dry-run", action="store_true",
        help="Print what would be ingested without writing to Cognee.",
    )
    args = parser.parse_args()

    print()
    print("=" * 60)
    print("  AMEP AI Literacy — Cognee Ingest")
    print(f"  {'DRY RUN — ' if args.dry_run else ''}26 files → amep_ai_literacy")
    print("=" * 60)
    print()

    result = asyncio.run(ingest(dry_run=args.dry_run))

    print()
    print("=" * 60)
    print(f"  Ingested: {result['ingested']}")
    print(f"  Errors:   {len(result['errors'])}")
    if result["errors"]:
        for e in result["errors"]:
            print(f"    - {e['file']}: {e['error']}")
    print(f"  Dataset:  {result['dataset']}")
    print("=" * 60)
    print()

    return 0 if not result["errors"] else 1


if __name__ == "__main__":
    sys.exit(main())
