"""AssemblyAI-backed transcription handlers.

Three handlers:
  - transcribe_assemblyai             uploads a local audio file and starts a new job
  - import_assemblyai_transcript      pulls an ALREADY-COMPLETED transcript by id
                                      (reuse work that's already in the dashboard)
  - bulk_import_assemblyai_romanian   list the dashboard, keep only completed
                                      Romanian transcripts, write each to disk

Both write the same output shape as transcribe_ro so the rest of the
pipeline (postprocess_transcript → youtube_metadata) is drop-in compatible:

  /data/transcripts/<stem>/
      segments.json       normalized segments (start/end in seconds)
      transcript.srt
      transcript.vtt
      transcript.txt
      assemblyai.raw.json full API response, preserved for provenance

Operator contract:
  - ASSEMBLYAI_API_KEY env var must be set. If missing, the handlers
    refuse with status=error — no silent retries, no hard-coded keys.
  - httpx is the only HTTP dep (async-native).
  - AssemblyAI timestamps are milliseconds; we convert to seconds.
"""
from __future__ import annotations

import asyncio
import json
import os
from pathlib import Path
from typing import Any

_API_BASE = "https://api.assemblyai.com/v2"
_DEFAULT_POLL_SEC = 5
_DEFAULT_POLL_TIMEOUT_SEC = 30 * 60  # 30 minutes covers a one-hour video


def _fmt_ts(sec: float, sep: str) -> str:
    ms = int(round(sec * 1000))
    h, ms = divmod(ms, 3_600_000)
    m, ms = divmod(ms, 60_000)
    s, ms = divmod(ms, 1000)
    return f"{h:02d}:{m:02d}:{s:02d}{sep}{ms:03d}"


