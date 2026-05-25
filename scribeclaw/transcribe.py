"""transcribe_ro — Romanian-first transcription via faster-whisper.

Operator contract:
  - `faster-whisper` is installed (see requirements.txt).
  - CPU-only by default (int8). If CUDA is available and WHISPER_DEVICE=cuda,
    the handler will honor it. No GPU detection magic — explicit opt-in.
  - The model (default `large-v3`) is downloaded into WHISPER_CACHE_DIR on
    first use. That first call will block on the download; subsequent calls
    are local.

Outputs (under /data/transcripts/<stem>/):
  - segments.json   — full faster-whisper segments + word timestamps
  - transcript.srt  — SRT subtitles
  - transcript.vtt  — WebVTT
  - transcript.txt  — plain text (one paragraph per segment)
"""
from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any


def _format_ts(seconds: float, sep: str = ",") -> str:
    ms = int(round(seconds * 1000))
    h, ms = divmod(ms, 3_600_000)
    m, ms = divmod(ms, 60_000)
    s, ms = divmod(ms, 1000)
    return f"{h:02d}:{m:02d}:{s:02d}{sep}{ms:03d}"


def _write_srt(segments: list[dict], path: Path) -> None:
    lines: list[str] = []
    for i, seg in enumerate(segments, start=1):
        lines.append(str(i))
        lines.append(
            f"{_format_ts(seg['start'], ',')} --> {_format_ts(seg['end'], ',')}"
        )
        lines.append(seg["text"].strip())
        lines.append("")
    path.write_text("\n".join(lines), encoding="utf-8")


def _write_vtt(segments: list[dict], path: Path) -> None:
    lines: list[str] = ["WEBVTT", ""]
    for seg in segments:
        lines.append(
            f"{_format_ts(seg['start'], '.')} --> {_format_ts(seg['end'], '.')}"
        )
        lines.append(seg["text"].strip())
        lines.append("")
    path.write_text("\n".join(lines), encoding="utf-8")


async def transcribe_ro(payload: dict[str, Any], data_root: Path) -> dict:
    """Transcribe a WAV (ideally 16 kHz mono) produced by audio_extract.

    Payload:
      input       (str, required): wav filename under /data/media/audio/
      model       (str, optional): faster-whisper model id; default env or large-v3
      language    (str, optional): default 'ro'
      beam_size   (int, optional): default 5
      vad_filter  (bool, optional): default True
      word_timestamps (bool, optional): default True
    """
    try:
        from faster_whisper import WhisperModel
    except ImportError as exc:
        return {"status": "error", "handler": "transcribe_ro",
                "error": "faster_whisper_not_installed",
                "hint": "pip install faster-whisper",
                "detail": str(exc)}

    in_name = Path(payload["input"]).name
    in_path = data_root / "media" / "audio" / in_name
    if not in_path.exists():
        return {"status": "error", "handler": "transcribe_ro",
                "error": "input_not_found", "expected_at": str(in_path),
                "hint": "run audio_extract first"}

    model_id = payload.get("model") or os.getenv("WHISPER_MODEL", "large-v3")
    device = os.getenv("WHISPER_DEVICE", "cpu")
    compute_type = os.getenv("WHISPER_COMPUTE", "int8" if device == "cpu" else "float16")
    cache_dir = os.getenv("WHISPER_CACHE_DIR") or None

    try:
        model = WhisperModel(
            model_id, device=device, compute_type=compute_type,
            download_root=cache_dir,
        )
    except Exception as exc:
        return {"status": "error", "handler": "transcribe_ro",
                "error": "model_load_failed", "detail": str(exc),
                "model": model_id, "device": device, "compute_type": compute_type}

    segments_iter, info = model.transcribe(
        str(in_path),
        language=payload.get("language", "ro"),
        beam_size=int(payload.get("beam_size", 5)),
        vad_filter=bool(payload.get("vad_filter", True)),
        word_timestamps=bool(payload.get("word_timestamps", True)),
    )

    segments: list[dict] = []
    for seg in segments_iter:
        words = None
        if seg.words:
            words = [
                {"start": float(w.start), "end": float(w.end),
                 "word": w.word, "probability": float(w.probability)}
                for w in seg.words
            ]
        segments.append({
            "id": seg.id,
            "start": float(seg.start),
            "end": float(seg.end),
            "text": seg.text,
            "avg_logprob": float(seg.avg_logprob),
            "no_speech_prob": float(seg.no_speech_prob),
            "words": words,
        })

    out_dir = data_root / "transcripts" / in_path.stem
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "segments.json").write_text(
        json.dumps({
            "language": info.language,
            "language_probability": float(info.language_probability),
            "duration": float(info.duration),
            "model": model_id,
            "segments": segments,
        }, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    _write_srt(segments, out_dir / "transcript.srt")
    _write_vtt(segments, out_dir / "transcript.vtt")
    (out_dir / "transcript.txt").write_text(
        "\n\n".join(s["text"].strip() for s in segments if s["text"].strip()),
        encoding="utf-8",
    )

    return {
        "status": "success",
        "handler": "transcribe_ro",
        "input": str(in_path),
        "output_dir": str(out_dir),
        "language": info.language,
        "language_probability": float(info.language_probability),
        "duration_sec": float(info.duration),
        "segments": len(segments),
        "model": model_id,
        "device": device,
        "compute_type": compute_type,
    }
