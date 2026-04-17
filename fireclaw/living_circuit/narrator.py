#!/usr/bin/env python3
"""Living Circuit · Stage 2 — Narrator.

Subscribes to the relay's /stream SSE endpoint and appends every event as
a single Markdown line to an Obsidian daily journal note. The constellation
writes its own diary.

Zero dependencies. Reconnects on any failure. Ordered. Append-only.

Env
---
LC_RELAY         default http://127.0.0.1:8899/stream
LC_VAULT         default ~/Obsidian/Constellation
LC_JOURNAL_DIR   default Journal
"""
from __future__ import annotations

import json
import os
import sys
import time
import urllib.request
from pathlib import Path

RELAY_URL = os.environ.get("LC_RELAY", "http://127.0.0.1:8899/stream")
VAULT = Path(os.environ.get(
    "LC_VAULT", str(Path.home() / "Obsidian" / "Constellation")
)).expanduser()
JOURNAL_DIR = os.environ.get("LC_JOURNAL_DIR", "Journal")

ICONS = {"fire": "🔥", "return": "↩️", "decision": "⚖️", "narration": "📜"}


def daily_file() -> Path:
    day = time.strftime("%Y-%m-%d")
    d = VAULT / JOURNAL_DIR
    d.mkdir(parents=True, exist_ok=True)
    f = d / f"{day}.md"
    if not f.exists():
        f.write_text(
            f"# Constellation journal — {day}\n\n"
            "> Written by the Living Circuit narrator.\n"
            "> Truth · Beauty · Goodness. Never stop.\n\n",
            encoding="utf-8",
        )
    return f


def render(event: dict) -> str:
    kind = event.get("kind", "?")
    ts = event.get("ts", "?")
    body = event.get("body", {})
    icon = ICONS.get(kind, "•")
    src = body.get("source", "?")
    sev = body.get("severity", "")
    msg = body.get("message", "")
    parts = [f"- `{ts}` {icon} **{kind}** · {src}"]
    if sev:
        parts.append(f" · _{sev}_")
    if msg:
        parts.append(f" — {msg}")
    return "".join(parts) + "\n"


def append(event: dict) -> None:
    with daily_file().open("a", encoding="utf-8") as f:
        f.write(render(event))


def listen() -> None:
    req = urllib.request.Request(
        RELAY_URL, headers={"Accept": "text/event-stream"}
    )
    with urllib.request.urlopen(req, timeout=None) as resp:
        buf = ""
        while True:
            raw = resp.readline()
            if not raw:
                return
            line = raw.decode("utf-8", errors="replace")
            if line.startswith(":"):       # heartbeat / comment
                continue
            if line.startswith("data: "):
                buf = line[6:].strip()
                continue
            if line.strip() == "" and buf:
                try:
                    append(json.loads(buf))
                except (json.JSONDecodeError, OSError) as e:
                    sys.stderr.write(f"narrator skip: {e}\n")
                buf = ""


def main() -> int:
    sys.stderr.write(
        f"Narrator · relay={RELAY_URL} · vault={VAULT}/{JOURNAL_DIR}\n"
    )
    while True:
        try:
            listen()
        except (urllib.error.URLError, TimeoutError, ConnectionError) as e:
            sys.stderr.write(f"reconnect in 3s: {e}\n")
            time.sleep(3)
        except KeyboardInterrupt:
            sys.stderr.write("narrator stopped\n")
            return 0


if __name__ == "__main__":
    sys.exit(main())
