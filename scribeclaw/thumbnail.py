"""thumbnail_generate — produce a 1280x720 YouTube thumbnail from a video.

Two-step pipeline:
  1. ffmpeg extracts a single frame at the operator-chosen timestamp,
     scales to YouTube's 1280x720 target, writes an intermediate JPG.
  2. Pillow optionally draws an overlay strip with title text (pulled
     from the YouTube bundle if `title` is not provided in the payload).

Written to: /data/youtube/<stem>/thumbnail.jpg
Kept as canonical output so `youtube_upload` (once live) can pick it up
without re-deriving paths.

Operator contract:
  - ffmpeg must be on PATH (shared with media_edit / audio_extract).
  - Pillow must be installed (`pillow` in requirements.txt). When Pillow
    is missing the handler still returns the raw ffmpeg frame — refusing
    would be annoying, and the raw 1280x720 JPG is already uploadable.
    The result payload surfaces `overlay_applied: false` with the
    reason so the caller is never misled.
"""
from __future__ import annotations

import asyncio
import json
import shutil
from pathlib import Path
from typing import Any

# Reasonable-defaults for text layout. Each is tunable via payload.
_DEFAULT_FRAME_TS = "00:00:03"
_OVERLAY_HEIGHT_FRAC = 0.18   # strip height relative to 720
_OVERLAY_ALPHA = 170          # 0-255
_OVERLAY_PAD_PX = 36
_MAX_FONT_PX = 72
_MIN_FONT_PX = 28


async def _run(cmd: list[str]) -> tuple[int, str, str]:
    proc = await asyncio.create_subprocess_exec(
        *cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    out, err = await proc.communicate()
    return (proc.returncode or 0,
            out.decode("utf-8", "replace"),
            err.decode("utf-8", "replace"))


def _resolve_input(data_root: Path, name: str) -> Path | None:
    base = Path(name).name
    for candidate in (data_root / "media" / "edited" / base,
                      data_root / "media" / "in" / base,
                      data_root / "media" / "audio" / base):
        if candidate.exists():
            return candidate
    return None


def _load_title_from_bundle(out_dir: Path) -> str | None:
    bundle_file = out_dir / "bundle.json"
    if not bundle_file.exists():
        return None
    try:
        data = json.loads(bundle_file.read_text(encoding="utf-8"))
    except Exception:
        return None
    candidates = data.get("title_candidates") or []
    return candidates[0] if candidates else None


def _font_for_size(size_px: int):
    """Return a PIL ImageFont trying DejaVuSans (ships in python:3.12-slim
    via apt fonts-dejavu if present) before falling back to default."""
    from PIL import ImageFont
    for candidate in (
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    ):
        try:
            return ImageFont.truetype(candidate, size_px)
        except OSError:
            continue
    return ImageFont.load_default()


def _fit_text(draw, text: str, max_width: int, max_font: int, min_font: int):
    """Binary-search-ish shrink-to-fit. Cheap enough for a single line."""
    size = max_font
    while size >= min_font:
        font = _font_for_size(size)
        bbox = draw.textbbox((0, 0), text, font=font)
        if (bbox[2] - bbox[0]) <= max_width:
            return font, bbox
        size -= 4
    font = _font_for_size(min_font)
    return font, draw.textbbox((0, 0), text, font=font)


def _apply_overlay(thumb_path: Path, text: str) -> tuple[bool, str | None]:
    """Draw a translucent bottom strip and write text into it. Mutates
    the file in place. Returns (applied, reason_if_not)."""
    try:
        from PIL import Image, ImageDraw
    except ImportError:
        return False, "pillow_not_installed"

    try:
        img = Image.open(thumb_path).convert("RGBA")
    except Exception as exc:
        return False, f"pil_open_failed: {exc}"

    w, h = img.size
    strip_h = int(h * _OVERLAY_HEIGHT_FRAC)
    overlay = Image.new("RGBA", (w, strip_h), (0, 0, 0, _OVERLAY_ALPHA))
    img.paste(overlay, (0, h - strip_h), overlay)

    draw = ImageDraw.Draw(img)
    usable_w = w - 2 * _OVERLAY_PAD_PX
    font, bbox = _fit_text(draw, text, usable_w, _MAX_FONT_PX, _MIN_FONT_PX)
    tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
    x = (w - tw) // 2
    y = h - strip_h + (strip_h - th) // 2 - bbox[1]
    draw.text((x, y), text, fill=(255, 255, 255, 255), font=font)

    img.convert("RGB").save(thumb_path, "JPEG", quality=92)
    return True, None


async def thumbnail_generate(payload: dict[str, Any], data_root: Path) -> dict:
    """Extract a frame and optionally overlay a title — write thumbnail.jpg.

    Payload:
      input        (str, required): video under media/edited/ or media/in/
      stem         (str, optional): output dirname; default = Path(input).stem
      timestamp    (str, optional): ffmpeg -ss value; default "00:00:03"
      title        (str, optional): overlay text; default = bundle's first
                                    title_candidate if present, else no overlay
      no_overlay   (bool, optional): force raw frame (skip Pillow entirely)
    """
    if shutil.which("ffmpeg") is None:
        return {"status": "error", "handler": "thumbnail_generate",
                "error": "ffmpeg_not_on_path",
                "hint": "install ffmpeg in the container image"}

    in_name = str(payload.get("input") or "").strip()
    if not in_name:
        return {"status": "error", "handler": "thumbnail_generate",
                "error": "input_required"}
    in_path = _resolve_input(data_root, in_name)
    if in_path is None:
        return {"status": "error", "handler": "thumbnail_generate",
                "error": "input_not_found",
                "searched": ["media/edited/", "media/in/", "media/audio/"]}

    stem = str(payload.get("stem") or Path(in_name).stem).strip()
    stem = Path(stem).name or Path(in_name).stem
    out_dir = data_root / "youtube" / stem
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / "thumbnail.jpg"

    timestamp = str(payload.get("timestamp") or _DEFAULT_FRAME_TS)

    # Scale then pad to exactly 1280x720 — preserves aspect, black bars if
    # source isn't 16:9 (YouTube's recommended size).
    vf = ("scale=1280:720:force_original_aspect_ratio=decrease,"
          "pad=1280:720:(ow-iw)/2:(oh-ih)/2:color=black")
    cmd = [
        "ffmpeg", "-y", "-hide_banner", "-loglevel", "error",
        "-ss", timestamp, "-i", str(in_path),
        "-frames:v", "1", "-vf", vf, "-q:v", "2",
        str(out_path),
    ]
    rc, _out, err = await _run(cmd)
    if rc != 0 or not out_path.exists():
        return {"status": "error", "handler": "thumbnail_generate",
                "error": "ffmpeg_failed", "returncode": rc,
                "stderr_tail": err[-1500:]}

    overlay_applied = False
    overlay_reason: str | None = None
    overlay_text: str | None = None

    if not bool(payload.get("no_overlay", False)):
        text = payload.get("title")
        if not text:
            text = _load_title_from_bundle(out_dir)
        if text:
            text = str(text).strip()
            if text:
                overlay_text = text
                overlay_applied, overlay_reason = _apply_overlay(out_path, text)
        else:
            overlay_reason = "no_title_supplied_or_in_bundle"

    return {
        "status": "success",
        "handler": "thumbnail_generate",
        "input": str(in_path),
        "stem": stem,
        "output": str(out_path),
        "size": [1280, 720],
        "timestamp": timestamp,
        "overlay_applied": overlay_applied,
        "overlay_text": overlay_text,
        "overlay_skipped_reason": overlay_reason if not overlay_applied else None,
    }
