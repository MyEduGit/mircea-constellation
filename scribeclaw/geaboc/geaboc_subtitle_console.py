#!/usr/bin/env python3
"""Geaboc Subtitle Console — AssemblyAI-only Romanian subtitle workflow.

Human entry point:
    python3 geaboc_subtitle_console.py serve

Agent/terminal entry point:
    python3 geaboc_subtitle_console.py run --episode C0083 --audio /path/audio.mp3

Offline fixture validation:
    python3 geaboc_subtitle_console.py fixture --episode C0082 \
        --assembly-json /path/C0082_assemblyai_transcript.json \
        --sbv /path/captions.sbv --output-root /tmp/geaboc-test

No MacWhisper or local speech-to-text engine is used. AssemblyAI is the sole
text authority. An optional YouTube SBV file contributes cue boundaries only.
"""

from __future__ import annotations

import argparse
import bisect
import hashlib
import html
import http.client
import json
import os
import re
import shutil
import socket
import subprocess
import sys
import tempfile
import threading
import time
import traceback
import urllib.parse
import webbrowser
import warnings
from dataclasses import dataclass
from datetime import datetime, timezone
from email import policy
from email.parser import BytesParser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any, Callable

warnings.filterwarnings(
    "ignore",
    message=r".*'cgi' is deprecated.*",
    category=DeprecationWarning,
)
try:
    import cgi
except ModuleNotFoundError:  # Python 3.13+
    cgi = None  # type: ignore[assignment]


APP_NAME = "Geaboc Subtitle Console"
APP_VERSION = "1.0.0"
AUTHOR = "Codex"
API_HOST = "api.assemblyai.com"
API_PREFIX = "/v2"
DEFAULT_SSD_ROOT = Path("/Volumes/SSD_Adobe:FCP")
DEFAULT_VAULT_ROOT = (
    Path.home()
    / "Library"
    / "Mobile Documents"
    / "com~apple~CloudDocs"
    / "UrantiPedia"
    / "Urantia-Vault"
    / "JRP"
    / "Geaboc"
)
KEYCHAIN_SERVICE = "Geaboc AssemblyAI API Key"
SECRETS_FILE = Path.home() / ".openclaw" / "secrets.env"
EPISODE_RE = re.compile(r"^C\d{4}$", re.IGNORECASE)
PUNCT_NO_SPACE = re.compile(r"\s+([,.;:!?%»)\]])")
SPACE_AFTER_OPEN = re.compile(r"([«(\[])\s+")
CEDILLA_MAP = str.maketrans({"ş": "ș", "Ş": "Ș", "ţ": "ț", "Ţ": "Ț"})


SAFE_CORRECTIONS: dict[str, str] = {
    "duhul sfant": "Duhul Sfânt",
    "spiritul sfant": "Spiritul Sfânt",
    "isus hristos": "Iisus Hristos",
    "iisus hristos": "Iisus Hristos",
    "elen white": "Ellen White",
    "ellen white": "Ellen White",
    "sora white": "Sora White",
    "elenoid": "Ellen White",
    "e.j. wagner": "E.J. Waggoner",
    "e. j. wagner": "E.J. Waggoner",
    "waggoner": "Waggoner",
    "a.t. jones": "A.T. Jones",
    "a. t. jones": "A.T. Jones",
    "j.h. kellogg": "J.H. Kellogg",
    "j. h. kellogg": "J.H. Kellogg",
    "alan stomp": "Alan Stump",
    "alan stamp": "Alan Stump",
    "filioche": "Filioque",
    "escotologia": "escatologie",
    "teologia ultimei generatii": "Teologia Ultimei Generații",
    "neprihanitre": "neprihănire",
    "neprihânire": "neprihănire",
    "conferinta generala": "Conferința Generală",
    "spiritul profetic": "Spiritul Profetic",
    "hritos lumina lumii": "Hristos Lumina Lumii",
    "hristos lumina lumei": "Hristos Lumina Lumii",
    "tragedia veacurilor": "Tragedia Veacurilor",
    "marea lupta": "Marea Luptă",
    "patriarhi si profeti": "Patriarhi și Profeți",
    "profeti si regi": "Profeți și Regi",
    "solii alese": "Solii Alese",
    "surorile fox": "Surorile Fox",
    "fetele fox": "Surorile Fox",
    "hidesville": "Hydesville",
    "haidsville": "Hydesville",
    "swedenborg": "Emanuel Swedenborg",
    "svedenborg": "Emanuel Swedenborg",
    "allan kardec": "Allan Kardec",
    "alan kardec": "Allan Kardec",
    "conan doyle": "Arthur Conan Doyle",
    "mișcarea new age": "Mișcarea New Age",
    "miscarea new age": "Mișcarea New Age",
    "sedinta spiritista": "ședință spiritistă",
    "starea mortilor": "Starea Morților",
    "mortii nu stiu nimic": "Morții nu știu nimic",
    # ── Reformation-history name-set (added from episode C0083) ──
    # Canonical-form normalization for the Reformation figures/terms these
    # sermons use. Keyed to lowercased / mis-accented / mis-spelled forms;
    # each maps to a single unambiguous canonical spelling (case + diacritics)
    # without imposing a first-name variant the speaker didn't use. Tune
    # against a real AssemblyAI transcript when one is in hand.
    "merle d'aubigné": "Merle d'Aubigné",
    "merle d'aubigne": "Merle d'Aubigné",
    "merle d’aubigné": "Merle d'Aubigné",
    "merle daubigne": "Merle d'Aubigné",
    "d'aubigné": "d'Aubigné",
    "d'aubigne": "d'Aubigné",
    "valdensi": "valdenzi",
    "waldensi": "valdenzi",
    "waldenses": "valdenzi",
    "valbenci": "valdenzi",
    "jan hus": "Jan Hus",
    "ioan hus": "Ioan Hus",
    "jan huss": "Jan Hus",
    "john wycliffe": "John Wycliffe",
    "ioan wycliffe": "Ioan Wycliffe",
    "wickliffe": "Wycliffe",
    "william tyndale": "William Tyndale",
    "tindale": "Tyndale",
    "girolamo savonarola": "Girolamo Savonarola",
    "savonarola": "Savonarola",
    "ulrich zwingli": "Ulrich Zwingli",
    "zwingli": "Zwingli",
    "filip melanchthon": "Filip Melanchthon",
    "melanchthon": "Melanchthon",
    "martin luther": "Martin Luther",
    "jean calvin": "Jean Calvin",
    "ioan calvin": "Ioan Calvin",
}


