"""youtube_metadata — package a ready-to-upload bundle for YouTube.

Deterministic, offline. Generates:
  - title candidates   (trimmed, <= 100 chars, from first-sentence heuristics)
  - description        (header + auto-chapters + full transcript + footer)
  - chapters           (timestamp list from segments)
  - tags               (frequency-based, stop-word filtered, deduped)
  - thumbnail.spec.txt (human-readable; the actual thumbnail is out-of-scope)

Does NOT upload. youtube_upload is a stub; uploading requires the operator
to supply an OAuth2 client_secret.json and an authorized refresh token.
This scaffold refuses to upload rather than silently fail or demand creds.
"""
from __future__ import annotations

import json
import re
from collections import Counter
from pathlib import Path
from typing import Any

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

    # Description composition — chapters block first (YouTube surfaces them),
    # then transcript, then operator footer.
    lines: list[str] = []
    if chapters:
        lines.append("Capitole:")
        for ch in chapters:
            lines.append(f"{_ts_chapter(ch['start'])} {ch['title']}")
        lines.append("")
    lines.append("Transcript:")
    lines.append(full_text)
    if payload.get("channel_footer"):
        lines.append("")
        lines.append(str(payload["channel_footer"]))
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


# youtube_upload lives in .youtube_upload now (real OAuth-backed uploader).
# Re-export for backwards compatibility with existing main.py imports.
from .youtube_upload import youtube_upload  # noqa: F401,E402
