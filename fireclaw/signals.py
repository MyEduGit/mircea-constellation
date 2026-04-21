"""Signal collectors for Fireclaw.

A signal is a single observation: "is X healthy right now?" Collectors
return a dict with a stable shape:

    {"kind": "http", "ok": True|False, "detail": "...", "raw": <any>}

No collector ever raises — failures become ok=False with a detail.
"""
from __future__ import annotations

import json
import os
import socket
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any


def http(url: str, expect_status: int = 200, timeout: float = 3.0) -> dict[str, Any]:
    """HTTP GET probe. ok=True iff response status matches expect_status."""
    try:
        req = urllib.request.Request(url, method="GET")
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            status = resp.status
            ok = status == expect_status
            return {
                "kind": "http",
                "ok": ok,
                "detail": f"status={status}",
                "raw": {"status": status, "url": url},
            }
    except urllib.error.HTTPError as e:
        return {
            "kind": "http",
            "ok": e.code == expect_status,
            "detail": f"http_error={e.code}",
            "raw": {"status": e.code, "url": url},
        }
    except (urllib.error.URLError, TimeoutError) as e:
        return {
            "kind": "http",
            "ok": False,
            "detail": f"unreachable: {e}",
            "raw": {"url": url},
        }


def tcp(host: str, port: int, timeout: float = 2.0) -> dict[str, Any]:
    """TCP connect probe. ok=True iff handshake completes."""
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return {
                "kind": "tcp",
                "ok": True,
                "detail": f"{host}:{port} reachable",
                "raw": {"host": host, "port": port},
            }
    except (TimeoutError, OSError) as e:
        return {
            "kind": "tcp",
            "ok": False,
            "detail": f"{host}:{port} {e}",
            "raw": {"host": host, "port": port},
        }


def file_field(path: str, field_path: str, expect: Any) -> dict[str, Any]:
    """Read a JSON file and check a dotted field equals expected value.

    Example: file_field("status.json", "ollama.status", "ok")
    """
    p = Path(os.path.expanduser(path))
    if not p.exists():
        return {
            "kind": "file",
            "ok": False,
            "detail": f"missing: {p}",
            "raw": {"path": str(p)},
        }
    try:
        data = json.loads(p.read_text())
    except (OSError, json.JSONDecodeError) as e:
        return {
            "kind": "file",
            "ok": False,
            "detail": f"unreadable: {e}",
            "raw": {"path": str(p)},
        }

    cur: Any = data
    for part in field_path.split("."):
        if not isinstance(cur, dict) or part not in cur:
            return {
                "kind": "file",
                "ok": False,
                "detail": f"missing field: {field_path}",
                "raw": {"path": str(p)},
            }
        cur = cur[part]
    ok = cur == expect
    return {
        "kind": "file",
        "ok": ok,
        "detail": f"{field_path}={cur!r} (expect {expect!r})",
        "raw": {"path": str(p), "value": cur},
    }


def nemoclaw(view: str = "nemoclaw_latest_status", service: str | None = None,
             dsn: str | None = None) -> dict[str, Any]:
    """Read NemoClaw observer view from Postgres. ok=True iff service status='ok'.

    Returns ok=False with detail='nemoclaw_unavailable' when psycopg2 is not
    installed or the DB is unreachable — a soft skip, not a fault.
    """
    try:
        import psycopg2  # type: ignore
    except ImportError:
        return {
            "kind": "nemoclaw",
            "ok": False,
            "detail": "nemoclaw_unavailable: psycopg2 not installed",
            "raw": {},
        }
    dsn = dsn or os.environ.get("FIRECLAW_PG_DSN")
    if not dsn:
        return {
            "kind": "nemoclaw",
            "ok": False,
            "detail": "nemoclaw_unavailable: FIRECLAW_PG_DSN not set",
            "raw": {},
        }
    try:
        with psycopg2.connect(dsn, connect_timeout=3) as conn, conn.cursor() as cur:
            if service:
                cur.execute(f"SELECT status FROM {view} WHERE service = %s LIMIT 1",
                            (service,))
                row = cur.fetchone()
                if row is None:
                    return {
                        "kind": "nemoclaw",
                        "ok": False,
                        "detail": f"no row for service={service}",
                        "raw": {},
                    }
                ok = row[0] == "ok"
                return {
                    "kind": "nemoclaw",
                    "ok": ok,
                    "detail": f"service={service} status={row[0]}",
                    "raw": {"service": service, "status": row[0]},
                }
            cur.execute(f"SELECT count(*) FROM {view} WHERE status <> 'ok'")
            bad = cur.fetchone()[0]
            return {
                "kind": "nemoclaw",
                "ok": bad == 0,
                "detail": f"{bad} services not ok",
                "raw": {"non_ok": bad},
            }
    except Exception as e:  # connection / query errors are soft
        return {
            "kind": "nemoclaw",
            "ok": False,
            "detail": f"nemoclaw_unavailable: {e}",
            "raw": {},
        }


def process(name: str | None = None, pid_file: str | None = None) -> dict[str, Any]:
    """Check if a named process is running or a PID file points to a live PID.

    Specify exactly one of:
      name     — match against full command line (pgrep -f)
      pid_file — path to a .pid file; checks that the PID inside is alive
    """
    import subprocess

    if pid_file:
        p = Path(os.path.expanduser(pid_file))
        if not p.exists():
            return {"kind": "process", "ok": False,
                    "detail": f"pid_file missing: {p}", "raw": {}}
        try:
            pid = int(p.read_text().strip())
            os.kill(pid, 0)  # signal 0 = existence check, no actual signal sent
            return {"kind": "process", "ok": True,
                    "detail": f"pid={pid} alive", "raw": {"pid": pid}}
        except ValueError as e:
            return {"kind": "process", "ok": False,
                    "detail": f"pid_file unreadable: {e}", "raw": {}}
        except OSError as e:
            return {"kind": "process", "ok": False,
                    "detail": f"pid {pid} dead: {e}", "raw": {"pid": pid}}

    if name:
        try:
            r = subprocess.run(["pgrep", "-f", name],
                               capture_output=True, text=True)
            ok = r.returncode == 0
            pids = r.stdout.strip().split() if ok else []
            detail = (f"{name} running pids={','.join(pids)}"
                      if ok else f"{name} not found")
            return {"kind": "process", "ok": ok,
                    "detail": detail, "raw": {"pids": pids}}
        except FileNotFoundError:
            return {"kind": "process", "ok": False,
                    "detail": "pgrep not available on this system", "raw": {}}

    return {"kind": "process", "ok": False,
            "detail": "neither 'name' nor 'pid_file' specified", "raw": {}}


def collect(spec: dict[str, Any]) -> dict[str, Any]:
    """Dispatch a signal spec from rules.yaml to the right collector."""
    kind = spec.get("kind")
    if kind == "http":
        return http(spec["url"], spec.get("expect_status", 200),
                    float(spec.get("timeout", 3.0)))
    if kind == "tcp":
        return tcp(spec["host"], int(spec["port"]),
                   float(spec.get("timeout", 2.0)))
    if kind == "file":
        return file_field(spec["path"], spec["field"], spec.get("expect", "ok"))
    if kind == "nemoclaw":
        return nemoclaw(spec.get("view", "nemoclaw_latest_status"),
                        spec.get("service"), spec.get("dsn"))
    if kind == "process":
        return process(spec.get("name"), spec.get("pid_file"))
    return {"kind": kind or "unknown", "ok": False,
            "detail": f"unknown signal kind: {kind!r}", "raw": spec}
