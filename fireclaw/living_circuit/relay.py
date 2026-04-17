#!/usr/bin/env python3
"""Living Circuit · Stage 1 — SSE relay.

Minimal bidirectional event bus for the constellation:

    POST /fire     edge pushes a signal UP
    GET  /stream   any subscriber (dashboard, edge) listens (SSE)
    POST /return   cloud pushes a decision DOWN (broadcast to subscribers)

This is the scaffold. Semantic routing, narration, and scoring arrive in
later stages — but the bus already lets the dashboard display fires live.

Zero dependencies (Python stdlib). Thread-per-subscriber fan-out. Every
event is also appended to a persistent JSONL log for replay.

Env
---
LC_PORT       default 8899
LC_BIND       default 127.0.0.1
LC_LOG        default ~/.fireclaw/living_circuit.jsonl
LC_VALUES     default "truth,beauty,goodness" (injected into every event)
"""
from __future__ import annotations

import json
import os
import queue
import sys
import threading
import time
import uuid
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any

PORT = int(os.environ.get("LC_PORT", "8899"))
BIND = os.environ.get("LC_BIND", "127.0.0.1")
LOG_PATH = Path(os.environ.get(
    "LC_LOG", str(Path.home() / ".fireclaw" / "living_circuit.jsonl")
)).expanduser()
VALUES = [v.strip() for v in os.environ.get(
    "LC_VALUES", "truth,beauty,goodness").split(",") if v.strip()]

_subscribers: list[queue.Queue[str]] = []
_sub_lock = threading.Lock()


def _persist(event: dict[str, Any]) -> None:
    LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    with LOG_PATH.open("a", encoding="utf-8") as f:
        f.write(json.dumps(event, separators=(",", ":")) + "\n")


def _broadcast(event: dict[str, Any]) -> None:
    payload = "data: " + json.dumps(event, separators=(",", ":")) + "\n\n"
    with _sub_lock:
        dead: list[queue.Queue[str]] = []
        for q in _subscribers:
            try:
                q.put_nowait(payload)
            except queue.Full:
                dead.append(q)
        for q in dead:
            _subscribers.remove(q)


def _emit(kind: str, body: dict[str, Any]) -> dict[str, Any]:
    event = {
        "id": str(uuid.uuid4()),
        "ts": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "kind": kind,
        "values": VALUES,
        "body": body,
    }
    _persist(event)
    _broadcast(event)
    return event


class Handler(BaseHTTPRequestHandler):
    server_version = "LivingCircuit/0.1"

    def _json(self, code: int, body: dict) -> None:
        raw = json.dumps(body).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)

    def log_message(self, fmt: str, *args) -> None:
        sys.stderr.write(f"{time.strftime('%H:%M:%S')} lc {fmt % args}\n")

    # ── Subscribe: /stream (Server-Sent Events) ─────────────────────
    def do_GET(self) -> None:
        if self.path == "/stream":
            self.send_response(200)
            self.send_header("Content-Type", "text/event-stream")
            self.send_header("Cache-Control", "no-cache")
            self.send_header("Connection", "keep-alive")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()

            q: queue.Queue[str] = queue.Queue(maxsize=256)
            with _sub_lock:
                _subscribers.append(q)
            try:
                self.wfile.write(b": welcome to the living circuit\n\n")
                self.wfile.flush()
                while True:
                    try:
                        payload = q.get(timeout=15)
                        self.wfile.write(payload.encode("utf-8"))
                        self.wfile.flush()
                    except queue.Empty:
                        # heartbeat so proxies don't kill the stream
                        self.wfile.write(b": heartbeat\n\n")
                        self.wfile.flush()
            except (BrokenPipeError, ConnectionResetError):
                pass
            finally:
                with _sub_lock:
                    if q in _subscribers:
                        _subscribers.remove(q)
            return

        if self.path == "/health":
            with _sub_lock:
                subs = len(_subscribers)
            self._json(200, {"ok": True, "subscribers": subs,
                             "log": str(LOG_PATH), "values": VALUES})
            return

        self._json(404, {"ok": False, "error": "not found"})

    # ── Push in (edge → circuit) and down (cloud → subscribers) ─────
    def do_POST(self) -> None:
        if self.path not in ("/fire", "/return"):
            self._json(404, {"ok": False, "error": "not found"})
            return

        length = int(self.headers.get("Content-Length") or 0)
        raw = self.rfile.read(length) if length else b"{}"
        try:
            body = json.loads(raw.decode("utf-8") or "{}")
        except json.JSONDecodeError:
            self._json(400, {"ok": False, "error": "invalid json"})
            return

        kind = "fire" if self.path == "/fire" else "return"
        event = _emit(kind, body)
        self._json(200, {"ok": True, "id": event["id"], "kind": kind})


def main() -> int:
    sys.stderr.write(
        f"Living Circuit on {BIND}:{PORT} · log={LOG_PATH} · values={VALUES}\n"
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
