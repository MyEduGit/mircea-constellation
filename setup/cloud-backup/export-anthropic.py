#!/usr/bin/env python3
"""
export-anthropic.py — Export Claude Code transcripts and Council Anthropic
seat data to ~/Documents/Obsidian/Anthropic-Data/ for cloud backup.

Scans:
  ~/.claude/projects/        — Claude Code session JSONL transcripts
  ~/.council-keys/logs/      — Council of Seven execution logs (if present)

Outputs structured Markdown per session to the Anthropic-Data Obsidian vault.
"""

import json
import os
import sys
import hashlib
from datetime import datetime, timezone
from pathlib import Path

# ── Paths ─────────────────────────────────────────────────────────────────────
CLAUDE_PROJECTS = Path.home() / ".claude" / "projects"
COUNCIL_LOGS    = Path.home() / ".council-keys" / "logs"
VAULT           = Path(os.environ.get(
    "OBSIDIAN_ANTHROPIC_VAULT",
    str(Path.home() / "Documents" / "Obsidian" / "Anthropic-Data")
))
SEEN_FILE       = Path.home() / ".cloud-backup" / "exported-transcripts.json"

# ── Helpers ───────────────────────────────────────────────────────────────────

def load_seen() -> set:
    if SEEN_FILE.exists():
        return set(json.loads(SEEN_FILE.read_text()))
    return set()

def save_seen(seen: set):
    SEEN_FILE.parent.mkdir(parents=True, exist_ok=True)
    SEEN_FILE.write_text(json.dumps(sorted(seen), indent=2))

def file_hash(path: Path) -> str:
    return hashlib.sha1(path.read_bytes()).hexdigest()[:12]

def extract_text(content) -> str:
    """Flatten content blocks or plain string to text."""
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts = []
        for block in content:
            if isinstance(block, dict):
                btype = block.get("type", "")
                if btype == "text":
                    parts.append(block.get("text", ""))
                elif btype == "tool_use":
                    name  = block.get("name", "tool")
                    inp   = json.dumps(block.get("input", {}), indent=2)
                    parts.append(f"**Tool call:** `{name}`\n```json\n{inp}\n```")
                elif btype == "tool_result":
                    out = block.get("content", "")
                    if isinstance(out, list):
                        out = "\n".join(
                            b.get("text", "") for b in out
                            if isinstance(b, dict) and b.get("type") == "text"
                        )
                    parts.append(f"**Tool result:**\n```\n{out}\n```")
        return "\n\n".join(p for p in parts if p)
    return str(content)

def parse_jsonl(path: Path) -> list[dict]:
    """Parse a JSONL file, skipping malformed lines."""
    messages = []
    for line in path.read_text(errors="replace").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            obj = json.loads(line)
        except json.JSONDecodeError:
            continue
        messages.append(obj)
    return messages

def messages_to_markdown(messages: list[dict], session_id: str) -> str:
    """Convert a list of Claude Code JSONL entries to Markdown."""
    lines = [
        f"---",
        f"session_id: {session_id}",
        f"source: claude-code",
        f"exported: {datetime.now(timezone.utc).isoformat()}",
        f"---",
        "",
        f"# Claude Code Session — `{session_id}`",
        "",
    ]

    for entry in messages:
        etype = entry.get("type", "")

        if etype == "system":
            continue  # skip system preamble

        if etype in ("message", "assistant", "user"):
            role    = entry.get("role", etype)
            content = extract_text(entry.get("content", ""))
            if not content.strip():
                continue
            label = "**Assistant (Claude)**" if role == "assistant" else "**User**"
            lines.append(f"### {label}")
            lines.append(content.strip())
            lines.append("")

        elif etype == "tool_use":
            name = entry.get("name", "tool")
            inp  = json.dumps(entry.get("input", {}), indent=2)
            lines.append(f"### Tool: `{name}`")
            lines.append(f"```json\n{inp}\n```")
            lines.append("")

        elif etype == "tool_result":
            content = extract_text(entry.get("content", ""))
            lines.append(f"### Tool Result")
            lines.append(f"```\n{content.strip()}\n```")
            lines.append("")

    return "\n".join(lines)

