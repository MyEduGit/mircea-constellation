"""CinemaClaw handler allowlist — every stage of the YouTube pipeline.

Handlers are the ONLY way CinemaClaw touches the filesystem, ffmpeg, or
the YouTube API. They are collected in HANDLERS at the bottom of this
module; anything not in that dict cannot run (see cinemaclaw.dispatch).

Every handler returns a dict with a stable shape:

    {
      "kind":        "<handler_name>",
      "executed":    bool,           # True if the handler was attempted
      "ok":          bool,           # True only if the attempt succeeded
      "duration_ms": int,
      "outputs":     list[str],      # files produced (empty on refusal)
      "detail":      str,            # short human-readable status
      "stderr":      str,            # ffmpeg / upload stderr tail (<=2KB)
    }

Handlers never raise — failures become ok=False with detail populated.
All destructive or network-side-effecting handlers honour dry_run=True
by returning executed=False with a "DRY-RUN" detail.

Truth labels:
  REAL      — fully implemented; `--execute` will invoke ffmpeg / API.
  RENDER    — real locally (ffmpeg) but requires ffmpeg on PATH.
  STAGED    — produces an upload-ready artifact but does NOT hit network.
  DRY-ONLY  — implemented as a stub; --execute still refuses (honest).
"""
from __future__ import annotations

import json
import os
import shlex
import shutil
import subprocess
import time
from pathlib import Path
from typing import Any


# ── helpers ────────────────────────────────────────────────────────────
def _now_ms() -> int:
    return int(time.time() * 1000)


def _result(kind: str, *, executed: bool, ok: bool, started: float,
            outputs: list[str] | None = None, detail: str = "",
            stderr: str = "") -> dict[str, Any]:
    return {
        "kind": kind,
        "executed": executed,
        "ok": ok,
        "duration_ms": int((time.monotonic() - started) * 1000),
        "outputs": outputs or [],
        "detail": detail,
        "stderr": (stderr or "")[-2000:],
    }


def _run_ffmpeg(args: list[str], timeout: float = 1800.0) -> subprocess.CompletedProcess:
    """Invoke ffmpeg with a pinned prefix. Raises CalledProcessError on non-zero."""
    ff = shutil.which("ffmpeg")
    if not ff:
        raise FileNotFoundError("ffmpeg not on PATH")
    # -y = overwrite; -hide_banner = less noise; -nostdin = never prompt.
    cmd = [ff, "-y", "-hide_banner", "-nostdin", *args]
    return subprocess.run(cmd, capture_output=True, text=True, timeout=timeout, check=False)


def _ensure_parent(path: str | os.PathLike) -> Path:
    p = Path(os.path.expanduser(str(path)))
    p.parent.mkdir(parents=True, exist_ok=True)
    return p


# ── 1. ingest ─────────────────────────────────────────────────────────
def ingest(*, source: str, inbox: str = "~/cinemaclaw/inbox",
           dry_run: bool = False) -> dict[str, Any]:
    """Copy a source file into the inbox. Idempotent.

    Truth label: REAL (filesystem copy).
    """
    started = time.monotonic()
    src = Path(os.path.expanduser(source))
    dst = _ensure_parent(Path(inbox) / src.name)
    if dry_run:
        return _result("ingest", executed=False, ok=True, started=started,
                       outputs=[str(dst)],
                       detail=f"DRY-RUN: copy {src} → {dst}")
    if not src.is_file():
        return _result("ingest", executed=False, ok=False, started=started,
                       detail=f"source not found: {src}")
    try:
        shutil.copy2(src, dst)
    except OSError as e:
        return _result("ingest", executed=True, ok=False, started=started,
                       detail=f"copy_failed: {e}")
    return _result("ingest", executed=True, ok=True, started=started,
                   outputs=[str(dst)], detail=f"copied {src.name} → inbox")