@dataclass
class Cue:
    start_ms: int
    end_ms: int
    text: str = ""


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def normalize_episode(value: str) -> str:
    episode = value.strip().upper()
    if not EPISODE_RE.fullmatch(episode):
        raise ValueError("Episode code must look like C0083 (C plus four digits).")
    return episode


def fmt_srt(ms: int) -> str:
    ms = max(0, int(ms))
    hours, rest = divmod(ms, 3_600_000)
    minutes, rest = divmod(rest, 60_000)
    seconds, millis = divmod(rest, 1000)
    return f"{hours:02d}:{minutes:02d}:{seconds:02d},{millis:03d}"


def parse_timecode(value: str) -> int:
    value = value.strip().replace(",", ".")
    parts = value.split(":")
    if len(parts) == 2:
        hours = 0
        minutes, seconds = parts
    elif len(parts) == 3:
        hours, minutes, seconds = parts
    else:
        raise ValueError(f"Invalid timecode: {value}")
    return int(hours) * 3_600_000 + int(minutes) * 60_000 + int(float(seconds) * 1000)


def parse_sbv(path: Path) -> list[Cue]:
    raw = path.read_text(encoding="utf-8-sig", errors="replace")
    blocks = re.split(r"\r?\n\s*\r?\n", raw.strip())
    cues: list[Cue] = []
    for block in blocks:
        lines = [line.strip() for line in block.splitlines() if line.strip()]
        if not lines or "," not in lines[0]:
            continue
        left, right = [part.strip() for part in lines[0].split(",", 1)]
        cues.append(Cue(parse_timecode(left), parse_timecode(right)))
    if not cues:
        raise ValueError("No valid timing cues found in the SBV file.")
    return cues


def parse_srt_text(raw: str) -> list[Cue]:
    cues: list[Cue] = []
    for block in re.split(r"\r?\n\s*\r?\n", raw.strip()):
        lines = [line.rstrip() for line in block.splitlines()]
        if len(lines) < 3:
            continue
        time_line = lines[1] if "-->" in lines[1] else lines[0]
        match = re.search(
            r"(\d{1,2}:\d{2}:\d{2}[,.]\d{3})\s*-->\s*"
            r"(\d{1,2}:\d{2}:\d{2}[,.]\d{3})",
            time_line,
        )
        if not match:
            continue
        text_start = 2 if "-->" in lines[1] else 1
        text_value = " ".join(line.strip() for line in lines[text_start:] if line.strip())
        cues.append(Cue(parse_timecode(match.group(1)), parse_timecode(match.group(2)), text_value))
    if not cues:
        raise ValueError("No valid cues found in AssemblyAI SRT output.")
    return cues


def apply_safe_corrections(text: str) -> str:
    text = text.translate(CEDILLA_MAP)
    text = re.sub(r"[ \t]+", " ", text)
    text = PUNCT_NO_SPACE.sub(r"\1", text)
    text = SPACE_AFTER_OPEN.sub(r"\1", text)
    for wrong, right in sorted(SAFE_CORRECTIONS.items(), key=lambda item: len(item[0]), reverse=True):
        text = re.sub(rf"(?<!\w){re.escape(wrong)}(?!\w)", right, text, flags=re.IGNORECASE)
    return text.strip()


def join_words(words: list[dict[str, Any]]) -> str:
    return apply_safe_corrections(" ".join(str(word.get("text") or "").strip() for word in words))


def wrap_two_lines(text: str, target: int = 42) -> str:
    text = " ".join(text.split())
    if len(text) <= target:
        return text
    words = text.split()
    if len(words) < 2:
        return text
    best_index = 1
    best_score = len(text)
    for index in range(1, len(words)):
        left = " ".join(words[:index])
        right = " ".join(words[index:])
        score = abs(len(left) - len(right))
        if score < best_score:
            best_score = score
            best_index = index
    return " ".join(words[:best_index]) + "\n" + " ".join(words[best_index:])


def render_srt(cues: list[Cue]) -> str:
    blocks = []
    for index, cue in enumerate(cues, start=1):
        blocks.append(
            f"{index}\n{fmt_srt(cue.start_ms)} --> {fmt_srt(cue.end_ms)}\n"
            f"{wrap_two_lines(cue.text)}"
        )
    return "\n\n".join(blocks) + "\n"


def align_assembly_words_to_sbv(
    words: list[dict[str, Any]], cues: list[Cue]
) -> tuple[list[Cue], dict[str, Any]]:
    if not words:
        raise ValueError("AssemblyAI response contains no word-level timestamps.")
    starts = [cue.start_ms for cue in cues]
    buckets: list[list[dict[str, Any]]] = [[] for _ in cues]
    unassigned: list[dict[str, Any]] = []

    for word in words:
        start = int(word.get("start") or 0)
        end = int(word.get("end") or start)
        midpoint = (start + end) // 2
        index = bisect.bisect_right(starts, midpoint) - 1
        chosen: int | None = None
        if 0 <= index < len(cues) and midpoint <= cues[index].end_ms:
            chosen = index
        else:
            candidates = []
            if 0 <= index < len(cues):
                candidates.append((abs(midpoint - cues[index].end_ms), index))
            if index + 1 < len(cues):
                candidates.append((abs(cues[index + 1].start_ms - midpoint), index + 1))
            if candidates:
                distance, nearest = min(candidates)
                if distance <= 1500:
                    chosen = nearest
        if chosen is None:
            unassigned.append(word)
        else:
            buckets[chosen].append(word)

    aligned: list[Cue] = []
    empty_indices: list[int] = []
    for index, (cue, bucket) in enumerate(zip(cues, buckets), start=1):
        text_value = join_words(bucket)
        if not text_value:
            empty_indices.append(index)
        aligned.append(Cue(cue.start_ms, cue.end_ms, text_value))

    # Empty timing cards contain no AssemblyAI words. Remove them rather than
    # importing YouTube text, keeping AssemblyAI as the sole text authority.
    final_cues = [cue for cue in aligned if cue.text]
    report = {
        "timing_source": "YouTube SBV cue boundaries",
        "text_source": "AssemblyAI words only",
        "source_cues": len(cues),
        "output_cues": len(final_cues),
        "empty_source_cues_removed": len(empty_indices),
        "empty_source_cue_numbers": empty_indices[:100],
        "assembly_words": len(words),
        "unassigned_words": len(unassigned),
        "unassigned_word_examples": [w.get("text") for w in unassigned[:20]],
    }
    return final_cues, report


