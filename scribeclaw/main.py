#!/usr/bin/env python3
"""ScribeClaw — media transcription execution runtime.

Canonical role: controlled execution (media-pipeline sub-role).
Truthful label: deployable scaffold. Real handlers: media_edit,
audio_extract, transcribe_ro, postprocess_transcript, youtube_metadata.
Stub handler: youtube_upload (refuses; operator must supply OAuth).

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
from fastapi import Body, FastAPI, HTTPException, Query
from fastapi.responses import FileResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles

from . import __version__
from .assemblyai import (
    bulk_import_assemblyai_romanian,
    import_assemblyai_transcript,
    transcribe_assemblyai,
)
from .edit import audio_extract, media_edit
from .postprocess import postprocess_transcript
from .transcribe import transcribe_ro
from .youtube import youtube_metadata, youtube_upload

CLAW_NAME = os.getenv("CLAW_NAME", "ScribeClaw")
DATA_ROOT = Path(os.getenv("DATA_ROOT", "/data"))
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
HTTP_HOST = os.getenv("HTTP_HOST", "0.0.0.0")
HTTP_PORT = int(os.getenv("HTTP_PORT", "8081"))

for _sub in ("media/in", "media/edited", "media/audio",
             "transcripts", "youtube", "logs", "evidence"):
    (DATA_ROOT / _sub).mkdir(parents=True, exist_ok=True)

logging.basicConfig(
    level=LOG_LEVEL,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    handlers=[
        logging.FileHandler(DATA_ROOT / "logs" / "scribeclaw.log"),
        logging.StreamHandler(sys.stdout),
    ],
)
logger = logging.getLogger(CLAW_NAME)


ALLOWED_HANDLERS: frozenset[str] = frozenset({
    "smoke_test",
    "media_edit",
    "audio_extract",
    "transcribe_ro",
    "transcribe_assemblyai",
    "import_assemblyai_transcript",
    "bulk_import_assemblyai_romanian",
    "postprocess_transcript",
    "youtube_metadata",
    "youtube_upload",
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
    import shutil
    faster_whisper_installed = True
    try:
        import faster_whisper  # noqa: F401
    except ImportError:
        faster_whisper_installed = False
    httpx_installed = True
    try:
        import httpx  # noqa: F401
    except ImportError:
        httpx_installed = False
    return {
        "ffmpeg_on_path": shutil.which("ffmpeg") is not None,
        "faster_whisper_installed": faster_whisper_installed,
        "httpx_installed": httpx_installed,
        "assemblyai_key_set": bool(os.getenv("ASSEMBLYAI_API_KEY", "").strip()),
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
    "smoke_test":                   lambda p: _handle_smoke_test(p),
    "media_edit":                   lambda p: media_edit(p, DATA_ROOT),
    "audio_extract":                lambda p: audio_extract(p, DATA_ROOT),
    "transcribe_ro":                lambda p: transcribe_ro(p, DATA_ROOT),
    "transcribe_assemblyai":        lambda p: transcribe_assemblyai(p, DATA_ROOT),
    "import_assemblyai_transcript": lambda p: import_assemblyai_transcript(p, DATA_ROOT),
    "bulk_import_assemblyai_romanian": lambda p: bulk_import_assemblyai_romanian(p, DATA_ROOT),
    "postprocess_transcript":       lambda p: postprocess_transcript(p, DATA_ROOT),
    "youtube_metadata":             lambda p: youtube_metadata(p, DATA_ROOT),
    "youtube_upload":               lambda p: youtube_upload(p, DATA_ROOT),
}
assert set(_HANDLERS) == set(ALLOWED_HANDLERS), \
    "dispatch table must match ALLOWED_HANDLERS exactly"


async def safe_execute(handler: str, payload: dict) -> dict:
    if handler not in ALLOWED_HANDLERS:
        result = {"status": "rejected", "handler": handler,
                  "error": "not in ScribeClaw allowlist"}
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


# ── Dashboard API (read-only; mutation flows stay on POST /tasks) ──────
def _safe_resolve_under(root: Path, rel: str) -> Path:
    """Resolve `rel` under `root`, raising HTTPException on escape.

    Prevents '../../etc/passwd'-style traversal in the static file proxy."""
    candidate = (root / rel).resolve()
    root_resolved = root.resolve()
    try:
        candidate.relative_to(root_resolved)
    except ValueError:
        raise HTTPException(status_code=400, detail="path_escape")
    return candidate


@app.get("/api/transcripts")
def api_list_transcripts() -> dict:
    td = DATA_ROOT / "transcripts"
    if not td.is_dir():
        return {"transcripts": []}
    out: list[dict] = []
    for entry in sorted(td.iterdir()):
        if not entry.is_dir():
            continue
        seg_clean = entry / "segments.clean.json"
        seg_raw = entry / "segments.json"
        seg = seg_clean if seg_clean.exists() else seg_raw
        meta = {"stem": entry.name, "segments": 0, "language": None,
                "duration_sec": None, "has_cues": (entry / "cues.json").exists(),
                "has_bundle": (DATA_ROOT / "youtube" / entry.name / "bundle.json").exists(),
                "has_thumbnail": (DATA_ROOT / "youtube" / entry.name / "thumbnail.jpg").exists(),
                "has_upload": (DATA_ROOT / "youtube" / entry.name / "upload.result.json").exists()}
        if seg.exists():
            try:
                data = json.loads(seg.read_text(encoding="utf-8"))
                meta["segments"] = len(data.get("segments", []))
                meta["language"] = data.get("language")
                meta["duration_sec"] = data.get("duration")
            except Exception:
                pass
        out.append(meta)
    return {"transcripts": out, "count": len(out)}


@app.get("/api/transcripts/{stem}")
def api_transcript_detail(stem: str) -> dict:
    stem = Path(stem).name  # strip any accidental slashes
    tdir = DATA_ROOT / "transcripts" / stem
    if not tdir.is_dir():
        raise HTTPException(status_code=404, detail="stem_not_found")
    seg_clean = tdir / "segments.clean.json"
    seg_raw = tdir / "segments.json"
    source = seg_clean if seg_clean.exists() else seg_raw
    data = {}
    preview: list[dict] = []
    if source.exists():
        try:
            data = json.loads(source.read_text(encoding="utf-8"))
            for s in data.get("segments", [])[:8]:
                preview.append({"start": s.get("start", 0),
                                "end": s.get("end", 0),
                                "text": s.get("text", "")})
        except Exception:
            pass
    ydir = DATA_ROOT / "youtube" / stem
    bundle = None
    if (ydir / "bundle.json").exists():
        try: bundle = json.loads((ydir / "bundle.json").read_text(encoding="utf-8"))
        except Exception: bundle = None
    upload = None
    if (ydir / "upload.result.json").exists():
        try: upload = json.loads((ydir / "upload.result.json").read_text(encoding="utf-8"))
        except Exception: upload = None
    # Guess a default video filename for the dashboard's thumbnail button.
    video_hint = None
    ed = DATA_ROOT / "media" / "edited"
    if ed.is_dir():
        for p in sorted(ed.iterdir()):
            if p.suffix.lower() in (".mp4", ".mov", ".mkv", ".webm") and p.stem.startswith(stem):
                video_hint = p.name
                break
    return {
        "stem": stem,
        "source_file": str(source) if source.exists() else None,
        "segments": len(data.get("segments", [])),
        "language": data.get("language"),
        "duration_sec": data.get("duration"),
        "segments_preview": preview,
        "has_bundle": bundle is not None,
        "has_thumbnail": (ydir / "thumbnail.jpg").exists(),
        "has_cues": (tdir / "cues.json").exists(),
        "has_upload": upload is not None,
        "bundle": bundle,
        "upload": upload,
        "video_hint": video_hint,
    }


@app.get("/api/evidence")
def api_evidence(limit: int = Query(30, ge=1, le=200)) -> dict:
    ed = DATA_ROOT / "evidence"
    if not ed.is_dir():
        return {"evidence": []}
    files = sorted(ed.glob("evidence_*.json"),
                   key=lambda p: p.stat().st_mtime, reverse=True)[:limit]
    items: list[dict] = []
    for f in files:
        try:
            items.append(json.loads(f.read_text(encoding="utf-8")))
        except Exception:
            continue
    return {"evidence": items}


_FILE_WHITELIST_PREFIXES = ("youtube/", "transcripts/", "media/edited/", "media/audio/")


@app.get("/api/file")
def api_file(path: str = Query(..., min_length=1, max_length=500)) -> FileResponse:
    """Proxy small static assets (thumbnails, subtitles) from under
    DATA_ROOT. Restricted to an explicit prefix allowlist and guarded
    against traversal — this is the only path the dashboard needs to
    read files the handlers produced."""
    if not any(path.startswith(p) for p in _FILE_WHITELIST_PREFIXES):
        raise HTTPException(status_code=403, detail="path_not_whitelisted")
    target = _safe_resolve_under(DATA_ROOT, path)
    if not target.is_file():
        raise HTTPException(status_code=404, detail="not_found")
    return FileResponse(str(target))


# ── Static UI ─────────────────────────────────────────────────────────
# The web/ directory ships with the module; see scribeclaw/web/.
_WEB_DIR = Path(__file__).parent / "web"
if _WEB_DIR.is_dir():
    app.mount("/ui", StaticFiles(directory=str(_WEB_DIR), html=True), name="ui")


@app.get("/")
def root_redirect() -> RedirectResponse:
    """Land operators on the command-centre UI by default."""
    return RedirectResponse(url="/ui/")


def _run_http_server() -> None:
    uvicorn.run(app, host=HTTP_HOST, port=HTTP_PORT, log_level="warning")


def main() -> int:
    parser = argparse.ArgumentParser(prog="scribeclaw")
    parser.add_argument(
        "--mode",
        default="daemon",
        choices=("daemon", "one-shot", "pipeline"),
        help=(
            "daemon: HTTP server; one-shot: run smoke_test and exit; "
            "pipeline: run full chain on --input"
        ),
    )
    parser.add_argument("--input", help="video filename under /data/media/in/ (pipeline mode)")
    args = parser.parse_args()
    logger.info(f"{CLAW_NAME} v{__version__} starting (mode={args.mode})")

    smoke = asyncio.run(safe_execute("smoke_test", {}))
    logger.info(f"startup smoke_test: {smoke.get('status')}")

    if args.mode == "one-shot":
        return 0 if smoke.get("status") == "success" else 1

    if args.mode == "pipeline":
        if not args.input:
            logger.error("pipeline mode requires --input")
            return 2
        results: list[dict] = []
        for handler, payload in [
            ("media_edit", {"input": args.input}),
            ("audio_extract", {"input": f"{Path(args.input).stem}.edited{Path(args.input).suffix}"}),
            ("transcribe_ro", {"input": f"{Path(args.input).stem}.edited.wav"}),
            ("postprocess_transcript", {"stem": f"{Path(args.input).stem}.edited"}),
            ("youtube_metadata", {"stem": f"{Path(args.input).stem}.edited"}),
        ]:
            logger.info(f"pipeline: {handler}")
            r = asyncio.run(safe_execute(handler, payload))
            results.append(r)
            if r.get("status") not in ("success", "partial"):
                logger.error(f"pipeline halted at {handler}: {r}")
                print(json.dumps(results, indent=2, ensure_ascii=False))
                return 1
        print(json.dumps(results, indent=2, ensure_ascii=False))
        return 0

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
