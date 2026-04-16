"""youtube_upload — live upload via YouTube Data API v3.

Promoted from the stub. Operator contract:

  1. Create an OAuth2 client in Google Cloud Console (Desktop app type).
     Download client_secret.json. Drop it at:
         /data/youtube/credentials/client_secret.json

  2. Run the token bootstrap ONCE on a machine with a browser:
         python -m scribeclaw.youtube_oauth bootstrap \\
             --client-secret /path/to/client_secret.json \\
             --token /path/to/save/token.json
     Then copy the resulting token.json to:
         /data/youtube/credentials/token.json

  3. After both files exist the handler refreshes the token
     automatically on every call (google-auth handles rotation).

The handler refuses cleanly if either file is missing — never silently
falls back and never uploads as the wrong account.

Inputs (all optional unless noted):
  stem            (str, required): must match a /data/youtube/<stem>/bundle.json
  video_file      (str): path under /data/media/edited/ or /data/media/in/
                         default: <stem><ext> discovered by extension
  privacy_status  (str): "private" (default), "unlisted", or "public"
  category_id     (str): YouTube category id; default "22" (People & Blogs)
  made_for_kids   (bool): default False (operator must opt in)
  title           (str): overrides bundle's first title_candidate
  tags            (list[str]): overrides bundle's tags
  upload_thumbnail (bool): default True if thumbnail.jpg exists
  upload_captions  (bool): default True if transcript.cues.srt or transcript.srt
                           exists; uploads the first match in that order

Output:
  /data/youtube/<stem>/upload.result.json — preserved for provenance.
"""
from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

logger = logging.getLogger("scribeclaw.youtube_upload")

_YT_SCOPES = (
    "https://www.googleapis.com/auth/youtube.upload",
    "https://www.googleapis.com/auth/youtube.force-ssl",
)
_VIDEO_EXTS = (".mp4", ".mov", ".mkv", ".webm", ".m4v")


def _creds_paths(data_root: Path) -> tuple[Path, Path]:
    base = data_root / "youtube" / "credentials"
    return base / "client_secret.json", base / "token.json"


def _require_google_libs() -> dict | None:
    try:
        import googleapiclient  # noqa: F401
        import google.auth  # noqa: F401
    except ImportError as exc:
        return {
            "status": "error", "handler": "youtube_upload",
            "error": "google_libs_not_installed",
            "detail": str(exc),
            "hint": "pip install google-api-python-client google-auth "
                    "google-auth-oauthlib google-auth-httplib2",
        }
    return None


def _load_credentials(token_file: Path, client_secret_file: Path):
    """Load + refresh OAuth2 credentials. Never triggers an interactive
    flow — that's done once via `python -m scribeclaw.youtube_oauth`."""
    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials

    creds = Credentials.from_authorized_user_file(str(token_file), list(_YT_SCOPES))
    if not creds.valid:
        if creds.expired and creds.refresh_token:
            creds.refresh(Request())
            # Persist the refreshed token so the next call skips the refresh.
            token_file.write_text(creds.to_json(), encoding="utf-8")
        else:
            raise RuntimeError(
                "token expired without a refresh_token; re-bootstrap "
                f"with: python -m scribeclaw.youtube_oauth bootstrap "
                f"--client-secret {client_secret_file} --token {token_file}"
            )
    return creds


def _resolve_video_file(data_root: Path, stem: str,
                        payload: dict) -> Path | None:
    if payload.get("video_file"):
        name = Path(payload["video_file"]).name
        for d in ("media/edited", "media/in"):
            p = data_root / d / name
            if p.exists():
                return p
        return None
    for d in ("media/edited", "media/in"):
        for ext in _VIDEO_EXTS:
            p = data_root / d / f"{stem}{ext}"
            if p.exists():
                return p
    # Final sweep: any file in media/edited whose stem starts with the
    # requested one. Covers the `<video>.edited.mp4` naming the media_edit
    # handler emits.
    ed = data_root / "media" / "edited"
    if ed.is_dir():
        for p in sorted(ed.iterdir()):
            if p.suffix.lower() in _VIDEO_EXTS and p.stem.startswith(stem):
                return p
    return None


def _upload_video(youtube, video_path: Path, body: dict) -> dict:
    from googleapiclient.http import MediaFileUpload
    media = MediaFileUpload(
        str(video_path),
        chunksize=8 * 1024 * 1024,
        resumable=True,
        mimetype="video/*",
    )
    req = youtube.videos().insert(
        part="snippet,status", body=body, media_body=media,
    )
    response = None
    last_progress = -1
    while response is None:
        status, response = req.next_chunk()
        if status is not None:
            pct = int(status.progress() * 100)
            if pct != last_progress:
                logger.info(f"youtube_upload: {pct}%")
                last_progress = pct
    return response


def _upload_thumbnail(youtube, video_id: str, thumb_path: Path) -> dict:
    from googleapiclient.http import MediaFileUpload
    media = MediaFileUpload(str(thumb_path), mimetype="image/jpeg")
    return youtube.thumbnails().set(videoId=video_id, media_body=media).execute()


def _upload_caption(youtube, video_id: str, caption_path: Path,
                    language: str = "ro") -> dict:
    from googleapiclient.http import MediaFileUpload
    media = MediaFileUpload(str(caption_path), mimetype="application/octet-stream")
    body = {
        "snippet": {
            "videoId": video_id,
            "language": language,
            "name": "Romanian",
            "isDraft": False,
        }
    }
    return youtube.captions().insert(
        part="snippet", body=body, media_body=media,
    ).execute()


