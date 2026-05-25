#!/usr/bin/env python3
"""
capture.py — Obsidian Perpetual Capture engine.

Scans every AI/work data source and writes structured Markdown captures to
~/Obsidian/UrantiPedia/00_Inbox/<source>/ with mandatory frontmatter.

Sources handled:
  Claude Code     — ~/.claude/projects/**/*.jsonl
  ChatGPT exports — ~/Downloads/conversations.json  (official export)
                    ~/Downloads/ChatGPT-*.html
  Council/n8n     — ~/.council-keys/logs/*.json
  NemoClaw logs   — ~/.cognee/data/logs/*.json (if present)
  Telegram export — ~/Downloads/Telegram Desktop/ChatExport_*/result.json
  Terminal cmds   — ~/.bash_history, ~/.zsh_history (last N lines)
  Drop folder     — ~/Obsidian/UrantiPedia/00_Inbox/AI_Captures/*.txt|*.md

Never summarises — preserves full raw content.
Fails loudly on missing paths that are configured as required.
"""

import hashlib
import json
import os
import platform
import socket
import sys
from datetime import datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

# ── Config ────────────────────────────────────────────────────────────────────
TZ_MELB   = ZoneInfo("Australia/Melbourne")
VAULT     = Path(os.environ.get(
    "OBSIDIAN_URANTIPEDIA_VAULT",
    str(Path.home() / "Obsidian" / "UrantiPedia")
))
SEEN_FILE = Path.home() / ".cloud-backup" / "perpetual-seen.json"
TERM_LINES = 500  # how many shell history lines to capture per run

SOURCE_MAP = {
    "claude_code":  VAULT / "00_Inbox" / "Claude",
    "chatgpt":      VAULT / "00_Inbox" / "ChatGPT",
    "council":      VAULT / "00_Inbox" / "n8n",
    "nemoclaw":     VAULT / "00_Inbox" / "NemoClaw",
    "openclaw":     VAULT / "00_Inbox" / "OpenClaw",
    "telegram":     VAULT / "00_Inbox" / "Telegram",
    "terminal":     VAULT / "00_Inbox" / "Terminal",
    "drop":         VAULT / "00_Inbox" / "AI_Captures",
}

# ── Helpers ───────────────────────────────────────────────────────────────────

def now_melb() -> str:
    return datetime.now(TZ_MELB).strftime("%Y-%m-%dT%H:%M:%S%z")

def capture_id(source: str, topic: str) -> str:
    ts = datetime.now(TZ_MELB).strftime("%Y-%m-%d-%H%M%S")
    slug = topic[:30].lower().replace(" ", "-").replace("/", "-")
    return f"{ts}-{source}-{slug}"

def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()

def detect_host() -> str:
    hostname = socket.gethostname().lower()
    if "imac" in hostname or "m4" in hostname:
        return "iMac_M4"
    if "macbook" in hostname or "mbp" in hostname or "m1" in hostname:
        return "MacBookPro_M1"
    if "hetzner" in hostname or "urantios" in hostname or "vps" in hostname:
        return "Hetzner"
    if platform.system() == "Darwin":
        return "Mac_Unknown"
    return "Unknown"

def load_seen() -> dict:
    if SEEN_FILE.exists():
        return json.loads(SEEN_FILE.read_text())
    return {}

def save_seen(seen: dict):
    SEEN_FILE.parent.mkdir(parents=True, exist_ok=True)
    SEEN_FILE.write_text(json.dumps(seen, indent=2))

def file_hash(path: Path) -> str:
    return hashlib.sha1(path.read_bytes()).hexdigest()[:16]

def ensure_dirs():
    VAULT.mkdir(parents=True, exist_ok=True)
    for d in SOURCE_MAP.values():
        d.mkdir(parents=True, exist_ok=True)
    (VAULT / "04_Backups_Index").mkdir(exist_ok=True)

