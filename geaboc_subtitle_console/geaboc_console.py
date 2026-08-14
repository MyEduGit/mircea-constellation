#!/usr/bin/env python3
"""Geaboc Subtitle Console — AssemblyAI transcription + subtitles, on a Mac.

Standalone companion to `scribeclaw/assemblyai.py`. Same output shape, so
anything downstream (postprocess_transcript, youtube_metadata) stays
drop-in compatible — but with three differences that matter to a human
operator sitting at an iMac:

  1. **Standard library only.** No httpx, no Docker, no FastAPI, no
     /opt/scribeclaw-data. macOS ships everything this needs.
  2. **Dialogs, not curl.** Episode code, audio file and API key are asked
     for through native macOS dialogs (osascript).
  3. **Desktop output.** Results land in ~/Desktop/Geaboc Subtitles/<CODE>/
     so the folder can be found and uploaded without using a terminal.

AssemblyAI is the only transcription backend. MacWhisper output is not
accepted, by design — the approved C0086 workflow is AssemblyAI-only, and
silently falling back to another engine would break that contract.

The API key is read from (in order): the ASSEMBLYAI_API_KEY environment
variable, then the login Keychain. It is never written to the transcript
folder, never printed, and never echoed on screen.

Usage (GUI — this is what the .command launcher runs):
    python3 geaboc_console.py

Usage (headless, for scripting):
    python3 geaboc_console.py transcribe --code C0086 --audio "C0086.mp3"
    python3 geaboc_console.py announce  --code C0086 --url "https://youtu.be/..."
    python3 geaboc_console.py --self-test      # no network, no API credits
"""
from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any, Iterable

__version__ = "1.0.0"

API_BASE = "https://api.assemblyai.com/v2"
KEYCHAIN_SERVICE = "AssemblyAI API Key"
DEFAULT_LANGUAGE = "ro"
POLL_SEC = 5.0
# A Geaboc sermon runs 60-90 minutes. AssemblyAI transcribes at roughly
# 20-40x realtime, but queueing is not guaranteed — 90 minutes of polling
# is generous enough that we never abandon a job that is still coming.
POLL_TIMEOUT_SEC = 90 * 60
UPLOAD_CHUNK = 5 * 1024 * 1024

# YouTube caption convention: at most two lines, 42 characters each.
CAPTION_MAX_CHARS = 42
CAPTION_MAX_LINES = 2

AUDIO_SUFFIXES = {".mp3", ".m4a", ".wav", ".aiff", ".aif", ".flac",
                  ".mp4", ".mov", ".m4v", ".caf", ".aac"}


# ─────────────────────────────────────────────────────────────────────────
# Pure helpers — no network, no macOS. Everything here is unit-tested.
# ─────────────────────────────────────────────────────────────────────────

_CODE_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,63}$")


def validate_code(raw: str) -> str:
    """Normalize an episode code (C0086) into a safe single folder name.

    Rejects anything that could escape the output directory or collide with
    shell/Finder conventions. The operator types this by hand under time
    pressure, so the failure has to be loud rather than creative.
    """
    code = (raw or "").strip()
    if not code:
        raise ValueError("Episode code is empty. Example: C0086")
    if code != Path(code).name or code in {".", ".."}:
        raise ValueError(f"Episode code must not contain a path: {raw!r}")
    if not _CODE_RE.match(code):
        raise ValueError(
            f"Episode code {raw!r} is not usable as a folder name.\n"
            "Use letters, digits, dot, dash or underscore. Example: C0086"
        )
    return code


def fmt_timestamp(sec: float, sep: str) -> str:
    """Seconds → HH:MM:SS<sep>mmm. `sep` is ',' for SRT and '.' for VTT."""
    ms = int(round(max(0.0, sec) * 1000))
    h, ms = divmod(ms, 3_600_000)
    m, ms = divmod(ms, 60_000)
    s, ms = divmod(ms, 1000)
    return f"{h:02d}:{m:02d}:{s:02d}{sep}{ms:03d}"


def fmt_duration(sec: float) -> str:
    """Seconds → H:MM:SS, for human-facing summaries."""
    total = int(round(max(0.0, sec)))
    h, rem = divmod(total, 3600)
    m, s = divmod(rem, 60)
    return f"{h}:{m:02d}:{s:02d}"


# Legacy Romanian cedilla → correct comma-below forms. Identical mapping to
# scribeclaw/postprocess.py; ASR engines still emit the Turkish cedilla.
_CEDILLA_MAP = str.maketrans({
    "ş": "ș",  # ş → ș
    "Ş": "Ș",  # Ş → Ș
    "ţ": "ț",  # ţ → ț
    "Ţ": "Ț",  # Ţ → Ț
})

_SENTENCE_SPLIT = re.compile(r"(?<=[.!?])\s+(?=[A-ZĂÂÎȘȚ])")
_MULTISPACE = re.compile(r"[ \t]+")
_SPACE_BEFORE_PUNCT = re.compile(r"\s+([,.;:!?])")