def export_claude_transcripts(seen: set) -> int:
    """Export new/changed JSONL transcripts from ~/.claude/projects/."""
    if not CLAUDE_PROJECTS.exists():
        print(f"[export] ~/.claude/projects not found — skipping transcript export")
        return 0

    VAULT.mkdir(parents=True, exist_ok=True)
    (VAULT / "transcripts").mkdir(exist_ok=True)

    exported = 0
    for jsonl_path in sorted(CLAUDE_PROJECTS.rglob("*.jsonl")):
        fhash = file_hash(jsonl_path)
        seen_key = f"transcript:{jsonl_path}:{fhash}"
        if seen_key in seen:
            continue

        # Derive a human-readable session slug from the parent folder name
        session_id = jsonl_path.stem
        project_id = jsonl_path.parent.name[:16]
        date_str   = datetime.fromtimestamp(
            jsonl_path.stat().st_mtime, tz=timezone.utc
        ).strftime("%Y-%m-%d")

        messages = parse_jsonl(jsonl_path)
        if not messages:
            seen.add(seen_key)
            continue

        md  = messages_to_markdown(messages, session_id)
        out = VAULT / "transcripts" / f"{date_str}_{project_id}_{session_id[:20]}.md"
        out.write_text(md, encoding="utf-8")
        seen.add(seen_key)
        exported += 1
        print(f"[export] transcript → {out.name}")

    return exported

def export_council_anthropic_logs(seen: set) -> int:
    """Export Council of Seven Anthropic-seat (Seat 2) execution logs."""
    if not COUNCIL_LOGS.exists():
        return 0

    (VAULT / "council").mkdir(parents=True, exist_ok=True)

    exported = 0
    for log_path in sorted(COUNCIL_LOGS.glob("*.json")):
        fhash = file_hash(log_path)
        seen_key = f"council:{log_path}:{fhash}"
        if seen_key in seen:
            continue

        try:
            data = json.loads(log_path.read_text())
        except json.JSONDecodeError:
            continue

        # Only export entries that used the Anthropic / Claude seat
        seat = data.get("seat", "")
        model = data.get("model", "")
        is_anthropic = (
            "claude" in model.lower()
            or "anthropic" in str(data).lower()
            or seat in ("2", "son", "Son")
        )
        if not is_anthropic:
            seen.add(seen_key)
            continue

        date_str = datetime.fromtimestamp(
            log_path.stat().st_mtime, tz=timezone.utc
        ).strftime("%Y-%m-%d")
        slug = log_path.stem[:40]
        out  = VAULT / "council" / f"{date_str}_{slug}.md"

        lines = [
            "---",
            f"source: council-seat2-anthropic",
            f"model: {model}",
            f"exported: {datetime.now(timezone.utc).isoformat()}",
            "---",
            "",
            f"# Council Anthropic Log — {slug}",
            "",
            "```json",
            json.dumps(data, indent=2),
            "```",
        ]
        out.write_text("\n".join(lines), encoding="utf-8")
        seen.add(seen_key)
        exported += 1
        print(f"[export] council log → {out.name}")

    return exported

def export_council_registry():
    """Mirror the Council Model Registry snapshot (always overwrite)."""
    registry = Path(__file__).parents[2] / "council" / "COUNCIL_MODEL_REGISTRY.json"
    if not registry.exists():
        return
    (VAULT / "council").mkdir(parents=True, exist_ok=True)
    dest = VAULT / "council" / "COUNCIL_MODEL_REGISTRY.md"
    data = json.loads(registry.read_text())
    anthropic_seats = {
        k: v for k, v in data.items()
        if "claude" in json.dumps(v).lower() or "anthropic" in json.dumps(v).lower()
    }
    lines = [
        "---",
        f"source: council-model-registry",
        f"exported: {datetime.now(timezone.utc).isoformat()}",
        "---",
        "",
        "# Council Model Registry — Anthropic Seats",
        "",
        "```json",
        json.dumps(anthropic_seats, indent=2),
        "```",
    ]
    dest.write_text("\n".join(lines), encoding="utf-8")
    print(f"[export] registry snapshot → {dest.name}")

# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    seen = load_seen()
    total = 0

    total += export_claude_transcripts(seen)
    total += export_council_anthropic_logs(seen)
    export_council_registry()

    save_seen(seen)
    print(f"[export] Done. {total} new file(s) exported to {VAULT}")

if __name__ == "__main__":
    main()
