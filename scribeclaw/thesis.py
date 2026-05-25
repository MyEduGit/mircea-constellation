"""ScribeClaw — OpenMythos thesis generator handler.

Calls the OpenMythos inference server (POST /v1/chat/completions) with a
cleaned transcript and returns a structured thesis bundle: thesis_ro,
thesis_en, subCaption. Used by the JabbokRiver pipeline before Council review.

The server must be running:
    python -m openmythos.serve --port 11435 --device auto
"""
from __future__ import annotations

import json
import logging
import os
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

logger = logging.getLogger("ScribeClaw.thesis")

OPENMYTHOS_ENDPOINT = os.getenv(
    "OPENMYTHOS_ENDPOINT", "http://localhost:11435/v1/chat/completions"
)
OPENMYTHOS_TIMEOUT = float(os.getenv("OPENMYTHOS_TIMEOUT", "120"))
OPENMYTHOS_LOOPS = int(os.getenv("OPENMYTHOS_THESIS_LOOPS", "12"))

_SYSTEM_PROMPT = (
    "You are a theological synthesis engine grounded in the Urantia Book and "
    "the Foreword. Given a Romanian sermon or teaching transcript, produce a "
    "JSON object with exactly three keys:\n"
    "  thesis_ro: a single Romanian sentence (≤25 words) capturing the core "
    "spiritual thesis of the discourse.\n"
    "  thesis_en: the English translation of thesis_ro.\n"
    "  subCaption: a short English subtitle phrase (≤8 words) for the "
    "Remotion ThesisTitleCard component.\n"
    "Output only valid JSON. No prose outside the JSON object."
)

_MAX_TRANSCRIPT_CHARS = 12000  # budget for the 770M model


async def openmythos_thesis(payload: dict, data_root: Path) -> dict:
    """Generate a theological thesis from a cleaned transcript.

    Payload keys:
      stem (required): transcript stem, e.g. 'interviu.edited'
      series_key (optional): channel series id for context
      loops (optional): override default loop count (default 12)
      transcript_path (optional): explicit path override

    Reads from: <data_root>/transcripts/<stem>/transcript.clean.txt
    Writes to:  <data_root>/transcripts/<stem>/thesis.json
    """
    stem = payload.get("stem", "").strip()
    if not stem:
        return {"status": "error", "handler": "openmythos_thesis",
                "error": "missing_stem"}

    loops = int(payload.get("loops", OPENMYTHOS_LOOPS))
    loops = max(2, min(loops, 16))

    # Locate transcript
    transcript_path_override = payload.get("transcript_path", "").strip()
    if transcript_path_override:
        transcript_path = Path(transcript_path_override)
    else:
        transcript_path = data_root / "transcripts" / stem / "transcript.clean.txt"

    if not transcript_path.exists():
        return {
            "status": "error",
            "handler": "openmythos_thesis",
            "error": f"transcript_not_found: {transcript_path}",
            "hint": "run postprocess_transcript first",
        }

    try:
        transcript = transcript_path.read_text(encoding="utf-8")
    except Exception as exc:
        return {"status": "error", "handler": "openmythos_thesis",
                "error": f"read_failed: {exc}"}

    series_key = payload.get("series_key", "")
    context_line = f"Series: {series_key}\n\n" if series_key else ""
    user_content = (
        f"{context_line}"
        f"Transcript (truncated to {_MAX_TRANSCRIPT_CHARS} chars):\n"
        f"<<<\n{transcript[:_MAX_TRANSCRIPT_CHARS]}\n>>>"
    )

    request_body = json.dumps({
        "model": "openmythos-urantia-770m",
        "messages": [
            {"role": "system", "content": _SYSTEM_PROMPT},
            {"role": "user", "content": user_content},
        ],
        "n_loops": loops,
        "max_tokens": 256,
        "temperature": 0.3,
        "stream": False,
    }).encode("utf-8")

    req = urllib.request.Request(
        OPENMYTHOS_ENDPOINT,
        data=request_body,
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    ts_start = time.time()
    try:
        with urllib.request.urlopen(req, timeout=OPENMYTHOS_TIMEOUT) as resp:
            raw = resp.read().decode("utf-8")
    except (urllib.error.URLError, TimeoutError) as exc:
        return {
            "status": "error",
            "handler": "openmythos_thesis",
            "error": f"openmythos_unreachable: {exc}",
            "hint": (
                "Start the server: python -m openmythos.serve "
                "--port 11435 --device auto"
            ),
        }

    elapsed = round(time.time() - ts_start, 2)

    try:
        envelope = json.loads(raw)
        content = envelope["choices"][0]["message"]["content"]
        thesis = json.loads(content)
    except (json.JSONDecodeError, KeyError, IndexError) as exc:
        return {
            "status": "error",
            "handler": "openmythos_thesis",
            "error": f"parse_failed: {exc}",
            "raw": raw[:500],
        }

    required = {"thesis_ro", "thesis_en", "subCaption"}
    missing = required - set(thesis.keys())
    if missing:
        return {
            "status": "error",
            "handler": "openmythos_thesis",
            "error": f"missing_keys: {sorted(missing)}",
            "partial": thesis,
        }

    # Write thesis bundle alongside transcript
    out_path = transcript_path.parent / "thesis.json"
    record: dict[str, Any] = {
        "stem": stem,
        "series_key": series_key,
        "thesis_ro": thesis["thesis_ro"],
        "thesis_en": thesis["thesis_en"],
        "subCaption": thesis["subCaption"],
        "loops_used": loops,
        "elapsed_s": elapsed,
        "model": "openmythos-urantia-770m",
        "ts_iso": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
    }
    out_path.write_text(json.dumps(record, indent=2, ensure_ascii=False))
    logger.info(
        f"openmythos_thesis: {stem} → thesis.json "
        f"({loops} loops, {elapsed}s)"
    )

    return {
        "status": "success",
        "handler": "openmythos_thesis",
        "stem": stem,
        "thesis_ro": thesis["thesis_ro"],
        "thesis_en": thesis["thesis_en"],
        "subCaption": thesis["subCaption"],
        "loops_used": loops,
        "elapsed_s": elapsed,
        "output": str(out_path),
    }
