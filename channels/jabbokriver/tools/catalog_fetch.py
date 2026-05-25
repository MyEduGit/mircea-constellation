#!/usr/bin/env python3
"""Archive the public source videos listed in catalog.yaml.

Safety posture:
  - Dry-run by default. Pass --execute to actually invoke yt-dlp.
  - Never uploads anything.
  - Refuses to run without yt-dlp on PATH (with an install hint).
  - Writes attribution sidecars; updates state.json beside the catalog.

The public-channel videos this script archives are NOT re-uploaded to
JabbokRiverProductions. They are pulled for transcription and editorial
commentary only. See channels/jabbokriver/README.md for the policy.

Usage:
  # Dry-run — prints the yt-dlp commands it would run, touches nothing.
  python channels/jabbokriver/tools/catalog_fetch.py

  # Actually archive.
  python channels/jabbokriver/tools/catalog_fetch.py --execute

Dependencies:
  pip install pyyaml
  yt-dlp must be on PATH.
"""
from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
CHANNEL_DIR = HERE.parent
DEFAULT_CATALOG = CHANNEL_DIR / "catalog.yaml"
DEFAULT_STATE = CHANNEL_DIR / "state.json"
DEFAULT_MEDIA_ROOT = Path("/opt/scribeclaw-data/media/in")


def _die(msg: str, code: int = 1) -> None:
    print(f"[catalog_fetch] {msg}", file=sys.stderr)
    sys.exit(code)


def _load_state(path: Path) -> dict:
    if not path.exists():
        return {"fetched": {}}
    return json.loads(path.read_text(encoding="utf-8"))


def _save_state(path: Path, state: dict) -> None:
    path.write_text(json.dumps(state, indent=2, ensure_ascii=False), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(prog="catalog_fetch")
    parser.add_argument("--catalog", default=str(DEFAULT_CATALOG))
    parser.add_argument(
        "--media-root", default=str(DEFAULT_MEDIA_ROOT),
        help=f"destination for downloaded files (default: {DEFAULT_MEDIA_ROOT})",
    )
    parser.add_argument(
        "--execute", action="store_true",
        help="actually run yt-dlp (default: dry-run; prints commands only)",
    )
    parser.add_argument(
        "--state", default=str(DEFAULT_STATE),
        help=f"state file tracking id→filename (default: {DEFAULT_STATE})",
    )
    args = parser.parse_args()

    try:
        import yaml
    except ImportError:
        _die("PyYAML required. pip install pyyaml")

    catalog_path = Path(args.catalog)
    if not catalog_path.exists():
        _die(f"catalog not found: {catalog_path}")
    data = yaml.safe_load(catalog_path.read_text(encoding="utf-8"))
    entries = data.get("entries") or []

    media_root = Path(args.media_root)
    if args.execute:
        if shutil.which("yt-dlp") is None:
            _die("yt-dlp not on PATH. Install: pip install yt-dlp  (or) apt install yt-dlp")
        media_root.mkdir(parents=True, exist_ok=True)

    state = _load_state(Path(args.state))
    mode = "EXECUTE" if args.execute else "DRY-RUN"
    print(f"[catalog_fetch] mode={mode}  media_root={media_root}  entries={len(entries)}")

    queued = 0
    skipped = 0
    for entry in entries:
        eid = entry.get("id", "")
        url = (entry.get("source_url") or "").strip()
        status = entry.get("download_status", "pending")
        if status != "pending":
            skipped += 1
            continue
        if not url:
            print(f"  skip  {eid}: empty source_url (likely operator-held; import manually)")
            skipped += 1
            continue

        template = str(media_root / f"{eid}.%(ext)s")
        cmd = ["yt-dlp", "-o", template, "--no-playlist", "--", url]
        print(f"  plan  {eid}: {' '.join(cmd)}")

        if not args.execute:
            queued += 1
            continue

        rc = subprocess.call(cmd)
        if rc != 0:
            print(f"  FAIL  {eid}: yt-dlp exited {rc}")
            continue

        # Attribution sidecar — always.
        sidecar = media_root / f"{eid}.source.txt"
        sidecar.write_text(
            f"Source video archived for internal study + editorial commentary.\n"
            f"Source URL:     {url}\n"
            f"Source channel: {entry.get('source_channel', '')}\n"
            f"Host:           {entry.get('host', '')}\n"
            f"Title:          {entry.get('title', '')}\n"
            f"Pulled at:      {datetime.now(timezone.utc).isoformat()}\n"
            f"Publishing policy: catalog_and_link (no re-upload without rights).\n",
            encoding="utf-8",
        )
        state["fetched"][eid] = {
            "url": url,
            "media_root": str(media_root),
            "at": datetime.now(timezone.utc).isoformat(),
        }
        print(f"  OK    {eid}")
        queued += 1

    if args.execute:
        _save_state(Path(args.state), state)

    print(f"[catalog_fetch] done. queued={queued} skipped={skipped}")
    if not args.execute and queued:
        print("[catalog_fetch] pass --execute to actually archive.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
