#!/usr/bin/env python3
"""Build the fine-tune dataset for OpenMythos (openmythos-urantia-770m).

Sources:
  1. UrantiPedia Obsidian vault (.md files) — 477 docs
  2. Urantia Book full text (if available as plain text or EPUB)
  3. mircea_corpus ingested JSONL (chatcode exports, classified docs)

Output:
  openmythos/finetune/data/train.jsonl   (~80%)
  openmythos/finetune/data/val.jsonl     (~10%)
  openmythos/finetune/data/test.jsonl    (~10%)

Each record is a JSON line with:
  {"prompt": "...", "completion": "...", "source": "...", "paper": N|null}

Target: ~50k pairs (Chinchilla-optimal for 770M at 1 epoch = 35M tokens).

Usage:
    python -m openmythos.finetune.build_dataset \\
        --vault /path/to/UrantiPedia \\
        --urantia-text /path/to/urantia_book.txt \\
        --corpus /opt/openclaw-data/classified \\
        --out openmythos/finetune/data \\
        --target 50000
"""
from __future__ import annotations

import argparse
import hashlib
import json
import logging
import random
import re
import sys
from pathlib import Path
from typing import Iterator

logger = logging.getLogger("openmythos.finetune.build_dataset")
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(name)s] %(message)s")

# ---------------------------------------------------------------------------
# Source readers
# ---------------------------------------------------------------------------

def _iter_vault_docs(vault_path: Path) -> Iterator[dict]:
    """Yield {text, source, paper} dicts from UrantiPedia Obsidian vault."""
    for md in sorted(vault_path.rglob("*.md")):
        if ".obsidian" in md.parts:
            continue
        try:
            text = md.read_text(encoding="utf-8", errors="replace").strip()
        except Exception as exc:
            logger.warning(f"vault: skip {md}: {exc}")
            continue
        if len(text) < 80:
            continue
        paper = _detect_paper_number(md.stem + " " + text[:200])
        yield {"text": text, "source": f"vault:{md.name}", "paper": paper}


def _iter_urantia_text(text_path: Path) -> Iterator[dict]:
    """Yield paragraphs from a plain-text Urantia Book, tagged by Paper number."""
    try:
        raw = text_path.read_text(encoding="utf-8", errors="replace")
    except Exception as exc:
        logger.warning(f"urantia text: {exc}")
        return

    current_paper: int | None = None
    buffer: list[str] = []

    for line in raw.splitlines():
        paper_match = re.match(r"^\s*PAPER\s+(\d+)", line, re.IGNORECASE)
        if paper_match:
            if buffer:
                yield {
                    "text": " ".join(buffer).strip(),
                    "source": "urantia_book",
                    "paper": current_paper,
                }
                buffer = []
            current_paper = int(paper_match.group(1))
            continue
        stripped = line.strip()
        if stripped:
            buffer.append(stripped)
        elif buffer and len(" ".join(buffer)) > 200:
            yield {
                "text": " ".join(buffer).strip(),
                "source": "urantia_book",
                "paper": current_paper,
            }
            buffer = []

    if buffer:
        yield {
            "text": " ".join(buffer).strip(),
            "source": "urantia_book",
            "paper": current_paper,
        }


def _iter_corpus_classified(classified_dir: Path) -> Iterator[dict]:
    """Yield text snippets from openclaw_ingest classified records."""
    for rec_path in sorted(classified_dir.glob("*.json")):
        try:
            rec = json.loads(rec_path.read_text())
        except Exception:
            continue
        # Only use canonical/active transparent docs
        axes = rec.get("axes", {})
        if axes.get("lucifer_test") == "flagged":
            continue
        if axes.get("goodness") == "serves_self":
            continue
        source_file = rec.get("source_file", rec_path.name)
        # The text itself is not in the classified record (only sha + axes);
        # try to find the original in ingested/chatcode/.
        ingested_path = classified_dir.parent / "ingested" / "chatcode" / source_file
        if not ingested_path.exists():
            continue
        try:
            text = ingested_path.read_text(encoding="utf-8", errors="replace").strip()
        except Exception:
            continue
        if len(text) < 80:
            continue
        paper = _detect_paper_number(text[:400])
        yield {"text": text, "source": f"corpus:{source_file}", "paper": paper}


def _detect_paper_number(text: str) -> int | None:
    m = re.search(r"\bPaper\s+(\d{1,3})\b", text, re.IGNORECASE)
    if m:
        n = int(m.group(1))
        if 0 <= n <= 196:
            return n
    return None


# ---------------------------------------------------------------------------
# Pair generators
# ---------------------------------------------------------------------------

_QUESTION_TEMPLATES = [
    "What is the central spiritual teaching of this passage?",
    "How does this text relate to the concept of God the Father in the Urantia Book?",
    "Summarise the main thesis of this passage in one sentence.",
    "What practical lesson does this passage offer for personal spiritual growth?",
    "How does this passage connect to the Foreword's definition of Deity?",
    "What does this passage say about the relationship between personality and spirit?",
    "How does this text illuminate the mission of The Urantia Book?",
    "What is the theological significance of this passage within its Paper context?",
    "How does this passage demonstrate Truth · Beauty · Goodness?",
    "What would Gabriel (the synthesizer) conclude from this passage?",
]

_FOREWORD_CONCEPTS = [
    "Deity", "Divinity", "God", "the Universal Father", "the Eternal Son",
    "the Infinite Spirit", "the Supreme Being", "personality", "reality levels",
    "the Trinity", "the Paradise Isle", "energy", "spirit", "mind",
    "the Absolutes", "cosmic mind", "the Master Universe",
]