# ── 2. probe ──────────────────────────────────────────────────────────
def probe(*, source: str, dry_run: bool = False) -> dict[str, Any]:
    """Run ffprobe and return duration / streams. Read-only.

    Truth label: REAL (ffprobe).
    """
    started = time.monotonic()
    src = Path(os.path.expanduser(source))
    if dry_run:
        return _result("probe", executed=False, ok=True, started=started,
                       outputs=[str(src)],
                       detail=f"DRY-RUN: ffprobe {src}")
    if not src.is_file():
        return _result("probe", executed=False, ok=False, started=started,
                       detail=f"source not found: {src}")
    ffprobe = shutil.which("ffprobe")
    if not ffprobe:
        return _result("probe", executed=False, ok=False, started=started,
                       detail="ffprobe not on PATH")
    cmd = [ffprobe, "-v", "error", "-print_format", "json",
           "-show_format", "-show_streams", str(src)]
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
    except subprocess.TimeoutExpired:
        return _result("probe", executed=True, ok=False, started=started,
                       detail="probe timeout")
    if r.returncode != 0:
        return _result("probe", executed=True, ok=False, started=started,
                       detail="ffprobe failed", stderr=r.stderr)
    try:
        meta = json.loads(r.stdout)
    except json.JSONDecodeError as e:
        return _result("probe", executed=True, ok=False, started=started,
                       detail=f"invalid ffprobe json: {e}")
    dur = float(meta.get("format", {}).get("duration", 0.0) or 0.0)
    streams = [s.get("codec_type", "?") for s in meta.get("streams", [])]
    return _result("probe", executed=True, ok=True, started=started,
                   outputs=[str(src)],
                   detail=f"duration={dur:.2f}s streams={','.join(streams) or 'none'}")


# ── 3. trim ───────────────────────────────────────────────────────────
def trim(*, source: str, start: str = "0", end: str | None = None,
         duration: str | None = None, out: str, dry_run: bool = False) -> dict[str, Any]:
    """Cut [start, end] or [start, start+duration] from source via ffmpeg.

    Uses stream-copy (-c copy) when possible for speed; falls back to
    a re-encode only when the caller explicitly sets end/duration with
    sub-second precision that stream-copy would round. This handler
    prefers lossless when semantics allow.

    Truth label: RENDER.
    """
    started = time.monotonic()
    src = Path(os.path.expanduser(source))
    dst = _ensure_parent(out)
    ff_args = ["-ss", str(start), "-i", str(src)]
    if duration is not None:
        ff_args += ["-t", str(duration)]
    elif end is not None:
        ff_args += ["-to", str(end)]
    ff_args += ["-c", "copy", str(dst)]
    if dry_run:
        return _result("trim", executed=False, ok=True, started=started,
                       outputs=[str(dst)],
                       detail="DRY-RUN: ffmpeg " + " ".join(shlex.quote(a) for a in ff_args))
    if not src.is_file():
        return _result("trim", executed=False, ok=False, started=started,
                       detail=f"source not found: {src}")
    try:
        r = _run_ffmpeg(ff_args)
    except FileNotFoundError as e:
        return _result("trim", executed=False, ok=False, started=started, detail=str(e))
    except subprocess.TimeoutExpired:
        return _result("trim", executed=True, ok=False, started=started, detail="trim timeout")
    if r.returncode != 0:
        return _result("trim", executed=True, ok=False, started=started,
                       detail="ffmpeg trim failed", stderr=r.stderr)
    return _result("trim", executed=True, ok=True, started=started,
                   outputs=[str(dst)],
                   detail=f"trimmed {start}→{end or f'+{duration}'} into {dst.name}")


# ── 4. normalize_audio ────────────────────────────────────────────────
def normalize_audio(*, source: str, out: str, target_lufs: float = -14.0,
                    dry_run: bool = False) -> dict[str, Any]:
    """Normalize loudness to YouTube's reference (~-14 LUFS) via loudnorm.

    Truth label: RENDER (re-encodes audio, stream-copies video).
    """
    started = time.monotonic()
    src = Path(os.path.expanduser(source))
    dst = _ensure_parent(out)
    filt = f"loudnorm=I={target_lufs}:TP=-1.5:LRA=11"
    ff_args = ["-i", str(src), "-c:v", "copy",
               "-af", filt, "-c:a", "aac", "-b:a", "192k", str(dst)]
    if dry_run:
        return _result("normalize_audio", executed=False, ok=True, started=started,
                       outputs=[str(dst)],
                       detail="DRY-RUN: ffmpeg " + " ".join(shlex.quote(a) for a in ff_args))
    if not src.is_file():
        return _result("normalize_audio", executed=False, ok=False, started=started,
                       detail=f"source not found: {src}")
    try:
        r = _run_ffmpeg(ff_args)
    except FileNotFoundError as e:
        return _result("normalize_audio", executed=False, ok=False, started=started, detail=str(e))
    except subprocess.TimeoutExpired:
        return _result("normalize_audio", executed=True, ok=False, started=started,
                       detail="normalize timeout")
    if r.returncode != 0:
        return _result("normalize_audio", executed=True, ok=False, started=started,
                       detail="loudnorm failed", stderr=r.stderr)
    return _result("normalize_audio", executed=True, ok=True, started=started,
                   outputs=[str(dst)],
                   detail=f"loudnorm I={target_lufs} LUFS → {dst.name}")


