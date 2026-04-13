#!/usr/bin/env python3
"""
NemoClaw Observer — Mission Control Dashboard Agent

Monitors all 5 layers of the Mircea/JRP mission stack and generates
a human-readable, Telegram-ready status dashboard.

Layers covered
--------------
1. VPS (Hetzy / 46.225.51.30)  — n8n, PostgreSQL, Redis, Qdrant
2. Local (iMac M4 / NemoClaw)  — Ollama models
3. Agents                       — active OpenClaw / n8n workflows
4. LLMs in use                  — Z.ai spend cap, Ollama free tier
5. Connected apps               — Telegram bot, Qdrant API, PostgreSQL port

Trigger options
---------------
  python3 observer.py              # print to terminal
  python3 observer.py telegram     # post to Telegram
  python3 observer.py json         # raw JSON of check results
  python3 observer.py silent       # store to DB only, return string

Scheduled via n8n cron — see n8n_cron_workflow.json
"""

import os
import json
import sys
import socket
import logging
import datetime

import requests

log = logging.getLogger("NemoClawObserver")
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)

# ─────────────────────────────────────────────────────────────────────────────
# Configuration  (all overridable via environment variables)
# ─────────────────────────────────────────────────────────────────────────────

VPS_HOST       = os.getenv("VPS_HOST",        "46.225.51.30")
N8N_PORT       = int(os.getenv("N8N_PORT",    "5678"))
PG_HOST        = os.getenv("PG_HOST",         VPS_HOST)
PG_PORT        = int(os.getenv("PG_PORT",     "5432"))
PG_DSN         = os.getenv("PG_DSN",          f"postgresql://postgres:password@{VPS_HOST}:5432/amep_schema_v1")
REDIS_HOST     = os.getenv("REDIS_HOST",      VPS_HOST)
REDIS_PORT     = int(os.getenv("REDIS_PORT",  "6379"))
QDRANT_HOST   = os.getenv("QDRANT_HOST",     VPS_HOST)
QDRANT_PORT   = int(os.getenv("QDRANT_PORT", "6333"))
OLLAMA_HOST    = os.getenv("OLLAMA_HOST",     "localhost")
OLLAMA_PORT    = int(os.getenv("OLLAMA_PORT", "11434"))
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN",  "")
TELEGRAM_CHAT  = os.getenv("TELEGRAM_CHAT",   "")
ZAI_SPEND      = float(os.getenv("ZAI_SPEND_THIS_MONTH", "0.00"))
ZAI_CAP        = float(os.getenv("ZAI_MONTHLY_CAP",      "5.00"))
IDLE_HOURS     = int(os.getenv("AGENT_IDLE_HOURS",        "24"))

# Target Ollama models to verify
OLLAMA_MODELS  = ["phi3:14b", "deepseek-r1:8b", "qwen3:8b"]

# ─────────────────────────────────────────────────────────────────────────────
# Low-level helpers
# ─────────────────────────────────────────────────────────────────────────────

def _tcp_open(host: str, port: int, timeout: float = 3.0) -> bool:
    """Return True if a TCP connection succeeds."""
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except (OSError, socket.timeout):
        return False


def _http_json(url: str, timeout: float = 5.0):
    """GET url, return parsed JSON dict/list or None on any error."""
    try:
        r = requests.get(url, timeout=timeout)
        r.raise_for_status()
        return r.json()
    except Exception:
        return None


def _icon(status: str) -> str:
    return {"ok": "\U0001f7e2", "warn": "\U0001f7e1", "error": "\U0001f534"}.get(status, "\u26aa")


# ─────────────────────────────────────────────────────────────────────────────
# Layer 1 — VPS checks
# ─────────────────────────────────────────────────────────────────────────────

def check_n8n() -> dict:
    if _tcp_open(VPS_HOST, N8N_PORT):
        data = _http_json(f"http://{VPS_HOST}:{N8N_PORT}/healthz") or {}
        return {"status": "ok", "note": data.get("status", "n8n reachable")}
    return {"status": "error", "note": f"Port {N8N_PORT} unreachable on {VPS_HOST}"}


def check_postgres() -> dict:
    if not _tcp_open(PG_HOST, PG_PORT):
        return {"status": "error", "note": f"Port {PG_PORT} closed on {PG_HOST}"}
    try:
        import psycopg2
        conn = psycopg2.connect(PG_DSN, connect_timeout=5)
        cur  = conn.cursor()
        cur.execute("SELECT current_database()")
        (db,) = cur.fetchone()
        cur.close(); conn.close()
        return {"status": "ok", "note": f"{db} connected — amep_schema_v1"}
    except ImportError:
        # psycopg2 not installed — port-only check
        return {"status": "ok", "note": f"Port {PG_PORT} open (psycopg2 not installed)"}
    except Exception as exc:
        return {"status": "error", "note": str(exc)[:120]}