def _make_qa_pairs(doc: dict, rng: random.Random, max_pairs: int = 3) -> list[dict]:
    text = doc["text"]
    source = doc["source"]
    paper = doc["paper"]
    pairs: list[dict] = []

    # 1. Generic Q&A
    for q in rng.sample(_QUESTION_TEMPLATES, min(max_pairs, len(_QUESTION_TEMPLATES))):
        pairs.append({
            "prompt": f"Context:\n{text[:3000]}\n\nQuestion: {q}",
            "completion": f"[Fine-tune target — model learns from corpus patterns]",
            "source": source,
            "paper": paper,
            "pair_type": "qa",
        })
        if len(pairs) >= max_pairs:
            break

    # 2. Concept extraction (if text mentions known Foreword concepts)
    for concept in rng.sample(_FOREWORD_CONCEPTS, min(4, len(_FOREWORD_CONCEPTS))):
        if concept.lower() in text.lower():
            pairs.append({
                "prompt": (
                    f"Context:\n{text[:2000]}\n\n"
                    f"How does this passage define or use the concept of '{concept}'?"
                ),
                "completion": "[Fine-tune target]",
                "source": source,
                "paper": paper,
                "pair_type": "concept_extraction",
            })
            if len(pairs) >= max_pairs + 2:
                break

    return pairs


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def build(
    vault_path: Path | None,
    urantia_text_path: Path | None,
    corpus_dir: Path | None,
    out_dir: Path,
    target: int,
    seed: int,
) -> dict:
    rng = random.Random(seed)
    out_dir.mkdir(parents=True, exist_ok=True)

    docs: list[dict] = []

    if vault_path and vault_path.is_dir():
        vault_docs = list(_iter_vault_docs(vault_path))
        logger.info(f"vault: {len(vault_docs)} docs")
        docs.extend(vault_docs)
    else:
        logger.warning("vault not provided or not found — skipping")

    if urantia_text_path and urantia_text_path.exists():
        ub_docs = list(_iter_urantia_text(urantia_text_path))
        logger.info(f"urantia_book: {len(ub_docs)} paragraphs")
        docs.extend(ub_docs)
    else:
        logger.warning("urantia text not provided or not found — skipping")

    if corpus_dir and corpus_dir.is_dir():
        corpus_docs = list(_iter_corpus_classified(corpus_dir))
        logger.info(f"corpus: {len(corpus_docs)} docs")
        docs.extend(corpus_docs)
    else:
        logger.warning("corpus dir not provided or not found — skipping")

    if not docs:
        logger.error("No source documents found. Provide at least one source.")
        return {"status": "error", "error": "no_source_documents"}

    logger.info(f"Total source docs: {len(docs)}")

    # Generate pairs
    all_pairs: list[dict] = []
    rng.shuffle(docs)
    for doc in docs:
        pairs = _make_qa_pairs(doc, rng, max_pairs=3)
        all_pairs.extend(pairs)
        if len(all_pairs) >= target * 2:
            break

    # Deduplicate by prompt hash
    seen: set[str] = set()
    unique: list[dict] = []
    for p in all_pairs:
        h = hashlib.sha256(p["prompt"].encode()).hexdigest()
        if h not in seen:
            seen.add(h)
            unique.append(p)

    rng.shuffle(unique)
    final = unique[:target]
    logger.info(f"Pairs after dedup + cap: {len(final)} (target={target})")

    # Split 80/10/10
    n = len(final)
    n_train = int(n * 0.8)
    n_val = int(n * 0.1)
    splits = {
        "train": final[:n_train],
        "val": final[n_train:n_train + n_val],
        "test": final[n_train + n_val:],
    }

    for split_name, records in splits.items():
        path = out_dir / f"{split_name}.jsonl"
        with open(path, "w", encoding="utf-8") as f:
            for rec in records:
                f.write(json.dumps(rec, ensure_ascii=False) + "\n")
        logger.info(f"  {split_name}: {len(records)} pairs → {path}")

    stats = {
        "status": "success",
        "total_pairs": len(final),
        "train": len(splits["train"]),
        "val": len(splits["val"]),
        "test": len(splits["test"]),
        "source_docs": len(docs),
        "out_dir": str(out_dir),
    }
    (out_dir / "stats.json").write_text(json.dumps(stats, indent=2))
    return stats


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Build OpenMythos fine-tune dataset from UrantiPedia + Urantia Book + corpus"
    )
    parser.add_argument("--vault", type=Path, default=None,
                        help="Path to UrantiPedia Obsidian vault directory")
    parser.add_argument("--urantia-text", type=Path, default=None,
                        help="Path to Urantia Book plain text file")
    parser.add_argument("--corpus", type=Path, default=None,
                        help="Path to openclaw_ingest /data/classified directory")
    parser.add_argument("--out", type=Path,
                        default=Path(__file__).parent / "data",
                        help="Output directory (default: openmythos/finetune/data/)")
    parser.add_argument("--target", type=int, default=50000,
                        help="Target number of Q&A pairs (default: 50000)")
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()

    result = build(
        vault_path=args.vault,
        urantia_text_path=args.urantia_text,
        corpus_dir=args.corpus,
        out_dir=args.out,
        target=args.target,
        seed=args.seed,
    )
    print(json.dumps(result, indent=2))
    return 0 if result.get("status") == "success" else 1


if __name__ == "__main__":
    sys.exit(main())