def _write_outputs(out_dir: Path, raw: dict, segments: list[dict]) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    duration_sec = float(raw.get("audio_duration") or 0.0)
    (out_dir / "assemblyai.raw.json").write_text(
        json.dumps(raw, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    (out_dir / "segments.json").write_text(
        json.dumps({
            "language": raw.get("language_code", "ro"),
            "language_probability": 1.0,
            "duration": duration_sec,
            "model": f"assemblyai:{raw.get('speech_model') or 'default'}",
            "segments": segments,
            "source": "assemblyai",
            "assemblyai_id": raw.get("id"),
        }, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    srt_lines: list[str] = []
    for i, seg in enumerate(segments, start=1):
        srt_lines.append(str(i))
        srt_lines.append(f"{_fmt_ts(seg['start'], ',')} --> {_fmt_ts(seg['end'], ',')}")
        srt_lines.append(seg["text"].strip())
        srt_lines.append("")
    (out_dir / "transcript.srt").write_text("\n".join(srt_lines), encoding="utf-8")

    vtt_lines = ["WEBVTT", ""]
    for seg in segments:
        vtt_lines.append(f"{_fmt_ts(seg['start'], '.')} --> {_fmt_ts(seg['end'], '.')}")
        vtt_lines.append(seg["text"].strip())
        vtt_lines.append("")
    (out_dir / "transcript.vtt").write_text("\n".join(vtt_lines), encoding="utf-8")

    (out_dir / "transcript.txt").write_text(
        "\n\n".join(s["text"].strip() for s in segments if s["text"].strip()),
        encoding="utf-8",
    )


def _normalize_segments(sentences_payload: dict, fallback_text: str) -> list[dict]:
    """Convert AssemblyAI sentences (or fallback whole-text) into our shape."""
    out: list[dict] = []
    for i, s in enumerate(sentences_payload.get("sentences", [])):
        out.append({
            "id": i,
            "start": float(s["start"]) / 1000.0,
            "end": float(s["end"]) / 1000.0,
            "text": (s.get("text") or "").strip(),
            "words": None,
        })
    if not out and fallback_text.strip():
        # Dashboard transcripts without sentence segmentation — single segment.
        out.append({"id": 0, "start": 0.0, "end": 0.0,
                    "text": fallback_text.strip(), "words": None})
    return out


async def _upload_file(client, api_key: str, path: Path) -> str:
    """Stream the audio bytes to /upload. Returns the temporary upload_url."""
    headers = {"authorization": api_key}

    def chunks():
        with path.open("rb") as fh:
            while True:
                b = fh.read(5 * 1024 * 1024)
                if not b:
                    break
                yield b

    r = await client.post(f"{_API_BASE}/upload", headers=headers, content=chunks())
    r.raise_for_status()
    return r.json()["upload_url"]


# AssemblyAI deprecated the singular `speech_model` field in favour of
# the plural `speech_models` array. Submitting the singular form returns
# 400 "speech_models must be a non-empty list". We accept either spelling
# in the payload for operator ergonomics but always send the plural array
# on the wire. Keep this list pinned to known-good IDs; AssemblyAI has
# dropped unlisted models without notice before.
_DEFAULT_SPEECH_MODELS: tuple[str, ...] = ("universal-2",)


def _normalise_speech_models(payload: dict) -> list[str]:
    # New API: `speech_models` (array). Accept as-is.
    val = payload.get("speech_models")
    if isinstance(val, list) and val:
        return [str(m) for m in val]
    # Legacy operator habit: `speech_model` (singular string). Upgrade.
    legacy = payload.get("speech_model")
    if isinstance(legacy, str) and legacy.strip():
        return [legacy.strip()]
    return list(_DEFAULT_SPEECH_MODELS)


async def _start_job(client, api_key: str, audio_url: str, payload: dict) -> str:
    headers = {"authorization": api_key, "content-type": "application/json"}
    body: dict[str, Any] = {
        "audio_url": audio_url,
        "language_code": payload.get("language", "ro"),
        "punctuate": bool(payload.get("punctuate", True)),
        "format_text": bool(payload.get("format_text", True)),
        "speaker_labels": bool(payload.get("speaker_labels", False)),
        "speech_models": _normalise_speech_models(payload),
    }
    r = await client.post(f"{_API_BASE}/transcript", headers=headers, json=body)
    r.raise_for_status()
    return r.json()["id"]


async def _poll(client, api_key: str, transcript_id: str,
                poll_sec: float, timeout_sec: float) -> dict:
    headers = {"authorization": api_key}
    waited = 0.0
    while True:
        r = await client.get(f"{_API_BASE}/transcript/{transcript_id}", headers=headers)
        r.raise_for_status()
        data = r.json()
        status = data.get("status")
        if status == "completed":
            return data
        if status == "error":
            raise RuntimeError(f"assemblyai_error: {data.get('error')}")
        if waited >= timeout_sec:
            raise TimeoutError(f"poll_timeout after {waited:.0f}s; last status={status}")
        await asyncio.sleep(poll_sec)
        waited += poll_sec


async def _fetch_sentences(client, api_key: str, transcript_id: str) -> dict:
    """/transcript/{id}/sentences — nicer segment boundaries than raw words."""
    headers = {"authorization": api_key}
    r = await client.get(
        f"{_API_BASE}/transcript/{transcript_id}/sentences", headers=headers
    )
    # 404 is acceptable here (older transcripts without sentences). Propagate
    # other errors honestly.
    if r.status_code == 404:
        return {"sentences": []}
    r.raise_for_status()
    return r.json()


def _require_httpx() -> dict | None:
    try:
        import httpx  # noqa: F401
    except ImportError:
        return {"status": "error", "error": "httpx_not_installed",
                "hint": "pip install httpx"}
    return None


def _require_api_key() -> tuple[str | None, dict | None]:
    key = os.getenv("ASSEMBLYAI_API_KEY", "").strip()
    if not key:
        return None, {"status": "error", "error": "ASSEMBLYAI_API_KEY_missing",
                      "hint": "set ASSEMBLYAI_API_KEY in scribeclaw/.env and restart"}
    return key, None


async def transcribe_assemblyai(payload: dict[str, Any], data_root: Path) -> dict:
    """Upload a local audio file and start a new AssemblyAI job.

    Payload:
      input           (str, required): audio filename under /data/media/audio/
                                       (or a video under media/edited, media/in —
                                       AssemblyAI accepts common formats directly)
      language        (str, optional): default "ro"
      speaker_labels  (bool, optional): default False
      speech_models   (list[str], optional): AssemblyAI model ids; default
                                             ["universal-2"]. The legacy
                                             singular `speech_model` field is
                                             accepted and auto-upgraded to the
                                             plural array now required by the
                                             API.
      poll_sec        (int, optional): default 5
      poll_timeout_sec (int, optional): default 1800 (30 min)
    """
    miss = _require_httpx()
    if miss is not None:
        return {"handler": "transcribe_assemblyai", **miss}
    api_key, err = _require_api_key()
    if err is not None:
        return {"handler": "transcribe_assemblyai", **err}

    import httpx

    name = Path(payload["input"]).name
    for candidate in (data_root / "media" / "audio" / name,
                      data_root / "media" / "edited" / name,
                      data_root / "media" / "in" / name):
        if candidate.exists():
            in_path = candidate
            break
    else:
        return {"status": "error", "handler": "transcribe_assemblyai",
                "error": "input_not_found",
                "searched": ["media/audio/", "media/edited/", "media/in/"]}

    timeout = httpx.Timeout(connect=30.0, read=120.0, write=300.0, pool=30.0)
    async with httpx.AsyncClient(timeout=timeout) as client:
        try:
            upload_url = await _upload_file(client, api_key, in_path)
            transcript_id = await _start_job(client, api_key, upload_url, payload)
            raw = await _poll(
                client, api_key, transcript_id,
                poll_sec=float(payload.get("poll_sec", _DEFAULT_POLL_SEC)),
                timeout_sec=float(payload.get("poll_timeout_sec", _DEFAULT_POLL_TIMEOUT_SEC)),
            )
            sentences = await _fetch_sentences(client, api_key, transcript_id)
        except httpx.HTTPStatusError as exc:
            return {"status": "error", "handler": "transcribe_assemblyai",
                    "error": "assemblyai_http", "code": exc.response.status_code,
                    "detail": exc.response.text[-1000:]}
        except Exception as exc:
            return {"status": "error", "handler": "transcribe_assemblyai",
                    "error": exc.__class__.__name__, "detail": str(exc)}

    segments = _normalize_segments(sentences, raw.get("text") or "")
    out_dir = data_root / "transcripts" / in_path.stem
    _write_outputs(out_dir, raw, segments)

    return {
        "status": "success",
        "handler": "transcribe_assemblyai",
        "input": str(in_path),
        "output_dir": str(out_dir),
        "assemblyai_id": raw.get("id"),
        "language": raw.get("language_code", "ro"),
        "duration_sec": float(raw.get("audio_duration") or 0.0),
        "segments": len(segments),
    }


async def import_assemblyai_transcript(payload: dict[str, Any], data_root: Path) -> dict:
    """Pull an ALREADY-COMPLETED transcript by id — no upload, no re-billing.

    Use this to reuse work already visible in the AssemblyAI dashboard.

    Payload:
      transcript_id (str, required): AssemblyAI transcript id from the dashboard
      stem          (str, optional): output dirname under /data/transcripts/
                                     (default: transcript_id)
    """
    miss = _require_httpx()
    if miss is not None:
        return {"handler": "import_assemblyai_transcript", **miss}
    api_key, err = _require_api_key()
    if err is not None:
        return {"handler": "import_assemblyai_transcript", **err}

    import httpx

    transcript_id = str(payload["transcript_id"]).strip()
    if not transcript_id:
        return {"status": "error", "handler": "import_assemblyai_transcript",
                "error": "transcript_id_required"}
    stem = Path(payload.get("stem") or transcript_id).name

    timeout = httpx.Timeout(connect=30.0, read=60.0, write=30.0, pool=30.0)
    async with httpx.AsyncClient(timeout=timeout) as client:
        headers = {"authorization": api_key}
        try:
            r = await client.get(f"{_API_BASE}/transcript/{transcript_id}", headers=headers)
            r.raise_for_status()
            raw = r.json()
            if raw.get("status") != "completed":
                return {"status": "error", "handler": "import_assemblyai_transcript",
                        "error": "transcript_not_completed",
                        "assemblyai_status": raw.get("status"),
                        "hint": "wait for the job to finish, or use transcribe_assemblyai"}
            sentences = await _fetch_sentences(client, api_key, transcript_id)
        except httpx.HTTPStatusError as exc:
            return {"status": "error", "handler": "import_assemblyai_transcript",
                    "error": "assemblyai_http", "code": exc.response.status_code,
                    "detail": exc.response.text[-1000:]}
        except Exception as exc:
            return {"status": "error", "handler": "import_assemblyai_transcript",
                    "error": exc.__class__.__name__, "detail": str(exc)}

    segments = _normalize_segments(sentences, raw.get("text") or "")
    out_dir = data_root / "transcripts" / stem
    _write_outputs(out_dir, raw, segments)

    return {
        "status": "success",
        "handler": "import_assemblyai_transcript",
        "assemblyai_id": transcript_id,
        "stem": stem,
        "output_dir": str(out_dir),
        "language": raw.get("language_code", "ro"),
        "duration_sec": float(raw.get("audio_duration") or 0.0),
        "segments": len(segments),
    }


async def _list_page(client, api_key: str, before_id: str | None,
                     limit: int) -> dict:
    """GET /v2/transcript — paginated list. Returns {transcripts:[...],
    page_details:{prev_url, next_url, ...}}. `before_id` drives the cursor
    (AssemblyAI list is reverse-chronological)."""
    headers = {"authorization": api_key}
    params: dict[str, Any] = {"limit": limit, "status": "completed"}
    if before_id:
        params["before_id"] = before_id
    r = await client.get(f"{_API_BASE}/transcript", headers=headers, params=params)
    r.raise_for_status()
    return r.json()


async def bulk_import_assemblyai_romanian(
    payload: dict[str, Any], data_root: Path
) -> dict:
    """Clone every completed Romanian transcript from the dashboard.

    AssemblyAI's list endpoint does NOT filter by language_code, so we page
    through completed transcripts and fetch each detail to check
    language_code == 'ro' (or whatever the caller specified). Idempotent:
    skips transcripts whose output dir already exists unless overwrite=True.

    Payload:
      language        (str,  optional): default "ro"
      max_transcripts (int,  optional): soft cap; default 50
      page_size       (int,  optional): list page size; default 50, max 200
      overwrite       (bool, optional): default False
      stem_prefix     (str,  optional): prepended to each id for the stem
      start_before_id (str,  optional): start cursor (advanced; resumes a run)
    """
    miss = _require_httpx()
    if miss is not None:
        return {"handler": "bulk_import_assemblyai_romanian", **miss}
    api_key, err = _require_api_key()
    if err is not None:
        return {"handler": "bulk_import_assemblyai_romanian", **err}

    import httpx

    language = str(payload.get("language", "ro")).strip().lower()
    max_transcripts = int(payload.get("max_transcripts", 50))
    page_size = max(1, min(int(payload.get("page_size", 50)), 200))
    overwrite = bool(payload.get("overwrite", False))
    stem_prefix = str(payload.get("stem_prefix", "")).strip()
    before_id: str | None = payload.get("start_before_id") or None

    imported: list[dict] = []
    skipped_existing: list[str] = []
    skipped_language: list[dict] = []
    errors: list[dict] = []
    pages_seen = 0
    last_cursor: str | None = before_id

    timeout = httpx.Timeout(connect=30.0, read=120.0, write=30.0, pool=30.0)
    async with httpx.AsyncClient(timeout=timeout) as client:
        try:
            while len(imported) < max_transcripts:
                page = await _list_page(client, api_key, before_id, page_size)
                pages_seen += 1
                entries = page.get("transcripts", []) or []
                if not entries:
                    break
                for entry in entries:
                    if len(imported) >= max_transcripts:
                        break
                    tid = entry.get("id")
                    if not tid:
                        continue
                    last_cursor = tid
                    # /transcript list entries don't carry language_code, so
                    # we have to fetch detail to filter. This is the whole
                    # reason this handler exists as a dedicated endpoint
                    # rather than a one-liner.
                    try:
                        rdet = await client.get(
                            f"{_API_BASE}/transcript/{tid}",
                            headers={"authorization": api_key},
                        )
                        rdet.raise_for_status()
                        raw = rdet.json()
                    except httpx.HTTPStatusError as exc:
                        errors.append({"id": tid, "stage": "detail",
                                       "code": exc.response.status_code,
                                       "detail": exc.response.text[-500:]})
                        continue

                    lang = (raw.get("language_code") or "").lower()
                    if lang != language:
                        skipped_language.append({"id": tid, "language": lang or None})
                        continue

                    stem = f"{stem_prefix}{tid}" if stem_prefix else tid
                    out_dir = data_root / "transcripts" / stem
                    if out_dir.exists() and not overwrite:
                        skipped_existing.append(tid)
                        continue

                    try:
                        sentences = await _fetch_sentences(client, api_key, tid)
                    except httpx.HTTPStatusError as exc:
                        errors.append({"id": tid, "stage": "sentences",
                                       "code": exc.response.status_code,
                                       "detail": exc.response.text[-500:]})
                        continue

                    segments = _normalize_segments(sentences, raw.get("text") or "")
                    _write_outputs(out_dir, raw, segments)
                    imported.append({
                        "id": tid,
                        "stem": stem,
                        "output_dir": str(out_dir),
                        "duration_sec": float(raw.get("audio_duration") or 0.0),
                        "segments": len(segments),
                    })

                # Advance cursor — AssemblyAI uses the last id on the current
                # page as the `before_id` for the next page.
                before_id = entries[-1].get("id")
                if not before_id:
                    break
        except httpx.HTTPStatusError as exc:
            errors.append({"stage": "list", "code": exc.response.status_code,
                           "detail": exc.response.text[-500:]})
        except Exception as exc:  # network, timeout, etc. — surface honestly
            errors.append({"stage": "list",
                           "error": exc.__class__.__name__,
                           "detail": str(exc)})

    status = "success"
    if errors and not imported:
        status = "error"
    elif errors:
        status = "partial"

    return {
        "status": status,
        "handler": "bulk_import_assemblyai_romanian",
        "language": language,
        "pages_seen": pages_seen,
        "imported_count": len(imported),
        "imported": imported,
        "skipped_existing": skipped_existing,
        "skipped_language_count": len(skipped_language),
        "errors": errors,
        "resume_before_id": last_cursor,
        "hint": (
            "pass resume_before_id as start_before_id to continue from here "
            "on the next run"
        ),
    }
