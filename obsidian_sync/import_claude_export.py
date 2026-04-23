#!/usr/bin/env python3
"""
Import a claude.ai "Export Data" ZIP into an Obsidian vault folder.

Claude.ai → Settings → Privacy → Export Data emails a ZIP with 24-hour expiry.
The ZIP contains conversations.json (and usually projects.json, users.json).
conversations.json is an array of conversations; each has a chat_messages list.

This script writes one Markdown file per conversation to the target folder,
with YAML frontmatter, and is idempotent: if a file with the same UUID-derived
name already exists AND has the same updated_at, it is skipped.

Usage:
    python3 import_claude_export.py <export.zip> <target_folder>

Example (on the Mac):
    python3 import_claude_export.py \\
        ~/Downloads/data-2026-04-21-01-02-03.zip \\
        "~/Library/Mobile Documents/iCloud~md~obsidian/Documents/Urantia-Vault/Claude-Archive/claude-chat"
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import zipfile
from datetime import datetime, timezone
from pathlib import Path


SAFE_CHARS = re.compile(r"[^A-Za-z0-9._\- ]+")


def slugify(title: str, max_len: int = 80) -> str:
    title = (title or "untitled").strip()
    title = SAFE_CHARS.sub("-", title)
    title = re.sub(r"-+", "-", title).strip("-._ ")
    if not title:
        title = "untitled"
    return title[:max_len]


def iso_to_aest_date(iso: str | None) -> str:
    if not iso:
        return "unknown-date"
    try:
        dt = datetime.fromisoformat(iso.replace("Z", "+00:00"))
    except ValueError:
        return "unknown-date"
    return dt.astimezone(timezone.utc).strftime("%Y-%m-%d")


def render_message(msg: dict) -> str:
    sender = msg.get("sender") or msg.get("role") or "unknown"
    created = msg.get("created_at") or ""
    parts: list[str] = []
    text = msg.get("text")
    if text:
        parts.append(text)
    for content in msg.get("content") or []:
        ctype = content.get("type")
        if ctype == "text":
            t = content.get("text")
            if t and t not in parts:
                parts.append(t)
        elif ctype == "tool_use":
            name = content.get("name", "tool")
            parts.append(f"*[tool call: {name}]*")
        elif ctype == "tool_result":
            parts.append(f"*[tool result]*")
    for attach in msg.get("attachments") or []:
        name = attach.get("file_name") or "attachment"
        parts.append(f"*[attached: {name}]*")
    body = "\n\n".join(p for p in parts if p).strip() or "*(empty)*"
    header = f"### {sender}"
    if created:
        header += f"  \n*{created}*"
    return f"{header}\n\n{body}\n"


def conversation_to_markdown(conv: dict) -> tuple[str, str]:
    uuid = conv.get("uuid") or ""
    name = conv.get("name") or "Untitled conversation"
    created = conv.get("created_at") or ""
    updated = conv.get("updated_at") or created
    messages = conv.get("chat_messages") or []

    date_prefix = iso_to_aest_date(created)
    slug = slugify(name)
    short_uuid = (uuid or "").split("-")[0] or "no-uuid"
    filename = f"{date_prefix}-{slug}-{short_uuid}.md"

    fm_lines = [
        "---",
        "source: claude-chat",
        f"title: {json.dumps(name)}",
        f"uuid: {uuid}",
        f"created_at: {created}",
        f"updated_at: {updated}",
        f"message_count: {len(messages)}",
        "---",
        "",
        f"# {name}",
        "",
    ]
    body = "\n".join(render_message(m) for m in messages)
    return filename, "\n".join(fm_lines) + body + "\n"


def read_conversations(zip_path: Path) -> list[dict]:
    with zipfile.ZipFile(zip_path) as zf:
        candidates = [n for n in zf.namelist() if n.endswith("conversations.json")]
        if not candidates:
            sys.exit(f"ERROR: conversations.json not found in {zip_path}")
        # Prefer a top-level conversations.json if present.
        candidates.sort(key=len)
        with zf.open(candidates[0]) as f:
            data = json.load(f)
    if not isinstance(data, list):
        sys.exit("ERROR: conversations.json was not a JSON array")
    return data


def existing_updated_at(path: Path) -> str | None:
    try:
        with path.open("r", encoding="utf-8") as f:
            head = f.read(2048)
    except OSError:
        return None
    m = re.search(r"^updated_at:\s*(.+)$", head, re.MULTILINE)
    return m.group(1).strip() if m else None


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("zip_path", type=Path)
    ap.add_argument("target_folder", type=Path)
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    zip_path: Path = args.zip_path.expanduser()
    target: Path = args.target_folder.expanduser()

    if not zip_path.is_file():
        sys.exit(f"ERROR: zip not found: {zip_path}")
    if not args.dry_run:
        target.mkdir(parents=True, exist_ok=True)

    conversations = read_conversations(zip_path)
    written = skipped = 0
    for conv in conversations:
        filename, markdown = conversation_to_markdown(conv)
        out = target / filename
        incoming_updated = conv.get("updated_at") or conv.get("created_at") or ""
        if out.exists() and existing_updated_at(out) == incoming_updated:
            skipped += 1
            continue
        if args.dry_run:
            print(f"DRY: would write {out}")
        else:
            out.write_text(markdown, encoding="utf-8")
        written += 1

    print(f"Done. {written} written, {skipped} skipped (unchanged), {len(conversations)} total.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
