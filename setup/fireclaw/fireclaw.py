#!/usr/bin/env python3
"""
FireClaw — the constellation's hot line.

A tiny, dependency-free HTTP daemon that accepts urgent ("fire") signals
from local agents (iPhone Shortcuts, iMac menubar, LobsterBot, Claude Code
sessions) and forwards them to the NemoClaw n8n webhook on OpenClaw.

UrantiOS governed — Truth, Beauty, Goodness.
No claim beyond evidence: FireClaw only relays; it does not decide.

Protocol
--------
POST /fire
  Content-Type: application/json
  Body: {"source": "...", "severity": "low|med|high", "message": "...", "meta": {...}}
  Response: {"ok": true, "forwarded": true|false, "id": "<uuid>"}

GET /health
  Response: {"ok": true, "uptime_s": <int>, "forwarded": <int>, "failed": <int>}

Environment
-----------
FIRECLAW_PORT       (default: 8797)
FIRECLAW_BIND       (default: 127.0.0.1)
FIRECLAW_FORWARD    (default: http://46.225.51.30/webhook/fireclaw)
FIRECLAW_TOKEN      (optional bearer token required on /fire if set)
FIRECLAW_LOG        (default: ~/.fireclaw/fireclaw.log)
"""
from __future__ import annotations

import json
import os
import sys
import time
import uuid
import urllib.request
import urllib.error
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

PORT = int(os.environ.get("FIRECLAW_PORT", "8797"))
BIND = os.environ.get("FIRECLAW_BIND", "127.0.0.1")
FORWARD_URL = os.environ.get(
    "FIRECLAW_FORWARD", "http://46.225.51.30/webhook/fireclaw"
)
TOKEN = os.environ.get("FIRECLAW_TOKEN", "").strip()
LOG_PATH = Path(
    os.environ.get("FIRECLAW_LOG", str(Path.home() / ".fireclaw" / "fireclaw.log"))
).expanduser()

START_TS = time.time()
STATS = {"forwarded": 0, "failed": 0}


def log(msg: str) -> None:
    LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    line = f"{time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())} {msg}\n"
    with LOG_PATH.open("a", encoding="utf-8") as f:
        f.write(line)
    sys.stderr.write(line)


def forward(payload: dict) -> bool:
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        FORWARD_URL,
        data=data,
        method="POST",
        headers={"Content-Type": "application/json", "User-Agent": "FireClaw/0.1"},
    )
    try:
        with urllib.request.urlopen(req, timeout=5) as resp:
            resp.read()
            return 200 <= resp.status < 300
    except (urllib.error.URLError, TimeoutError) as e:
        log(f"forward failed: {e!r}")
        return False


class Handler(BaseHTTPRequestHandler):
    server_version = "FireClaw/0.1"

    def _json(self, code: int, body: dict) -> None:
        raw = json.dumps(body).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)

    def log_message(self, fmt: str, *args) -> None:  # quiet default logger
        log("http " + (fmt % args))

    def do_GET(self) -> None:
        if self.path == "/health":
            self._json(
                200,
                {
                    "ok": True,
                    "uptime_s": int(time.time() - START_TS),
                    "forwarded": STATS["forwarded"],
                    "failed": STATS["failed"],
                    "forward_url": FORWARD_URL,
                },
            )
            return
        self._json(404, {"ok": False, "error": "not found"})

    def do_POST(self) -> None:
        if self.path != "/fire":
            self._json(404, {"ok": False, "error": "not found"})
            return

        if TOKEN:
            auth = self.headers.get("Authorization", "")
            if auth != f"Bearer {TOKEN}":
                self._json(401, {"ok": False, "error": "unauthorized"})
                return

        length = int(self.headers.get("Content-Length") or 0)
        raw = self.rfile.read(length) if length else b"{}"
        try:
            payload = json.loads(raw.decode("utf-8") or "{}")
        except json.JSONDecodeError:
            self._json(400, {"ok": False, "error": "invalid json"})
            return

        payload.setdefault("source", "unknown")
        payload.setdefault("severity", "med")
        payload["id"] = str(uuid.uuid4())
        payload["received_at"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

        ok = forward(payload)
        if ok:
            STATS["forwarded"] += 1
        else:
            STATS["failed"] += 1

        log(
            f"fire id={payload['id']} source={payload['source']} "
            f"severity={payload['severity']} forwarded={ok}"
        )
        self._json(200, {"ok": True, "forwarded": ok, "id": payload["id"]})


def main() -> int:
    log(f"FireClaw starting on {BIND}:{PORT} -> {FORWARD_URL}")
    server = ThreadingHTTPServer((BIND, PORT), Handler)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        log("FireClaw shutting down")
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
