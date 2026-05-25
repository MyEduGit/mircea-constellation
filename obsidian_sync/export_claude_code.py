#!/usr/bin/env python3
"""
Harvest Claude Code sessions into an Obsidian vault folder.

Claude Code stores each session as a JSONL file under:
    ~/.claude/projects/<encoded-path>/<session-uuid>.jsonl

Each line is a JSON object with a type (user|assistant|system|summary) and
content. This script converts every session it can find into a Markdown file
and is idempotent: a session is skipped if the existing output file already
contains the same final event timestamp.

Usage:
    python3 export_claude_code.py <target_folder> [--projects-root DIR] [--since YYYY-MM-DD]

Example (on the Mac):
    python3 export_claude_code.py \\
        "~/Library/Mobile Documents/iCloud~md~obsidian/Documents/Urantia-Vault/Claude-Archive/claude-code"
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path


SAFE_CHARS = re.compile(r"[^A-Za-z0-9._\- ]+")


def slugify(title: str, max_len: int = 60) -> str:
    title = (title or "session").strip()
    title = SAFE_CHARS.sub("-", title)
    title = re.sub(r"-+", "-", title).strip("-._ ")
    return (title or "session")[:max_len]


def decode_project_path(dirname: str) -> str:
    # Claude Code encodes "/Users/foo/repo" as "-Users-foo-repo" (approx).
    return dirname.replace("-", "/")


def iso_date(iso: str | None) -> str:
    if not iso:
        return "unknown-date"
    try:
        dt = datetime.fromisoformat(iso.replace("Z", "+00:00"))
    except ValueError:
        return "unknown-date"
    return dt.astimezone(timezone.utc).strftime("%Y-%m-%d")


def extract_text(content) -> str:
    if content is None:
        return ""
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        out: list[str] = []
        for item in content:
            if not isinstance(item, dict):
                continue
            t = item.get("type")
            if t == "text":
                out.append(item.get("text", ""))
            elif t == "tool_use":
                out.append(f"*[tool call: {item.get('name','tool')}]*")
            elif t == "tool_result":
                inner = item.get("content")
                out.append(f"*[tool result]*\n{extract_text(inner)}" if inner else "*[tool result]*")
            elif t == "thinking":
                out.append(f"*[thinking]* {item.get('thinking','')}")
        return "\n\n".join(s for s in out if s)
    if isinstance(content, dict):
        return extract_text([content])
    return str(content)


def session_to_markdown(jsonl_path: Path) -> tuple[str | None, str, str]:
    """Return (filename, markdown, last_timestamp) or (None, "", "") if empty."""
    lines: list[dict] = []
    with jsonl_path.open("r", encoding="utf-8") as f:
        for raw in f:
            raw = raw.strip()
            if not raw:
                continue
            try:
                lines.append(json.loads(raw))
            except json.JSONDecodeError:
                continue
    if not lines:
        return None, "", ""

    first_ts = next((e.get("timestamp") for e in lines if e.get("timestamp")), "")
    last_ts = next((e.get("timestamp") for e in reversed(lines) if e.get("timestamp")), first_ts)

    summary = next((e.get("summary") for e in lines if e.get("type") == "summary" and e.get("summary")), None)
    first_user = next(
        (extract_text((e.get("message") or {}).get("content")) for e in lines if e.get("type") == "user"),
        "",
    )
    title = (summary or first_user or jsonl_path.stem)[:120].strip().replace("\n", " ")

    date_prefix = iso_date(first_ts)
    slug = slugify(title)
    session_id = jsonl_path.stem.split("-")[0]
    filename = f"{date_prefix}-{slug}-{session_id}.md"

    project_path = decode_project_path(jsonl_path.parent.name)

    fm = [
        "---",
        "source: claude-code",
        f"title: {json.dumps(title)}",
        f"session_id: {jsonl_path.stem}",
        f"project: {json.dumps(project_path)}",
        f"first_timestamp: {first_ts}",
        f"last_timestamp: {last_ts}",
        f"event_count: {len(lines)}",
        "---",
        "",
        f"# {title}",
        "",
        f"*Project: `{project_path}`*",
        "",
    ]

    body_parts: list[str] = []
    for e in lines:
        etype = e.get("type")
        ts = e.get("timestamp", "")
        if etype == "summary":
            continue
        if etype == "user":
            text = extract_text((e.get("message") or {}).get("content"))
            if text:
                body_parts.append(f"### user  \n*{ts}*\n\n{text}\n")
        elif etype == "assistant":
            text = extract_text((e.get("message") or {}).get("content"))
            if text:
                body_parts.append(f"### assistant  \n*{ts}*\n\n{text}\n")
        elif etype == "system":
            text = extract_text(e.get("content"))
            if text:
                body_parts.append(f"### system  \n*{ts}*\n\n{text}\n")
    return filename, "\n".join(fm) + "\n".join(body_parts) + "\n", last_ts


def existing_last_timestamp(path: Path) -> str | None:
    try:
        with path.open("r", encoding="utf-8") as f:
            head = f.read(4096)
    except OSError:
        return None
    m = re.search(r"^last_timestamp:\s*(.+)$", head, re.MULTILINE)
    return m.group(1).strip() if m else None


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("target_folder", type=Path)
    ap.add_argument("--projects-root", type=Path, default=Path("~/.claude/projects"))
    ap.add_argument("--since", type=str, default=None, help="Only export sessions whose last timestamp is >= YYYY-MM-DD")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    root: Path = args.projects_root.expanduser()
    target: Path = args.target_folder.expanduser()
    if not root.is_dir():
        sys.exit(f"ERROR: projects root not found: {root}")
    if not args.dry_run:
        target.mkdir(parents=True, exist_ok=True)

    since_dt: datetime | None = None
    if args.since:
        since_dt = datetime.strptime(args.since, "%Y-%m-%d").replace(tzinfo=timezone.utc)

    written = skipped = empty = 0
    for jsonl in sorted(root.rglob("*.jsonl")):
        filename, markdown, last_ts = session_to_markdown(jsonl)
        if not filename:
            empty += 1
            continue
        if since_dt and last_ts:
            try:
                ts_dt = datetime.fromisoformat(last_ts.replace("Z", "+00:00"))
                if ts_dt < since_dt:
                    skipped += 1
                    continue
            except ValueError:
                pass
        out = target / filename
        if out.exists() and existing_last_timestamp(out) == last_ts:
            skipped += 1
            continue
        if args.dry_run:
            print(f"DRY: would write {out}")
        else:
            out.write_text(markdown, encoding="utf-8")
        written += 1

    print(f"Done. {written} written, {skipped} skipped, {empty} empty.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