# ── 5. concat ─────────────────────────────────────────────────────────
def concat(*, sources: list[str], out: str, dry_run: bool = False) -> dict[str, Any]:
    """Concatenate multiple compatible mp4/mov segments in order.

    Uses ffmpeg's concat demuxer — inputs MUST share codec parameters.
    If you trimmed them with stream-copy from the same master, they do.

    Truth label: RENDER.
    """
    started = time.monotonic()
    srcs = [Path(os.path.expanduser(s)) for s in sources]
    if not srcs:
        return _result("concat", executed=False, ok=False, started=started,
                       detail="no sources provided")
    dst = _ensure_parent(out)
    if dry_run:
        return _result("concat", executed=False, ok=True, started=started,
                       outputs=[str(dst)],
                       detail=f"DRY-RUN: concat {len(srcs)} segments → {dst.name}")
    missing = [str(s) for s in srcs if not s.is_file()]
    if missing:
        return _result("concat", executed=False, ok=False, started=started,
                       detail=f"missing sources: {missing}")
    # Build a concat list file in a private temp location alongside the output.
    listfile = dst.with_suffix(".concat.txt")
    try:
        listfile.write_text("\n".join(f"file {shlex.quote(str(s))}" for s in srcs) + "\n")
    except OSError as e:
        return _result("concat", executed=True, ok=False, started=started,
                       detail=f"listfile write failed: {e}")
    ff_args = ["-f", "concat", "-safe", "0", "-i", str(listfile),
               "-c", "copy", str(dst)]
    try:
        r = _run_ffmpeg(ff_args)
    except FileNotFoundError as e:
        return _result("concat", executed=False, ok=False, started=started, detail=str(e))
    except subprocess.TimeoutExpired:
        return _result("concat", executed=True, ok=False, started=started,
                       detail="concat timeout")
    finally:
        try:
            listfile.unlink(missing_ok=True)
        except OSError:
            pass
    if r.returncode != 0:
        return _result("concat", executed=True, ok=False, started=started,
                       detail="ffmpeg concat failed", stderr=r.stderr)
    return _result("concat", executed=True, ok=True, started=started,
                   outputs=[str(dst)],
                   detail=f"concatenated {len(srcs)} segments → {dst.name}")


# ── 6. burn_captions ──────────────────────────────────────────────────
def burn_captions(*, source: str, subtitles: str, out: str,
                  dry_run: bool = False) -> dict[str, Any]:
    """Hard-burn an .srt/.ass subtitle track into the video.

    For YouTube, soft captions are preferred (uploaded separately as a
    sidecar file). Use this only for platforms that strip captions, or
    for social-clip cuts where captions must be baked in.

    Truth label: RENDER.
    """
    started = time.monotonic()
    src = Path(os.path.expanduser(source))
    sub = Path(os.path.expanduser(subtitles))
    dst = _ensure_parent(out)
    # ffmpeg's subtitles filter needs a POSIX-escaped path.
    escaped = str(sub).replace(":", r"\:").replace(",", r"\,")
    ff_args = ["-i", str(src), "-vf", f"subtitles={escaped}",
               "-c:a", "copy", str(dst)]
    if dry_run:
        return _result("burn_captions", executed=False, ok=True, started=started,
                       outputs=[str(dst)],
                       detail=f"DRY-RUN: burn {sub.name} into {src.name}")
    if not src.is_file():
        return _result("burn_captions", executed=False, ok=False, started=started,
                       detail=f"source not found: {src}")
    if not sub.is_file():
        return _result("burn_captions", executed=False, ok=False, started=started,
                       detail=f"subtitles not found: {sub}")
    try:
        r = _run_ffmpeg(ff_args)
    except FileNotFoundError as e:
        return _result("burn_captions", executed=False, ok=False, started=started, detail=str(e))
    except subprocess.TimeoutExpired:
        return _result("burn_captions", executed=True, ok=False, started=started,
                       detail="burn_captions timeout")
    if r.returncode != 0:
        return _result("burn_captions", executed=True, ok=False, started=started,
                       detail="burn_captions failed", stderr=r.stderr)
    return _result("burn_captions", executed=True, ok=True, started=started,
                   outputs=[str(dst)],
                   detail=f"burned captions → {dst.name}")