def write_capture(
    dest_dir: Path,
    filename: str,
    source: str,
    topic: str,
    raw_content: str,
    context: str = "",
    commands: str = "",
    outputs: str = "",
    priority: str = "TIER 2",
    host: str = "",
    checksum: str = "",
) -> Path:
    cid   = capture_id(source, topic)
    ts    = now_melb()
    host  = host or detect_host()
    cksum = checksum or sha256(raw_content.encode())

    frontmatter = f"""---
capture_id: {cid}
created_at: {ts}
updated_at: {ts}
source: {source}
host_device: {host}
target_system: Obsidian
topic: {topic[:80]}
priority: {priority}
status: captured
verification_status: unverified
tags: []
checksum: {cksum}
---"""

    body = f"""{frontmatter}

# {topic}

## Context
{context or "_No context recorded._"}

## Identifiers
- capture_id: `{cid}`
- host: `{host}`
- source: `{source}`

## Commands / Instructions
{commands or "_None extracted._"}

## Outputs / Proof
{outputs or "_None extracted._"}

## Decisions
_Pending review._

## Pending Actions
_None._

## Risks / Failures
_None detected at capture time._

## Automation Hooks
_None._

## Raw Full Content

```
{raw_content}
```
"""
    out = dest_dir / filename
    out.write_text(body, encoding="utf-8")
    size = out.stat().st_size
    print(f"[capture] {source} → {out.name} ({size} bytes)")
    return out

# ── Source: Claude Code JSONL transcripts ─────────────────────────────────────

def capture_claude_code(seen: dict) -> int:
    projects = Path.home() / ".claude" / "projects"
    if not projects.exists():
        return 0
    dest = SOURCE_MAP["claude_code"]
    count = 0
    for jsonl in sorted(projects.rglob("*.jsonl")):
        fhash = file_hash(jsonl)
        key   = f"claude:{jsonl}"
        if seen.get(key) == fhash:
            continue

        raw     = jsonl.read_text(errors="replace")
        date_s  = datetime.fromtimestamp(
            jsonl.stat().st_mtime, tz=TZ_MELB
        ).strftime("%Y-%m-%d")
        project = jsonl.parent.name[:20]
        stem    = jsonl.stem[:20]
        fname   = f"{date_s}_{project}_{stem}.md"
        topic   = f"Claude Code Session — {stem}"

        # Extract assistant messages as outputs
        outputs_lines = []
        for line in raw.splitlines():
            try:
                obj = json.loads(line)
                if obj.get("role") == "assistant":
                    content = obj.get("content", "")
                    if isinstance(content, list):
                        for blk in content:
                            if isinstance(blk, dict) and blk.get("type") == "text":
                                outputs_lines.append(blk.get("text", "")[:500])
                    elif isinstance(content, str):
                        outputs_lines.append(content[:500])
            except Exception:
                pass

        write_capture(
            dest, fname, "Claude Code", topic,
            raw_content=raw,
            context=f"Project dir: {jsonl.parent.name}",
            outputs="\n".join(outputs_lines[:5]),
            priority="TIER 1",
            checksum=sha256(raw.encode()),
        )
        seen[key] = fhash
        count += 1
    return count

# ── Source: ChatGPT conversations.json export ──────────────────────────────────

def capture_chatgpt(seen: dict) -> int:
    candidates = list(Path.home().glob("Downloads/conversations.json")) + \
                 list(Path.home().glob("Downloads/ChatGPT-*.html"))
    if not candidates:
        return 0
    dest = SOURCE_MAP["chatgpt"]
    count = 0
    for src in candidates:
        fhash = file_hash(src)
        key   = f"chatgpt:{src}"
        if seen.get(key) == fhash:
            continue

        raw   = src.read_text(errors="replace")
        date_s = datetime.fromtimestamp(
            src.stat().st_mtime, tz=TZ_MELB
        ).strftime("%Y-%m-%d")
        fname = f"{date_s}_{src.stem[:40]}.md"
        topic = f"ChatGPT Export — {src.name}"
        cksum = sha256(raw.encode())

        convos = []
        if src.suffix == ".json":
            try:
                data = json.loads(raw)
                if isinstance(data, list):
                    for c in data[:3]:
                        title = c.get("title", "untitled")[:60]
                        convos.append(f"- {title}")
            except Exception:
                pass

        write_capture(
            dest, fname, "ChatGPT", topic,
            raw_content=raw,
            context=f"Export file: {src.name}",
            outputs="\n".join(convos) if convos else "",
            priority="TIER 2",
            checksum=cksum,
        )
        seen[key] = fhash
        count += 1
    return count