def normalize_assembly_srt(raw_srt: str) -> tuple[list[Cue], dict[str, Any]]:
    cues = parse_srt_text(raw_srt)
    output = [
        Cue(cue.start_ms, cue.end_ms, apply_safe_corrections(cue.text))
        for cue in cues
        if cue.text.strip()
    ]
    return output, {
        "timing_source": "AssemblyAI SRT",
        "text_source": "AssemblyAI SRT",
        "source_cues": len(cues),
        "output_cues": len(output),
        "empty_source_cues_removed": len(cues) - len(output),
        "unassigned_words": 0,
    }


def qa_cues(cues: list[Cue]) -> dict[str, Any]:
    overlaps: list[int] = []
    invalid_durations: list[int] = []
    long_lines: list[int] = []
    empty: list[int] = []
    for index, cue in enumerate(cues, start=1):
        if cue.end_ms <= cue.start_ms:
            invalid_durations.append(index)
        if index > 1 and cue.start_ms < cues[index - 2].end_ms:
            overlaps.append(index)
        if not cue.text.strip():
            empty.append(index)
        if any(len(line) > 64 for line in wrap_two_lines(cue.text).splitlines()):
            long_lines.append(index)
    passed = not overlaps and not invalid_durations and not empty
    return {
        "passed": passed,
        "cue_count": len(cues),
        "overlap_count": len(overlaps),
        "overlap_cues": overlaps[:100],
        "invalid_duration_count": len(invalid_durations),
        "invalid_duration_cues": invalid_durations[:100],
        "empty_count": len(empty),
        "empty_cues": empty[:100],
        "long_line_warning_count": len(long_lines),
        "long_line_cues": long_lines[:100],
        "first_start_ms": cues[0].start_ms if cues else None,
        "last_end_ms": cues[-1].end_ms if cues else None,
    }


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def api_request(
    method: str,
    path: str,
    api_key: str,
    json_body: dict[str, Any] | None = None,
    timeout: int = 180,
) -> tuple[int, bytes, str]:
    connection = http.client.HTTPSConnection(API_HOST, timeout=timeout)
    body = json.dumps(json_body).encode("utf-8") if json_body is not None else None
    headers = {"Authorization": api_key}
    if body is not None:
        headers["Content-Type"] = "application/json"
    connection.request(method, path, body=body, headers=headers)
    response = connection.getresponse()
    data = response.read()
    content_type = response.getheader("Content-Type", "")
    status = response.status
    connection.close()
    if status >= 400:
        detail = data.decode("utf-8", errors="replace")[-1200:]
        raise RuntimeError(f"AssemblyAI HTTP {status}: {detail}")
    return status, data, content_type


def api_json(
    method: str,
    path: str,
    api_key: str,
    json_body: dict[str, Any] | None = None,
    timeout: int = 180,
) -> dict[str, Any]:
    _, data, _ = api_request(method, path, api_key, json_body=json_body, timeout=timeout)
    return json.loads(data.decode("utf-8"))


def upload_media(path: Path, api_key: str, progress: Callable[[str], None]) -> str:
    size = path.stat().st_size
    connection = http.client.HTTPSConnection(API_HOST, timeout=600)
    connection.putrequest("POST", f"{API_PREFIX}/upload")
    connection.putheader("Authorization", api_key)
    connection.putheader("Content-Type", "application/octet-stream")
    connection.putheader("Content-Length", str(size))
    connection.endheaders()
    sent = 0
    last_percent = -10
    with path.open("rb") as handle:
        while True:
            chunk = handle.read(5 * 1024 * 1024)
            if not chunk:
                break
            connection.send(chunk)
            sent += len(chunk)
            percent = int((sent / size) * 100) if size else 100
            if percent >= last_percent + 10:
                progress(f"Uploading audio to AssemblyAI: {percent}%")
                last_percent = percent
    response = connection.getresponse()
    data = response.read()
    status = response.status
    connection.close()
    if status >= 400:
        raise RuntimeError(
            f"AssemblyAI upload HTTP {status}: "
            + data.decode("utf-8", errors="replace")[-1200:]
        )
    return json.loads(data.decode("utf-8"))["upload_url"]


def run_assemblyai(
    audio_path: Path, api_key: str, progress: Callable[[str], None]
) -> tuple[dict[str, Any], str, str]:
    progress("AssemblyAI is the only transcription engine; MacWhisper is disabled.")
    upload_url = upload_media(audio_path, api_key, progress)
    progress("Submitting Romanian transcript request.")
    payload = {
        "audio_url": upload_url,
        "language_code": "ro",
        "speech_models": ["universal-3-5-pro", "universal-2"],
        "punctuate": True,
        "format_text": True,
    }
    submitted = api_json("POST", f"{API_PREFIX}/transcript", api_key, payload)
    transcript_id = submitted["id"]
    progress(f"Transcript submitted: {transcript_id}.")

    started = time.monotonic()
    last_status = ""
    while True:
        raw = api_json("GET", f"{API_PREFIX}/transcript/{transcript_id}", api_key)
        status = str(raw.get("status") or "")
        if status != last_status:
            progress(f"AssemblyAI status: {status}.")
            last_status = status
        if status == "completed":
            break
        if status == "error":
            raise RuntimeError(f"AssemblyAI transcription failed: {raw.get('error')}")
        if time.monotonic() - started > 7200:
            raise TimeoutError(
                f"Timed out after two hours; transcript ID is {transcript_id}."
            )
        time.sleep(8)

    _, srt_bytes, _ = api_request(
        "GET", f"{API_PREFIX}/transcript/{transcript_id}/srt?chars_per_caption=84", api_key
    )
    _, vtt_bytes, _ = api_request(
        "GET", f"{API_PREFIX}/transcript/{transcript_id}/vtt?chars_per_caption=84", api_key
    )
    return raw, srt_bytes.decode("utf-8"), vtt_bytes.decode("utf-8")


