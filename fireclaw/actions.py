"""Action primitives for Fireclaw.

Every action returns a dict with a stable shape:

    {"kind": "...", "executed": bool, "exit_code": int|None,
     "duration_ms": int, "stdout": str, "stderr": str}

Actions never raise. Failures are reported as executed=True with a
non-zero exit_code, or executed=False with an error in stderr if the
runtime refused to attempt the action.

All actions support dry_run=True — in that mode they log what *would*
happen and return executed=False with a "DRY-RUN" stderr.
"""
from __future__ import annotations

import os
import shlex
import subprocess
import time
import urllib.error
import urllib.request
from typing import Any


def _run(cmd: list[str], timeout: float = 30.0) -> dict[str, Any]:
    start = time.monotonic()
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        return {
            "executed": True,
            "exit_code": r.returncode,
            "duration_ms": int((time.monotonic() - start) * 1000),
            "stdout": r.stdout[-2000:],
            "stderr": r.stderr[-2000:],
        }
    except FileNotFoundError as e:
        return {
            "executed": False,
            "exit_code": None,
            "duration_ms": int((time.monotonic() - start) * 1000),
            "stdout": "",
            "stderr": f"command not found: {e}",
        }
    except subprocess.TimeoutExpired:
        return {
            "executed": True,
            "exit_code": None,
            "duration_ms": int((time.monotonic() - start) * 1000),
            "stdout": "",
            "stderr": f"timeout after {timeout}s",
        }


def restart_systemd(target: str, host: str = "localhost",
                    dry_run: bool = False) -> dict[str, Any]:
    """systemctl restart <target>.

    For host != localhost, runs over ssh — ssh key auth must already work.
    """
    base = ["systemctl", "restart", target]
    if host not in ("localhost", "127.0.0.1", ""):
        cmd = ["ssh", "-o", "BatchMode=yes", "-o", "ConnectTimeout=5", host,
               "sudo", *base]
    else:
        cmd = ["sudo", *base] if os.geteuid() != 0 else base
    if dry_run:
        return {"kind": "restart_systemd", "executed": False, "exit_code": None,
                "duration_ms": 0, "stdout": "", "stderr": "DRY-RUN: " + " ".join(shlex.quote(c) for c in cmd)}
    out = _run(cmd, timeout=30.0)
    return {"kind": "restart_systemd", **out}


def restart_docker(container: str, host: str = "localhost",
                   dry_run: bool = False) -> dict[str, Any]:
    """docker restart <container>."""
    base = ["docker", "restart", container]
    cmd = ["ssh", "-o", "BatchMode=yes", "-o", "ConnectTimeout=5", host, *base] \
        if host not in ("localhost", "127.0.0.1", "") else base
    if dry_run:
        return {"kind": "restart_docker", "executed": False, "exit_code": None,
                "duration_ms": 0, "stdout": "", "stderr": "DRY-RUN: " + " ".join(shlex.quote(c) for c in cmd)}
    out = _run(cmd, timeout=30.0)
    return {"kind": "restart_docker", **out}