def fix_romanian(text: str) -> str:
    """Deterministic Romanian orthography cleanup. No LLM, no guessing.

    Missing diacritics are NOT invented — that needs a language model and a
    human reviewer, and quietly guessing would corrupt a sermon transcript.
    """
    s = text.translate(_CEDILLA_MAP)
    s = _MULTISPACE.sub(" ", s)
    s = _SPACE_BEFORE_PUNCT.sub(r"\1", s)
    return s.strip()


def reflow_paragraphs(segments: list[dict]) -> list[str]:
    """Join segments, then split on sentence boundaries for a readable .txt."""
    full = fix_romanian(" ".join(s.get("text", "") for s in segments
                                 if s.get("text")))
    return [p.strip() for p in _SENTENCE_SPLIT.split(full) if p.strip()]


def normalize_segments(sentences_payload: dict,
                       fallback_text: str = "") -> list[dict]:
    """AssemblyAI sentences (milliseconds) → our segment shape (seconds)."""
    out: list[dict] = []
    for i, s in enumerate(sentences_payload.get("sentences") or []):
        text = (s.get("text") or "").strip()
        if not text:
            continue
        out.append({
            "id": len(out),
            "start": float(s.get("start", 0)) / 1000.0,
            "end": float(s.get("end", 0)) / 1000.0,
            "text": text,
            "words": None,
        })
    if not out and fallback_text.strip():
        # Some transcripts come back without sentence segmentation.
        out.append({"id": 0, "start": 0.0, "end": 0.0,
                    "text": fallback_text.strip(), "words": None})
    return out


def wrap_caption(text: str, max_chars: int = CAPTION_MAX_CHARS,
                 max_lines: int = CAPTION_MAX_LINES) -> list[str]:
    """Greedy word wrap into at most `max_lines` lines of `max_chars`.

    Returns every line produced — the caller decides how to split overflow
    across cues. A single word longer than max_chars is left intact rather
    than hyphenated mid-word.
    """
    words = text.split()
    if not words:
        return []
    lines: list[str] = []
    current = ""
    for word in words:
        candidate = f"{current} {word}".strip()
        if current and len(candidate) > max_chars:
            lines.append(current)
            current = word
        else:
            current = candidate
    if current:
        lines.append(current)
    return lines


def split_into_cues(segments: list[dict], max_chars: int = CAPTION_MAX_CHARS,
                    max_lines: int = CAPTION_MAX_LINES) -> list[dict]:
    """Break long segments into readable subtitle cues.

    AssemblyAI returns one sentence per segment, and a preacher's sentence
    can run 30 seconds. Dropping that on screen as a wall of text is
    unreadable, so each sentence is wrapped and then chunked into cues of
    at most `max_lines` lines. Cue timings are apportioned by character
    count within the parent sentence, which tracks speech rate closely
    enough for subtitles and never drifts outside the sentence's own span.
    """
    cues: list[dict] = []
    for seg in segments:
        text = (seg.get("text") or "").strip()
        if not text:
            continue
        start = float(seg.get("start", 0.0))
        end = float(seg.get("end", 0.0))
        lines = wrap_caption(text, max_chars, max_lines)
        if not lines:
            continue

        groups = [lines[i:i + max_lines] for i in range(0, len(lines), max_lines)]
        total_chars = sum(len(" ".join(g)) for g in groups) or 1
        span = max(0.0, end - start)
        cursor = start
        for gi, group in enumerate(groups):
            share = len(" ".join(group)) / total_chars
            # Last cue absorbs rounding so the final end matches the segment.
            cue_end = end if gi == len(groups) - 1 else cursor + span * share
            cues.append({
                "id": len(cues),
                "start": cursor,
                "end": max(cue_end, cursor),
                "text": "\n".join(group),
            })
            cursor = cue_end
    return cues


def render_srt(cues: Iterable[dict]) -> str:
    lines: list[str] = []
    for i, cue in enumerate(cues, start=1):
        lines.append(str(i))
        lines.append(f"{fmt_timestamp(cue['start'], ',')} --> "
                     f"{fmt_timestamp(cue['end'], ',')}")
        lines.append(cue["text"].strip())
        lines.append("")
    return "\n".join(lines)


def render_vtt(cues: Iterable[dict]) -> str:
    lines = ["WEBVTT", ""]
    for cue in cues:
        lines.append(f"{fmt_timestamp(cue['start'], '.')} --> "
                     f"{fmt_timestamp(cue['end'], '.')}")
        lines.append(cue["text"].strip())
        lines.append("")
    return "\n".join(lines)


# ── YouTube link hygiene ────────────────────────────────────────────────
# Three defects were reported against the previous announcements: the link
# did not work, the video did not start at the beginning, and the text
# pasted into WhatsApp unformatted. The first two are the same bug — a URL
# carrying `t=` (start offset) and `si=` (share tracking) copied straight
# out of the YouTube share sheet. normalize_youtube_url strips both.

