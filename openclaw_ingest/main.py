#!/usr/bin/env python3
"""OpenClaw@URANTiOS-ingest — execution runtime, ingestion sub-role.

Canonical role: controlled execution (singular).
Truthful label:  deployable scaffold with two real handlers
(``ingest_normalize`` and ``categorise_by_axes``).

Three of the five canonical handlers (cross_link, governance_check,
export_urantipedia) remain declared-but-stubbed pending follow-up PR.
The allowlist boundary is preserved: nothing outside ALLOWED_HANDLERS
can run.

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
import urllib.error
import urllib.request
from pathlib import Path
from threading import Thread
from typing import Any

import uvicorn
from fastapi import Body, FastAPI

from . import __version__
from .axes import AXES, UNCLEAR, axis_names, validate_classification

# ── Config (all via env, nothing hardcoded that the operator would override) ─
CLAW_NAME = os.getenv("CLAW_NAME", "OpenClaw@URANTiOS-ingest")
DATA_ROOT = Path(os.getenv("DATA_ROOT", "/data"))
DATASET_NAME = os.getenv("DATASET_NAME", "mircea_corpus")
DATASET_SUBSCRIPTIONS = os.getenv("SUBSCRIPTION_DATASET", "mircea_subscribers")
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
HTTP_HOST = os.getenv("HTTP_HOST", "0.0.0.0")
HTTP_PORT = int(os.getenv("HTTP_PORT", "8080"))

# Ollama — reuse the same endpoint Cognee is configured against. Same host,
# same model, so the classifier cannot drift from the corpus embeddings' LLM.
OLLAMA_ENDPOINT = os.getenv(
    "OLLAMA_ENDPOINT",
    os.getenv("COGNEE_OLLAMA_ENDPOINT", "http://host.docker.internal:11434"),
)
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "qwen2.5:32b")
OLLAMA_TIMEOUT = float(os.getenv("OLLAMA_TIMEOUT", "120"))
# Classifier context budget — truncate long docs to keep the LLM honest.
CLASSIFY_MAX_CHARS = int(os.getenv("CLASSIFY_MAX_CHARS", "8000"))

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
    "subscription_subscribe",
    "subscription_unsubscribe",
    "subscription_list",
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


def _build_classification_prompt(content: str) -> str:
    """Compose the strict JSON-only prompt used by ``categorise_by_axes``."""
    axes_spec = "\n".join(
        f"- {a['name']}: {a['prompt']} Allowed: {a['labels']}."
        for a in AXES
    )
    return (
        "You classify a document along exactly 12 axes. For each axis, "
        "return one label from its allowed set. If the evidence does not "
        f"support a choice, return {UNCLEAR!r}. Output strictly a single "
        "JSON object whose keys are the axis names and whose values are "
        "the chosen labels. No prose, no keys outside the axis set.\n\n"
        f"Axes:\n{axes_spec}\n\n"
        f"Document (truncated to {CLASSIFY_MAX_CHARS} chars):\n"
        f"<<<\n{content[:CLASSIFY_MAX_CHARS]}\n>>>"
    )


def _classify_via_ollama(content: str) -> dict[str, Any]:
    """Ask Ollama for a 12-axis classification. Return the parsed JSON or
    ``{"error": ...}`` — never raises."""
    body = json.dumps({
        "model": OLLAMA_MODEL,
        "prompt": _build_classification_prompt(content),
        "stream": False,
        "format": "json",
    }).encode("utf-8")
    req = urllib.request.Request(
        f"{OLLAMA_ENDPOINT.rstrip('/')}/api/generate",
        data=body,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=OLLAMA_TIMEOUT) as resp:
            raw = resp.read().decode("utf-8")
    except (urllib.error.URLError, TimeoutError) as exc:
        return {"error": f"ollama_unreachable: {exc}"}

    try:
        envelope = json.loads(raw)
        response = envelope.get("response", "")
        parsed = json.loads(response)
    except (json.JSONDecodeError, AttributeError) as exc:
        return {"error": f"ollama_bad_json: {exc}", "raw": raw[:500]}

    if not isinstance(parsed, dict):
        return {"error": "ollama_not_object", "raw": raw[:500]}
    return parsed


async def _handle_categorise_by_axes(payload: dict) -> dict:
    """Classify every ingested document along the 12 axes in ``axes.py``.

    Scans ``/data/ingested/chatcode/*.jsonl``. For each file:

    * Compute ``sha256`` of the content. If ``classified/{sha256}.json``
      already exists, skip (idempotent — safe to re-run).
    * Ask Ollama for a 12-axis classification (strict JSON).
    * Validate against the closed label sets in :mod:`axes`. Missing or
      out-of-vocabulary labels are coerced to the ``unclear`` sentinel so
      downstream handlers always receive a complete axis map, but the
      coercions are recorded in ``validation_errors``.
    * Write the full record to ``classified/{sha256}.json``.

    Honest failure: if Ollama is unreachable, return ``status=error`` with
    the list of pending files — no silent partial success.
    """
    src_dir = DATA_ROOT / "ingested" / "chatcode"
    out_dir = DATA_ROOT / "classified"
    out_dir.mkdir(parents=True, exist_ok=True)
    files = sorted(src_dir.glob("*.jsonl"))

    if not files:
        return {"status": "success", "handler": "categorise_by_axes",
                "classified": 0, "skipped": 0,
                "message": "no jsonl files in ingested/chatcode"}

    classified = 0
    skipped = 0
    errors: list[dict[str, str]] = []

    for f in files:
        try:
            content = f.read_text(encoding="utf-8")
        except Exception as exc:
            errors.append({"file": f.name, "error": f"read_failed: {exc}"})
            continue

        sha = hashlib.sha256(content.encode("utf-8")).hexdigest()
        record_path = out_dir / f"{sha}.json"
        if record_path.exists():
            skipped += 1
            continue

        raw = _classify_via_ollama(content)
        if "error" in raw:
            errors.append({"file": f.name, "error": raw["error"]})
            # Fail fast on unreachability — retrying every file is wasteful.
            if raw["error"].startswith("ollama_unreachable"):
                break
            continue

        ok, validation_errors = validate_classification(raw)
        # Coerce invalid/missing labels to UNCLEAR so downstream never sees
        # out-of-vocabulary values. Record the coercions honestly.
        allowed_by_axis = {ax["name"]: set(ax["labels"]) for ax in AXES}
        axes_result = {
            name: raw[name] if raw.get(name) in allowed_by_axis[name] else UNCLEAR
            for name in axis_names()
        }

        record = {
            "sha256": sha,
            "source_file": f.name,
            "axes": axes_result,
            "validation_errors": validation_errors,
            "model": OLLAMA_MODEL,
            "claw": CLAW_NAME,
            "version": __version__,
            "ts_iso": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        }
        record_path.write_text(json.dumps(record, indent=2, sort_keys=True))
        classified += 1
        logger.info(
            f"categorise_by_axes: {f.name} -> {sha[:12]} "
            f"(valid={ok}, errors={len(validation_errors)})")

    return {
        "status": "success" if not errors else "partial",
        "handler": "categorise_by_axes",
        "classified": classified,
        "skipped": skipped,
        "errors": errors,
        "axes_version": len(AXES),
        "model": OLLAMA_MODEL,
    }


# ── Subscription handlers ─────────────────────────────────────────────
# Subscribers live in the Cognee graph under DATASET_SUBSCRIPTIONS, tagged
# via ``node_set`` so other constellation services can recall them through
# the same cognee.search() surface used for the corpus. Append-only: an
# unsubscribe writes a new status:inactive record rather than mutating the
# original — matches the project's evidence-trail discipline.
_VALID_CHANNELS: frozenset[str] = frozenset({"newsletter", "telegram", "bot_fleet"})


def _identifier_sha256(identifier: str) -> str:
    return hashlib.sha256(identifier.encode("utf-8")).hexdigest()


def _subscription_node_set(
    channel: str,
    identifier_sha: str,
    status: str,
    tags: list[str] | None,
) -> list[str]:
    ns = [
        "source:subscription",
        f"channel:{channel}",
        f"identifier_sha256:{identifier_sha}",
        f"status:{status}",
    ]
    for t in tags or []:
        ns.append(f"tag:{t}")
    return ns


async def _handle_subscription_subscribe(payload: dict) -> dict:
    """Record a subscriber as a Cognee node in DATASET_SUBSCRIPTIONS.

    Required payload keys: ``channel`` (one of newsletter/telegram/bot_fleet)
    and ``identifier`` (email address or ``telegram:<chat_id>``).
    Optional: ``tags`` — list of opt-in topic tags.

    Honest failure: if Cognee is unavailable or the payload is malformed,
    return ``status=error`` with a diagnostic and do not write to the graph.
    """
    channel = payload.get("channel")
    identifier = payload.get("identifier")
    tags = payload.get("tags") or []

    if channel not in _VALID_CHANNELS:
        return {"status": "error", "handler": "subscription_subscribe",
                "error": "invalid_channel",
                "allowed_channels": sorted(_VALID_CHANNELS)}
    if not isinstance(identifier, str) or not identifier.strip():
        return {"status": "error", "handler": "subscription_subscribe",
                "error": "missing_identifier"}
    if not isinstance(tags, list) or not all(isinstance(t, str) for t in tags):
        return {"status": "error", "handler": "subscription_subscribe",
                "error": "invalid_tags"}

    if not COGNEE_READY:
        return {"status": "error", "handler": "subscription_subscribe",
                "error": "cognee_not_ready",
                "hint": "check cognee_config.init() output and Ollama reachability"}

    identifier_sha = _identifier_sha256(identifier)
    record = {
        "kind": "subscription",
        "channel": channel,
        "identifier_sha256": identifier_sha,
        "status": "active",
        "tags": tags,
        "ts_iso": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
    }
    node_set = _subscription_node_set(channel, identifier_sha, "active", tags)

    try:
        await cognee.add(
            json.dumps(record, sort_keys=True),
            dataset_name=DATASET_SUBSCRIPTIONS,
            node_set=node_set,
        )
    except Exception as exc:
        logger.exception("subscription_subscribe failed")
        return {"status": "error", "handler": "subscription_subscribe",
                "error": f"cognee_add_failed: {exc}"}

    logger.info(
        f"subscription_subscribe: channel={channel} "
        f"identifier_sha256={identifier_sha[:12]} tags={tags}")
    return {
        "status": "success",
        "handler": "subscription_subscribe",
        "channel": channel,
        "identifier_sha256": identifier_sha,
        "tags": tags,
        "dataset": DATASET_SUBSCRIPTIONS,
    }


async def _handle_subscription_unsubscribe(payload: dict) -> dict:
    """Append a ``status:inactive`` subscriber record.

    Required payload key: ``identifier``. Optional: ``channel`` — if omitted
    the unsubscribe applies to every channel the identifier might be in;
    downstream list/search filters use the ``identifier_sha256`` node tag.

    Append-only: no node is deleted — the latest record for a given
    identifier_sha256 is authoritative.
    """
    identifier = payload.get("identifier")
    channel = payload.get("channel")

    if not isinstance(identifier, str) or not identifier.strip():
        return {"status": "error", "handler": "subscription_unsubscribe",
                "error": "missing_identifier"}
    if channel is not None and channel not in _VALID_CHANNELS:
        return {"status": "error", "handler": "subscription_unsubscribe",
                "error": "invalid_channel",
                "allowed_channels": sorted(_VALID_CHANNELS)}

    if not COGNEE_READY:
        return {"status": "error", "handler": "subscription_unsubscribe",
                "error": "cognee_not_ready"}

    identifier_sha = _identifier_sha256(identifier)
    record = {
        "kind": "subscription",
        "channel": channel or "*",
        "identifier_sha256": identifier_sha,
        "status": "inactive",
        "ts_iso": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
    }
    node_set = _subscription_node_set(
        channel or "*", identifier_sha, "inactive", None)

    try:
        await cognee.add(
            json.dumps(record, sort_keys=True),
            dataset_name=DATASET_SUBSCRIPTIONS,
            node_set=node_set,
        )
    except Exception as exc:
        logger.exception("subscription_unsubscribe failed")
        return {"status": "error", "handler": "subscription_unsubscribe",
                "error": f"cognee_add_failed: {exc}"}

    logger.info(
        f"subscription_unsubscribe: channel={channel or '*'} "
        f"identifier_sha256={identifier_sha[:12]}")
    return {
        "status": "success",
        "handler": "subscription_unsubscribe",
        "channel": channel or "*",
        "identifier_sha256": identifier_sha,
        "dataset": DATASET_SUBSCRIPTIONS,
    }


async def _handle_subscription_list(payload: dict) -> dict:
    """Recall subscribers from DATASET_SUBSCRIPTIONS.

    Optional payload key: ``channel`` — restrict the recall query.

    Scope (first draft): returns whatever ``cognee.search`` surfaces for a
    channel-scoped query, plus the raw payload. Richer filtering (last
    status per identifier, tag intersection) can be added in a follow-up
    once the graph surface stabilises.
    """
    channel = payload.get("channel")
    if channel is not None and channel not in _VALID_CHANNELS:
        return {"status": "error", "handler": "subscription_list",
                "error": "invalid_channel",
                "allowed_channels": sorted(_VALID_CHANNELS)}

    if not COGNEE_READY:
        return {"status": "error", "handler": "subscription_list",
                "error": "cognee_not_ready"}

    query = (
        f"subscribers on channel {channel}" if channel
        else "all subscribers"
    )
    try:
        results = await cognee.search(
            query_text=query,
            datasets=[DATASET_SUBSCRIPTIONS],
        )
    except Exception as exc:
        logger.exception("subscription_list failed")
        return {"status": "error", "handler": "subscription_list",
                "error": f"cognee_search_failed: {exc}"}

    return {
        "status": "success",
        "handler": "subscription_list",
        "channel": channel,
        "dataset": DATASET_SUBSCRIPTIONS,
        "results": results,
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
    "categorise_by_axes": _handle_categorise_by_axes,
    "cross_link":         lambda p: _handle_stub("cross_link", p),
    "governance_check":   lambda p: _handle_stub("governance_check", p),
    "export_urantipedia": lambda p: _handle_stub("export_urantipedia", p),
    "subscription_subscribe":   _handle_subscription_subscribe,
    "subscription_unsubscribe": _handle_subscription_unsubscribe,
    "subscription_list":        _handle_subscription_list,
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
        "subscription_dataset": DATASET_SUBSCRIPTIONS,
        "allowed_handlers": sorted(ALLOWED_HANDLERS),
        "axes": axis_names(),
        "classifier_model": OLLAMA_MODEL,
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