def find_api_key(explicit: str = "") -> tuple[str, str]:
    if explicit.strip():
        return explicit.strip(), "entered for this run"
    if os.getenv("ASSEMBLYAI_API_KEY", "").strip():
        return os.environ["ASSEMBLYAI_API_KEY"].strip(), "environment"
    if sys.platform == "darwin" and shutil.which("security"):
        result = subprocess.run(
            [
                "security",
                "find-generic-password",
                "-a",
                os.getenv("USER", ""),
                "-s",
                KEYCHAIN_SERVICE,
                "-w",
            ],
            capture_output=True,
            text=True,
        )
        if result.returncode == 0 and result.stdout.strip():
            return result.stdout.strip(), "macOS Keychain"
    if SECRETS_FILE.exists():
        for line in SECRETS_FILE.read_text(encoding="utf-8", errors="replace").splitlines():
            match = re.match(
                r"\s*(?:export\s+)?ASSEMBLYAI_API_KEY\s*=\s*['\"]?([^'\"\s]+)",
                line,
            )
            if match and match.group(1).strip():
                return match.group(1).strip(), "~/.openclaw/secrets.env"
    return "", "missing"


def save_api_key_to_keychain(api_key: str) -> None:
    if sys.platform != "darwin" or not shutil.which("security"):
        raise RuntimeError("macOS Keychain is unavailable on this machine.")
    subprocess.run(
        [
            "security",
            "add-generic-password",
            "-U",
            "-a",
            os.getenv("USER", ""),
            "-s",
            KEYCHAIN_SERVICE,
            "-w",
            api_key,
        ],
        check=True,
        capture_output=True,
        text=True,
    )


def detect_drive_root() -> Path | None:
    candidates: list[Path] = []
    cloud_storage = Path.home() / "Library" / "CloudStorage"
    if cloud_storage.exists():
        for item in sorted(cloud_storage.glob("GoogleDrive-*")):
            candidates.extend([item / "My Drive", item])
    candidates.extend(
        [
            Path("/Volumes/GoogleDrive/My Drive"),
            Path("/Volumes/GoogleDrive"),
            Path.home() / "Google Drive" / "My Drive",
            Path.home() / "Google Drive",
        ]
    )
    for candidate in candidates:
        if (candidate / "UrantiPedia").exists():
            return candidate
    return None


def resolved_paths(output_root: Path | None = None) -> dict[str, Path | None]:
    ssd_root = output_root or Path(os.getenv("GEABOC_OUTPUT_ROOT", str(DEFAULT_SSD_ROOT)))
    vault_root = Path(os.getenv("GEABOC_OBSIDIAN_ROOT", str(DEFAULT_VAULT_ROOT)))
    return {
        "ssd_root": ssd_root.expanduser(),
        "vault_root": vault_root.expanduser(),
        "drive_root": detect_drive_root(),
    }


def write_qa_markdown(
    episode: str,
    raw: dict[str, Any],
    alignment: dict[str, Any],
    qa: dict[str, Any],
) -> str:
    status = "PASS" if qa["passed"] else "BLOCKED"
    model = raw.get("speech_model_used") or raw.get("speech_model") or "unknown"
    return f"""# {episode} Subtitle QA — {AUTHOR}

## Result

**{status}**

| Check | Result |
|---|---|
| Transcript engine | AssemblyAI only |
| MacWhisper | Not used |
| Language | {raw.get("language_code") or "ro"} |
| Model actually used | {model} |
| Text source | {alignment.get("text_source")} |
| Timing source | {alignment.get("timing_source")} |
| Final cues | {qa.get("cue_count")} |
| Overlaps | {qa.get("overlap_count")} |
| Invalid durations | {qa.get("invalid_duration_count")} |
| Empty cues | {qa.get("empty_count")} |
| Long-line warnings | {qa.get("long_line_warning_count")} |
| Unassigned AssemblyAI words | {alignment.get("unassigned_words", 0)} |
| Empty SBV cues removed | {alignment.get("empty_source_cues_removed", 0)} |

Generated: {utc_now()}
"""


def sync_outputs(
    episode: str,
    episode_dir: Path,
    final_srt: Path,
    qa_path: Path,
    manifest_path: Path,
    progress: Callable[[str], None],
    paths: dict[str, Path | None],
) -> dict[str, Any]:
    sync: dict[str, Any] = {}
    vault_root = paths["vault_root"]
    if isinstance(vault_root, Path):
        transcripts = vault_root / "Transcripts"
        videos = vault_root / "Videos"
        sops = vault_root / "SOPs"
        transcripts.mkdir(parents=True, exist_ok=True)
        videos.mkdir(parents=True, exist_ok=True)
        sops.mkdir(parents=True, exist_ok=True)
        obsidian_srt = transcripts / final_srt.name
        shutil.copy2(final_srt, obsidian_srt)
        episode_note = videos / f"{episode}.md"
        note = f"""# {episode} — AssemblyAI subtitles

## Status

- Transcript authority: **AssemblyAI only**
- MacWhisper: **not used**
- Final SRT: `[[../Transcripts/{final_srt.name}]]`
- SSD folder: `{episode_dir}`
- QA: `{qa_path}`
- Manifest: `{manifest_path}`
- Generated by: {AUTHOR}
- Generated: {utc_now()}

## Cloud handoff

- Google Drive episode path: `UrantiPedia/03_Content/YouTube/{episode}/`
- Google Drive transcript path: `UrantiPedia/03_Content/Transcripts/`
- Notion hub: https://app.notion.com/p/29e8525ab5a081619084f31301c6cf2e
- GitHub source history: https://github.com/MyEduGit/mircea-constellation/tree/claude/fix-romanian-subtitles-Hg00H/scribeclaw

## Next action

Upload `{final_srt.name}` to YouTube Studio as Romanian subtitles with timing.
"""
        episode_note.write_text(note, encoding="utf-8")
        sync["obsidian_srt"] = str(obsidian_srt)
        sync["obsidian_note"] = str(episode_note)
        progress(f"Obsidian updated: {episode_note}.")

    drive_root = paths["drive_root"]
    if isinstance(drive_root, Path):
        episode_drive = drive_root / "UrantiPedia" / "03_Content" / "YouTube" / episode
        central_transcripts = drive_root / "UrantiPedia" / "03_Content" / "Transcripts"
        episode_drive.mkdir(parents=True, exist_ok=True)
        central_transcripts.mkdir(parents=True, exist_ok=True)
        for source in (final_srt, qa_path, manifest_path):
            shutil.copy2(source, episode_drive / source.name)
        shutil.copy2(final_srt, central_transcripts / final_srt.name)
        sync["drive_episode"] = str(episode_drive)
        sync["drive_transcript"] = str(central_transcripts / final_srt.name)
        progress(f"Google Drive desktop folder updated: {episode_drive}.")
    else:
        sync["drive_status"] = "Google Drive for Desktop not detected; handoff file created."
        progress("Google Drive desktop folder not mounted; cloud handoff remains in the manifest.")
    return sync