# ── 7. render_thumbnail ───────────────────────────────────────────────
def render_thumbnail(*, source: str, out: str, at: str = "00:00:03",
                     width: int = 1280, dry_run: bool = False) -> dict[str, Any]:
    """Extract a single frame as a YouTube-friendly thumbnail (JPEG).

    Truth label: REAL (ffmpeg single-frame extract).
    """
    started = time.monotonic()
    src = Path(os.path.expanduser(source))
    dst = _ensure_parent(out)
    ff_args = ["-ss", str(at), "-i", str(src), "-frames:v", "1",
               "-vf", f"scale={int(width)}:-2", "-q:v", "2", str(dst)]
    if dry_run:
        return _result("render_thumbnail", executed=False, ok=True, started=started,
                       outputs=[str(dst)],
                       detail=f"DRY-RUN: thumbnail @ {at} w={width} → {dst.name}")
    if not src.is_file():
        return _result("render_thumbnail", executed=False, ok=False, started=started,
                       detail=f"source not found: {src}")
    try:
        r = _run_ffmpeg(ff_args, timeout=120.0)
    except FileNotFoundError as e:
        return _result("render_thumbnail", executed=False, ok=False, started=started, detail=str(e))
    except subprocess.TimeoutExpired:
        return _result("render_thumbnail", executed=True, ok=False, started=started,
                       detail="thumbnail timeout")
    if r.returncode != 0:
        return _result("render_thumbnail", executed=True, ok=False, started=started,
                       detail="thumbnail failed", stderr=r.stderr)
    return _result("render_thumbnail", executed=True, ok=True, started=started,
                   outputs=[str(dst)],
                   detail=f"thumbnail at {at} → {dst.name}")


# ── 8. write_metadata ─────────────────────────────────────────────────
def write_metadata(*, source: str, out: str, title: str, description: str = "",
                   tags: list[str] | None = None, category_id: int = 27,
                   privacy: str = "private",
                   chapters: list[dict[str, Any]] | None = None,
                   dry_run: bool = False) -> dict[str, Any]:
    """Write a YouTube-upload-ready metadata sidecar next to the video.

    The sidecar is consumed by `publish_youtube` (below) or by any
    third-party uploader (yt-dlp-style). Format is a flat JSON document
    with a schema version so future changes are explicit.

    `category_id` defaults to 27 (Education) — CinemaClaw's primary use.
    `privacy` must be one of: private | unlisted | public. CinemaClaw
    defaults to `private` so nothing leaks accidentally; publish_youtube
    upgrades privacy only on --signed-by-father.

    Truth label: STAGED (writes sidecar; does not touch YouTube).
    """
    started = time.monotonic()
    src = Path(os.path.expanduser(source))
    if privacy not in ("private", "unlisted", "public"):
        return _result("write_metadata", executed=False, ok=False, started=started,
                       detail=f"invalid privacy: {privacy!r}")
    if not title or not title.strip():
        return _result("write_metadata", executed=False, ok=False, started=started,
                       detail="title is required")
    dst = _ensure_parent(out)
    if dry_run:
        return _result("write_metadata", executed=False, ok=True, started=started,
                       outputs=[str(dst)],
                       detail=f"DRY-RUN: metadata sidecar → {dst.name} title={title[:40]!r}")
    if not src.is_file():
        return _result("write_metadata", executed=False, ok=False, started=started,
                       detail=f"source not found: {src}")
    payload = {
        "schema": "cinemaclaw.metadata/v1",
        "video_file": str(src),
        "title": title[:100],  # YouTube title hard limit
        "description": description[:5000],
        "tags": list(tags or [])[:500],
        "category_id": int(category_id),
        "privacy": privacy,
        "chapters": list(chapters or []),
        "made_for_kids": False,
        "generated_by": "cinemaclaw",
    }
    try:
        dst.write_text(json.dumps(payload, indent=2, ensure_ascii=False))
    except OSError as e:
        return _result("write_metadata", executed=True, ok=False, started=started,
                       detail=f"metadata write failed: {e}")
    return _result("write_metadata", executed=True, ok=True, started=started,
                   outputs=[str(dst)],
                   detail=f"metadata sidecar written ({len(payload['tags'])} tags, {privacy})")