async def youtube_upload(payload: dict[str, Any], data_root: Path) -> dict:
    """Live upload. Delegates OAuth to operator-supplied token; refuses
    cleanly when creds are missing. Preserves upload.result.json for
    provenance. Every branch surfaces the concrete failure reason."""
    miss = _require_google_libs()
    if miss is not None:
        return miss

    stem = Path(str(payload.get("stem") or "")).name
    if not stem:
        return {"status": "error", "handler": "youtube_upload",
                "error": "stem_required"}

    youtube_dir = data_root / "youtube" / stem
    bundle_file = youtube_dir / "bundle.json"
    if not bundle_file.exists():
        return {"status": "error", "handler": "youtube_upload",
                "error": "bundle_not_found", "expected_at": str(bundle_file),
                "hint": "run youtube_metadata first"}

    client_secret_file, token_file = _creds_paths(data_root)
    missing = [str(p) for p in (client_secret_file, token_file) if not p.exists()]
    if missing:
        return {"status": "error", "handler": "youtube_upload",
                "error": "oauth_credentials_missing",
                "missing": missing,
                "hint": "run `python -m scribeclaw.youtube_oauth bootstrap` "
                        "once on a machine with a browser, then copy token.json "
                        "to /data/youtube/credentials/"}

    video_path = _resolve_video_file(data_root, stem, payload)
    if video_path is None:
        return {"status": "error", "handler": "youtube_upload",
                "error": "video_file_not_found",
                "searched": ["media/edited/", "media/in/"],
                "hint": "pass payload.video_file explicitly, or ensure the "
                        "edited video filename starts with the stem"}

    bundle = json.loads(bundle_file.read_text(encoding="utf-8"))
    title = str(payload.get("title") or
                (bundle.get("title_candidates") or [stem])[0])[:100]
    description = bundle.get("description") or ""
    tags = payload.get("tags") if payload.get("tags") is not None \
        else bundle.get("tags") or []
    privacy_status = str(payload.get("privacy_status", "private"))
    if privacy_status not in ("private", "unlisted", "public"):
        return {"status": "error", "handler": "youtube_upload",
                "error": "invalid_privacy_status",
                "got": privacy_status,
                "allowed": ["private", "unlisted", "public"]}
    category_id = str(payload.get("category_id", "22"))
    language = str(payload.get("language") or bundle.get("language") or "ro")

    # ── OAuth + client ─────────────────────────────────────────────────
    try:
        creds = _load_credentials(token_file, client_secret_file)
    except Exception as exc:
        return {"status": "error", "handler": "youtube_upload",
                "error": "oauth_refresh_failed",
                "detail": str(exc)}
    from googleapiclient.discovery import build
    from googleapiclient.errors import HttpError
    youtube = build("youtube", "v3", credentials=creds, cache_discovery=False)

    body = {
        "snippet": {
            "title": title,
            "description": description,
            "tags": tags,
            "categoryId": category_id,
            "defaultLanguage": language,
            "defaultAudioLanguage": language,
        },
        "status": {
            "privacyStatus": privacy_status,
            "selfDeclaredMadeForKids": bool(payload.get("made_for_kids", False)),
            "embeddable": True,
        },
    }

    # ── Video upload (chunked, resumable) ─────────────────────────────
    try:
        video_response = _upload_video(youtube, video_path, body)
    except HttpError as exc:
        return {"status": "error", "handler": "youtube_upload",
                "error": "youtube_api_http",
                "code": exc.resp.status if getattr(exc, "resp", None) else None,
                "detail": str(exc)[-1500:]}
    except Exception as exc:
        return {"status": "error", "handler": "youtube_upload",
                "error": exc.__class__.__name__, "detail": str(exc)}

    video_id = video_response.get("id")
    result: dict[str, Any] = {
        "status": "success",
        "handler": "youtube_upload",
        "stem": stem,
        "video_id": video_id,
        "video_url": f"https://www.youtube.com/watch?v={video_id}" if video_id else None,
        "privacy_status": privacy_status,
        "title": title,
        "video_source": str(video_path),
        "thumbnail_upload": None,
        "caption_upload": None,
    }

    # ── Thumbnail (best-effort) ───────────────────────────────────────
    thumb = youtube_dir / "thumbnail.jpg"
    want_thumb = bool(payload.get("upload_thumbnail", thumb.exists()))
    if want_thumb:
        if not thumb.exists():
            result["thumbnail_upload"] = {"status": "skipped",
                                          "reason": "thumbnail.jpg not found"}
        else:
            try:
                thumb_resp = _upload_thumbnail(youtube, video_id, thumb)
                result["thumbnail_upload"] = {"status": "success",
                                              "response": thumb_resp}
            except HttpError as exc:
                result["thumbnail_upload"] = {"status": "error",
                                              "detail": str(exc)[-500:]}

    # ── Captions (best-effort). Prefer the phrase-cue SRT if present. ──
    want_caps = bool(payload.get("upload_captions", True))
    if want_caps:
        transcripts_dir = data_root / "transcripts" / stem
        caption_candidates = [
            transcripts_dir / "transcript.cues.srt",
            transcripts_dir / "transcript.srt",
        ]
        chosen = next((p for p in caption_candidates if p.exists()), None)
        if chosen is None:
            result["caption_upload"] = {"status": "skipped",
                                        "reason": "no .srt found in transcripts/<stem>/"}
        else:
            try:
                cap_resp = _upload_caption(youtube, video_id, chosen, language=language)
                result["caption_upload"] = {"status": "success",
                                            "source": str(chosen),
                                            "response": cap_resp}
            except HttpError as exc:
                result["caption_upload"] = {"status": "error",
                                            "source": str(chosen),
                                            "detail": str(exc)[-500:]}

    # Provenance record.
    (youtube_dir / "upload.result.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return result