_YT_ID_RE = re.compile(r"^[A-Za-z0-9_-]{11}$")


def extract_youtube_id(url: str) -> str | None:
    """Pull the 11-character video id out of any common YouTube URL form."""
    raw = (url or "").strip()
    if not raw:
        return None
    if _YT_ID_RE.match(raw):
        return raw  # already a bare id
    if "://" not in raw:
        raw = "https://" + raw

    try:
        parts = urllib.parse.urlsplit(raw)
    except ValueError:
        return None

    # No str.removeprefix — it needs Python 3.9, and this has to run on
    # whatever Python the operator's Mac happens to ship.
    host = (parts.hostname or "").lower()
    if host.startswith("www."):
        host = host[4:]
    path = parts.path or ""

    if host in {"youtu.be"}:
        candidate = path.lstrip("/").split("/")[0]
    elif host.endswith("youtube.com") or host.endswith("youtube-nocookie.com"):
        query = urllib.parse.parse_qs(parts.query)
        if "v" in query and query["v"]:
            candidate = query["v"][0]
        else:
            segments = [p for p in path.split("/") if p]
            # /live/<id>, /shorts/<id>, /embed/<id>, /v/<id>
            if len(segments) >= 2 and segments[0] in {"live", "shorts",
                                                      "embed", "v"}:
                candidate = segments[1]
            else:
                return None
    else:
        return None

    candidate = candidate.strip()
    return candidate if _YT_ID_RE.match(candidate) else None


def normalize_youtube_url(url: str) -> str:
    """Any YouTube URL → clean https://youtu.be/<id>.

    Drops `t`/`start` (so the video starts at the beginning), `si` (share
    tracking), `list`/`index` (so it does not open inside a playlist) and
    every other parameter. Raises ValueError if no video id is present,
    rather than handing back a link that will not work.
    """
    video_id = extract_youtube_id(url)
    if not video_id:
        raise ValueError(
            f"Could not find a YouTube video id in: {url!r}\n"
            "Paste the full link from the browser address bar, e.g.\n"
            "https://www.youtube.com/watch?v=ZKbWtcBfjQU"
        )
    return f"https://youtu.be/{video_id}"


def build_whatsapp_announcement(title: str, url: str, host: str,
                                summary: str = "",
                                duration_sec: float = 0.0) -> str:
    """Compose a WhatsApp channel post that survives copy-paste.

    WhatsApp has no Markdown. Pasting `# Heading` or `**bold**` leaves the
    punctuation visible on screen — that is the "still pastes unformatted"
    complaint. WhatsApp's own markup is *bold*, _italic_, ~strike~, and
    line breaks are literal newlines. Nothing else survives, so nothing
    else is emitted: no headings, no bullet characters that render as
    asterisks, no tables, no links wrapped in angle brackets.
    """
    clean_url = normalize_youtube_url(url)
    lines: list[str] = [f"*{title.strip()}*"]
    if host.strip():
        lines.append(f"_{host.strip()}_")
    lines.append("")
    if summary.strip():
        lines.append(summary.strip())
        lines.append("")
    if duration_sec > 0:
        lines.append(f"Durata: {fmt_duration(duration_sec)}")
        lines.append("")
    lines.append("Priviți aici:")
    # Bare URL on its own line — WhatsApp only auto-links when the URL is
    # not glued to surrounding punctuation.
    lines.append(clean_url)
    return "\n".join(lines).rstrip() + "\n"


def build_youtube_metadata(code: str, segments: list[dict],
                           duration_sec: float, host: str) -> str:
    """Operator-facing metadata worksheet.

    Deliberately does NOT invent a title or a description. Those are
    editorial claims about what a preacher said, and a transcription tool
    is not entitled to make them. What it can do honestly is hand over the
    derivable facts — runtime, chapter marks, the opening lines — with the
    editorial fields left blank for the operator.
    """
    chapters = suggest_chapters(segments)
    out = [
        f"# YouTube metadata — {code}",
        "",
        "## Title (fill in — max 100 characters)",
        "",
        "",
        "## Description",
        "",
        "",
        f"Durata: {fmt_duration(duration_sec)}",
        "",
        "## Chapters (paste into the description; 00:00 is required first)",
        "",
    ]
    out.extend(chapters)
    out.extend([
        "",
        "## Opening lines (for reference when writing the title)",
        "",
    ])
    for seg in segments[:5]:
        out.append(f"  [{fmt_duration(seg['start'])}] {seg['text']}")
    out.extend([
        "",
        "## Tags",
        "",
        f"{host}, predica, crestin, adventist",
        "",
        "## Subtitles",
        "",
        f"Upload {code}.srt in YouTube Studio → Subtitles → Romanian.",
        "",
    ])
    return "\n".join(out) + "\n"


