#!/usr/bin/env python3
"""Validate channels/jabbokriver/catalog.yaml against catalog.schema.json.

Exits 0 on success, non-zero on failure. Prints the first few errors.

Usage:
  python channels/jabbokriver/tools/validate_catalog.py
  python channels/jabbokriver/tools/validate_catalog.py <path/to/catalog.yaml>

Dependencies (install hints printed if missing):
  pip install pyyaml jsonschema
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
CHANNEL_DIR = HERE.parent
DEFAULT_CATALOG = CHANNEL_DIR / "catalog.yaml"
SCHEMA = CHANNEL_DIR / "schema" / "catalog.schema.json"


def _die(msg: str, code: int = 1) -> None:
    print(f"[validate_catalog] {msg}", file=sys.stderr)
    sys.exit(code)


def main() -> int:
    try:
        import yaml
    except ImportError:
        _die("PyYAML is required. Install with: pip install pyyaml")

    try:
        import jsonschema
    except ImportError:
        _die("jsonschema is required. Install with: pip install jsonschema")

    catalog_path = Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_CATALOG
    if not catalog_path.exists():
        _die(f"catalog not found: {catalog_path}")
    if not SCHEMA.exists():
        _die(f"schema not found: {SCHEMA}")

    with catalog_path.open("r", encoding="utf-8") as f:
        data = yaml.safe_load(f)
    schema = json.loads(SCHEMA.read_text(encoding="utf-8"))

    validator = jsonschema.Draft202012Validator(schema)
    errors = sorted(validator.iter_errors(data), key=lambda e: list(e.absolute_path))
    if errors:
        print(f"[validate_catalog] {len(errors)} error(s) in {catalog_path}:", file=sys.stderr)
        for e in errors[:10]:
            loc = "/".join(str(p) for p in e.absolute_path) or "<root>"
            print(f"  - {loc}: {e.message}", file=sys.stderr)
        if len(errors) > 10:
            print(f"  ... and {len(errors) - 10} more", file=sys.stderr)
        return 1

    entries = data.get("entries", [])
    print(f"[validate_catalog] OK — {catalog_path} ({len(entries)} entries)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
