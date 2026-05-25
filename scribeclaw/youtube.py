"""youtube_metadata + youtube_upload — build and publish a YouTube bundle.

youtube_metadata is deterministic + offline. It generates:
  - title candidates   (trimmed, <= 100 chars, from first-sentence heuristics)
  - description        (header + auto-chapters + full transcript + footer)
  - chapters           (timestamp list from segments)
  - tags               (frequency-based, stop-word filtered, deduped)
  - thumbnail.spec.txt (human-readable; the actual thumbnail is out-of-scope)

youtube_upload posts the rendered video via the YouTube Data API v3.
It requires the operator to supply, under a credentials directory
(default <data_root>/youtube/credentials/, overridable via
YOUTUBE_CREDENTIALS_DIR env):
  - client_secret.json   (Google Cloud Console → OAuth 2.0 Desktop)
  - refresh_token.json   (one-time operator OAuth flow)
If anything is missing, the handler returns a structured 'not_ready'
refusal naming exactly what's missing. It never silently half-uploads.
"""
from __future__ import annotations

import json
import re
from collections import Counter
from pathlib import Path
from typing import Any

from .channels import apply_channel, load_channel, load_series

# Minimal Romanian stop-word set. Kept short and predictable; operators
# override by supplying `extra_stopwords` in the payload.
_STOP_RO = {
    "și", "sau", "dar", "că", "este", "sunt", "era", "fi", "fie",
    "nu", "da", "cu", "de", "la", "în", "pe", "pentru", "din", "pân",
    "până", "cum", "ce", "cine", "care", "acest", "aceasta", "acesta",
    "aceea", "acolo", "aici", "mai", "prea", "foarte", "tot", "toate",
    "un", "o", "unei", "unui", "al", "ale", "ai", "am", "ai", "are",
    "a", "s", "m", "se", "mi", "ți", "i", "îi", "le", "li", "îl",
    "eu", "tu", "el", "ea", "noi", "voi", "ei", "ele",
    "mea", "tău", "său", "mă", "te", "ne", "vă",
    "așa", "atunci", "acum", "după", "înainte", "doar", "numai",
    "the", "and", "to", "of", "a", "in", "is", "it", "that",
}

_WORD = re.compile(r"[A-Za-zĂÂÎȘȚăâîșț]{3,}")
_SENT = re.compile(r"[^.!?]+[.!?]")


def _ts_chapter(seconds: float) -> str:
    s = int(seconds)
    h, s = divmod(s, 3600)
    m, s = divmod(s, 60)
    return f"{h:d}:{m:02d}:{s:02d}" if h else f"{m:d}:{s:02d}"


def _title_candidates(full_text: str, limit: int = 100) -> list[str]:
    sents = [s.strip() for s in _SENT.findall(full_text) if s.strip()]
    out: list[str] = []
    for s in sents[:6]:
        t = s.rstrip(".!?").strip()
        if len(t) > limit:
            t = t[: limit - 1].rsplit(" ", 1)[0] + "…"
        if t and t not in out:
            out.append(t)
        if len(out) >= 3:
            break
    return out or ["Video"]


def _build_chapters(segments: list[dict], min_gap_sec: float) -> list[dict]:
    """Derive chapters by grouping segments into ~min_gap_sec windows.

    YouTube requires: first chapter at 00:00, at least 3 chapters,
    each chapter >= 10 seconds. We enforce the first-at-zero rule
    and leave the 3-chapter floor to the operator (short videos
    simply don't get chapters)."""
    if not segments:
        return []
    chapters: list[dict] = []
    last_ts = -1e9
    for seg in segments:
        start = float(seg["start"])
        if start - last_ts < min_gap_sec and chapters:
            continue
        title = seg["text"].strip().rstrip(".!?")
        if len(title) > 80:
            title = title[:79].rsplit(" ", 1)[0] + "…"
        chapters.append({"start": start, "title": title or "…"})
        last_ts = start
    # First chapter must start at 0.
    if chapters and chapters[0]["start"] > 0:
        chapters.insert(0, {"start": 0.0, "title": "Introducere"})
    return chapters if len(chapters) >= 3 else []


