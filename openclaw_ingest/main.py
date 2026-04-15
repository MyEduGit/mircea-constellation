#!/usr/bin/env python3
"""OpenClaw@URANTiOS-ingest — execution runtime, ingestion sub-role.

Canonical role: controlled execution (singular).
Truthful label:  deployable scaffold with first real handler (ingest_normalize).

The other four canonical handlers (categorise_by_axes, cross_link,
governance_check, export_urantipedia) are declared in the allowlist and
dispatched to a 'not_implemented' stub pending a follow-up PR. The
allowlist boundary is preserved: nothing outside ALLOWED_HANDLERS can
run.

UrantiOS governed — Truth, Beauty, Goodness.
"""
from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import logging
import os
import sys
import time
from pathlib import Path
from threading import Thread
from typing import Any

import uvicorn
from fastapi import Body, FastAPI

from . import __version__

# ── Config (all via env, nothing hardcoded that the operator would override) ─
CLAW_NAME = os.getenv("CLAW_NAME", "OpenClaw@URANTiOS-ingest")
DATA_ROOT = Path(os.getenv("DATA_ROOT", "/data"))
DATASET_NAME = os.getenv("DATASET_NAME", "mircea_corpus")
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
HTTP_HOST = os.getenv("HTTP_HOST", "0.0.0.0")
HTTP_PORT = int(os.getenv("HTTP_PORT", "8080"))

# Ensure directory layout on every start (idempotent).
for _sub in ("ingest/chatcode", "ingested/chatcode", "classified",
             "canon", "logs", "evidence"):
    (DATA_ROOT / _sub).mkdir(parents=True, exist_ok=True)

logging.basicConfig(
    level=LOG_LEVEL,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    handlers=[
        logging.FileHandler(DATA_ROOT / "logs" / "openclaw.log"),
        logging.StreamHandler(sys.stdout),
    ],
)
logger = logging.getLogger(CLAW_NAME)

# ── Cognee init — single source of truth loaded as a proper import ─────
# cognee_config.py lives at the repo root and is COPY'd into /app by the
# Dockerfile. We import it rather than exec() so failures surface honestly.
COGNEE_READY = False
COGNEE_INIT_INFO: dict[str, Any] = {"initialized": False}
try:
    import cognee  # noqa: F401  (ensures lib is actually installed)
    import cognee_config  # repo-root module, copied into /app
    COGNEE_INIT_INFO = cognee_config.init(
        mode=os.getenv("COGNEE_MODE", "auto"),
        verbose=True,
    )
    COGNEE_READY = True
    logger.info(f"cognee initialised: {COGNEE_INIT_INFO}")
except Exception as exc:  # honest failure — scaffold still runs
    logger.warning(f"cognee init skipped: {exc}")

# ── Allowlist — canonical boundary. Nothing bypasses this. ─────────────
ALLOWED_HANDLERS: frozenset[str] = frozenset({
    "ingest_normalize",
    "categorise_by_axes",
    "cross_link",
    "governance_check",
    "export_urantipedia",
    "smoke_test",
})


# ── Evidence emission — every handler call leaves proof. ───────────────
def write_evidence(handler: str, payload: dict, result: dict) -> str:
    """Append an evidence record for every invocation.

    Filename uses integer millisecond epoch + handler name to avoid collisions.
    sha256 over canonicalised JSON of both payload and result — deterministic
    across runs, same file → same hash.
    """
    ev = {
        "claw": CLAW_NAME,
        "version": __version__,
        "handler": handler,
        "payload_sha256": hashlib.sha256(
            json.dumps(payload, sort_keys=True, default=str).encode("utf-8")
        ).hexdigest(),
        "result_sha256": hashlib.sha256(
            json.dumps(result, sort_keys=True, default=str).encode("utf-8")
        ).hexdigest(),
        "ts_epoch": time.time(),
        "ts_iso": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "cognee_ready": COGNEE_READY,
        "urantios_governed": True,
    }
    fn = f"evidence_{int(time.time() * 1000)}_{handler}.json"
    path = DATA_ROOT / "evidence" / fn
    path.write_text(json.dumps(ev, indent=2, default=str))
    logger.info(f"evidence: {fn}")
    return str(path)


# ── Handlers ──────────────────────────────────────────────────────────
async def _handle_smoke_test(payload: dict) -> dict:
    return {
        "status": "success",
        "handler": "smoke_test",
        "message": f"{CLAW_NAME} scaffold smoke test passed",
        "version": __version__,
        "cognee_ready": COGNEE_READY,
    }


