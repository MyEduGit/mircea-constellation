"""SeedanceClaw — fal.ai Seedance video generation handlers.

Handlers:
  text_to_video   — generate a video from a text prompt
  image_to_video  — generate a video from an image + text prompt
  download_video  — fetch a remote video URL to /data/videos/

All handlers are async and return a dict with at minimum:
  {"status": "success"|"error", ...}

UrantiOS governed — Truth, Beauty, Goodness.
"""
from __future__ import annotations

import os
import time
from pathlib import Path
from typing import Any

# ---------------------------------------------------------------------------
# Model ID defaults — overridable via environment variables
# ---------------------------------------------------------------------------
_DEFAULT_T2V_MODEL = os.getenv(
    "SEEDANCE_MODEL_T2V",
    "fal-ai/bytedance/seedance/v1/pro/text-to-video",
)
_DEFAULT_I2V_MODEL = os.getenv(
    "SEEDANCE_MODEL_I2V",
    "fal-ai/bytedance/seedance/v1/pro/image-to-video",
)


def _fal_client():
    import fal_client  # noqa: PLC0415
    return fal_client


def _require_fal_key() -> str:
    key = os.getenv("FAL_KEY", "").strip()
    if not key:
        raise RuntimeError(
            "FAL_KEY environment variable is not set. "
            "Obtain a key at https://fal.ai and set FAL_KEY in seedanceclaw/.env"
        )
    return key


def _save_video(url: str, dest_dir: Path, stem: str) -> Path:
    """Download a video URL to dest_dir/<stem>.mp4 and return the path."""
    import httpx  # noqa: PLC0415

    dest_dir.mkdir(parents=True, exist_ok=True)
    dest = dest_dir / f"{stem}.mp4"
    with httpx.stream("GET", url, follow_redirects=True, timeout=300) as r:
        r.raise_for_status()
        with open(dest, "wb") as fh:
            for chunk in r.iter_bytes(chunk_size=65536):
                fh.write(chunk)
    return dest


async def text_to_video(payload: dict[str, Any], data_root: Path) -> dict:
    """Generate a video from a text prompt via Seedance on fal.ai."""
    _require_fal_key()
    fal = _fal_client()

    prompt = payload.get("prompt", "").strip()
    if not prompt:
        return {"status": "error", "error": "payload.prompt is required"}

    model = payload.get("model", _DEFAULT_T2V_MODEL)
    arguments: dict[str, Any] = {
        "prompt": prompt,
        "duration": int(payload.get("duration", 5)),
        "aspect_ratio": payload.get("aspect_ratio", "16:9"),
        "resolution": payload.get("resolution", "720p"),
    }
    # Forward any extra fal.ai arguments the caller supplies
    for k, v in payload.items():
        if k not in ("prompt", "model", "duration", "aspect_ratio", "resolution"):
            arguments[k] = v

    result = await fal.run_async(model, arguments=arguments)

    video_url: str = ""
    if isinstance(result, dict):
        # fal.ai typically returns {"video": {"url": "..."}} or {"url": "..."}
        video_info = result.get("video") or result
        video_url = (video_info.get("url") or "") if isinstance(video_info, dict) else ""

    local_path = ""
    if video_url:
        stem = f"t2v_{int(time.time() * 1000)}"
        dest = _save_video(video_url, data_root / "videos", stem)
        local_path = str(dest)

    return {
        "status": "success",
        "handler": "text_to_video",
        "model": model,
        "prompt": prompt,
        "video_url": video_url,
        "local_path": local_path,
        "fal_result": result,
    }


async def image_to_video(payload: dict[str, Any], data_root: Path) -> dict:
    """Generate a video from an image + text prompt via Seedance on fal.ai."""
    _require_fal_key()
    fal = _fal_client()

    prompt = payload.get("prompt", "").strip()
    image_url: str = payload.get("image_url", "").strip()
    image_path: str = payload.get("image_path", "").strip()

    if not prompt:
        return {"status": "error", "error": "payload.prompt is required"}
    if not image_url and not image_path:
        return {"status": "error", "error": "payload.image_url or payload.image_path is required"}

    # Upload a local file to fal.ai storage if a path was given
    if image_path and not image_url:
        local = data_root / "images" / image_path
        if not local.exists():
            return {"status": "error", "error": f"image_path not found: {local}"}
        image_url = await fal.upload_file_async(str(local))

    model = payload.get("model", _DEFAULT_I2V_MODEL)
    arguments: dict[str, Any] = {
        "prompt": prompt,
        "image_url": image_url,
        "duration": int(payload.get("duration", 5)),
        "aspect_ratio": payload.get("aspect_ratio", "16:9"),
        "resolution": payload.get("resolution", "720p"),
    }
    for k, v in payload.items():
        if k not in ("prompt", "model", "image_url", "image_path",
                     "duration", "aspect_ratio", "resolution"):
            arguments[k] = v

    result = await fal.run_async(model, arguments=arguments)

    video_url = ""
    if isinstance(result, dict):
        video_info = result.get("video") or result
        video_url = (video_info.get("url") or "") if isinstance(video_info, dict) else ""

    local_path = ""
    if video_url:
        stem = f"i2v_{int(time.time() * 1000)}"
        dest = _save_video(video_url, data_root / "videos", stem)
        local_path = str(dest)

    return {
        "status": "success",
        "handler": "image_to_video",
        "model": model,
        "prompt": prompt,
        "image_url": image_url,
        "video_url": video_url,
        "local_path": local_path,
        "fal_result": result,
    }


async def download_video(payload: dict[str, Any], data_root: Path) -> dict:
    """Fetch a remote video URL and save it under /data/videos/."""
    url = payload.get("url", "").strip()
    if not url:
        return {"status": "error", "error": "payload.url is required"}

    stem = payload.get("stem", f"download_{int(time.time() * 1000)}")
    dest = _save_video(url, data_root / "videos", stem)
    return {
        "status": "success",
        "handler": "download_video",
        "url": url,
        "local_path": str(dest),
    }
