"""media_edit + audio_extract handlers — ffmpeg wrappers.

Operator contract: ffmpeg must be on PATH. If it is not, the handler
returns status=error with a clear reason; it does not attempt install.

All paths are resolved against DATA_ROOT (the module caller supplies it)
so that the container's bind-mount is the single source of truth.
"""
from __future__ import annotations

import asyncio
import shutil
from pathlib import Path
from typing import Any


async def _run(cmd: list[str]) -> tuple[int, str, str]:
    proc = await asyncio.create_subprocess_exec(
        *cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    out, err = await proc.communicate()
    return proc.returncode or 0, out.decode("utf-8", "replace"), err.decode("utf-8", "replace")


def _ffmpeg_missing() -> dict | None:
    if shutil.which("ffmpeg") is None:
        return {"status": "error", "error": "ffmpeg_not_on_path",
                "hint": "install ffmpeg (apt-get install -y ffmpeg) and retry"}
    return None


async def media_edit(payload: dict[str, Any], data_root: Path) -> dict:
    """Trim, loudness-normalize, and optionally strip long silences.

    Payload:
      input        (str, required): path under /data/media/in/
      output       (str, optional): path under /data/media/edited/
      start        (str, optional): ffmpeg -ss argument (e.g. "00:00:05")
      end          (str, optional): ffmpeg -to argument (e.g. "01:02:30")
      loudnorm     (bool, default True): EBU R128 two-pass approximation (single-pass)
      remove_silence (bool, default False): silenceremove filter
      silence_threshold_db (int, default -35)
      silence_min_ms       (int, default 700)
    """
    miss = _ffmpeg_missing()
    if miss is not None:
        return {"handler": "media_edit", **miss}

    in_path = data_root / "media" / "in" / Path(payload["input"]).name
    if not in_path.exists():
        return {"status": "error", "handler": "media_edit",
                "error": "input_not_found", "expected_at": str(in_path)}

    out_dir = data_root / "media" / "edited"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_name = payload.get("output") or f"{in_path.stem}.edited{in_path.suffix}"
    out_path = out_dir / Path(out_name).name

    filters: list[str] = []
    if payload.get("loudnorm", True):
        filters.append("loudnorm=I=-16:TP=-1.5:LRA=11")
    if payload.get("remove_silence", False):
        th = int(payload.get("silence_threshold_db", -35))
        ms = int(payload.get("silence_min_ms", 700))
        filters.append(
            f"silenceremove=stop_periods=-1:stop_duration={ms/1000:.3f}:stop_threshold={th}dB"
        )

    cmd: list[str] = ["ffmpeg", "-y", "-hide_banner", "-loglevel", "error"]
    if payload.get("start"):
        cmd += ["-ss", str(payload["start"])]
    if payload.get("end"):
        cmd += ["-to", str(payload["end"])]
    cmd += ["-i", str(in_path)]
    if filters:
        cmd += ["-af", ",".join(filters)]
    cmd += ["-c:v", "copy" if not filters else "libx264",
            "-c:a", "aac", "-b:a", "192k",
            str(out_path)]

    rc, _out, err = await _run(cmd)
    if rc != 0:
        return {"status": "error", "handler": "media_edit",
                "error": "ffmpeg_failed", "returncode": rc,
                "stderr_tail": err[-2000:]}
    return {
        "status": "success",
        "handler": "media_edit",
        "input": str(in_path),
        "output": str(out_path),
        "filters": filters,
    }


async def audio_extract(payload: dict[str, Any], data_root: Path) -> dict:
    """Extract 16 kHz mono WAV suitable for Whisper.

    Payload:
      input  (str, required): path under /data/media/edited/ or /data/media/in/
      output (str, optional): path under /data/media/audio/ (default <stem>.wav)
    """
    miss = _ffmpeg_missing()
    if miss is not None:
        return {"handler": "audio_extract", **miss}

    name = Path(payload["input"]).name
    for candidate in (data_root / "media" / "edited" / name,
                      data_root / "media" / "in" / name):
        if candidate.exists():
            in_path = candidate
            break
    else:
        return {"status": "error", "handler": "audio_extract",
                "error": "input_not_found",
                "searched": ["media/edited/", "media/in/"]}

    out_dir = data_root / "media" / "audio"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_name = payload.get("output") or f"{in_path.stem}.wav"
    out_path = out_dir / Path(out_name).name

    cmd = [
        "ffmpeg", "-y", "-hide_banner", "-loglevel", "error",
        "-i", str(in_path),
        "-vn", "-ac", "1", "-ar", "16000",
        "-c:a", "pcm_s16le",
        str(out_path),
    ]
    rc, _out, err = await _run(cmd)
    if rc != 0:
        return {"status": "error", "handler": "audio_extract",
                "error": "ffmpeg_failed", "returncode": rc,
                "stderr_tail": err[-2000:]}
    return {"status": "success", "handler": "audio_extract",
            "input": str(in_path), "output": str(out_path),
            "sample_rate": 16000, "channels": 1}
