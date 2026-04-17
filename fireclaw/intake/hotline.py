#!/usr/bin/env python3
"""FireClaw intake — hot-line for pushed fires.

Accepts `POST /fire` from edge agents, appends to an append-only JSONL
queue, and exposes `GET /status` that main's FireClaw remediator probes
as a standard `http` signal (rules.yaml).

Design: this module adds a NEW capability to the remediation layer without
modifying any existing file. Push events become pollable signals.

Contract — `~/.fireclaw/queue.jsonl`
    append-only JSON lines, one per fire.
    fields: id, received_at, source, severity, message, meta, acked

Env
---
FIRECLAW_INTAKE_PORT    default 8797
FIRECLAW_INTAKE_BIND    default 127.0.0.1
FIRECLAW_INTAKE_QUEUE   default ~/.fireclaw/queue.jsonl
FIRECLAW_INTAKE_TOKEN   optional bearer token on POST /fire
FIRECLAW_INTAKE_HIGH_MAX default 0  (pending-high threshold before /status→503)
"""
from __future__ import annotations

import json
import os
import sys
import time
import uuid
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

PORT = int(os.environ.get("FIRECLAW_INTAKE_PORT", "8797"))
BIND = os.environ.get("FIRECLAW_INTAKE_BIND", "127.0.0.1")
QUEUE = Path(os.environ.get(
    "FIRECLAW_INTAKE_QUEUE",
    str(Path.home() / ".fireclaw" / "queue.jsonl"),
)).expanduser()
TOKEN = os.environ.get("FIRECLAW_INTAKE_TOKEN", "").strip()
HIGH_MAX = int(os.environ.get("FIRECLAW_INTAKE_HIGH_MAX", "0"))


def _append(record: dict) -> None:
    QUEUE.parent.mkdir(parents=True, exist_ok=True)
    with QUEUE.open("a", encoding="utf-8") as f:
        f.write(json.dumps(record, separators=(",", ":")) + "\n")


def _pending() -> tuple[int, int]:
    """Return (pending_high, pending_total) — cheap scan of the queue."""
    if not QUEUE.exists():
        return 0, 0
    high = total = 0
    with QUEUE.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                rec = json.loads(line)
            except json.JSONDecodeError:
                continue
            if rec.get("acked"):
                continue
            total += 1
            if rec.get("severity") == "high":
                high += 1
    return high, total


class Handler(BaseHTTPRequestHandler):
    server_version = "FireClawIntake/0.1"

    def _json(self, code: int, body: dict) -> None:
        raw = json.dumps(body).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)

    def log_message(self, fmt: str, *args) -> None:
        sys.stderr.write(f"{time.strftime('%H:%M:%S')} intake {fmt % args}\n")

    def do_GET(self) -> None:
        if self.path == "/status":
            high, total = _pending()
            ok = high <= HIGH_MAX
            self._json(
                200 if ok else 503,
                {"ok": ok, "pending_high": high, "pending_total": total,
                 "queue": str(QUEUE)},
            )
            return
        if self.path == "/health":
            self._json(200, {"ok": True, "queue": str(QUEUE)})
            return
        self._json(404, {"ok": False, "error": "not found"})

    def do_POST(self) -> None:
        if self.path != "/fire":
            self._json(404, {"ok": False, "error": "not found"})
            return
        if TOKEN and self.headers.get("Authorization", "") != f"Bearer {TOKEN}":
            self._json(401, {"ok": False, "error": "unauthorized"})
            return

        length = int(self.headers.get("Content-Length") or 0)
        raw = self.rfile.read(length) if length else b"{}"
        try:
            payload = json.loads(raw.decode("utf-8") or "{}")
        except json.JSONDecodeError:
            self._json(400, {"ok": False, "error": "invalid json"})
            return

        record = {
            "id": str(uuid.uuid4()),
            "received_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "source": payload.get("source", "unknown"),
            "severity": payload.get("severity", "med"),
            "message": payload.get("message", ""),
            "meta": payload.get("meta", {}),
            "acked": False,
        }
        _append(record)
        self._json(200, {"ok": True, "queued": True, "id": record["id"]})


def main() -> int:
    sys.stderr.write(
        f"FireClaw intake on {BIND}:{PORT} -> {QUEUE} "
        f"(high_max={HIGH_MAX})\n"
    )
    server = ThreadingHTTPServer((BIND, PORT), Handler)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
