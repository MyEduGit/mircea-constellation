#!/usr/bin/env python3
"""Build a deterministic local manifest for the UrantiPedia vault.

This script is intentionally boring:
- standard library only
- no network
- no models
- no vector stores
- no Cognee
- read-only against the source vault
- writes only the repo-local manifest and summary files
"""

from __future__ import annotations

import hashlib
import json
import os
import re
from collections import Counter
from pathlib import Path
from typing import Any


REPO_ROOT = Path("/Users/mircea8me.com/mircea-constellation")
SOURCE_VAULT = Path(
    "/Users/mircea8me.com/Library/Mobile Documents/iCloud~md~obsidian/Documents/UrantiPedia"
)
OUT_DIR = REPO_ROOT / "openclaw_ingest" / "out"
MANIFEST_PATH = OUT_DIR / "vault_manifest.jsonl"
SUMMARY_PATH = OUT_DIR / "vault_manifest_summary.json"

SKIP_DIR_NAMES = frozenset(
    {
        ".git",
        ".obsidian",
        ".trash",
        "__pycache__",
        "node_modules",
    }
)
SKIP_FILE_NAMES = frozenset(
    {
        ".DS_Store",
    }
)
TEXT_EXTENSIONS = frozenset(
    {
        ".md",
        ".markdown",
        ".txt",
        ".json",
        ".jsonl",
        ".csv",
        ".tsv",
        ".yaml",
        ".yml",
        ".toml",
    }
)
MARKDOWN_EXTENSIONS = frozenset({".md", ".markdown"})


def stable_posix(path: Path) -> str:
    """Return a stable POSIX-style path string."""
    return path.as_posix()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def decode_text(path: Path) -> tuple[str | None, str | None]:
    try:
        return path.read_text(encoding="utf-8"), None
    except UnicodeDecodeError as exc:
        return None, f"utf8_decode_error: {exc}"
    except OSError as exc:
        return None, f"read_error: {exc}"


def extract_frontmatter_keys(text: str) -> tuple[bool, list[str]]:
    if text.startswith("\ufeff"):
        text = text.removeprefix("\ufeff")
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return False, []

    end_index = None
    for index, line in enumerate(lines[1:], start=1):
        if line.strip() in {"---", "..."}:
            end_index = index
            break

    if end_index is None:
        return True, []

    keys: list[str] = []
    for line in lines[1:end_index]:
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        match = re.match(r"^([A-Za-z0-9_.-]+)\s*:", line)
        if match:
            keys.append(match.group(1))
    return True, sorted(set(keys))


def markdown_stats(text: str) -> dict[str, Any]:
    lines = text.splitlines()
    headings = [
        line.strip()
        for line in lines
        if re.match(r"^#{1,6}\s+\S", line)
    ]
    tags = re.findall(r"(?<!\w)#([A-Za-z0-9_/-]+)", text)
    wikilinks = re.findall(r"\[\[([^\]]+)\]\]", text)
    frontmatter_present, frontmatter_keys = extract_frontmatter_keys(text)

    return {
        "line_count": len(lines),
        "word_count": len(re.findall(r"\b\w+\b", text)),
        "heading_count": len(headings),
        "first_heading": headings[0].lstrip("#").strip() if headings else None,
        "wikilink_count": len(wikilinks),
        "tag_count": len(tags),
        "frontmatter_present": frontmatter_present,
        "frontmatter_keys": frontmatter_keys,
    }


def classify_kind(path: Path) -> str:
    suffix = path.suffix.lower()
    if suffix in MARKDOWN_EXTENSIONS:
        return "markdown"
    if suffix in TEXT_EXTENSIONS:
        return "text"
    return "binary_or_other"


def should_skip_dir(path: Path) -> bool:
    return path.name in SKIP_DIR_NAMES


def iter_files(root: Path) -> list[Path]:
    files: list[Path] = []
    resolved_root = root.resolve()
    for current_root, dir_names, file_names in os.walk(root):
        current = Path(current_root)
        dir_names[:] = sorted(
            d for d in dir_names if not should_skip_dir(current / d)
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
    return sorted(files, key=lambda p: stable_posix(p.relative_to(root)))


def error_record(path: Path, error: str) -> dict[str, Any]:
    relative_path = path.relative_to(SOURCE_VAULT)
    suffix = path.suffix.lower()
    return {
        "schema_version": "1.0",
        "source_vault": stable_posix(SOURCE_VAULT),
        "absolute_path": stable_posix(path),
        "vault_relative_path": stable_posix(relative_path),
        "file_name": path.name,
        "extension": suffix,
        "kind": classify_kind(path),
        "size_bytes": None,
        "mtime_epoch": None,
        "sha256": None,
        "line_count": 0,
        "word_count": 0,
        "heading_count": 0,
        "first_heading": None,
        "wikilink_count": 0,
        "tag_count": 0,
        "frontmatter_present": False,
        "frontmatter_keys": [],
        "scan_errors": [error],
    }


def build_record(path: Path) -> dict[str, Any]:
    try:
        stat = path.stat()
        file_sha256 = sha256_file(path)
    except OSError as exc:
        return error_record(path, str(exc))

    relative_path = path.relative_to(SOURCE_VAULT)
    suffix = path.suffix.lower()
    kind = classify_kind(path)
    errors: list[str] = []

    record: dict[str, Any] = {
        "schema_version": "1.0",
        "source_vault": stable_posix(SOURCE_VAULT),
        "absolute_path": stable_posix(path),
        "vault_relative_path": stable_posix(relative_path),
        "file_name": path.name,
        "extension": suffix,
        "kind": kind,
        "size_bytes": stat.st_size,
        "mtime_epoch": int(stat.st_mtime),
        "sha256": file_sha256,
        "line_count": 0,
        "word_count": 0,
        "heading_count": 0,
        "first_heading": None,
        "wikilink_count": 0,
        "tag_count": 0,
        "frontmatter_present": False,
        "frontmatter_keys": [],
        "scan_errors": errors,
    }

    if kind in {"markdown", "text"}:
        text, error = decode_text(path)
        if error:
            errors.append(error)
        elif text is not None:
            record.update(markdown_stats(text))

    return record


def write_json(path: Path, data: dict[str, Any]) -> None:
    path.write_text(
        json.dumps(data, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def main() -> int:
    if not SOURCE_VAULT.exists() or not SOURCE_VAULT.is_dir():
        raise SystemExit(f"source vault not found: {SOURCE_VAULT}")

    OUT_DIR.mkdir(parents=True, exist_ok=True)

    records = [build_record(path) for path in iter_files(SOURCE_VAULT)]
    with MANIFEST_PATH.open("w", encoding="utf-8") as handle:
        for record in records:
            handle.write(
                json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n"
            )

    extensions = Counter(record["extension"] or "<none>" for record in records)
    kinds = Counter(record["kind"] for record in records)
    error_count = sum(1 for record in records if record["scan_errors"])
    summary = {
        "schema_version": "1.0",
        "source_vault": stable_posix(SOURCE_VAULT),
        "manifest_path": stable_posix(MANIFEST_PATH),
        "summary_path": stable_posix(SUMMARY_PATH),
        "total_files": len(records),
        "total_bytes": sum(record["size_bytes"] or 0 for record in records),
        "error_count": error_count,
        "extensions": dict(sorted(extensions.items())),
        "kinds": dict(sorted(kinds.items())),
    }
    write_json(SUMMARY_PATH, summary)

    print(f"manifest: {MANIFEST_PATH}")
    print(f"summary:  {SUMMARY_PATH}")
    print(f"files:    {len(records)}")
    print(f"errors:   {error_count}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