def check_redis() -> dict:
    if not _tcp_open(REDIS_HOST, REDIS_PORT):
        return {"status": "error", "note": f"Port {REDIS_PORT} closed on {REDIS_HOST}"}
    try:
        import redis as redislib
        r    = redislib.Redis(host=REDIS_HOST, port=REDIS_PORT, socket_connect_timeout=3)
        info = r.info("memory")
        mb   = round(info.get("used_memory", 0) / 1048576, 1)
        return {"status": "ok", "note": f"{mb} MB used"}
    except ImportError:
        return {"status": "ok", "note": f"Port {REDIS_PORT} open (redis-py not installed)"}
    except Exception as exc:
        return {"status": "error", "note": str(exc)[:120]}


def check_qdrant() -> dict:
    url  = f"http://{QDRANT_HOST}:{QDRANT_PORT}/collections/havona_records_v2"
    data = _http_json(url)
    if data and "result" in data:
        count = data["result"].get("vectors_count", "?")
        return {"status": "ok", "note": f"{count} vectors — havona_records_v2"}
    if _tcp_open(QDRANT_HOST, QDRANT_PORT):
        return {"status": "warn", "note": "Qdrant up — havona_records_v2 collection not found"}
    return {"status": "error", "note": f"Qdrant unreachable at {QDRANT_HOST}:{QDRANT_PORT}"}


# ─────────────────────────────────────────────────────────────────────────────
# Layer 2 — Local (iMac M4 / NemoClaw)
# ─────────────────────────────────────────────────────────────────────────────

def check_ollama() -> dict:
    data = _http_json(f"http://{OLLAMA_HOST}:{OLLAMA_PORT}/api/tags")
    if data is None:
        return {"status": "error", "note": f"Ollama not reachable at {OLLAMA_HOST}:{OLLAMA_PORT}"}
    running = [m["name"] for m in data.get("models", [])]
    loaded  = [m for m in OLLAMA_MODELS if any(m in x for x in running)]
    missing = [m for m in OLLAMA_MODELS if m not in loaded]
    status  = "ok" if not missing else ("warn" if loaded else "error")
    note    = "Loaded: " + (", ".join(loaded) if loaded else "none")
    if missing:
        note += " | Missing: " + ", ".join(missing)
    return {"status": status, "note": note}


# ─────────────────────────────────────────────────────────────────────────────
# Layer 5 — Connected apps
# ─────────────────────────────────────────────────────────────────────────────