# ── Source: Council / n8n execution logs ──────────────────────────────────────

def capture_council(seen: dict) -> int:
    log_dirs = [
        Path.home() / ".council-keys" / "logs",
        Path(__file__).parents[2] / "council" / "logs",
    ]
    dest = SOURCE_MAP["council"]
    count = 0
    for log_dir in log_dirs:
        if not log_dir.exists():
            continue
        for log in sorted(log_dir.glob("*.json")):
            fhash = file_hash(log)
            key   = f"council:{log}"
            if seen.get(key) == fhash:
                continue
            raw   = log.read_text(errors="replace")
            date_s = datetime.fromtimestamp(
                log.stat().st_mtime, tz=TZ_MELB
            ).strftime("%Y-%m-%d")
            fname = f"{date_s}_{log.stem[:50]}.md"
            topic = f"Council/n8n Log — {log.stem}"
            try:
                data  = json.loads(raw)
                model = data.get("model", "unknown")
                seat  = data.get("seat", "?")
                ctx   = f"Seat: {seat}, Model: {model}"
            except Exception:
                ctx = "n8n execution log"
            write_capture(
                dest, fname, "n8n", topic,
                raw_content=raw,
                context=ctx,
                priority="TIER 2",
                checksum=sha256(raw.encode()),
            )
            seen[key] = fhash
            count += 1
    return count

# ── Source: Telegram JSON export ──────────────────────────────────────────────

def capture_telegram(seen: dict) -> int:
    # Official Telegram Desktop export: ~/Downloads/Telegram Desktop/ChatExport_*/result.json
    candidates = list(Path.home().glob(
        "Downloads/Telegram Desktop/ChatExport_*/result.json"
    )) + list(Path.home().glob("Downloads/result.json"))
    dest  = SOURCE_MAP["telegram"]
    count = 0
    for src in candidates:
        fhash = file_hash(src)
        key   = f"telegram:{src}"
        if seen.get(key) == fhash:
            continue
        raw   = src.read_text(errors="replace")
        date_s = datetime.fromtimestamp(
            src.stat().st_mtime, tz=TZ_MELB
        ).strftime("%Y-%m-%d")
        fname = f"{date_s}_telegram_{src.parent.name[:30]}.md"
        topic = f"Telegram Export — {src.parent.name}"
        chat_name = ""
        try:
            data = json.loads(raw)
            chat_name = data.get("name", "")
        except Exception:
            pass
        write_capture(
            dest, fname, "Telegram", topic,
            raw_content=raw,
            context=f"Chat: {chat_name}" if chat_name else "Telegram export",
            priority="TIER 3",
            checksum=sha256(raw.encode()),
        )
        seen[key] = fhash
        count += 1
    return count

# ── Source: Terminal history ───────────────────────────────────────────────────

def capture_terminal(seen: dict) -> int:
    histories = [
        Path.home() / ".bash_history",
        Path.home() / ".zsh_history",
    ]
    dest  = SOURCE_MAP["terminal"]
    count = 0
    for hist in histories:
        if not hist.exists():
            continue
        lines = hist.read_text(errors="replace").splitlines()
        # Only capture last N lines; key on last-line content to detect change
        tail   = lines[-TERM_LINES:]
        sample = "\n".join(tail)
        fhash  = sha256(sample.encode())[:16]
        key    = f"terminal:{hist}"
        if seen.get(key) == fhash:
            continue
        date_s = datetime.now(TZ_MELB).strftime("%Y-%m-%d")
        shell  = hist.name.replace(".", "").replace("_history", "")
        fname  = f"{date_s}_{shell}_history.md"
        topic  = f"Terminal History — {shell} ({len(tail)} lines)"
        write_capture(
            dest, fname, "Terminal", topic,
            raw_content=sample,
            context=f"Shell: {shell}, last {len(tail)} commands",
            commands=sample,
            priority="TIER 3",
            checksum=sha256(sample.encode()),
        )
        seen[key] = fhash
        count += 1
    return count

# ── Source: Drop folder (manual drops) ────────────────────────────────────────