async def _handle_ingest_normalize(payload: dict) -> dict:
    """First real handler.

    Reads every ``*.jsonl`` file from ``/data/ingest/chatcode/``, adds each
    file's content to Cognee under DATASET_NAME with ``source:chatcode_imac``
    node-set tagging, and moves the processed file to
    ``/data/ingested/chatcode/`` so the next run does not re-ingest it.

    Honest behaviour when cognee is unavailable: refuse to act and return the
    list of pending files unchanged. No silent partial success.
    """
    src_dir = DATA_ROOT / "ingest" / "chatcode"
    dst_dir = DATA_ROOT / "ingested" / "chatcode"
    dst_dir.mkdir(parents=True, exist_ok=True)
    files = sorted(src_dir.glob("*.jsonl"))

    if not files:
        return {"status": "success", "handler": "ingest_normalize",
                "normalized": 0, "message": "no jsonl files in ingest/chatcode"}

    if not COGNEE_READY:
        return {"status": "error", "handler": "ingest_normalize",
                "error": "cognee_not_ready",
                "files_pending": [f.name for f in files],
                "hint": "check cognee_config.init() output and Ollama reachability"}

    processed = 0
    errors: list[dict[str, str]] = []
    for f in files:
        try:
            content = f.read_text(encoding="utf-8")
            sha = hashlib.sha256(content.encode("utf-8")).hexdigest()
            # cognee.add is the canonical ingestion call; signature verified
            # against cognee 0.1.x.
            await cognee.add(
                content,
                dataset_name=DATASET_NAME,
                node_set=[
                    "source:chatcode_imac",
                    f"file:{f.name}",
                    f"sha256:{sha}",
                ],
            )
            dest = dst_dir / f.name
            f.rename(dest)
            processed += 1
            logger.info(
                f"ingest_normalize: {f.name} -> ingested/ (sha256={sha[:12]})")
        except Exception as exc:
            errors.append({"file": f.name, "error": str(exc)})
            logger.exception(f"ingest_normalize failed on {f.name}")

    return {
        "status": "success" if not errors else "partial",
        "handler": "ingest_normalize",
        "normalized": processed,
        "errors": errors,
        "dataset": DATASET_NAME,
    }


async def _handle_stub(name: str, payload: dict) -> dict:
    return {
        "status": "not_implemented",
        "handler": name,
        "reason": "scaffold; follow-up PR will implement.",
    }


# Dispatch table — 1:1 with ALLOWED_HANDLERS. Changes here require changes
# to the allowlist above (and vice versa); the invariant is asserted below.
_HANDLERS = {
    "smoke_test": _handle_smoke_test,
    "ingest_normalize": _handle_ingest_normalize,
    "categorise_by_axes": lambda p: _handle_stub("categorise_by_axes", p),
    "cross_link":         lambda p: _handle_stub("cross_link", p),
    "governance_check":   lambda p: _handle_stub("governance_check", p),
    "export_urantipedia": lambda p: _handle_stub("export_urantipedia", p),
}
assert set(_HANDLERS) == set(ALLOWED_HANDLERS), \
    "dispatch table must match ALLOWED_HANDLERS exactly"


async def safe_execute(handler: str, payload: dict) -> dict:
    """Evaluate against allowlist, dispatch, write evidence. No bypass path."""
    if handler not in ALLOWED_HANDLERS:
        result = {"status": "rejected", "handler": handler,
                  "error": "not in OpenClaw allowlist"}
        write_evidence(handler, payload, result)
        return result
    fn = _HANDLERS[handler]
    try:
        result = await fn(payload)
    except Exception as exc:
        logger.exception(f"handler {handler} crashed")
        result = {"status": "error", "handler": handler, "error": str(exc)}
    write_evidence(handler, payload, result)
    return result


# ── HTTP surface (local-only; port published to 127.0.0.1 in compose) ──
app = FastAPI(title=CLAW_NAME, version=__version__)


@app.get("/health")
def health() -> dict:
    return {
        "status": "healthy",
        "claw": CLAW_NAME,
        "version": __version__,
        "governed_by": "URANTiOS",
        "cognee_ready": COGNEE_READY,
        "cognee_init": COGNEE_INIT_INFO,
        "dataset": DATASET_NAME,
        "allowed_handlers": sorted(ALLOWED_HANDLERS),
    }


@app.post("/tasks")
async def run_task(
    handler: str = Body(..., embed=True),
    payload: dict = Body(default_factory=dict, embed=True),
) -> dict:
    return await safe_execute(handler, payload)


def _run_http_server() -> None:
    uvicorn.run(app, host=HTTP_HOST, port=HTTP_PORT, log_level="warning")


# ── Entry ─────────────────────────────────────────────────────────────
def main() -> int:
    parser = argparse.ArgumentParser(prog="openclaw_ingest")
    parser.add_argument(
        "--mode",
        default="ingest-daemon",
        choices=("ingest-daemon", "one-shot"),
        help="ingest-daemon: run HTTP server; one-shot: run smoke_test and exit",
    )
    args = parser.parse_args()
    logger.info(f"{CLAW_NAME} v{__version__} starting (mode={args.mode})")

    smoke = asyncio.run(safe_execute("smoke_test", {}))
    logger.info(f"startup smoke_test: {smoke.get('status')}")

    if args.mode == "one-shot":
        return 0 if smoke.get("status") == "success" else 1

    Thread(target=_run_http_server, daemon=True).start()
    logger.info(f"{CLAW_NAME} daemon ready — POST /tasks to invoke handlers")
    try:
        while True:
            time.sleep(60)
    except KeyboardInterrupt:
        logger.info("shutdown")
        return 0


if __name__ == "__main__":
    sys.exit(main())
