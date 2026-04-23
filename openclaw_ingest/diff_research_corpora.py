#!/usr/bin/env python3
"""Deterministically diff the two approved research corpora.

Read-only inputs:
- /Users/mircea8me.com/Obsidian/UrantiPedia/03_PhD_Research
- /Users/mircea8me.com/Documents/Obsidian/PhD-Triune-Monism

Writes only:
- openclaw_ingest/out/research_corpora_diff.json
- openclaw_ingest/out/research_corpora_diff_summary.json

Standard library only. No network. No models. No vector stores. No Cognee.
"""

from __future__ import annotations

import hashlib
import json
import os
from collections import Counter
from pathlib import Path
from typing import Any


REPO_ROOT = Path("/Users/mircea8me.com/mircea-constellation")
PRIMARY_ROOT = Path("/Users/mircea8me.com/Obsidian/UrantiPedia/03_PhD_Research")
SECONDARY_ROOT = Path("/Users/mircea8me.com/Documents/Obsidian/PhD-Triune-Monism")

OUT_DIR = REPO_ROOT / "openclaw_ingest" / "out"
DIFF_PATH = OUT_DIR / "research_corpora_diff.json"
SUMMARY_PATH = OUT_DIR / "research_corpora_diff_summary.json"

SKIP_DIR_NAMES = frozenset(
    {
        ".git",
        ".obsidian",
        "__pycache__",
        "node_modules",
    }
)
SKIP_FILE_NAMES = frozenset(
    {
        ".DS_Store",
    }
)
GROUPS = (
    "only_in_primary",
    "only_in_secondary",
    "same_content",
    "different_content",
)


def stable_posix(path: Path) -> str:
    return path.as_posix()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def should_skip_dir(path: Path) -> bool:
    return path.name in SKIP_DIR_NAMES


def iter_files(root: Path) -> list[Path]:
    files: list[Path] = []
    resolved_root = root.resolve()
    for current_root, dir_names, file_names in os.walk(root):
        current = Path(current_root)
        dir_names[:] = sorted(
            dir_name
            for dir_name in dir_names
            if not should_skip_dir(current / dir_name)
        )
        for file_name in sorted(file_names):
            if file_name in SKIP_FILE_NAMES:
                continue
            path = current / file_name
            if path.is_symlink():
                continue
            try:
                resolved_path = path.resolve(strict=True)
                resolved_path.relative_to(resolved_root)
            except (OSError, ValueError):
                continue
            if path.is_file():
                files.append(path)
    return sorted(files, key=lambda path: stable_posix(path.relative_to(root)))


def file_record(path: Path, root: Path) -> dict[str, Any]:
    stat = path.stat()
    relative_path = path.relative_to(root)
    return {
        "absolute_path": stable_posix(path),
        "extension": path.suffix.lower(),
        "file_name": path.name,
        "mtime_epoch": int(stat.st_mtime),
        "relative_path": stable_posix(relative_path),
        "sha256": sha256_file(path),
        "size_bytes": stat.st_size,
    }


def scan_corpus(root: Path) -> tuple[dict[str, dict[str, Any]], list[dict[str, str]]]:
    records: dict[str, dict[str, Any]] = {}
    errors: list[dict[str, str]] = []

    if not root.exists() or not root.is_dir():
        errors.append(
            {
                "path": stable_posix(root),
                "error": "source_root_not_found_or_not_directory",
            }
        )
        return records, errors

    for path in iter_files(root):
        try:
            record = file_record(path, root)
            records[record["relative_path"]] = record
        except OSError as exc:
            errors.append({"path": stable_posix(path), "error": str(exc)})

    return records, errors


def compare_records(
    primary: dict[str, dict[str, Any]],
    secondary: dict[str, dict[str, Any]],
) -> dict[str, list[dict[str, Any]]]:
    grouped: dict[str, list[dict[str, Any]]] = {group: [] for group in GROUPS}

    for relative_path in sorted(set(primary) | set(secondary)):
        primary_record = primary.get(relative_path)
        secondary_record = secondary.get(relative_path)

        if primary_record and not secondary_record:
            grouped["only_in_primary"].append(
                {
                    "relative_path": relative_path,
                    "primary": primary_record,
                    "secondary": None,
                }
            )
            continue

        if secondary_record and not primary_record:
            grouped["only_in_secondary"].append(
                {
                    "relative_path": relative_path,
                    "primary": None,
                    "secondary": secondary_record,
                }
            )
            continue

        if primary_record is None or secondary_record is None:
            raise RuntimeError(f"unreachable comparison state for {relative_path}")

        group = (
            "same_content"
            if primary_record["sha256"] == secondary_record["sha256"]
            else "different_content"
        )
        grouped[group].append(
            {
                "relative_path": relative_path,
                "primary": primary_record,
                "secondary": secondary_record,
            }
        )

    return grouped


def write_json(path: Path, data: dict[str, Any]) -> None:
    path.write_text(
        json.dumps(data, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def main() -> int:
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    primary_records, primary_errors = scan_corpus(PRIMARY_ROOT)
    secondary_records, secondary_errors = scan_corpus(SECONDARY_ROOT)
    grouped = compare_records(primary_records, secondary_records)

    errors = {
        "primary": primary_errors,
        "secondary": secondary_errors,
    }
    counts = {group: len(grouped[group]) for group in GROUPS}
    primary_extensions = Counter(
        record["extension"] or "<none>" for record in primary_records.values()
    )
    secondary_extensions = Counter(
        record["extension"] or "<none>" for record in secondary_records.values()
    )

    diff = {
        "schema_version": "1.0",
        "primary_root": stable_posix(PRIMARY_ROOT),
        "secondary_root": stable_posix(SECONDARY_ROOT),
        "groups": grouped,
        "errors": errors,
    }
    summary = {
        "schema_version": "1.0",
        "primary_root": stable_posix(PRIMARY_ROOT),
        "secondary_root": stable_posix(SECONDARY_ROOT),
        "diff_path": stable_posix(DIFF_PATH),
        "summary_path": stable_posix(SUMMARY_PATH),
        "total_primary_files": len(primary_records),
        "total_secondary_files": len(secondary_records),
        "total_compared_relative_paths": len(set(primary_records) | set(secondary_records)),
        "total_primary_bytes": sum(
            record["size_bytes"] for record in primary_records.values()
        ),
        "total_secondary_bytes": sum(
            record["size_bytes"] for record in secondary_records.values()
        ),
        "classification_counts": counts,
        "primary_extensions": dict(sorted(primary_extensions.items())),
        "secondary_extensions": dict(sorted(secondary_extensions.items())),
        "error_count": len(primary_errors) + len(secondary_errors),
        "errors": errors,
    }

    write_json(DIFF_PATH, diff)
    write_json(SUMMARY_PATH, summary)

    print(f"diff:    {DIFF_PATH}")
    print(f"summary: {SUMMARY_PATH}")
    print(f"primary files:   {len(primary_records)}")
    print(f"secondary files: {len(secondary_records)}")
    print(f"errors:          {summary['error_count']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