def capture_drop(seen: dict) -> int:
    drop = SOURCE_MAP["drop"]
    count = 0
    for f in sorted(drop.glob("*.txt")) + sorted(drop.glob("*.md")):  # type: ignore[operator]
        fhash = file_hash(f)
        key   = f"drop:{f}"
        if seen.get(key) == fhash:
            continue
        raw   = f.read_text(errors="replace")
        date_s = datetime.fromtimestamp(
            f.stat().st_mtime, tz=TZ_MELB
        ).strftime("%Y-%m-%d")
        fname = f"{date_s}_drop_{f.stem[:40]}.captured.md"
        topic = f"Drop Capture — {f.stem}"
        write_capture(
            drop, fname, "Other", topic,
            raw_content=raw,
            context=f"Dropped file: {f.name}",
            priority="TIER 2",
            checksum=sha256(raw.encode()),
        )
        seen[key] = fhash
        count += 1
    return count

# ── Dashboard update ─────────────────────────────────────────────────────────

def update_dashboard(total: int, seen: dict):
    """Rewrite the AUTO-* sections of DASHBOARD.md with live stats."""
    dash = VAULT / "DASHBOARD.md"
    if not dash.exists():
        return  # scaffold hasn't run yet; skip silently

    ts = now_melb()
    host = detect_host()

    # File counts per source
    source_rows = []
    for src, d in SOURCE_MAP.items():
        files = sorted(d.glob("*.md")) if d.exists() else []
        n = len(files)
        last = (
            datetime.fromtimestamp(
                files[-1].stat().st_mtime, tz=TZ_MELB
            ).strftime("%Y-%m-%d %H:%M")
            if files else "—"
        )
        folder = f"00_Inbox/{d.name}"
        source_rows.append(
            f"| {src:<12} | `{folder}` | {n:>4} | {last} |"
        )

    total_md = sum(
        len(list(d.glob("*.md"))) for d in SOURCE_MAP.values() if d.exists()
    )
    try:
        vault_size = f"{sum(f.stat().st_size for f in VAULT.rglob('*.md')) / 1_048_576:.1f} MB"
    except Exception:
        vault_size = "—"

    # Recent captures: last 10 .md files across all sources by mtime
    all_files = []
    for d in SOURCE_MAP.values():
        if d.exists():
            all_files.extend(d.glob("*.md"))
    all_files.sort(key=lambda f: f.stat().st_mtime, reverse=True)
    recent_lines = []
    for f in all_files[:10]:
        rel = f.relative_to(VAULT)
        mtime = datetime.fromtimestamp(f.stat().st_mtime, tz=TZ_MELB).strftime("%Y-%m-%d")
        recent_lines.append(f"- `{mtime}` [[{rel}|{f.stem}]]")

    status_block = (
        f"| Last capture run | `{ts}` |\n"
        f"| Total .md files | {total_md} |\n"
        f"| Vault size | {vault_size} |\n"
        f"| Sync: Google Drive | pending sync |\n"
        f"| Sync: iCloud | pending sync |\n"
        f"| Sync: External SSD | pending sync |\n"
        f"| Host device | `{host}` |"
    )

    sources_header = "| Source | Inbox Folder | Files | Last Captured |\n|:---|:---|---:|:---|"
    sources_block = sources_header + "\n" + "\n".join(source_rows)

    recent_block = "\n".join(recent_lines) if recent_lines else "_No captures yet._"

    text = dash.read_text(encoding="utf-8")

    def replace_section(content: str, tag: str, replacement: str) -> str:
        start = f"<!-- {tag}-START -->"
        end   = f"<!-- {tag}-END -->"
        if start not in content or end not in content:
            return content
        before = content[:content.index(start) + len(start)]
        after  = content[content.index(end):]
        return before + "\n" + replacement + "\n" + after

    text = replace_section(text, "AUTO-STATUS",  status_block)
    text = replace_section(text, "AUTO-SOURCES", sources_block)
    text = replace_section(text, "AUTO-RECENT",  recent_block)

    # Update frontmatter updated_at and total_captures
    import re
    text = re.sub(r"^updated_at:.*$",       f"updated_at: {ts}",       text, flags=re.MULTILINE)
    text = re.sub(r"^total_captures:.*$",   f"total_captures: {total_md}", text, flags=re.MULTILINE)

    dash.write_text(text, encoding="utf-8")
    print(f"[capture] dashboard → DASHBOARD.md updated ({total_md} total captures)")