def disable_n8n_workflow(workflow_id: str, base_url: str | None = None,
                         api_key: str | None = None,
                         dry_run: bool = False) -> dict[str, Any]:
    """PATCH the n8n workflow to active=false."""
    base_url = base_url or os.environ.get("N8N_BASE_URL", "http://localhost:5678")
    api_key = api_key or os.environ.get("N8N_API_KEY", "")
    url = f"{base_url.rstrip('/')}/api/v1/workflows/{workflow_id}"
    if dry_run:
        return {"kind": "disable_n8n_workflow", "executed": False, "exit_code": None,
                "duration_ms": 0, "stdout": "", "stderr": f"DRY-RUN: PATCH {url} active=false"}
    start = time.monotonic()
    try:
        req = urllib.request.Request(
            url, method="PATCH",
            data=b'{"active":false}',
            headers={"Content-Type": "application/json", "X-N8N-API-KEY": api_key},
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            return {
                "kind": "disable_n8n_workflow",
                "executed": True,
                "exit_code": 0 if 200 <= resp.status < 300 else 1,
                "duration_ms": int((time.monotonic() - start) * 1000),
                "stdout": f"status={resp.status}",
                "stderr": "",
            }
    except urllib.error.HTTPError as e:
        return {
            "kind": "disable_n8n_workflow",
            "executed": True,
            "exit_code": 1,
            "duration_ms": int((time.monotonic() - start) * 1000),
            "stdout": "",
            "stderr": f"http_error={e.code}: {e.reason}",
        }
    except Exception as e:
        return {
            "kind": "disable_n8n_workflow",
            "executed": False,
            "exit_code": None,
            "duration_ms": int((time.monotonic() - start) * 1000),
            "stdout": "",
            "stderr": f"unreachable: {e}",
        }


def quarantine(target: str, marker_dir: str = "~/.fireclaw/quarantine",
               dry_run: bool = False) -> dict[str, Any]:
    """Mark a target as quarantined by touching a marker file.

    The target's launcher / process manager is expected to check for the
    marker and refuse to start when present. This is the simplest contract
    that works across systemd, docker, and shell-launched bots.
    """
    d = os.path.expanduser(marker_dir)
    marker = os.path.join(d, target.replace("/", "_") + ".quarantined")
    if dry_run:
        return {"kind": "quarantine", "executed": False, "exit_code": None,
                "duration_ms": 0, "stdout": "", "stderr": f"DRY-RUN: touch {marker}"}
    start = time.monotonic()
    try:
        os.makedirs(d, exist_ok=True)
        with open(marker, "w") as f:
            f.write(f"quarantined_at={time.time()}\n")
        return {
            "kind": "quarantine",
            "executed": True,
            "exit_code": 0,
            "duration_ms": int((time.monotonic() - start) * 1000),
            "stdout": f"marker={marker}",
            "stderr": "",
        }
    except OSError as e:
        return {
            "kind": "quarantine",
            "executed": True,
            "exit_code": 1,
            "duration_ms": int((time.monotonic() - start) * 1000),
            "stdout": "",
            "stderr": str(e),
        }


def alert_telegram(message: str, bot_token: str | None = None,
                   chat_id: str | None = None,
                   dry_run: bool = False) -> dict[str, Any]:
    """Send a Telegram message via Bot API. Used for escalation."""
    bot_token = bot_token or os.environ.get("FIRECLAW_TG_BOT_TOKEN", "")
    chat_id = chat_id or os.environ.get("FIRECLAW_TG_CHAT_ID", "")
    if dry_run:
        return {"kind": "alert_telegram", "executed": False, "exit_code": None,
                "duration_ms": 0, "stdout": "", "stderr": f"DRY-RUN: tg → {chat_id}: {message[:80]}"}
    if not bot_token or not chat_id:
        return {"kind": "alert_telegram", "executed": False, "exit_code": None,
                "duration_ms": 0, "stdout": "",
                "stderr": "skipped: FIRECLAW_TG_BOT_TOKEN / FIRECLAW_TG_CHAT_ID not set"}
    start = time.monotonic()
    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    body = f"chat_id={urllib.parse.quote(chat_id)}&text={urllib.parse.quote(message)}".encode()
    try:
        req = urllib.request.Request(url, data=body, method="POST",
                                     headers={"Content-Type": "application/x-www-form-urlencoded"})
        with urllib.request.urlopen(req, timeout=10) as resp:
            return {"kind": "alert_telegram", "executed": True,
                    "exit_code": 0 if 200 <= resp.status < 300 else 1,
                    "duration_ms": int((time.monotonic() - start) * 1000),
                    "stdout": f"status={resp.status}", "stderr": ""}
    except Exception as e:
        return {"kind": "alert_telegram", "executed": True, "exit_code": 1,
                "duration_ms": int((time.monotonic() - start) * 1000),
                "stdout": "", "stderr": str(e)}


def alert_only(message: str, dry_run: bool = False) -> dict[str, Any]:
    """No-op action for rules that just want to record an incident."""
    return {"kind": "alert_only", "executed": True, "exit_code": 0,
            "duration_ms": 0, "stdout": message, "stderr": ""}


# Dispatch table — only declared kinds are runnable.
DISPATCH = {
    "restart_systemd": lambda spec, dry_run: restart_systemd(
        spec["target"], spec.get("host", "localhost"), dry_run),
    "restart_docker": lambda spec, dry_run: restart_docker(
        spec["target"], spec.get("host", "localhost"), dry_run),
    "disable_n8n_workflow": lambda spec, dry_run: disable_n8n_workflow(
        spec["target"], spec.get("base_url"), spec.get("api_key"), dry_run),
    "quarantine": lambda spec, dry_run: quarantine(
        spec["target"], spec.get("marker_dir", "~/.fireclaw/quarantine"), dry_run),
    "alert_telegram": lambda spec, dry_run: alert_telegram(
        spec.get("message", "Fireclaw alert"),
        spec.get("bot_token"), spec.get("chat_id"), dry_run),
    "alert_only": lambda spec, dry_run: alert_only(
        spec.get("message", "Fireclaw incident"), dry_run),
}


def execute(spec: dict[str, Any], dry_run: bool = False) -> dict[str, Any]:
    kind = spec.get("kind")
    if kind not in DISPATCH:
        return {"kind": kind or "unknown", "executed": False, "exit_code": None,
                "duration_ms": 0, "stdout": "",
                "stderr": f"unknown action kind: {kind!r}"}
    return DISPATCH[kind](spec, dry_run)
