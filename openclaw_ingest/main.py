#!/usr/bin/env python3
"""OpenClaw@URANTiOS-ingest — execution runtime, ingestion sub-role.

Canonical role: controlled execution (singular).
Truthful label:  deployable scaffold with three real handlers
(``ingest_normalize``, ``categorise_by_axes``, ``cross_link``).

Two of the five canonical handlers (governance_check, export_urantipedia)
remain declared-but-stubbed pending follow-up PR. The allowlist
boundary is preserved: nothing outside ALLOWED_HANDLERS can run.

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
from .axes import (AXES, NONPOSITIVE_LABELS, UNCLEAR, WEIGHTS, axis_names,
                    validate_classification)

# ── Config (all via env, nothing hardcoded that the operator would override) ─
CLAW_NAME = os.getenv("CLAW_NAME", "OpenClaw@URANTiOS-ingest")
DATA_ROOT = Path(os.getenv("DATA_ROOT", "/data"))
DATASET_NAME = os.getenv("DATASET_NAME", "mircea_corpus")
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

# Cross-link scoring knobs — see ``axes.WEIGHTS`` for per-axis weights.
CROSS_LINK_THRESHOLD = float(os.getenv("CROSS_LINK_THRESHOLD", "5.0"))
CROSS_LINK_MAX_PAIRS = int(os.getenv("CROSS_LINK_MAX_PAIRS", "10000"))
CROSS_LINK_MAX_FANOUT = int(os.getenv("CROSS_LINK_MAX_FANOUT", "50"))

# Ensure directory layout on every start (idempotent).
for _sub in ("ingest/chatcode", "ingested/chatcode", "classified", "linked",
             "governed", "canon", "logs", "evidence"):
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


def _score_pair(axes_a: dict, axes_b: dict) -> tuple[float, list[dict]]:
    """Compute edge weight between two classification axis-maps.

    Pure function — no I/O, trivially testable. Matches earn weight only
    when labels are equal AND the label is not in ``NONPOSITIVE_LABELS``
    (so ``serves_self ↔ serves_self`` and ``absent ↔ absent`` do not
    reinforce linkage).
    """
    score = 0.0
    matched: list[dict] = []
    for axis in axis_names():
        la = axes_a.get(axis)
        lb = axes_b.get(axis)
        if la != lb or la in NONPOSITIVE_LABELS:
            continue
        w = WEIGHTS[axis]
        if w <= 0:
            continue
        score += w
        matched.append({"axis": axis, "label": la, "weight": w})
    return score, matched


async def _handle_cross_link(payload: dict) -> dict:
    """Score every classified-doc pair and emit edges above threshold.

    Reads ``/data/classified/*.json``. For each unordered pair with
    ``sha_a < sha_b``:

    * Skip if ``/data/linked/{sha_a}__{sha_b}.json`` already exists
      (idempotent — safe to re-run).
    * Skip if either document carries ``lucifer_test == "flagged"``.
      Iniquitous docs produce zero edges in either direction.
    * Compute the score via :func:`_score_pair` against ``axes.WEIGHTS``.
    * Emit an edge record if ``score >= threshold`` AND neither node has
      already hit ``max_fanout`` for this run. If Cognee is ready, also
      add a synthetic edge-content node tagged with both shas so the
      graph sees the relationship.

    Payload overrides (all optional): ``threshold``, ``max_pairs``,
    ``max_fanout``. Honest failure: Cognee add errors are collected per
    pair into ``errors`` (``status: partial``); nothing is silently
    dropped.
    """
    in_dir = DATA_ROOT / "classified"
    out_dir = DATA_ROOT / "linked"
    out_dir.mkdir(parents=True, exist_ok=True)

    threshold = float(payload.get("threshold", CROSS_LINK_THRESHOLD))
    max_pairs = int(payload.get("max_pairs", CROSS_LINK_MAX_PAIRS))
    max_fanout = int(payload.get("max_fanout", CROSS_LINK_MAX_FANOUT))

    records: list[dict] = []
    for f in sorted(in_dir.glob("*.json")):
        try:
            rec = json.loads(f.read_text())
            if "sha256" in rec and "axes" in rec:
                records.append(rec)
        except Exception as exc:
            logger.warning(f"cross_link: corrupt {f.name}: {exc}")

    if len(records) < 2:
        return {"status": "success", "handler": "cross_link",
                "message": f"need >=2 classified docs; have {len(records)}",
                "edges_emitted": 0, "documents": len(records)}

    records.sort(key=lambda r: r["sha256"])
    existing = {p.name for p in out_dir.glob("*.json")}

    fanout: dict[str, int] = {}
    edges_emitted = 0
    skipped_existing = 0
    skipped_flagged = 0
    skipped_below_threshold = 0
    skipped_fanout = 0
    pairs_considered = 0
    errors: list[dict] = []

    pairs_budget_exhausted = False
    for i, a in enumerate(records):
        if pairs_budget_exhausted:
            break
        for b in records[i + 1:]:
            if pairs_considered >= max_pairs:
                pairs_budget_exhausted = True
                break
            pairs_considered += 1

            sha_a, sha_b = a["sha256"], b["sha256"]
            pair_name = f"{sha_a}__{sha_b}.json"
            if pair_name in existing:
                skipped_existing += 1
                continue
            if (a["axes"].get("lucifer_test") == "flagged"
                    or b["axes"].get("lucifer_test") == "flagged"):
                skipped_flagged += 1
                continue
            if (fanout.get(sha_a, 0) >= max_fanout
                    or fanout.get(sha_b, 0) >= max_fanout):
                skipped_fanout += 1
                continue

            score, matched = _score_pair(a["axes"], b["axes"])
            if score < threshold:
                skipped_below_threshold += 1
                continue

            record = {
                "sha_a": sha_a,
                "sha_b": sha_b,
                "score": round(score, 3),
                "axes_matched": matched,
                "threshold": threshold,
                "claw": CLAW_NAME,
                "version": __version__,
                "ts_iso": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
            }
            (out_dir / pair_name).write_text(
                json.dumps(record, indent=2, sort_keys=True))
            fanout[sha_a] = fanout.get(sha_a, 0) + 1
            fanout[sha_b] = fanout.get(sha_b, 0) + 1
            edges_emitted += 1

            if COGNEE_READY:
                try:
                    await cognee.add(
                        f"cross_link edge: {sha_a[:12]} ↔ {sha_b[:12]} "
                        f"(score={score:.2f}, axes_matched="
                        f"{[m['axis'] for m in matched]})",
                        dataset_name=DATASET_NAME,
                        node_set=[
                            f"edge:{sha_a[:12]}__{sha_b[:12]}",
                            f"sha:{sha_a}",
                            f"sha:{sha_b}",
                            "kind:cross_link",
                        ],
                    )
                except Exception as exc:
                    errors.append({"pair": pair_name,
                                   "cognee_error": str(exc)})
                    logger.warning(
                        f"cross_link: cognee.add failed for {pair_name}: {exc}")

    total_pairs = len(records) * (len(records) - 1) // 2
    return {
        "status": "success" if not errors else "partial",
        "handler": "cross_link",
        "edges_emitted": edges_emitted,
        "skipped_existing": skipped_existing,
        "skipped_flagged": skipped_flagged,
        "skipped_below_threshold": skipped_below_threshold,
        "skipped_fanout": skipped_fanout,
        "pairs_considered": pairs_considered,
        "pairs_unseen": max(0, total_pairs - pairs_considered),
        "documents": len(records),
        "threshold": threshold,
        "max_fanout": max_fanout,
        "max_pairs": max_pairs,
        "cognee_ready": COGNEE_READY,
        "errors": errors,
    }


async def _handle_governance_check(payload: dict) -> dict:
    """Apply governance rules to every classified document.

    Reads ``/data/classified/*.json``. For each sha256 not already in
    ``/data/governed/{sha256}.governed.json`` (idempotent — safe to re-run):

    * Evaluate governance status from axes values (priority-ordered):

      1. ``lucifer_test == flagged`` → **blocked** (escalate to LuciferiClaw).
      2. ``lucifer_test == opaque``  → **requires_review**.
      3. ``goodness == serves_self`` → **warning** (self-serving content).
      4. ``lifecycle == canonical AND authority ∈ (user, canon)`` → **canonical**.
      5. ``lifecycle == canonical AND authority == agent`` →
         **pending_canonicalization** (agent cannot self-canonicalize).
      6. ``lifecycle == working`` → **active**.
      7. ``lifecycle == raw``     → **draft**.
      8. Default                  → **unclassified**.

    * Determine export eligibility: ``canonical`` or ``active`` AND
      ``confidentiality == public`` AND ``lucifer_test == transparent``.

    * Detect sha256 duplicates across the classified corpus.

    * Write ``governed/{sha256}.governed.json`` with the decision, reason,
      escalation target (if any), and the relevant axes snapshot.

    Governance decisions are append-only: once written, a re-run skips
    the sha256. To re-evaluate, delete the ``.governed.json`` file and
    re-run.

    Payload overrides: none currently. Future: ``force_reevaluate: true``.
    """
    in_dir = DATA_ROOT / "classified"
    out_dir = DATA_ROOT / "governed"
    out_dir.mkdir(parents=True, exist_ok=True)

    records: list[dict] = []
    for f in sorted(in_dir.glob("*.json")):
        try:
            rec = json.loads(f.read_text())
            if "sha256" in rec and "axes" in rec:
                records.append(rec)
        except Exception as exc:
            logger.warning(f"governance_check: corrupt {f.name}: {exc}")

    if not records:
        return {"status": "success", "handler": "governance_check",
                "governed": 0, "message": "no classified documents"}

    sha_counts: dict[str, int] = {}
    for rec in records:
        sha = rec["sha256"]
        sha_counts[sha] = sha_counts.get(sha, 0) + 1

    existing = {p.stem.replace(".governed", "")
                for p in out_dir.glob("*.governed.json")}

    governed = 0
    blocked = 0
    requires_review = 0
    warnings = 0
    canonical_count = 0
    export_eligible_count = 0
    skipped = 0

    for rec in records:
        sha = rec["sha256"]
        if sha in existing:
            skipped += 1
            continue

        axes = rec.get("axes", {})
        lt = axes.get("lucifer_test", UNCLEAR)
        lc = axes.get("lifecycle", UNCLEAR)
        au = axes.get("authority", UNCLEAR)
        gd = axes.get("goodness", UNCLEAR)
        conf = axes.get("confidentiality", UNCLEAR)

        governance_status = "unclassified"
        governance_reason = ""
        escalate_to = None

        if lt == "flagged":
            governance_status = "blocked"
            governance_reason = (
                "lucifer_test=flagged: self-serving, mission-hostile, "
                "or governance-rejecting pattern detected"
            )
            escalate_to = "LuciferiClaw"
            blocked += 1
        elif lt == "opaque":
            governance_status = "requires_review"
            governance_reason = (
                "lucifer_test=opaque: intent not transparent; "
                "human review required before reuse"
            )
            requires_review += 1
        elif gd == "serves_self":
            governance_status = "warning"
            governance_reason = (
                "goodness=serves_self: content serves agent self-interest "
                "over the mission"
            )
            warnings += 1
        elif lc == "canonical" and au in ("user", "canon"):
            governance_status = "canonical"
            governance_reason = (
                f"lifecycle=canonical + authority={au}: "
                f"accepted as authoritative"
            )
            canonical_count += 1
        elif lc == "canonical" and au == "agent":
            governance_status = "pending_canonicalization"
            governance_reason = (
                "lifecycle=canonical but authority=agent: agent cannot "
                "self-canonicalize; requires Father Function ratification"
            )
            requires_review += 1
        elif lc == "working":
            governance_status = "active"
            governance_reason = (
                f"lifecycle=working + authority={au}: "
                f"usable but not canonical"
            )
        elif lc == "raw":
            governance_status = "draft"
            governance_reason = (
                "lifecycle=raw: unfinished; not for reuse without upgrade"
            )
        else:
            governance_reason = (
                f"no clear governance signal "
                f"(lifecycle={lc}, authority={au}, lucifer_test={lt})"
            )

        export_eligible = (
            governance_status in ("canonical", "active")
            and conf == "public"
            and lt == "transparent"
        )
        if export_eligible:
            export_eligible_count += 1

        is_duplicate = sha_counts.get(sha, 0) > 1

        decision = {
            "sha256": sha,
            "source_file": rec.get("source_file", ""),
            "governance_status": governance_status,
            "governance_reason": governance_reason,
            "escalate_to": escalate_to,
            "export_eligible": export_eligible,
            "is_duplicate": is_duplicate,
            "axes_snapshot": {
                "lucifer_test": lt,
                "lifecycle": lc,
                "authority": au,
                "goodness": gd,
                "confidentiality": conf,
            },
            "claw": CLAW_NAME,
            "version": __version__,
            "ts_iso": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        }

        out_path = out_dir / f"{sha}.governed.json"
        out_path.write_text(json.dumps(decision, indent=2, sort_keys=True))
        governed += 1
        logger.info(
            f"governance_check: {sha[:12]} -> {governance_status}"
            f"{' (ESCALATE->LuciferiClaw)' if escalate_to else ''}"
            f"{' [export_eligible]' if export_eligible else ''}"
        )

    return {
        "status": "success",
        "handler": "governance_check",
        "governed": governed,
        "skipped_existing": skipped,
        "blocked": blocked,
        "requires_review": requires_review,
        "warnings": warnings,
        "canonical": canonical_count,
        "export_eligible": export_eligible_count,
        "documents_total": len(records),
    }


async def _handle_stub(name: str, payload: dict) -> dict:
    return {
        "status": "not_implemented",
        "handler": name,
        "reason": "scaffold; follow-up PR will implement.",
    }


async def _handle_categorise_by_axes(payload: dict) -> dict:
    """Run the 12-axis classifier on every file in /data/ingested/chatcode/.

    Reads each *.jsonl, classifies it, writes the result as JSON to
    /data/classified/<stem>.classified.json.

    Honest behaviour: pure rule-based. No embeddings yet (follow-up PR).
    Per-axis confidence is reported so downstream consumers can filter
    low-confidence hits.

    payload may contain:
      source_dir: override default '/data/ingested/chatcode'
      target_dir: override default '/data/classified'
      metadata:   dict applied to every file as starting metadata
    """
    from . import classifier  # local import — keeps cold start fast

    src = Path(payload.get("source_dir") or (DATA_ROOT / "ingested" / "chatcode"))
    dst = Path(payload.get("target_dir") or (DATA_ROOT / "classified"))
    dst.mkdir(parents=True, exist_ok=True)
    base_md = payload.get("metadata") or {}

    files = sorted(src.glob("*.jsonl"))
    if not files:
        return {"status": "success", "handler": "categorise_by_axes",
                "classified": 0, "message": f"no jsonl files in {src}"}

    classified_count = 0
    low_confidence_count = 0
    errors: list[dict[str, str]] = []
    summaries: list[dict[str, Any]] = []

    for f in files:
        try:
            full = classifier.classify_file(f, metadata=dict(base_md))
            out_path = dst / f"{f.stem}.classified.json"
            out_path.write_text(json.dumps(full, indent=2))
            classified_count += 1
            # Count low-confidence axes (confidence < 0.5).
            low_conf = [name for name, ax in full["axes"].items()
                        if ax.get("confidence", 1.0) < 0.5]
            if low_conf:
                low_confidence_count += 1
            summaries.append({
                "file": f.name,
                "out": out_path.name,
                "low_confidence_axes": low_conf,
                "doctrine_top": (full["axes"]["doctrine_topic"]["value"][0]["paper"]
                                 if full["axes"]["doctrine_topic"]["value"]
                                 else None),
            })
            logger.info(f"categorise_by_axes: {f.name} -> {out_path.name} "
                        f"(low_conf={len(low_conf)})")
        except Exception as exc:
            errors.append({"file": f.name, "error": str(exc)})
            logger.exception(f"categorise_by_axes failed on {f.name}")

    return {
        "status": "success" if not errors else "partial",
        "handler": "categorise_by_axes",
        "classified": classified_count,
        "low_confidence_files": low_confidence_count,
        "errors": errors,
        "summaries": summaries[:20],   # cap response size
        "source_dir": str(src),
        "target_dir": str(dst),
    }


# Dispatch table — 1:1 with ALLOWED_HANDLERS. Changes here require changes
# to the allowlist above (and vice versa); the invariant is asserted below.
_HANDLERS = {
    "smoke_test": _handle_smoke_test,
    "ingest_normalize": _handle_ingest_normalize,
    "categorise_by_axes": _handle_categorise_by_axes,
    "cross_link":         _handle_cross_link,
    "governance_check":   _handle_governance_check,
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
        "axes": axis_names(),
        "classifier_model": OLLAMA_MODEL,
        "cross_link": {
            "threshold": CROSS_LINK_THRESHOLD,
            "max_pairs": CROSS_LINK_MAX_PAIRS,
            "max_fanout": CROSS_LINK_MAX_FANOUT,
        },
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