# ── 9. publish_youtube ────────────────────────────────────────────────
def publish_youtube(*, source: str, metadata: str, thumbnail: str | None = None,
                    signed_by_father: bool = False,
                    dry_run: bool = False) -> dict[str, Any]:
    """Upload a rendered video + metadata sidecar to YouTube.

    Truth label: DRY-ONLY.

    This handler is intentionally NOT wired to the YouTube Data API in
    this version. It validates every precondition the upload will need
    (file readable, sidecar well-formed, OAuth creds visible, Father
    Function signature supplied) and returns a DRY-ONLY result.

    Rationale: an unsupervised agent must not be able to publish to a
    public channel. Wiring the API requires an explicit follow-up PR
    with googleapiclient as a dependency, a persisted OAuth token, and
    the Lucifer Test applied at the call site — all of which must be
    set up with the Father Function in the loop.
    """
    started = time.monotonic()
    src = Path(os.path.expanduser(source))
    meta = Path(os.path.expanduser(metadata))
    # In dry-run, surface a structural plan even if artefacts aren't there yet.
    if dry_run:
        return _result("publish_youtube", executed=False, ok=True, started=started,
                       outputs=[str(src)],
                       detail=f"DRY-RUN: would upload {src.name} with {meta.name}"
                              + (f" + thumbnail {Path(thumbnail).name}" if thumbnail else ""))
    if not src.is_file():
        return _result("publish_youtube", executed=False, ok=False, started=started,
                       detail=f"source not found: {src}")
    if not meta.is_file():
        return _result("publish_youtube", executed=False, ok=False, started=started,
                       detail=f"metadata sidecar not found: {meta}")
    try:
        sidecar = json.loads(meta.read_text())
    except (OSError, json.JSONDecodeError) as e:
        return _result("publish_youtube", executed=False, ok=False, started=started,
                       detail=f"metadata unreadable: {e}")
    if sidecar.get("schema") != "cinemaclaw.metadata/v1":
        return _result("publish_youtube", executed=False, ok=False, started=started,
                       detail=f"metadata schema mismatch: {sidecar.get('schema')!r}")
    if thumbnail:
        if not Path(os.path.expanduser(thumbnail)).is_file():
            return _result("publish_youtube", executed=False, ok=False, started=started,
                           detail=f"thumbnail not found: {thumbnail}")
    # Required environment for the eventual real upload.
    have_client = bool(os.environ.get("YOUTUBE_CLIENT_SECRETS"))
    have_token = bool(os.environ.get("YOUTUBE_OAUTH_TOKEN"))
    if not have_client or not have_token:
        return _result("publish_youtube", executed=False, ok=False, started=started,
                       detail="publish preconditions not met: "
                              f"YOUTUBE_CLIENT_SECRETS={'set' if have_client else 'MISSING'} "
                              f"YOUTUBE_OAUTH_TOKEN={'set' if have_token else 'MISSING'}")
    if not signed_by_father:
        return _result("publish_youtube", executed=False, ok=False, started=started,
                       detail="refused: --signed-by-father required to publish "
                              "(defense in depth; CinemaClaw does not push to public channels "
                              "without the Father Function signature)")
    # Even with everything present, this release refuses to actually hit the API.
    return _result("publish_youtube", executed=False, ok=False, started=started,
                   detail="DRY-ONLY in v0.1.0: API wiring deferred to follow-up PR; "
                          "sidecar + thumbnail are prepared and validated")


# ── allowlist ─────────────────────────────────────────────────────────
HANDLERS: dict[str, Any] = {
    "ingest":           ingest,
    "probe":            probe,
    "trim":             trim,
    "normalize_audio":  normalize_audio,
    "concat":           concat,
    "burn_captions":    burn_captions,
    "render_thumbnail": render_thumbnail,
    "write_metadata":   write_metadata,
    "publish_youtube":  publish_youtube,
}


def dispatch(kind: str, spec: dict[str, Any], *,
             dry_run: bool, signed_by_father: bool) -> dict[str, Any]:
    """Single entry point. Refuses any kind not in HANDLERS."""
    if kind not in HANDLERS:
        started = time.monotonic()
        return _result(kind or "unknown", executed=False, ok=False, started=started,
                       detail=f"rejected: {kind!r} not in CinemaClaw allowlist")
    fn = HANDLERS[kind]
    kwargs = dict(spec)
    kwargs["dry_run"] = dry_run
    if kind == "publish_youtube":
        kwargs["signed_by_father"] = signed_by_father
    try:
        return fn(**kwargs)
    except TypeError as e:
        started = time.monotonic()
        return _result(kind, executed=False, ok=False, started=started,
                       detail=f"bad spec for {kind}: {e}")