def _build_tags(full_text: str, extra_stop: set[str], top_n: int) -> list[str]:
    words = [w.lower() for w in _WORD.findall(full_text)]
    stop = _STOP_RO | {w.lower() for w in extra_stop}
    counts = Counter(w for w in words if w not in stop)
    return [w for w, _ in counts.most_common(top_n)]


async def youtube_metadata(payload: dict[str, Any], data_root: Path) -> dict:
    """Build YouTube upload bundle from a post-processed transcript.

    Payload:
      stem            (str, required)
      channel_footer  (str, optional): appended to description
      min_chapter_gap (int, default 60): seconds between chapter markers
      extra_stopwords (list[str], optional)
      tag_count       (int, default 20)
    """
    stem = Path(payload["stem"]).name
    d = data_root / "transcripts" / stem
    seg_file = d / "segments.clean.json"
    if not seg_file.exists():
        # Fall back to the un-cleaned output; still works.
        seg_file = d / "segments.json"
    if not seg_file.exists():
        return {"status": "error", "handler": "youtube_metadata",
                "error": "segments_not_found", "expected_at": str(seg_file),
                "hint": "run transcribe_ro (and optionally postprocess_transcript) first"}

    data = json.loads(seg_file.read_text(encoding="utf-8"))
    segments = data.get("segments", [])
    full_text = " ".join(s["text"].strip() for s in segments if s.get("text"))

    titles = _title_candidates(full_text)
    chapters = _build_chapters(
        segments, min_gap_sec=float(payload.get("min_chapter_gap", 60))
    )
    tags = _build_tags(
        full_text,
        extra_stop=set(payload.get("extra_stopwords", [])),
        top_n=int(payload.get("tag_count", 20)),
    )

    # Channel overlay (opt-in via channel_slug). Pure-functional; preserves
    # the deterministic-output contract when channel_slug is absent.
    explicit_footer = payload.get("channel_footer")
    footer: str | None = str(explicit_footer) if explicit_footer else None
    channel_slug = payload.get("channel_slug")
    channel_meta: dict[str, Any] | None = None
    if channel_slug:
        channel_meta = load_channel(str(channel_slug))
        if channel_meta is not None:
            series_key = payload.get("series")
            series_meta = None
            if series_key:
                all_series = load_series(str(channel_slug))
                series_meta = all_series.get(str(series_key))
            titles, tags, footer = apply_channel(
                channel_meta, series_meta, titles, tags,
                explicit_footer=str(explicit_footer) if explicit_footer else None,
            )

    # Description composition — chapters block first (YouTube surfaces them),
    # then transcript, then operator/channel footer.
    lines: list[str] = []
    if chapters:
        lines.append("Capitole:")
        for ch in chapters:
            lines.append(f"{_ts_chapter(ch['start'])} {ch['title']}")
        lines.append("")
    lines.append("Transcript:")
    lines.append(full_text)
    if footer:
        lines.append("")
        lines.append(footer)
    description = "\n".join(lines)

    # YouTube's description cap is 5000 chars. Truncate honestly at a word
    # boundary; surface the fact we truncated in the result payload.
    truncated = False
    if len(description) > 5000:
        description = description[:4997].rsplit(" ", 1)[0] + "…"
        truncated = True

    out_dir = data_root / "youtube" / stem
    out_dir.mkdir(parents=True, exist_ok=True)
    bundle = {
        "title_candidates": titles,
        "description": description,
        "description_truncated": truncated,
        "tags": tags,
        "chapters": [
            {"timestamp": _ts_chapter(c["start"]), "title": c["title"],
             "start_seconds": c["start"]}
            for c in chapters
        ],
        "language": data.get("language", "ro"),
        "source": str(seg_file),
    }
    (out_dir / "bundle.json").write_text(
        json.dumps(bundle, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    (out_dir / "description.txt").write_text(description, encoding="utf-8")
    (out_dir / "tags.txt").write_text(", ".join(tags), encoding="utf-8")
    (out_dir / "thumbnail.spec.txt").write_text(
        "Thumbnail spec (operator-supplied image):\n"
        "  - 1280x720, 16:9, <= 2 MB, JPG/PNG\n"
        "  - Suggested overlay text: " + (titles[0] if titles else "") + "\n",
        encoding="utf-8",
    )

    return {
        "status": "success",
        "handler": "youtube_metadata",
        "stem": stem,
        "output_dir": str(out_dir),
        "title_candidates": titles,
        "chapters": len(chapters),
        "tags": tags[:10],
        "description_truncated": truncated,
    }


async def youtube_upload(payload: dict[str, Any], data_root: Path) -> dict:
    """Upload a rendered video to YouTube using operator-supplied OAuth.

    This handler reads the metadata bundle produced by `youtube_metadata`
    and calls the YouTube Data API v3 `videos.insert` endpoint. It is
    deliberately "dry" — nothing networked happens until the operator
    has dropped three files under `YOUTUBE_CREDENTIALS_DIR`
    (default: `<data_root>/youtube/credentials/`):

      - `client_secret.json`   (Google Cloud Console → OAuth 2.0 Desktop)
      - `refresh_token.json`   (one-time operator OAuth flow)
      - `token.json` is cached automatically after the first call.

    If any prerequisite is missing, the handler returns a structured
    refusal identifying exactly what's missing; it never crashes and
    never silently half-uploads.

    Payload:
      stem             (str, required):   the video stem whose bundle.json
                                          was produced by youtube_metadata
      video_path       (str, optional):   path to the final .mp4 to upload;
                                          defaults to media/edited/<stem>.mp4
      privacy          (str, optional):   "private" (default) | "unlisted" | "public"
      category_id      (int, optional):   YouTube category; default 27 (Education)
      notify_subscribers (bool, optional): default False
      dry_run          (bool, optional):  default False; if True, validate
                                          everything but do not call insert().
      credentials_dir  (str, optional):   override for the credentials path
                                          (otherwise env `YOUTUBE_CREDENTIALS_DIR`
                                          then `<data_root>/youtube/credentials/`)
    """
    stem = Path(payload["stem"]).name if payload.get("stem") else None
    if not stem:
        return {"status": "error", "handler": "youtube_upload",
                "error": "stem_required",
                "hint": "pass payload.stem — the stem used in youtube_metadata"}

    bundle_path = data_root / "youtube" / stem / "bundle.json"
    if not bundle_path.exists():
        return {"status": "error", "handler": "youtube_upload",
                "error": "bundle_not_found", "expected_at": str(bundle_path),
                "hint": "run youtube_metadata first"}
    bundle = json.loads(bundle_path.read_text(encoding="utf-8"))

    video_path_raw = payload.get("video_path")
    if video_path_raw:
        video_path = Path(str(video_path_raw))
    else:
        video_path = data_root / "media" / "edited" / f"{stem}.mp4"
    if not video_path.exists():
        return {"status": "error", "handler": "youtube_upload",
                "error": "video_not_found", "expected_at": str(video_path),
                "hint": "render + concatenate intro/body/outro first, then "
                        "point payload.video_path at the final .mp4"}

    privacy = str(payload.get("privacy", "private"))
    if privacy not in ("private", "unlisted", "public"):
        return {"status": "error", "handler": "youtube_upload",
                "error": "invalid_privacy", "got": privacy,
                "allowed": ["private", "unlisted", "public"]}

    import os
    creds_dir_raw = (
        payload.get("credentials_dir")
        or os.getenv("YOUTUBE_CREDENTIALS_DIR")
        or str(data_root / "youtube" / "credentials")
    )
    creds_dir = Path(str(creds_dir_raw))
    client_secret = creds_dir / "client_secret.json"
    refresh_token_file = creds_dir / "refresh_token.json"
    token_cache = creds_dir / "token.json"

    if not client_secret.exists():
        return {"status": "not_ready", "handler": "youtube_upload",
                "missing": "client_secret.json",
                "expected_at": str(client_secret),
                "hint": "Google Cloud Console → OAuth 2.0 Client ID (Desktop) "
                        "→ download → place here and chmod 600"}

    client_cfg = json.loads(client_secret.read_text(encoding="utf-8"))
    client_block = client_cfg.get("installed") or client_cfg.get("web") or {}
    client_id = client_block.get("client_id")
    client_secret_val = client_block.get("client_secret")
    if not client_id or not client_secret_val:
        return {"status": "not_ready", "handler": "youtube_upload",
                "missing": "client_secret_shape",
                "hint": "client_secret.json must contain an 'installed' or "
                        "'web' block with client_id + client_secret"}

    refresh_token: str | None = None
    if token_cache.exists():
        try:
            cached = json.loads(token_cache.read_text(encoding="utf-8"))
            refresh_token = cached.get("refresh_token")
        except Exception:
            refresh_token = None
    if not refresh_token and refresh_token_file.exists():
        try:
            data = json.loads(refresh_token_file.read_text(encoding="utf-8"))
            refresh_token = data.get("refresh_token") if isinstance(data, dict) else str(data).strip()
        except Exception:
            refresh_token = refresh_token_file.read_text(encoding="utf-8").strip() or None
    if not refresh_token:
        return {"status": "not_ready", "handler": "youtube_upload",
                "missing": "refresh_token",
                "expected_at": str(refresh_token_file),
                "hint": "run a one-time OAuth flow (google-auth-oauthlib "
                        "InstalledAppFlow) against youtube.upload scope, "
                        "save the refresh_token as JSON here"}

    body = {
        "snippet": {
            "title": (bundle.get("title_candidates") or ["Video"])[0][:100],
            "description": bundle.get("description", "")[:5000],
            "tags": bundle.get("tags", [])[:500],
            "categoryId": str(int(payload.get("category_id", 27))),
            "defaultLanguage": bundle.get("language", "ro"),
            "defaultAudioLanguage": bundle.get("language", "ro"),
        },
        "status": {
            "privacyStatus": privacy,
            "selfDeclaredMadeForKids": False,
        },
    }

    if payload.get("dry_run"):
        return {
            "status": "success",
            "handler": "youtube_upload",
            "mode": "dry_run",
            "would_upload": {
                "video_path": str(video_path),
                "privacy": privacy,
                "title": body["snippet"]["title"],
                "tag_count": len(body["snippet"]["tags"]),
                "description_chars": len(body["snippet"]["description"]),
                "category_id": body["snippet"]["categoryId"],
            },
            "credentials_dir": str(creds_dir),
        }

    # Defer the Google imports so the module is importable without them
    # and dry-runs don't require the libraries.
    try:
        from google.auth.transport.requests import Request
        from google.oauth2.credentials import Credentials
        from googleapiclient.discovery import build
        from googleapiclient.http import MediaFileUpload
    except ImportError as exc:
        return {"status": "not_ready", "handler": "youtube_upload",
                "missing": "google_api_libs",
                "error": f"import_error: {exc}",
                "hint": "pip install google-api-python-client "
                        "google-auth google-auth-oauthlib"}

    creds = Credentials(
        token=None,
        refresh_token=refresh_token,
        client_id=client_id,
        client_secret=client_secret_val,
        token_uri="https://oauth2.googleapis.com/token",
        scopes=["https://www.googleapis.com/auth/youtube.upload"],
    )

    try:
        creds.refresh(Request())
    except Exception as exc:
        return {"status": "error", "handler": "youtube_upload",
                "error": "refresh_failed", "detail": str(exc),
                "hint": "refresh_token may be revoked or scope mismatch; "
                        "re-run the OAuth flow with youtube.upload scope"}

    token_cache.parent.mkdir(parents=True, exist_ok=True)
    token_cache.write_text(json.dumps({
        "access_token": creds.token,
        "refresh_token": creds.refresh_token or refresh_token,
        "expires_at": getattr(creds, "expiry", None).isoformat() if getattr(creds, "expiry", None) else None,
    }, default=str), encoding="utf-8")

    try:
        youtube = build("youtube", "v3", credentials=creds, cache_discovery=False)
        media = MediaFileUpload(str(video_path), mimetype="video/mp4",
                                chunksize=-1, resumable=True)
        request = youtube.videos().insert(
            part="snippet,status",
            body=body,
            media_body=media,
            notifySubscribers=bool(payload.get("notify_subscribers", False)),
        )
        response = None
        while response is None:
            _, response = request.next_chunk()
    except Exception as exc:
        return {"status": "error", "handler": "youtube_upload",
                "error": "upload_failed", "detail": str(exc)}

    video_id = (response or {}).get("id")
    return {
        "status": "success",
        "handler": "youtube_upload",
        "video_id": video_id,
        "url": f"https://youtu.be/{video_id}" if video_id else None,
        "privacy": privacy,
        "uploaded": {
            "video_path": str(video_path),
            "title": body["snippet"]["title"],
            "tag_count": len(body["snippet"]["tags"]),
        },
    }