def finalize_from_raw(
    episode: str,
    raw: dict[str, Any],
    raw_srt: str,
    raw_vtt: str,
    audio_path: Path | None,
    sbv_path: Path | None,
    output_root: Path,
    progress: Callable[[str], None],
) -> dict[str, Any]:
    episode = normalize_episode(episode)
    if not output_root.exists():
        raise RuntimeError(
            f"Required output root is not mounted: {output_root}. "
            "Mount SSD_Adobe:FCP before starting to avoid paying for a transcript with nowhere to save it."
        )
    episode_dir = output_root / episode
    episode_dir.mkdir(parents=True, exist_ok=True)
    progress(f"Saving to canonical episode folder: {episode_dir}.")

    raw_json_path = episode_dir / f"{episode}_assemblyai_raw_{AUTHOR}.json"
    raw_srt_path = episode_dir / f"{episode}_assemblyai_raw_{AUTHOR}.srt"
    raw_vtt_path = episode_dir / f"{episode}_assemblyai_raw_{AUTHOR}.vtt"
    full_text_path = episode_dir / f"{episode}_transcript_ro_{AUTHOR}.txt"
    final_srt_path = episode_dir / f"{episode}_subtitles_ro_FINAL_{AUTHOR}.srt"
    qa_path = episode_dir / f"{episode}_subtitle_QA_{AUTHOR}.md"
    manifest_path = episode_dir / f"{episode}_subtitle_manifest_{AUTHOR}.json"
    handoff_path = episode_dir / f"{episode}_cloud_handoff_{AUTHOR}.md"

    raw_json_path.write_text(
        json.dumps(raw, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    raw_srt_path.write_text(raw_srt, encoding="utf-8")
    raw_vtt_path.write_text(raw_vtt, encoding="utf-8")
    full_text_path.write_text(str(raw.get("text") or "").strip() + "\n", encoding="utf-8")

    if sbv_path:
        progress("Using YouTube SBV timing only; ignoring all SBV words.")
        source_cues = parse_sbv(sbv_path)
        cues, alignment = align_assembly_words_to_sbv(raw.get("words") or [], source_cues)
    else:
        progress("No SBV supplied; using AssemblyAI SRT timing and text.")
        cues, alignment = normalize_assembly_srt(raw_srt)

    qa = qa_cues(cues)
    final_srt_path.write_text(render_srt(cues), encoding="utf-8")
    qa_path.write_text(write_qa_markdown(episode, raw, alignment, qa), encoding="utf-8")

    paths = resolved_paths(output_root)
    vault_root = paths["vault_root"]
    assert isinstance(vault_root, Path)
    manifest: dict[str, Any] = {
        "schema": "geaboc-subtitle-console/v1",
        "episode": episode,
        "created_at": utc_now(),
        "created_by": AUTHOR,
        "app_version": APP_VERSION,
        "transcription_engine": "AssemblyAI",
        "macwhisper_used": False,
        "language": raw.get("language_code") or "ro",
        "speech_models_requested": ["universal-3-5-pro", "universal-2"],
        "speech_model_used": raw.get("speech_model_used") or raw.get("speech_model"),
        "assemblyai_transcript_id": raw.get("id"),
        "audio_duration_seconds": raw.get("audio_duration"),
        "audio_source_path": str(audio_path) if audio_path else "fixture",
        "audio_sha256": sha256_file(audio_path) if audio_path and audio_path.exists() else None,
        "sbv_timing_path": str(sbv_path) if sbv_path else None,
        "alignment": alignment,
        "qa": qa,
        "canonical_paths": {
            "ssd_episode": str(episode_dir),
            "obsidian_video": str(vault_root / "Videos" / f"{episode}.md"),
            "obsidian_transcript": str(vault_root / "Transcripts" / final_srt_path.name),
            "drive_episode": f"UrantiPedia/03_Content/YouTube/{episode}/",
            "drive_transcripts": "UrantiPedia/03_Content/Transcripts/",
            "notion_hub": "https://app.notion.com/p/29e8525ab5a081619084f31301c6cf2e",
            "github_history": (
                "https://github.com/MyEduGit/mircea-constellation/tree/"
                "claude/fix-romanian-subtitles-Hg00H/scribeclaw"
            ),
        },
        "outputs": {
            "final_srt": str(final_srt_path),
            "transcript_txt": str(full_text_path),
            "raw_json": str(raw_json_path),
            "raw_srt": str(raw_srt_path),
            "raw_vtt": str(raw_vtt_path),
            "qa": str(qa_path),
        },
    }
    manifest_path.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    sync = sync_outputs(
        episode,
        episode_dir,
        final_srt_path,
        qa_path,
        manifest_path,
        progress,
        paths,
    )
    manifest["sync"] = sync
    manifest_path.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    handoff_path.write_text(
        f"""# {episode} cloud handoff — {AUTHOR}

- Final SRT: `{final_srt_path}`
- Obsidian note: `{sync.get("obsidian_note", "not available")}`
- Google Drive episode: `{sync.get("drive_episode", "Drive desktop not mounted")}`
- Notion parent: https://app.notion.com/p/29e8525ab5a081619084f31301c6cf2e
- GitHub historical source: https://github.com/MyEduGit/mircea-constellation/tree/claude/fix-romanian-subtitles-Hg00H/scribeclaw
- AssemblyAI transcript ID: `{raw.get("id")}`
- QA passed: `{qa.get("passed")}`
- MacWhisper used: `false`
""",
        encoding="utf-8",
    )
    manifest["outputs"]["cloud_handoff"] = str(handoff_path)
    manifest_path.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    progress(f"Final SRT created: {final_srt_path}.")
    progress(f"QA result: {'PASS' if qa['passed'] else 'BLOCKED'}.")
    return manifest


def execute_live(
    episode: str,
    audio_path: Path,
    sbv_path: Path | None,
    api_key: str,
    save_key: bool,
    output_root: Path,
    progress: Callable[[str], None],
) -> dict[str, Any]:
    episode = normalize_episode(episode)
    if not audio_path.exists() or not audio_path.is_file():
        raise FileNotFoundError(f"Audio file not found: {audio_path}")
    if not output_root.exists():
        raise RuntimeError(f"SSD is not mounted at {output_root}.")
    key, source = find_api_key(api_key)
    if not key:
        raise RuntimeError(
            "AssemblyAI key not found. Enter it once in the dashboard and choose Save to Keychain."
        )
    progress(f"AssemblyAI key loaded from {source}; the key itself is never logged.")
    if save_key and api_key.strip():
        save_api_key_to_keychain(api_key.strip())
        progress("AssemblyAI key saved to macOS Keychain.")
    raw, raw_srt, raw_vtt = run_assemblyai(audio_path, key, progress)
    return finalize_from_raw(
        episode,
        raw,
        raw_srt,
        raw_vtt,
        audio_path,
        sbv_path,
        output_root,
        progress,
    )


def system_status() -> dict[str, Any]:
    paths = resolved_paths()
    _, key_source = find_api_key()
    ssd = paths["ssd_root"]
    vault = paths["vault_root"]
    return {
        "app": APP_NAME,
        "version": APP_VERSION,
        "ssd_root": str(ssd),
        "ssd_ready": isinstance(ssd, Path) and ssd.exists(),
        "vault_root": str(vault),
        "vault_ready": isinstance(vault, Path) and vault.exists(),
        "drive_root": str(paths["drive_root"]) if paths["drive_root"] else None,
        "drive_ready": paths["drive_root"] is not None,
        "api_key_ready": key_source != "missing",
        "api_key_source": key_source,
        "transcription_engine": "AssemblyAI only",
        "macwhisper": "disabled",
    }


INDEX_HTML = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Geaboc Subtitle Console</title>
<style>
:root{--bg:#08111f;--panel:#101d30;--panel2:#13243c;--text:#eef5ff;--muted:#9fb3cb;
--blue:#5ba8ff;--green:#43d19e;--amber:#f7c65f;--red:#ff7384;--line:#28405f}
*{box-sizing:border-box}body{margin:0;background:linear-gradient(145deg,#07101c,#0d1a2b 55%,#10223b);
color:var(--text);font:16px/1.45 -apple-system,BlinkMacSystemFont,"SF Pro Text",Inter,Arial,sans-serif}
main{max-width:980px;margin:0 auto;padding:38px 22px 70px}h1{font-size:36px;margin:0 0 6px;letter-spacing:-.03em}
.sub{color:var(--muted);margin-bottom:24px}.grid{display:grid;grid-template-columns:repeat(4,1fr);gap:10px;margin:18px 0 26px}
.card{background:rgba(16,29,48,.9);border:1px solid var(--line);border-radius:14px;padding:13px}
.label{font-size:12px;color:var(--muted);text-transform:uppercase;letter-spacing:.08em}.value{font-weight:700;margin-top:4px}
.ok{color:var(--green)}.bad{color:var(--red)}section{background:rgba(16,29,48,.92);border:1px solid var(--line);
border-radius:18px;padding:22px;margin-top:16px;box-shadow:0 18px 50px rgba(0,0,0,.18)}
.row{display:grid;grid-template-columns:1fr 2fr;gap:14px}.field{margin:13px 0}label{display:block;font-weight:650;margin-bottom:7px}
input[type=text],input[type=password],input[type=file]{width:100%;background:#0b1728;color:var(--text);border:1px solid #355375;
border-radius:10px;padding:12px}small{color:var(--muted)}button{background:linear-gradient(135deg,#4098ff,#6a7cff);
border:0;color:#fff;font-weight:750;border-radius:11px;padding:13px 19px;cursor:pointer;font-size:16px}
button:disabled{opacity:.45;cursor:wait}.note{border-left:3px solid var(--blue);padding:9px 12px;background:#0c192b;color:#cfe2fa;border-radius:4px}
#log{white-space:pre-wrap;background:#07111e;border:1px solid var(--line);border-radius:12px;padding:16px;min-height:150px;
max-height:390px;overflow:auto;color:#cde0f7;font-family:"SFMono-Regular",Menlo,monospace;font-size:13px}
.result{display:none;border:1px solid var(--green);background:#0b2b26;padding:15px;border-radius:12px;margin-top:14px}
@media(max-width:760px){.grid{grid-template-columns:1fr 1fr}.row{grid-template-columns:1fr}h1{font-size:30px}}
</style>
</head>
<body><main>
<h1>Geaboc Subtitle Console</h1>
<div class="sub">One click · AssemblyAI Romanian transcription · SSD + Obsidian + Drive</div>
<div class="grid" id="status"></div>
<section>
<div class="note"><strong>Permanent rule:</strong> AssemblyAI supplies every word. MacWhisper is disabled.
An optional YouTube SBV file supplies timing boundaries only.</div>
<form id="job" enctype="multipart/form-data">
<div class="row">
<div class="field"><label>Episode code</label><input name="episode" type="text" value="C0083" pattern="C[0-9]{4}" required>
<small>No trailing underscore. Example: C0083</small></div>
<div class="field"><label>Audio file</label><input name="audio" type="file" accept="audio/*,.mp3,.wav,.m4a,.aac,.flac,.mp4,.mov" required>
<small>Use audio extracted from the final edit.</small></div>
</div>
<div class="field"><label>YouTube SBV timing file (optional)</label><input name="sbv" type="file" accept=".sbv,text/plain">
<small>If supplied, its text is ignored. Only its start/end times are used.</small></div>
<div class="row">
<div class="field"><label>AssemblyAI API key (only if status says missing)</label><input name="api_key" type="password" autocomplete="off">
<small>The key is never written into reports or logs.</small></div>
<div class="field"><label style="margin-top:30px"><input name="save_key" type="checkbox" value="yes"> Save entered key to macOS Keychain</label></div>
</div>
<button id="run" type="submit">Transcribe with AssemblyAI</button>
</form>
<div class="result" id="result"></div>
</section>
<section><label>Live work log</label><div id="log">Ready.</div></section>
</main>
<script>
const statusEl=document.getElementById('status'), logEl=document.getElementById('log'),
runBtn=document.getElementById('run'), resultEl=document.getElementById('result');
function card(name,ready,detail){return `<div class="card"><div class="label">${name}</div><div class="value ${ready?'ok':'bad'}">${ready?'Ready':'Needs attention'}</div><small>${detail||''}</small></div>`}
async function loadStatus(){const s=await (await fetch('/api/status')).json();
statusEl.innerHTML=card('SSD',s.ssd_ready,s.ssd_root)+card('Obsidian',s.vault_ready,s.vault_root)+
card('Google Drive',s.drive_ready,s.drive_root||'Desktop sync not detected')+card('AssemblyAI key',s.api_key_ready,s.api_key_source);}
async function poll(){const s=await (await fetch('/api/job')).json();logEl.textContent=(s.log||[]).join('\\n')||'Ready.';
logEl.scrollTop=logEl.scrollHeight;if(s.state==='running'){setTimeout(poll,1500)}
else{runBtn.disabled=false;if(s.state==='completed'){resultEl.style.display='block';resultEl.innerHTML='<strong>Complete.</strong><br>Final SRT: '+s.result.outputs.final_srt+'<br>QA: '+(s.result.qa.passed?'PASS':'BLOCKED');loadStatus()}
else if(s.state==='error'){resultEl.style.display='block';resultEl.style.borderColor='var(--red)';resultEl.style.background='#35151d';resultEl.textContent='Stopped: '+s.error;}}}
document.getElementById('job').addEventListener('submit',async(e)=>{e.preventDefault();runBtn.disabled=true;resultEl.style.display='none';
logEl.textContent='Uploading the selected local file to the console…';const r=await fetch('/api/run',{method:'POST',body:new FormData(e.target)});
if(!r.ok){const j=await r.json();runBtn.disabled=false;alert(j.error||'Could not start');return}poll();});
loadStatus();
</script></body></html>"""


class JobState:
    def __init__(self) -> None:
        self.lock = threading.Lock()
        self.state = "idle"
        self.log: list[str] = []
        self.result: dict[str, Any] | None = None
        self.error = ""

    def start(self) -> None:
        with self.lock:
            if self.state == "running":
                raise RuntimeError("A transcription is already running.")
            self.state = "running"
            self.log = []
            self.result = None
            self.error = ""

    def progress(self, message: str) -> None:
        line = f"[{datetime.now().strftime('%H:%M:%S')}] {message}"
        with self.lock:
            self.log.append(line)

    def complete(self, result: dict[str, Any]) -> None:
        with self.lock:
            self.state = "completed"
            self.result = result

    def fail(self, error: str) -> None:
        with self.lock:
            self.state = "error"
            self.error = error
            self.log.append(f"[{datetime.now().strftime('%H:%M:%S')}] ERROR: {error}")

    def snapshot(self) -> dict[str, Any]:
        with self.lock:
            return {
                "state": self.state,
                "log": list(self.log),
                "result": self.result,
                "error": self.error,
            }


JOB = JobState()


def parse_multipart_without_cgi(
    handler: BaseHTTPRequestHandler,
) -> dict[str, dict[str, Any]]:
    """Compatibility parser for Python 3.13+, where cgi was removed.

    This fallback holds the browser upload in memory. Audio-only source files
    are expected; operators should not upload multi-gigabyte final videos.
    """
    content_type = handler.headers.get("Content-Type", "")
    content_length = int(handler.headers.get("Content-Length", "0"))
    if "multipart/form-data" not in content_type:
        raise ValueError("Expected a multipart form upload.")
    body = handler.rfile.read(content_length)
    envelope = (
        f"Content-Type: {content_type}\r\nMIME-Version: 1.0\r\n\r\n".encode("utf-8")
        + body
    )
    message = BytesParser(policy=policy.default).parsebytes(envelope)
    fields: dict[str, dict[str, Any]] = {}
    for part in message.iter_parts():
        name = part.get_param("name", header="content-disposition")
        if not name:
            continue
        fields[str(name)] = {
            "filename": part.get_filename() or "",
            "data": part.get_payload(decode=True) or b"",
        }
    return fields


class ConsoleHandler(BaseHTTPRequestHandler):
    server_version = "GeabocConsole/1.0"

    def log_message(self, format: str, *args: Any) -> None:
        return

    def send_json(self, data: dict[str, Any], status: int = 200) -> None:
        raw = json.dumps(data, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)

    def do_GET(self) -> None:
        route = urllib.parse.urlparse(self.path).path
        if route == "/":
            raw = INDEX_HTML.encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(raw)))
            self.end_headers()
            self.wfile.write(raw)
        elif route == "/api/status":
            self.send_json(system_status())
        elif route == "/api/job":
            self.send_json(JOB.snapshot())
        else:
            self.send_json({"error": "not found"}, 404)

    def do_POST(self) -> None:
        if urllib.parse.urlparse(self.path).path != "/api/run":
            self.send_json({"error": "not found"}, 404)
            return
        try:
            JOB.start()
            content_type = self.headers.get("Content-Type", "")
            content_length = self.headers.get("Content-Length", "0")
            if cgi is not None:
                form = cgi.FieldStorage(
                    fp=self.rfile,
                    headers=self.headers,
                    environ={
                        "REQUEST_METHOD": "POST",
                        "CONTENT_TYPE": content_type,
                        "CONTENT_LENGTH": content_length,
                    },
                    keep_blank_values=True,
                )
                episode = normalize_episode(form.getfirst("episode", ""))
                api_key = form.getfirst("api_key", "")
                save_key = form.getfirst("save_key", "") == "yes"
                temp_root = Path(tempfile.mkdtemp(prefix=f"geaboc-{episode}-"))
                audio_field = form["audio"] if "audio" in form else None
                if audio_field is None or not getattr(audio_field, "filename", ""):
                    raise ValueError("Choose an audio file.")
                audio_name = Path(audio_field.filename).name
                audio_path = temp_root / audio_name
                with audio_path.open("wb") as target:
                    shutil.copyfileobj(audio_field.file, target, length=1024 * 1024)
                sbv_path: Path | None = None
                if "sbv" in form and getattr(form["sbv"], "filename", ""):
                    sbv_path = temp_root / Path(form["sbv"].filename).name
                    with sbv_path.open("wb") as target:
                        shutil.copyfileobj(form["sbv"].file, target, length=1024 * 1024)
            else:
                fields = parse_multipart_without_cgi(self)
                episode = normalize_episode(
                    fields.get("episode", {}).get("data", b"").decode("utf-8")
                )
                api_key = fields.get("api_key", {}).get("data", b"").decode("utf-8")
                save_key = (
                    fields.get("save_key", {}).get("data", b"").decode("utf-8") == "yes"
                )
                temp_root = Path(tempfile.mkdtemp(prefix=f"geaboc-{episode}-"))
                audio_info = fields.get("audio", {})
                if not audio_info.get("filename"):
                    raise ValueError("Choose an audio file.")
                audio_path = temp_root / Path(str(audio_info["filename"])).name
                audio_path.write_bytes(audio_info["data"])
                sbv_info = fields.get("sbv", {})
                sbv_path = None
                if sbv_info.get("filename"):
                    sbv_path = temp_root / Path(str(sbv_info["filename"])).name
                    sbv_path.write_bytes(sbv_info["data"])

            output_root = resolved_paths()["ssd_root"]
            assert isinstance(output_root, Path)

            def worker() -> None:
                try:
                    result = execute_live(
                        episode,
                        audio_path,
                        sbv_path,
                        api_key,
                        save_key,
                        output_root,
                        JOB.progress,
                    )
                    JOB.complete(result)
                except Exception as exc:
                    JOB.fail(str(exc))
                finally:
                    shutil.rmtree(temp_root, ignore_errors=True)

            threading.Thread(target=worker, daemon=True).start()
            self.send_json({"started": True, "episode": episode}, 202)
        except Exception as exc:
            JOB.fail(str(exc))
            self.send_json({"error": str(exc)}, 400)


def find_open_port(preferred: int = 8765) -> int:
    for port in range(preferred, preferred + 20):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            try:
                sock.bind(("127.0.0.1", port))
                return port
            except OSError:
                continue
    raise RuntimeError("No free local port found.")


def serve(port: int, open_browser: bool = True) -> None:
    actual_port = find_open_port(port)
    url = f"http://127.0.0.1:{actual_port}"
    server = ThreadingHTTPServer(("127.0.0.1", actual_port), ConsoleHandler)
    print(f"{APP_NAME} {APP_VERSION}")
    print(f"Open: {url}")
    print("Press Control-C to stop.")
    if open_browser:
        threading.Timer(0.7, lambda: webbrowser.open(url)).start()
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nConsole stopped.")
    finally:
        server.server_close()


def cli_progress(message: str) -> None:
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {message}", flush=True)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)

    serve_parser = sub.add_parser("serve", help="Open the local dashboard")
    serve_parser.add_argument("--port", type=int, default=8765)
    serve_parser.add_argument("--no-open", action="store_true")

    run_parser = sub.add_parser("run", help="Transcribe one episode with AssemblyAI")
    run_parser.add_argument("--episode", required=True)
    run_parser.add_argument("--audio", type=Path, required=True)
    run_parser.add_argument("--sbv", type=Path)
    run_parser.add_argument("--api-key", default="")
    run_parser.add_argument("--save-key", action="store_true")
    run_parser.add_argument("--output-root", type=Path, default=DEFAULT_SSD_ROOT)

    fixture_parser = sub.add_parser(
        "fixture", help="Finalize an existing AssemblyAI JSON without any API charge"
    )
    fixture_parser.add_argument("--episode", required=True)
    fixture_parser.add_argument("--assembly-json", type=Path, required=True)
    fixture_parser.add_argument("--assembly-srt", type=Path)
    fixture_parser.add_argument("--assembly-vtt", type=Path)
    fixture_parser.add_argument("--sbv", type=Path)
    fixture_parser.add_argument("--output-root", type=Path, required=True)

    sub.add_parser("status", help="Print detected destinations and key status")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    try:
        if args.command == "serve":
            serve(args.port, not args.no_open)
        elif args.command == "status":
            print(json.dumps(system_status(), ensure_ascii=False, indent=2))
        elif args.command == "run":
            result = execute_live(
                args.episode,
                args.audio.expanduser(),
                args.sbv.expanduser() if args.sbv else None,
                args.api_key,
                args.save_key,
                args.output_root.expanduser(),
                cli_progress,
            )
            print(json.dumps(result, ensure_ascii=False, indent=2))
        elif args.command == "fixture":
            raw = json.loads(args.assembly_json.read_text(encoding="utf-8"))
            if args.assembly_srt:
                raw_srt = args.assembly_srt.read_text(encoding="utf-8")
            else:
                # Fixture mode normally uses SBV timing. This placeholder is
                # retained as provenance and is not used when --sbv is present.
                raw_srt = "1\n00:00:00,000 --> 00:00:01,000\nFixture\n"
            raw_vtt = (
                args.assembly_vtt.read_text(encoding="utf-8")
                if args.assembly_vtt
                else "WEBVTT\n"
            )
            args.output_root.mkdir(parents=True, exist_ok=True)
            result = finalize_from_raw(
                args.episode,
                raw,
                raw_srt,
                raw_vtt,
                None,
                args.sbv,
                args.output_root,
                cli_progress,
            )
            print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        if os.getenv("GEABOC_DEBUG") == "1":
            traceback.print_exc()
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
