#!/usr/bin/env python3
"""Transcribe an operator-held Geaboc recording with AssemblyAI (Romanian).

Standalone, stdlib-only — no pip installs, no ffmpeg. AssemblyAI accepts
MP3/MP4/WAV natively, so the source file is uploaded as-is.

Usage (on the operator host, e.g. the iMac):

    export ASSEMBLYAI_API_KEY='<key from Apple Passwords>'
    python3 channels/jabbokriver/tools/transcribe_local_assemblyai.py \
        "/Volumes/SSD_Adobe:FCP/C0081_/C0081.mp3"

With no argument it defaults to the C0081 path above. Outputs are written
next to the audio file:

    <stem>_ro.srt              subtitles (sentence-level timestamps)
    <stem>_ro.txt              plain text, one sentence per line
    <stem>_transcript_ro.md    clean markdown transcript

plus a copy of the .md into ~/Downloads when that directory exists.

Operator contract (matches scribeclaw/assemblyai.py):
  - ASSEMBLYAI_API_KEY env var must be set; the script refuses otherwise.
  - No hard-coded keys, ever.
"""
from __future__ import annotations

import json
import os
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

API_BASE = "https://api.assemblyai.com/v2"
DEFAULT_INPUT = "/Volumes/SSD_Adobe:FCP/C0081_/C0081.mp3"
UPLOAD_CHUNK = 5 * 1024 * 1024
POLL_SEC = 10
POLL_TIMEOUT_SEC = 60 * 60  # sermon-length audio; generous


def die(msg: str) -> "None":
    print(f"\n✗ {msg}", file=sys.stderr)
    sys.exit(1)


def api_key() -> str:
    key = os.getenv("ASSEMBLYAI_API_KEY", "").strip()
    if not key or "paste" in key.lower() or "your" in key.lower():
        die(
            "ASSEMBLYAI_API_KEY is not set (or still contains placeholder text).\n"
            "  Copy the real key from Apple Passwords ('Assembly AI - API key'),\n"
            "  then run:  export ASSEMBLYAI_API_KEY='<the-key>'  and re-run this script."
        )
    return key


def request(method: str, url: str, key: str, data: bytes | None = None,
            content_type: str | None = None) -> dict:
    req = urllib.request.Request(url, data=data, method=method)
    req.add_header("authorization", key)
    if content_type:
        req.add_header("content-type", content_type)
    try:
        with urllib.request.urlopen(req, timeout=300) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", "replace")[:500]
        if exc.code == 401:
            die("AssemblyAI rejected the API key (401 Invalid API key).\n"
                "  Double-check the key in Apple Passwords and re-export it.")
        die(f"AssemblyAI HTTP {exc.code} on {url}:\n  {body}")
    except urllib.error.URLError as exc:
        die(f"Network error reaching AssemblyAI: {exc.reason}")
    raise AssertionError("unreachable")


def upload(path: Path, key: str) -> str:
    size = path.stat().st_size
    print(f"→ Uploading {path.name} ({size / 1e6:.1f} MB) to AssemblyAI ...")
    sent = 0
    # Chunked read so a sermon-length file never sits fully in memory.
    body_parts: list[bytes] = []
    with path.open("rb") as fh:
        while True:
            chunk = fh.read(UPLOAD_CHUNK)
            if not chunk:
                break
            body_parts.append(chunk)
            sent += len(chunk)
            print(f"   read {sent / 1e6:.0f}/{size / 1e6:.0f} MB", end="\r")
    print()
    resp = request("POST", f"{API_BASE}/upload", key,
                   data=b"".join(body_parts),
                   content_type="application/octet-stream")
    return resp["upload_url"]


def fmt_ts(ms: int, sep: str = ",") -> str:
    h, ms = divmod(ms, 3_600_000)
    m, ms = divmod(ms, 60_000)
    s, ms = divmod(ms, 1000)
    return f"{h:02d}:{m:02d}:{s:02d}{sep}{ms:03d}"


def main() -> None:
    in_path = Path(sys.argv[1] if len(sys.argv) > 1 else DEFAULT_INPUT)
    if not in_path.exists():
        die(f"Audio file not found: {in_path}\n"
            "  Pass the path as an argument, e.g.\n"
            f"  python3 {sys.argv[0]} '/Volumes/SSD/my-recording.mp3'")
    key = api_key()

    audio_url = upload(in_path, key)

    print("→ Starting Romanian transcription (Universal model) ...")
    job = request("POST", f"{API_BASE}/transcript", key,
                  data=json.dumps({
                      "audio_url": audio_url,
                      "language_code": "ro",
                      "speech_model": "universal",
                      "punctuate": True,
                      "format_text": True,
                  }).encode("utf-8"),
                  content_type="application/json")
    tid = job["id"]
    print(f"   job id: {tid}")

    waited = 0
    while True:
        data = request("GET", f"{API_BASE}/transcript/{tid}", key)
        status = data.get("status")
        if status == "completed":
            break
        if status == "error":
            die(f"AssemblyAI job failed: {data.get('error')}")
        if waited >= POLL_TIMEOUT_SEC:
            die(f"Timed out after {waited}s (last status: {status}).\n"
                f"  The job may still finish — check the AssemblyAI dashboard for id {tid}.")
        print(f"   status: {status} ({waited}s elapsed)", end="\r")
        time.sleep(POLL_SEC)
        waited += POLL_SEC
    print("\n✓ Transcription complete.")

    sentences = request("GET", f"{API_BASE}/transcript/{tid}/sentences", key)
    sents = sentences.get("sentences") or []

    stem = in_path.with_suffix("")
    srt_path = Path(f"{stem}_ro.srt")
    txt_path = Path(f"{stem}_ro.txt")
    md_path = Path(f"{stem}_transcript_ro.md")

    srt_lines: list[str] = []
    for i, s in enumerate(sents, start=1):
        srt_lines += [str(i),
                      f"{fmt_ts(int(s['start']))} --> {fmt_ts(int(s['end']))}",
                      (s.get("text") or "").strip(), ""]
    srt_path.write_text("\n".join(srt_lines), encoding="utf-8")

    txt_path.write_text(
        "\n".join((s.get("text") or "").strip() for s in sents) or (data.get("text") or ""),
        encoding="utf-8",
    )

    dur = float(data.get("audio_duration") or 0)
    paragraphs: list[str] = []
    cur: list[str] = []
    for s in sents:
        cur.append((s.get("text") or "").strip())
        if len(cur) >= 6:
            paragraphs.append(" ".join(cur))
            cur = []
    if cur:
        paragraphs.append(" ".join(cur))
    md_path.write_text(
        f"# {in_path.stem} — transcriere în limba română\n\n"
        f"- Sursă: `{in_path}`\n"
        f"- Durată: {int(dur // 60)} min {int(dur % 60)} s\n"
        f"- Motor: AssemblyAI Universal (language_code=ro)\n"
        f"- AssemblyAI id: `{tid}`\n\n---\n\n"
        + "\n\n".join(paragraphs) + "\n",
        encoding="utf-8",
    )

    downloads = Path.home() / "Downloads"
    if downloads.is_dir():
        (downloads / md_path.name).write_text(
            md_path.read_text(encoding="utf-8"), encoding="utf-8")

    print(f"✓ Wrote:\n   {srt_path}\n   {txt_path}\n   {md_path}")
    if downloads.is_dir():
        print(f"   {downloads / md_path.name}")


if __name__ == "__main__":
    main()