def suggest_chapters(segments: list[dict], every_sec: float = 300.0) -> list[str]:
    """Timestamp marks every ~5 minutes, snapped to a sentence start.

    These are position markers, not topic labels — the label is left for
    the operator, because naming a section is an editorial act.
    """
    if not segments:
        return ["00:00 Început"]
    marks = ["00:00 Început"]
    next_at = every_sec
    for seg in segments:
        if seg["start"] >= next_at:
            preview = seg["text"][:48].strip()
            marks.append(f"{fmt_duration(seg['start'])} {preview}")
            next_at += every_sec
    return marks


# ─────────────────────────────────────────────────────────────────────────
# Output writing
# ─────────────────────────────────────────────────────────────────────────

def write_outputs(out_dir: Path, code: str, raw: dict, segments: list[dict],
                  audio_path: Path | None = None, host: str = "Dr. Emanoil Geaboc"
                  ) -> dict:
    """Write the full deliverable folder. Returns a summary dict."""
    out_dir.mkdir(parents=True, exist_ok=True)
    duration = float(raw.get("audio_duration") or 0.0)

    # 1. Provenance — the raw API response, untouched.
    (out_dir / "assemblyai.raw.json").write_text(
        json.dumps(raw, ensure_ascii=False, indent=2), encoding="utf-8")

    # 2. scribeclaw-compatible segment file.
    (out_dir / "segments.json").write_text(json.dumps({
        "language": raw.get("language_code", DEFAULT_LANGUAGE),
        "language_probability": 1.0,
        "duration": duration,
        "model": f"assemblyai:{raw.get('speech_model') or 'default'}",
        "segments": segments,
        "source": "assemblyai",
        "assemblyai_id": raw.get("id"),
    }, ensure_ascii=False, indent=2), encoding="utf-8")

    # 3. Verbatim transcript, one sentence per cue.
    (out_dir / "transcript.srt").write_text(render_srt(segments), encoding="utf-8")
    (out_dir / "transcript.vtt").write_text(render_vtt(segments), encoding="utf-8")
    (out_dir / "transcript.txt").write_text(
        "\n\n".join(s["text"] for s in segments if s["text"]), encoding="utf-8")

    # 4. Romanian-corrected transcript.
    clean_segments = [{**s, "text": fix_romanian(s["text"])} for s in segments]
    (out_dir / "segments.clean.json").write_text(json.dumps({
        "language": raw.get("language_code", DEFAULT_LANGUAGE),
        "duration": duration,
        "segments": clean_segments,
        "source": "assemblyai",
        "assemblyai_id": raw.get("id"),
    }, ensure_ascii=False, indent=2), encoding="utf-8")
    (out_dir / "transcript.clean.txt").write_text(
        "\n\n".join(reflow_paragraphs(segments)), encoding="utf-8")

    # 5. The upload-ready subtitle file — wrapped for YouTube.
    cues = split_into_cues(clean_segments)
    (out_dir / f"{code}.srt").write_text(render_srt(cues), encoding="utf-8")
    (out_dir / f"{code}.vtt").write_text(render_vtt(cues), encoding="utf-8")

    # 6. Operator worksheet.
    (out_dir / "youtube_metadata.txt").write_text(
        build_youtube_metadata(code, clean_segments, duration, host),
        encoding="utf-8")

    # 7. Run record.
    summary = {
        "code": code,
        "console_version": __version__,
        "assemblyai_id": raw.get("id"),
        "language": raw.get("language_code", DEFAULT_LANGUAGE),
        "duration_sec": duration,
        "duration_human": fmt_duration(duration),
        "segments": len(segments),
        "subtitle_cues": len(cues),
        "source_audio": audio_path.name if audio_path else None,
        "transcribed_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "engine": "assemblyai",
    }
    (out_dir / "RUN.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    return summary


# ─────────────────────────────────────────────────────────────────────────
# macOS integration — Keychain and dialogs
# ─────────────────────────────────────────────────────────────────────────

def is_macos() -> bool:
    return sys.platform == "darwin"


def keychain_get(service: str = KEYCHAIN_SERVICE) -> str | None:
    """Read the API key from the login Keychain. None if absent."""
    if not is_macos():
        return None
    try:
        result = subprocess.run(
            ["security", "find-generic-password", "-s", service,
             "-a", os.environ.get("USER", ""), "-w"],
            capture_output=True, text=True, timeout=30)
    except (OSError, subprocess.SubprocessError):
        return None
    if result.returncode != 0:
        return None
    key = result.stdout.strip()
    return key or None


def keychain_set(key: str, service: str = KEYCHAIN_SERVICE) -> bool:
    """Store the API key in the login Keychain, replacing any existing one."""
    if not is_macos():
        return False
    try:
        result = subprocess.run(
            ["security", "add-generic-password", "-U", "-s", service,
             "-a", os.environ.get("USER", ""), "-w", key],
            capture_output=True, text=True, timeout=30)
    except (OSError, subprocess.SubprocessError):
        return False
    return result.returncode == 0


def _as_literal(text: str) -> str:
    """Escape a Python string for embedding in an AppleScript string."""
    return text.replace("\\", "\\\\").replace('"', '\\"')


def _osascript(script: str, timeout: float = 600.0) -> tuple[int, str]:
    try:
        result = subprocess.run(["osascript", "-e", script],
                                capture_output=True, text=True, timeout=timeout)
    except (OSError, subprocess.SubprocessError) as exc:
        return 1, str(exc)
    return result.returncode, (result.stdout or result.stderr).strip()


class Cancelled(Exception):
    """The operator dismissed a dialog. Not an error — just stop."""


def ask_text(prompt: str, default: str = "", hidden: bool = False,
             title: str = "Geaboc Subtitle Console") -> str:
    """Native text prompt. Raises Cancelled if the operator hits Cancel."""
    hidden_clause = " with hidden answer" if hidden else ""
    script = (
        'tell application "System Events"\n'
        '  activate\n'
        f'  set r to display dialog "{_as_literal(prompt)}" '
        f'default answer "{_as_literal(default)}"{hidden_clause} '
        f'with title "{_as_literal(title)}"\n'
        '  return text returned of r\n'
        'end tell'
    )
    rc, out = _osascript(script)
    if rc != 0:
        raise Cancelled(out)
    return out


def ask_choice(prompt: str, options: list[str],
               title: str = "Geaboc Subtitle Console") -> str:
    """Native list picker. Raises Cancelled if dismissed."""
    items = ", ".join(f'"{_as_literal(o)}"' for o in options)
    script = (
        'tell application "System Events"\n'
        '  activate\n'
        f'  set r to choose from list {{{items}}} '
        f'with prompt "{_as_literal(prompt)}" with title "{_as_literal(title)}"\n'
        '  if r is false then return "__CANCELLED__"\n'
        '  return item 1 of r\n'
        'end tell'
    )
    rc, out = _osascript(script)
    if rc != 0 or out == "__CANCELLED__":
        raise Cancelled(out)
    return out


def ask_file(prompt: str) -> Path:
    """Native file picker, filtered to audio/video. Raises Cancelled."""
    typed = (
        'tell application "System Events"\n'
        '  activate\n'
        f'  set f to choose file with prompt "{_as_literal(prompt)}" '
        'of type {"public.audio", "public.movie", "public.mpeg-4-audio"}\n'
        '  return POSIX path of f\n'
        'end tell'
    )
    rc, out = _osascript(typed)
    if rc != 0 and "User cancelled" not in out and "-128" not in out:
        # Some macOS versions reject the UTI list; retry unfiltered rather
        # than blocking the operator over a cosmetic filter.
        untyped = (
            'tell application "System Events"\n'
            '  activate\n'
            f'  set f to choose file with prompt "{_as_literal(prompt)}"\n'
            '  return POSIX path of f\n'
            'end tell'
        )
        rc, out = _osascript(untyped)
    if rc != 0:
        raise Cancelled(out)
    return Path(out)


def say(message: str, title: str = "Geaboc Subtitle Console",
        buttons: str = "OK") -> None:
    script = (
        'tell application "System Events"\n'
        '  activate\n'
        f'  display dialog "{_as_literal(message)}" '
        f'with title "{_as_literal(title)}" buttons {{"{buttons}"}} '
        f'default button "{buttons}"\n'
        'end tell'
    )
    _osascript(script)


def reveal(path: Path) -> None:
    if is_macos():
        subprocess.run(["open", "-R", str(path)], capture_output=True)


def log(message: str) -> None:
    """Terminal progress. The .command window is visible while this runs."""
    print(message, flush=True)


# ─────────────────────────────────────────────────────────────────────────
# AssemblyAI client — urllib only
# ─────────────────────────────────────────────────────────────────────────

class AssemblyAIError(RuntimeError):
    """An API call failed. Message is safe to show the operator."""


class _ProgressReader:
    """File wrapper that reports upload progress to the terminal."""

    def __init__(self, fh, total: int):
        self._fh = fh
        self._total = total
        self._sent = 0
        self._last_pct = -1

    def read(self, size: int = -1) -> bytes:
        chunk = self._fh.read(size)
        self._sent += len(chunk)
        if self._total > 0:
            pct = int(self._sent * 100 / self._total)
            if pct != self._last_pct and pct % 5 == 0:
                self._last_pct = pct
                mb = self._sent / (1024 * 1024)
                log(f"    uploading… {pct:3d}%  ({mb:.1f} MB)")
        return chunk


def _request(url: str, api_key: str, method: str = "GET",
             body: dict | None = None, timeout: float = 120.0) -> dict:
    data = json.dumps(body).encode("utf-8") if body is not None else None
    req = urllib.request.Request(url, data=data, method=method)
    req.add_header("authorization", api_key)
    if data is not None:
        req.add_header("content-type", "application/json")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", "replace")[:500]
        if exc.code in (401, 403):
            raise AssemblyAIError(
                "AssemblyAI rejected the API key (HTTP "
                f"{exc.code}).\n\nCheck the key at assemblyai.com, then run "
                "the console again and choose “Change AssemblyAI key”."
            ) from exc
        raise AssemblyAIError(
            f"AssemblyAI returned HTTP {exc.code}.\n\n{detail}") from exc
    except urllib.error.URLError as exc:
        raise AssemblyAIError(
            f"Could not reach AssemblyAI: {exc.reason}\n\n"
            "Check the internet connection and try again.") from exc


def upload_audio(path: Path, api_key: str) -> str:
    """Stream the file to /upload. Returns the temporary upload URL."""
    size = path.stat().st_size
    log(f"[1/4] Uploading {path.name} ({size / (1024 * 1024):.1f} MB)…")
    with path.open("rb") as fh:
        req = urllib.request.Request(
            f"{API_BASE}/upload", data=_ProgressReader(fh, size), method="POST")
        req.add_header("authorization", api_key)
        req.add_header("content-type", "application/octet-stream")
        # Explicit length keeps urllib from switching to chunked encoding.
        req.add_header("content-length", str(size))
        try:
            with urllib.request.urlopen(req, timeout=3600) as resp:
                payload = json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", "replace")[:500]
            if exc.code in (401, 403):
                raise AssemblyAIError(
                    "AssemblyAI rejected the API key while uploading "
                    f"(HTTP {exc.code}).") from exc
            raise AssemblyAIError(
                f"Upload failed — HTTP {exc.code}.\n\n{detail}") from exc
        except urllib.error.URLError as exc:
            raise AssemblyAIError(
                f"Upload failed: {exc.reason}\n\n"
                "Check the internet connection and try again.") from exc
    url = payload.get("upload_url")
    if not url:
        raise AssemblyAIError("AssemblyAI did not return an upload URL.")
    log("      upload complete.")
    return url


def start_job(upload_url: str, api_key: str,
              language: str = DEFAULT_LANGUAGE) -> str:
    log(f"[2/4] Starting transcription (language={language})…")
    payload = _request(f"{API_BASE}/transcript", api_key, method="POST", body={
        "audio_url": upload_url,
        "language_code": language,
        "punctuate": True,
        "format_text": True,
    })
    job_id = payload.get("id")
    if not job_id:
        raise AssemblyAIError("AssemblyAI did not return a transcript id.")
    log(f"      job id: {job_id}")
    return job_id


def poll_job(job_id: str, api_key: str, poll_sec: float = POLL_SEC,
             timeout_sec: float = POLL_TIMEOUT_SEC) -> dict:
    log("[3/4] Transcribing — this takes a few minutes for a full sermon.")
    waited = 0.0
    while True:
        data = _request(f"{API_BASE}/transcript/{job_id}", api_key)
        status = data.get("status")
        if status == "completed":
            log("      transcription complete.")
            return data
        if status == "error":
            raise AssemblyAIError(
                f"AssemblyAI could not transcribe this file:\n\n"
                f"{data.get('error')}")
        if waited >= timeout_sec:
            raise AssemblyAIError(
                f"Gave up waiting after {int(waited / 60)} minutes "
                f"(last status: {status}).\n\nThe job may still finish. "
                f"Transcript id: {job_id}")
        if waited and waited % 30 == 0:
            log(f"      still working… {int(waited / 60)}m elapsed "
                f"(status: {status})")
        time.sleep(poll_sec)
        waited += poll_sec


def fetch_sentences(job_id: str, api_key: str) -> dict:
    """Sentence-level segmentation — better cue boundaries than raw words."""
    try:
        return _request(f"{API_BASE}/transcript/{job_id}/sentences", api_key)
    except AssemblyAIError:
        # Not fatal: we fall back to the single-blob transcript text.
        return {"sentences": []}


# ─────────────────────────────────────────────────────────────────────────
# Key resolution
# ─────────────────────────────────────────────────────────────────────────

def resolve_api_key(interactive: bool = True) -> str:
    """Environment → Keychain → ask. Offers to save what it was given."""
    env_key = os.environ.get("ASSEMBLYAI_API_KEY", "").strip()
    if env_key:
        return env_key

    stored = keychain_get()
    if stored:
        return stored

    if not interactive:
        raise AssemblyAIError(
            "No AssemblyAI API key found.\n\n"
            "Set ASSEMBLYAI_API_KEY, or run the console once in GUI mode to "
            "store the key in your Keychain.")

    key = ask_text(
        "Enter your AssemblyAI API key.\n\n"
        "Find it at assemblyai.com → Dashboard → API Keys.\n"
        "It is stored in your Mac's Keychain — never in a chat window.",
        hidden=True).strip()
    if not key:
        raise Cancelled("no key entered")

    if keychain_set(key):
        log("      API key saved to Keychain.")
    else:
        log("      WARNING: could not save to Keychain — key used for this run only.")
    return key


# ─────────────────────────────────────────────────────────────────────────
# Flows
# ─────────────────────────────────────────────────────────────────────────

def output_root() -> Path:
    return Path.home() / "Desktop" / "Geaboc Subtitles"


def transcribe(code: str, audio: Path, api_key: str,
               language: str = DEFAULT_LANGUAGE,
               out_root: Path | None = None) -> dict:
    """Full transcription run. Returns the summary written to RUN.json."""
    if not audio.exists():
        raise AssemblyAIError(f"Audio file not found:\n{audio}")
    if audio.suffix.lower() not in AUDIO_SUFFIXES:
        log(f"      note: {audio.suffix} is unusual — sending it anyway.")

    upload_url = upload_audio(audio, api_key)
    job_id = start_job(upload_url, api_key, language)
    raw = poll_job(job_id, api_key)
    sentences = fetch_sentences(job_id, api_key)

    segments = normalize_segments(sentences, raw.get("text") or "")
    if not segments:
        raise AssemblyAIError(
            "AssemblyAI returned an empty transcript.\n\n"
            "Check that the audio actually contains speech.")

    out_dir = (out_root or output_root()) / code
    log(f"[4/4] Writing {out_dir}…")
    summary = write_outputs(out_dir, code, raw, segments, audio)
    summary["output_dir"] = str(out_dir)
    return summary


def flow_transcribe() -> None:
    code = validate_code(ask_text(
        "Episode code?\n\nExample: C0086", default="C0086"))
    audio = ask_file(f"Choose the final audio file for {code}")
    api_key = resolve_api_key()

    log("")
    log(f"── {code} ─────────────────────────────────────")
    summary = transcribe(code, audio, api_key)
    out_dir = Path(summary["output_dir"])

    log("")
    log(f"Done. {summary['segments']} sentences, "
        f"{summary['duration_human']} of audio.")
    log(f"Folder: {out_dir}")

    say(f"{code} is ready.\n\n"
        f"Duration: {summary['duration_human']}\n"
        f"Sentences: {summary['segments']}\n"
        f"Subtitle cues: {summary['subtitle_cues']}\n\n"
        f"Everything is in:\n{out_dir}\n\n"
        f"Upload {code}.srt to YouTube Studio, and send the whole "
        f"{code} folder for correction.")
    reveal(out_dir)


def flow_announce() -> None:
    """Produce a WhatsApp post that pastes correctly and links correctly."""
    code = validate_code(ask_text("Episode code?", default="C0086"))
    title = ask_text("Video title, as it appears on YouTube:").strip()
    url = ask_text(
        "Paste the YouTube link.\n\n"
        "Any form works — the console strips the start-time and tracking "
        "parameters so the video opens at the beginning.").strip()

    clean = normalize_youtube_url(url)
    duration = 0.0
    run_file = output_root() / code / "RUN.json"
    if run_file.exists():
        try:
            duration = float(json.loads(
                run_file.read_text(encoding="utf-8")).get("duration_sec", 0.0))
        except (ValueError, OSError):
            duration = 0.0

    text = build_whatsapp_announcement(
        title or code, clean, "Dr. Emanoil Geaboc", duration_sec=duration)

    out_dir = output_root() / code
    out_dir.mkdir(parents=True, exist_ok=True)
    target = out_dir / "whatsapp_announcement.txt"
    target.write_text(text, encoding="utf-8")

    # Put it on the clipboard so the operator can paste straight into
    # WhatsApp without opening the file.
    if is_macos():
        try:
            subprocess.run(["pbcopy"], input=text, text=True, timeout=30)
        except (OSError, subprocess.SubprocessError):
            pass

    log(text)
    say("WhatsApp announcement copied to the clipboard.\n\n"
        f"Link: {clean}\n\n"
        "Paste it straight into the WhatsApp channel — the formatting and "
        "line breaks are already correct.\n\n"
        f"Also saved to:\n{target}")
    reveal(target)


def flow_change_key() -> None:
    key = ask_text(
        "Enter the AssemblyAI API key to store in your Keychain.\n\n"
        "This replaces any key saved earlier.", hidden=True).strip()
    if not key:
        raise Cancelled("no key entered")
    if keychain_set(key):
        say("API key saved to your Keychain.")
    else:
        say("Could not save the key to the Keychain.\n\n"
            "Open Keychain Access and check for a locked login keychain.")


MENU = {
    "Transcribe with AssemblyAI": flow_transcribe,
    "Make WhatsApp announcement": flow_announce,
    "Change AssemblyAI key": flow_change_key,
}


def gui_main() -> int:
    if not is_macos():
        print("The GUI console runs on macOS. On other systems use:\n"
              "  python3 geaboc_console.py transcribe --code C0086 "
              "--audio FILE", file=sys.stderr)
        return 2

    print("=" * 62)
    print("  Geaboc Subtitle Console " + __version__)
    print("  AssemblyAI · Romanian · JabbokRiver Productions")
    print("=" * 62)
    print()

    try:
        choice = ask_choice("What would you like to do?", list(MENU))
        MENU[choice]()
    except Cancelled:
        print("Cancelled.")
        return 0
    except (ValueError, AssemblyAIError) as exc:
        print(f"\nERROR: {exc}", file=sys.stderr)
        say(str(exc), title="Geaboc Subtitle Console — problem")
        return 1
    return 0


# ─────────────────────────────────────────────────────────────────────────
# Self-test — proves the install works without spending API credits
# ─────────────────────────────────────────────────────────────────────────

_FAKE_RAW = {
    "id": "self-test-0000",
    "status": "completed",
    "language_code": "ro",
    "audio_duration": 754.0,
    "text": "Bună seara. Religia lui Isus nu este religia despre Isus.",
}

_FAKE_SENTENCES = {"sentences": [
    {"start": 0, "end": 3200, "text": "Bună seara, fraţi şi surori."},
    {"start": 3200, "end": 11800,
     "text": "Astăzi vorbim despre credinţa lui Isus, aşa cum este ea "
             "prezentată în Evanghelie, şi despre ce înseamnă ea pentru noi."},
    {"start": 320000, "end": 326000, "text": "Tatăl ne cheamă să facem voia Lui."},
]}


def self_test() -> int:
    print("Geaboc Subtitle Console — self-test (no network, no API credits)")
    print()
    tmp = Path(tempfile.mkdtemp(prefix="geaboc-selftest-"))
    try:
        segments = normalize_segments(_FAKE_SENTENCES, _FAKE_RAW["text"])
        summary = write_outputs(tmp / "C0086", "C0086", _FAKE_RAW, segments)
        produced = sorted(p.name for p in (tmp / "C0086").iterdir())
        print(f"  segments parsed : {summary['segments']}")
        print(f"  subtitle cues   : {summary['subtitle_cues']}")
        print(f"  duration        : {summary['duration_human']}")
        print(f"  files written   : {len(produced)}")
        for name in produced:
            print(f"      {name}")
        print()
        sample = (tmp / "C0086" / "C0086.srt").read_text(encoding="utf-8")
        print("  first subtitle cue:")
        for line in sample.splitlines()[:4]:
            print(f"      {line}")
        print()
        print("  Keychain reachable :",
              "yes" if is_macos() else "n/a (not macOS)")
        print("  AssemblyAI key     :",
              "found" if (os.environ.get("ASSEMBLYAI_API_KEY")
                          or keychain_get()) else "not set yet")
        print()
        print("Self-test passed.")
        return 0
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


# ─────────────────────────────────────────────────────────────────────────
# Entry point
# ─────────────────────────────────────────────────────────────────────────

def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="geaboc_console",
        description="AssemblyAI transcription and subtitles for JabbokRiver.")
    parser.add_argument("--self-test", action="store_true",
                        help="verify the install without calling the API")
    parser.add_argument("--version", action="version",
                        version=f"Geaboc Subtitle Console {__version__}")
    sub = parser.add_subparsers(dest="command")

    p_tr = sub.add_parser("transcribe", help="transcribe an audio file")
    p_tr.add_argument("--code", required=True, help="episode code, e.g. C0086")
    p_tr.add_argument("--audio", required=True, type=Path, help="audio file")
    p_tr.add_argument("--language", default=DEFAULT_LANGUAGE)
    p_tr.add_argument("--out", type=Path, default=None,
                      help="output root (default: ~/Desktop/Geaboc Subtitles)")

    p_an = sub.add_parser("announce", help="build the WhatsApp announcement")
    p_an.add_argument("--code", required=True)
    p_an.add_argument("--url", required=True, help="YouTube link, any form")
    p_an.add_argument("--title", default="")
    p_an.add_argument("--out", type=Path, default=None,
                      help="output root (default: ~/Desktop/Geaboc Subtitles)")

    args = parser.parse_args(argv)

    if args.self_test:
        return self_test()

    try:
        if args.command == "transcribe":
            code = validate_code(args.code)
            # Check the file before asking for credentials — a typo in the
            # path should not look like a key problem.
            if not args.audio.exists():
                raise AssemblyAIError(f"Audio file not found:\n{args.audio}")
            api_key = resolve_api_key(interactive=False)
            summary = transcribe(code, args.audio, api_key,
                                 args.language, args.out)
            print(json.dumps(summary, ensure_ascii=False, indent=2))
            return 0
        if args.command == "announce":
            code = validate_code(args.code)
            text = build_whatsapp_announcement(
                args.title or code, args.url, "Dr. Emanoil Geaboc")
            out_dir = (args.out or output_root()) / code
            out_dir.mkdir(parents=True, exist_ok=True)
            (out_dir / "whatsapp_announcement.txt").write_text(
                text, encoding="utf-8")
            print(text)
            return 0
    except Cancelled:
        print("Cancelled.")
        return 0
    except (ValueError, AssemblyAIError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    return gui_main()


if __name__ == "__main__":
    sys.exit(main())
