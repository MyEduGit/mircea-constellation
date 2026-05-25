#!/usr/bin/env python3
"""SeedanceClaw — AI video generation execution runtime.

Canonical role: controlled execution (video-generation sub-role).
Truthful label: deployable scaffold. Real handlers: text_to_video,
image_to_video, download_video. Requires FAL_KEY from fal.ai.

The allowlist boundary is preserved: nothing outside ALLOWED_HANDLERS
can run. Every call writes an evidence record.

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
from .generate import download_video, image_to_video, text_to_video

CLAW_NAME = os.getenv("CLAW_NAME", "SeedanceClaw")
DATA_ROOT = Path(os.getenv("DATA_ROOT", "/data"))
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
HTTP_HOST = os.getenv("HTTP_HOST", "0.0.0.0")
HTTP_PORT = int(os.getenv("HTTP_PORT", "8086"))

for _sub in ("videos", "images", "logs", "evidence"):
    (DATA_ROOT / _sub).mkdir(parents=True, exist_ok=True)

logging.basicConfig(
    level=LOG_LEVEL,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    handlers=[
        logging.FileHandler(DATA_ROOT / "logs" / "seedanceclaw.log"),
        logging.StreamHandler(sys.stdout),
    ],
)
logger = logging.getLogger(CLAW_NAME)


ALLOWED_HANDLERS: frozenset[str] = frozenset({
    "smoke_test",
    "text_to_video",
    "image_to_video",
    "download_video",
})


def write_evidence(handler: str, payload: dict, result: dict) -> str:
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
        "urantios_governed": True,
    }
    fn = f"evidence_{int(time.time() * 1000)}_{handler}.json"
    path = DATA_ROOT / "evidence" / fn
    path.write_text(json.dumps(ev, indent=2, default=str))
    logger.info(f"evidence: {fn}")
    return str(path)


def _probe_runtime() -> dict:
    fal_client_installed = True
    try:
        import fal_client  # noqa: F401
    except ImportError:
        fal_client_installed = False
    httpx_installed = True
    try:
        import httpx  # noqa: F401
    except ImportError:
        httpx_installed = False
    return {
        "fal_client_installed": fal_client_installed,
        "httpx_installed": httpx_installed,
        "fal_key_set": bool(os.getenv("FAL_KEY", "").strip()),
        "t2v_model": os.getenv(
            "SEEDANCE_MODEL_T2V",
            "fal-ai/bytedance/seedance/v1/pro/text-to-video",
        ),
        "i2v_model": os.getenv(
            "SEEDANCE_MODEL_I2V",
            "fal-ai/bytedance/seedance/v1/pro/image-to-video",
        ),
    }


async def _handle_smoke_test(payload: dict) -> dict:
    return {
        "status": "success",
        "handler": "smoke_test",
        "message": f"{CLAW_NAME} scaffold smoke test passed",
        "version": __version__,
        **_probe_runtime(),
    }


_HANDLERS: dict[str, Any] = {
    "smoke_test":    lambda p: _handle_smoke_test(p),
    "text_to_video": lambda p: text_to_video(p, DATA_ROOT),
    "image_to_video": lambda p: image_to_video(p, DATA_ROOT),
    "download_video": lambda p: download_video(p, DATA_ROOT),
}
assert set(_HANDLERS) == set(ALLOWED_HANDLERS), \
    "dispatch table must match ALLOWED_HANDLERS exactly"


async def safe_execute(handler: str, payload: dict) -> dict:
    if handler not in ALLOWED_HANDLERS:
        result = {"status": "rejected", "handler": handler,
                  "error": "not in SeedanceClaw allowlist"}
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


app = FastAPI(title=CLAW_NAME, version=__version__)


@app.get("/health")
def health() -> dict:
    return {
        "status": "healthy",
        "claw": CLAW_NAME,
        "version": __version__,
        "governed_by": "URANTiOS",
        "data_root": str(DATA_ROOT),
        "allowed_handlers": sorted(ALLOWED_HANDLERS),
        **_probe_runtime(),
    }


@app.post("/tasks")
async def run_task(
    handler: str = Body(..., embed=True),
    payload: dict = Body(default_factory=dict, embed=True),
) -> dict:
    return await safe_execute(handler, payload)


def _run_http_server() -> None:
    uvicorn.run(app, host=HTTP_HOST, port=HTTP_PORT, log_level="warning")


def main() -> int:
    parser = argparse.ArgumentParser(prog="seedanceclaw")
    parser.add_argument(
        "--mode",
        default="daemon",
        choices=("daemon", "one-shot"),
        help="daemon: HTTP server; one-shot: run smoke_test and exit",
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