# ── Day index ─────────────────────────────────────────────────────────────────

def update_day_index(today: str):
    """Create/update ~/Obsidian/UrantiPedia/00_Inbox/YYYY-MM-DD_index.md"""
    idx_path = VAULT / "00_Inbox" / f"{today}_index.md"
    captures = []
    for src_dir in SOURCE_MAP.values():
        for f in sorted(src_dir.glob(f"{today}_*.md")):
            rel = f.relative_to(VAULT)
            captures.append(f"- [[{rel}]]")

    body = f"""---
type: day-index
date: {today}
generated_at: {now_melb()}
---

# Day Index — {today}

## Captures ({len(captures)})

{"".join(captures) if captures else "_No captures today._"}
"""
    idx_path.write_text(body, encoding="utf-8")
    print(f"[capture] day index → {idx_path.name} ({len(captures)} entries)")

# ── Master index ──────────────────────────────────────────────────────────────

def update_master_index(total: int):
    idx = VAULT / "04_Backups_Index" / "PERPETUAL_CAPTURE_INDEX.md"
    idx.parent.mkdir(parents=True, exist_ok=True)

    # Collect all daily indexes
    daily = sorted(
        (VAULT / "00_Inbox").glob("????-??-??_index.md"),
        reverse=True,
    )
    daily_links = "\n".join(f"- [[00_Inbox/{f.name}]]" for f in daily[:90])

    # Source stats
    stats = []
    for src, d in SOURCE_MAP.items():
        n = len(list(d.glob("*.md"))) if d.exists() else 0
        stats.append(f"| {src:<12} | {n:>5} |")

    body = f"""---
type: master-index
vault: UrantiPedia
updated_at: {now_melb()}
total_captures_this_run: {total}
---

# Perpetual Capture — Master Index

Last updated: `{now_melb()}`
This run added: **{total}** new capture(s).

## Daily Indexes (last 90 days)

{daily_links or "_None yet._"}

## Source Stats

| Source       | Files |
|:-------------|------:|
{"".join(chr(10) + s for s in stats)}

## Vault Structure

```
~/Obsidian/UrantiPedia/
  00_Inbox/
    AI_Captures/  — manual drops
    Claude/       — Claude Code JSONL sessions
    ChatGPT/      — ChatGPT exports
    Telegram/     — Telegram exports
    OpenClaw/     — OpenClaw logs
    NemoClaw/     — NemoClaw logs
    n8n/          — Council / n8n execution logs
    Terminal/     — shell history snapshots
    Proof/        — verification artifacts
  01_System/
  02_Projects/
  03_Workflows/
  04_Backups_Index/
  99_Archive/
```
"""
    idx.write_text(body, encoding="utf-8")
    print(f"[capture] master index → {idx.name}")

# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    # Fail loudly if vault is not accessible
    if not VAULT.exists():
        print(f"[capture] FAIL: vault not found at {VAULT}")
        print(f"[capture] Run: setup/perpetual-capture/scaffold-vault.sh")
        sys.exit(1)

    ensure_dirs()
    seen  = load_seen()
    total = 0

    total += capture_claude_code(seen)
    total += capture_chatgpt(seen)
    total += capture_council(seen)
    total += capture_telegram(seen)
    total += capture_terminal(seen)
    total += capture_drop(seen)

    today = datetime.now(TZ_MELB).strftime("%Y-%m-%d")
    update_day_index(today)
    update_master_index(total)
    update_dashboard(total, seen)

    save_seen(seen)

    # Proof output
    print("")
    print("=== PROOF ===")
    print(f"Vault:     {VAULT}")
    print(f"Captured:  {total} new file(s)")
    print(f"Timestamp: {now_melb()}")
    for src, d in SOURCE_MAP.items():
        if d.exists():
            files = list(d.glob("*.md"))
            total_size = sum(f.stat().st_size for f in files)
            print(f"  {src:<12}: {len(files):>4} files, {total_size:>8} bytes")
    print("=============")

if __name__ == "__main__":
    main()
