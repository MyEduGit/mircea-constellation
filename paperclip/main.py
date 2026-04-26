#!/usr/bin/env python3
"""Paperclip — evidence bundler execution runtime.

Canonical role: evidence preservation.
Singular contract: sweep evidence records emitted by other claws,
bundle them into tamper-evident packages, and expose a query surface.

Real handlers:
  - bundle_evidence   collect + bundle all evidence records found in EVIDENCE_DIRS
  - list_bundles      list existing bundles (metadata only, no full records)
  - get_bundle        retrieve a specific bundle by bundle_id

Standard handler:
  - smoke_test

EVIDENCE_DIRS (env, comma-separated, default: /data/evidence):
    Directories to sweep for claw evidence records. In a shared-volume
    deployment, mount each claw's /data/evidence/ here; in a single-box
    deployment the single default path suffices.

Idempotency: bundle_evidence computes a SHA-256 over the sorted canonical
JSON of all records found. If a bundle with that content hash already
exists, the call is a no-op and returns the existing bundle_id.

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

# ── Config ────────────────────────────────────────────────────────────────
CLAW_NAME = os.getenv("CLAW_NAME", "Paperclip")
DATA_ROOT = Path(os.getenv("DATA_ROOT", "/data"))
# Comma-separated list of directories that contain claw evidence JSON files.
_EVIDENCE_DIRS_RAW = os.getenv("EVIDENCE_DIRS", str(DATA_ROOT / "evidence"))
EVIDENCE_DIRS: list[Path] = [
    Path(p.strip()) for p in _EVIDENCE_DIRS_RAW.split(",") if p.strip()
]
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
HTTP_HOST = os.getenv("HTTP_HOST", "0.0.0.0")
HTTP_PORT = int(os.getenv("HTTP_PORT", "8083"))

# Pre-create directory layout (idempotent).
for _sub in ("bundles", "evidence", "logs"):
    (DATA_ROOT / _sub).mkdir(parents=True, exist_ok=True)

logging.basicConfig(
    level=LOG_LEVEL,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    handlers=[
        logging.FileHandler(DATA_ROOT / "logs" / "paperclip.log"),
        logging.StreamHandler(sys.stdout),
    ],
)
logger = logging.getLogger(CLAW_NAME)


# ── Allowlist ─────────────────────────────────────────────────────────────
ALLOWED_HANDLERS: frozenset[str] = frozenset({
    "smoke_test",
    "bundle_evidence",
    "list_bundles",
    "get_bundle",
})


# ── Evidence emission (Paperclip's OWN invocations) ──────────────────────
def write_evidence(handler: str, payload: dict, result: dict) -> str:
    ev = {
        "claw": CLAW_NAME,
        "version": __version__,
        "handler": handler,
        "payload_sha256": hashlib.sha256(
            json.dumps(payload, sort_keys=True, default=str).encode()
        ).hexdigest(),
        "result_sha256": hashlib.sha256(
            json.dumps(result, sort_keys=True, default=str).encode()
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


# ── Evidence sweeper ──────────────────────────────────────────────────────
def _sweep_evidence() -> tuple[list[dict[str, Any]], list[dict[str, str]]]:
    """Read all evidence JSON files from EVIDENCE_DIRS.

    Returns (records, errors). Records are deduplicated by filename (last
    directory wins, so later mounts can shadow earlier ones). Sorted by
    ts_epoch ascending (oldest first).
    """
    seen: dict[str, dict[str, Any]] = {}  # filename → record
    errors: list[dict[str, str]] = []

    for d in EVIDENCE_DIRS:
        if not d.exists():
            logger.debug(f"evidence dir absent, skipping: {d}")
            continue
        for f in sorted(d.glob("*.json")):
            try:
                rec = json.loads(f.read_text())
                # Attach source path so bundles are fully self-describing.
                rec["_source_path"] = str(f)
                seen[f.name] = rec
            except Exception as exc:
                errors.append({"file": str(f), "error": str(exc)})
                logger.warning(f"sweep: unreadable {f}: {exc}")

    records = sorted(seen.values(), key=lambda r: r.get("ts_epoch", 0))
    return records, errors


def _bundle_sha256(records: list[dict]) -> str:
    canonical = json.dumps(
        [
            {k: v for k, v in r.items() if k != "_source_path"}
            for r in records
        ],
        sort_keys=True,
        default=str,
    ).encode()
    return hashlib.sha256(canonical).hexdigest()


def _find_bundle_by_content_sha(content_sha: str) -> Path | None:
    bundles_dir = DATA_ROOT / "bundles"
    for p in bundles_dir.glob("*.bundle.json"):
        try:
            meta = json.loads(p.read_text())
            if meta.get("bundle_content_sha256") == content_sha:
                return p
        except Exception:
            pass
    return None


def _bundle_meta(bundle: dict) -> dict:
    return {
        k: v for k, v in bundle.items() if k != "records"
    }


# ── Handlers ──────────────────────────────────────────────────────────────
async def _handle_smoke_test(_payload: dict) -> dict:
    dir_status = []
    total_records = 0
    for d in EVIDENCE_DIRS:
        count = len(list(d.glob("*.json"))) if d.exists() else 0
        total_records += count
        dir_status.append({"path": str(d), "exists": d.exists(), "records": count})

    bundles_dir = DATA_ROOT / "bundles"
    bundle_count = len(list(bundles_dir.glob("*.bundle.json")))

    return {
        "status": "success",
        "handler": "smoke_test",
        "message": f"{CLAW_NAME} smoke test passed",
        "version": __version__,
        "evidence_dirs": dir_status,
        "total_evidence_records": total_records,
        "bundle_count": bundle_count,
        "bundles_dir": str(bundles_dir),
    }


async def _handle_bundle_evidence(payload: dict) -> dict:
    """Sweep all EVIDENCE_DIRS, bundle records into /data/bundles/.

    Idempotent: if a bundle whose content hash matches the current sweep
    already exists, return its id without writing a new file.

    Optional payload keys:
      - filter_claw:    only include records from this claw name
      - filter_handler: only include records from this handler name
      - label:          arbitrary string attached to the bundle (for human use)
    """
    filter_claw = payload.get("filter_claw")
    filter_handler = payload.get("filter_handler")
    label = payload.get("label", "")

    records, sweep_errors = _sweep_evidence()

    if filter_claw:
        records = [r for r in records if r.get("claw") == filter_claw]
    if filter_handler:
        records = [r for r in records if r.get("handler") == filter_handler]

    if not records:
        return {
            "status": "success",
            "handler": "bundle_evidence",
            "message": "no evidence records found matching filters",
            "record_count": 0,
            "sweep_errors": sweep_errors,
            "evidence_dirs": [str(d) for d in EVIDENCE_DIRS],
        }

    content_sha = _bundle_sha256(records)
    existing = _find_bundle_by_content_sha(content_sha)
    if existing:
        bundle_id = existing.stem.replace(".bundle", "")
        logger.info(f"bundle_evidence: content unchanged — existing bundle {bundle_id}")
        return {
            "status": "success",
            "handler": "bundle_evidence",
            "bundle_id": bundle_id,
            "bundle_content_sha256": content_sha,
            "record_count": len(records),
            "existing": True,
            "sweep_errors": sweep_errors,
        }

    ts_ms = int(time.time() * 1000)
    bundle_id = f"{time.strftime('%Y%m%dT%H%M%S')}_{content_sha[:12]}"

    claws = sorted({r.get("claw", "unknown") for r in records})
    handlers_seen = sorted({r.get("handler", "unknown") for r in records})

    bundle = {
        "bundle_id": bundle_id,
        "bundle_content_sha256": content_sha,
        "bundled_by": CLAW_NAME,
        "paperclip_version": __version__,
        "bundled_at_epoch": time.time(),
        "bundled_at_iso": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "label": label,
        "record_count": len(records),
        "claws_included": claws,
        "handlers_included": handlers_seen,
        "evidence_dirs_swept": [str(d) for d in EVIDENCE_DIRS],
        "filter_claw": filter_claw,
        "filter_handler": filter_handler,
        "sweep_errors": sweep_errors,
        "urantios_governed": True,
        "records": [
            {k: v for k, v in r.items() if k != "_source_path"}
            for r in records
        ],
    }

    bundle_path = DATA_ROOT / "bundles" / f"{bundle_id}.bundle.json"
    bundle_path.write_text(json.dumps(bundle, indent=2, default=str))

    logger.info(
        f"bundle_evidence: {bundle_id} — {len(records)} records "
        f"from {claws} sha={content_sha[:12]}"
    )
    return {
        "status": "success",
        "handler": "bundle_evidence",
        "bundle_id": bundle_id,
        "bundle_content_sha256": content_sha,
        "record_count": len(records),
        "claws_included": claws,
        "handlers_included": handlers_seen,
        "existing": False,
        "bundle_path": str(bundle_path),
        "sweep_errors": sweep_errors,
    }


async def _handle_list_bundles(payload: dict) -> dict:
    """List existing bundles newest-first, metadata only (no full records).

    Optional payload keys:
      - limit: max number of bundles to return (default: 50)
    """
    limit = int(payload.get("limit", 50))
    bundles_dir = DATA_ROOT / "bundles"
    summaries: list[dict] = []
    errors: list[dict[str, str]] = []

    for p in sorted(bundles_dir.glob("*.bundle.json"),
                    key=lambda f: f.stat().st_mtime, reverse=True):
        if len(summaries) >= limit:
            break
        try:
            bundle = json.loads(p.read_text())
            summaries.append(_bundle_meta(bundle))
        except Exception as exc:
            errors.append({"file": p.name, "error": str(exc)})
            logger.warning(f"list_bundles: unreadable {p.name}: {exc}")

    return {
        "status": "success",
        "handler": "list_bundles",
        "bundle_count": len(summaries),
        "limit": limit,
        "bundles": summaries,
        "errors": errors,
    }


async def _handle_get_bundle(payload: dict) -> dict:
    """Return the full content of a bundle by bundle_id.

    Required payload key: bundle_id
    """
    bundle_id = payload.get("bundle_id")
    if not bundle_id or not isinstance(bundle_id, str):
        return {
            "status": "error",
            "handler": "get_bundle",
            "error": "missing_bundle_id",
        }

    # Sanitise: reject traversal attempts.
    if "/" in bundle_id or "\\" in bundle_id or ".." in bundle_id:
        return {
            "status": "error",
            "handler": "get_bundle",
            "error": "invalid_bundle_id",
        }

    bundle_path = DATA_ROOT / "bundles" / f"{bundle_id}.bundle.json"
    if not bundle_path.exists():
        return {
            "status": "error",
            "handler": "get_bundle",
            "error": "bundle_not_found",
            "bundle_id": bundle_id,
        }

    try:
        bundle = json.loads(bundle_path.read_text())
    except Exception as exc:
        return {
            "status": "error",
            "handler": "get_bundle",
            "error": f"bundle_unreadable: {exc}",
            "bundle_id": bundle_id,
        }

    return {
        "status": "success",
        "handler": "get_bundle",
        "bundle_id": bundle_id,
        "bundle": bundle,
    }


# ── Dispatch ──────────────────────────────────────────────────────────────
_HANDLERS: dict[str, Any] = {
    "smoke_test":     lambda p: _handle_smoke_test(p),
    "bundle_evidence": lambda p: _handle_bundle_evidence(p),
    "list_bundles":   lambda p: _handle_list_bundles(p),
    "get_bundle":     lambda p: _handle_get_bundle(p),
}
assert set(_HANDLERS) == set(ALLOWED_HANDLERS), \
    "dispatch table must match ALLOWED_HANDLERS exactly"


async def safe_execute(handler: str, payload: dict) -> dict:
    if handler not in ALLOWED_HANDLERS:
        result = {"status": "rejected", "handler": handler,
                  "error": "not in Paperclip allowlist"}
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


# ── HTTP surface ──────────────────────────────────────────────────────────
app = FastAPI(title=CLAW_NAME, version=__version__)


@app.get("/health")
def health() -> dict:
    return {
        "status": "healthy",
        "claw": CLAW_NAME,
        "version": __version__,
        "governed_by": "URANTiOS",
        "data_root": str(DATA_ROOT),
        "evidence_dirs": [str(d) for d in EVIDENCE_DIRS],
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


# ── Entry ─────────────────────────────────────────────────────────────────
def main() -> int:
    parser = argparse.ArgumentParser(prog="paperclip")
    parser.add_argument(
        "--mode",
        default="daemon",
        choices=("daemon", "one-shot"),
        help="daemon: run HTTP server; one-shot: smoke_test and exit",
    )
    args = parser.parse_args()
    logger.info(f"{CLAW_NAME} v{__version__} starting (mode={args.mode})")

    smoke = asyncio.run(safe_execute("smoke_test", {}))
    logger.info(f"startup smoke_test: {smoke.get('status')}")

    if args.mode == "one-shot":
        return 0 if smoke.get("status") == "success" else 1

    Thread(target=_run_http_server, daemon=True).start()
    logger.info(
        f"{CLAW_NAME} daemon ready — POST /tasks to invoke handlers\n"
        f"  Evidence dirs: {[str(d) for d in EVIDENCE_DIRS]}\n"
        f"  Bundles dir:   {DATA_ROOT / 'bundles'}"
    )
    try:
        while True:
            import time as _t
            _t.sleep(60)
    except KeyboardInterrupt:
        logger.info("shutdown")
        return 0


if __name__ == "__main__":
    sys.exit(main())