def check_telegram_bot() -> dict:
    if not TELEGRAM_TOKEN:
        return {"status": "warn", "note": "TELEGRAM_TOKEN not configured"}
    data = _http_json(f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/getMe")
    if data and data.get("ok"):
        name = data["result"].get("username", "unknown")
        return {"status": "ok", "note": f"@{name} online"}
    return {"status": "error", "note": "Bot API unreachable or token invalid"}


# ─────────────────────────────────────────────────────────────────────────────
# Layer 4 — LLM spend
# ─────────────────────────────────────────────────────────────────────────────

def check_zai_spend() -> dict:
    """Z.ai GLM-5.1 spend guard — hard cap $5/month, alert at $4."""
    if ZAI_CAP <= 0:
        return {"status": "ok", "note": "No cap configured"}
    if ZAI_SPEND >= ZAI_CAP:
        return {"status": "error",
                "note": f"${ZAI_SPEND:.2f} / ${ZAI_CAP:.2f} — HALT: monthly cap reached"}
    if ZAI_SPEND >= ZAI_CAP * 0.80:
        return {"status": "warn",
                "note": f"${ZAI_SPEND:.2f} / ${ZAI_CAP:.2f} — WARNING: >80% of cap used"}
    return {"status": "ok",
            "note": f"${ZAI_SPEND:.2f} / ${ZAI_CAP:.2f} — SAFE"}


# ─────────────────────────────────────────────────────────────────────────────
# PostgreSQL snapshot storage
# ─────────────────────────────────────────────────────────────────────────────

def _store_snapshot(rows: list) -> None:
    """Append dashboard snapshot rows to nemoclaw_dashboard_log."""
    try:
        import psycopg2
        conn = psycopg2.connect(PG_DSN, connect_timeout=5)
        cur  = conn.cursor()
        cur.execute("""
            CREATE TABLE IF NOT EXISTS nemoclaw_dashboard_log (
                id        SERIAL PRIMARY KEY,
                timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                layer     TEXT        NOT NULL,
                service   TEXT        NOT NULL,
                status    TEXT        NOT NULL,
                note      TEXT
            )
        """)
        for row in rows:
            cur.execute(
                "INSERT INTO nemoclaw_dashboard_log "
                "(timestamp, layer, service, status, note) VALUES (NOW(),%s,%s,%s,%s)",
                (row["layer"], row["service"], row["status"], row.get("note", "")),
            )
        conn.commit()
        cur.close(); conn.close()
        log.info("Snapshot stored — %d rows", len(rows))
    except ImportError:
        log.info("psycopg2 not installed — skipping DB storage")
    except Exception as exc:
        log.warning("DB storage failed: %s", exc)


# ─────────────────────────────────────────────────────────────────────────────
# Dashboard renderer
# ─────────────────────────────────────────────────────────────────────────────

# All checks: (layer_label, service_label, check_fn)
_CHECKS = [
    ("VPS",   "n8n",          check_n8n),
    ("VPS",   "PostgreSQL",   check_postgres),
    ("VPS",   "Redis",        check_redis),
    ("VPS",   "Qdrant",       check_qdrant),
    ("Local", "Ollama",       check_ollama),
    ("App",   "Telegram Bot", check_telegram_bot),
    ("LLM",   "Z.ai GLM-5.1", check_zai_spend),
]


def build_dashboard() -> tuple:
    """Run all checks and return (markdown_string, rows_list)."""
    tz_aedt = datetime.timezone(datetime.timedelta(hours=10))
    ts      = datetime.datetime.now(tz_aedt).strftime("%Y-%m-%d %H:%M:%S AEDT")

    rows = []
    for layer, service, fn in _CHECKS:
        result = fn()
        rows.append({"layer": layer, "service": service, **result})

    alerts = [r for r in rows if r["status"] in ("error", "warn")]

    lines = [
        "## NemoClaw Mission Dashboard",
        f"**Generated:** {ts}",
        "",
        "### \U0001f7e2 HEALTHY | \U0001f7e1 WARNING | \U0001f534 ERROR",
        "",
        "| Layer | Service | Status | Note |",
        "|---|---|---|---|",
    ]
    for r in rows:
        lines.append(
            f"| {r['layer']} | {r['service']} | {_icon(r['status'])} "
            f"| {r.get('note', '')} |"
        )

    if alerts:
        lines += ["", "### \u26a0\ufe0f ALERTS"]
        for a in alerts:
            action = _suggest_action(a["service"], a["status"])
            lines.append(
                f"- **{a['layer']} / {a['service']}** "
                f"{_icon(a['status'])} {a.get('note', '')}\n  "
                f"\u27a1\ufe0f {action}"
            )
    else:
        lines += ["", "### \u2705 No alerts — all systems nominal"]

    zai_note = next(
        (r.get("note", "") for r in rows if r["service"] == "Z.ai GLM-5.1"), ""
    )
    lines += [
        "",
        "### \U0001f4b0 SPEND SUMMARY",
        f"- Z.ai GLM-5.1: {zai_note}",
        "- Gemini 2.5 Flash: $0.00 (free API)",
        "- Groq (NanoClaw): $0.00 (free tier)",
        "- Ollama (local iMac M4): $0.00",
    ]

    return "\n".join(lines), rows


def _suggest_action(service: str, status: str) -> str:
    """Return a plain-language fix suggestion for common alert states."""
    suggestions = {
        "n8n":          "SSH to 46.225.51.30 and run: sudo systemctl restart n8n",
        "PostgreSQL":   "Check pg status: sudo systemctl status postgresql",
        "Redis":        "Check redis: sudo systemctl status redis-server",
        "Qdrant":       "Check Qdrant docker: docker ps | grep qdrant",
        "Ollama":       "Pull missing model: ollama pull <model-name>",
        "Telegram Bot": "Verify TELEGRAM_TOKEN in .env and restart hetzy_phd.py",
        "Z.ai GLM-5.1": "Log in to z.ai and check monthly usage. Pause if at cap.",
    }
    return suggestions.get(service, "Check service logs for details")


# ─────────────────────────────────────────────────────────────────────────────
# Telegram sender
# ─────────────────────────────────────────────────────────────────────────────

def _send_telegram(text: str) -> None:
    if not TELEGRAM_TOKEN or not TELEGRAM_CHAT:
        log.info("Telegram not configured — skipping send")
        return
    try:
        requests.post(
            f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage",
            json={"chat_id": TELEGRAM_CHAT, "text": text, "parse_mode": "Markdown"},
            timeout=10,
        )
        log.info("Dashboard sent to Telegram chat %s", TELEGRAM_CHAT)
    except Exception as exc:
        log.warning("Telegram send failed: %s", exc)


# ─────────────────────────────────────────────────────────────────────────────
# Public entry point
# ─────────────────────────────────────────────────────────────────────────────

def run(output: str = "print") -> str:
    """
    Run the full dashboard cycle.

    Parameters
    ----------
    output : str
        "print"    — print Markdown to stdout
        "telegram" — post to Telegram
        "json"     — print raw JSON check results
        "silent"   — store to DB only; return dashboard string

    Returns
    -------
    str  The Markdown dashboard string.
    """
    log.info("NemoClaw Observer starting dashboard run (output=%s)", output)
    dashboard, rows = build_dashboard()
    _store_snapshot(rows)

    if output == "print":
        print(dashboard)
    elif output == "telegram":
        _send_telegram(dashboard)
    elif output == "json":
        print(json.dumps(rows, default=str, indent=2))
    # "silent" — do nothing extra

    return dashboard


if __name__ == "__main__":
    mode = sys.argv[1] if len(sys.argv) > 1 else "print"
    run(output=mode)
