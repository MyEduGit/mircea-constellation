#!/usr/bin/env python3
"""build_coldopen.py — Assemble the 30-sec viral cold-open MP4 for Geaboc sermons.

Run on the iMac M4 after find_phrases.py has produced <stem>_timecodes.json.

Usage:
    # Automatic (reads timecodes JSON produced by find_phrases.py):
    python3 build_coldopen.py /path/to/C0073_Unified.mp3

    # Manual override (if you corrected timecodes by hand in FCP):
    python3 build_coldopen.py /path/to/C0073_Unified.mp3 \
        --ufo      "00:38:12.000" "00:38:19.000" \
        --copeland "00:23:44.000" "00:23:51.000" \
        --tomb     "00:16:30.000" "00:16:37.000" \
        --daughters "00:11:42.000" "00:11:48.000" \
        --pivot    "00:44:35.000" "00:44:43.000"

Output: <parent>/<stem>_ColdOpen_30sec.mp4 — drop at 0:00 in FCP.

Requires: ffmpeg on PATH, Pillow (pip3 install Pillow)
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path


# ─── Design tokens (match existing lower-thirds spec) ─────────────────────
BG_COLOR   = "#0B1426"  # dark navy
FG_COLOR   = "#FFFFFF"  # white text
GOLD_COLOR = "#FCD34D"  # gold accent
PIVOT_BG   = "#FCD34D"  # gold background for the Sora White pivot card
PIVOT_FG   = "#0B1426"  # navy text on gold bg

FONT_FAMILY  = "Poppins-Bold"   # fallback: DejaVu-Bold
FONT_SIZE_PT = 56               # ~3% of 1920px height

WIDTH  = 1920
HEIGHT = 1080
FPS    = 25


# ─── Cold-open card order ─────────────────────────────────────────────────
# (phrase_id, bg, fg, is_pivot)
CARD_ORDER = [
    ("ufo",       BG_COLOR,   FG_COLOR,   False),
    ("copeland",  BG_COLOR,   FG_COLOR,   False),
    ("tomb",      BG_COLOR,   FG_COLOR,   False),
    ("daughters", BG_COLOR,   FG_COLOR,   False),
    ("pivot",     PIVOT_BG,   PIVOT_FG,   True),
]

BLACK_FRAME_DURATION = 0.5   # seconds — YouTube retention reset


# ─── Helpers ──────────────────────────────────────────────────────────────

def _run(cmd: list[str], check: bool = True) -> subprocess.CompletedProcess:
    result = subprocess.run(cmd, capture_output=True, text=True)
    if check and result.returncode != 0:
        print(f"\n❌ ffmpeg error:\n{result.stderr[-2000:]}")
        sys.exit(1)
    return result


def _find_font() -> str:
    """Return path to a Bold sans-serif font available on macOS/Linux."""
    candidates = [
        # macOS system fonts
        "/Library/Fonts/Poppins-Bold.ttf",
        "/Library/Fonts/Arial Bold.ttf",
        os.path.expanduser("~/Library/Fonts/Poppins-Bold.ttf"),
        # Linux fallbacks
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
        "/usr/share/fonts/truetype/freefont/FreeSansBold.ttf",
    ]
    for p in candidates:
        if Path(p).exists():
            return p
    # Last resort: ask fc-match
    try:
        result = subprocess.run(
            ["fc-match", "--format=%{file}", "sans:bold"],
            capture_output=True, text=True
        )
        if result.returncode == 0 and result.stdout.strip():
            return result.stdout.strip()
    except FileNotFoundError:
        pass
    raise RuntimeError(
        "No suitable font found. Install Poppins-Bold.ttf into ~/Library/Fonts/ "
        "or /Library/Fonts/ on macOS."
    )


def _hex_to_rgb(hex_color: str) -> tuple[int, int, int]:
    h = hex_color.lstrip("#")
    return int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)


def _make_text_card_ffmpeg(
    text: str,
    duration: float,
    bg_color: str,
    fg_color: str,
    font_path: str,
    out_path: Path,
) -> None:
    """Generate a solid-colour text card MP4 using ffmpeg drawtext."""
    r, g, b = _hex_to_rgb(bg_color)
    fr, fg_r, fb = _hex_to_rgb(fg_color)

    # Escape special ffmpeg filter chars
    def _esc(s: str) -> str:
        return s.replace("\\", "\\\\").replace("'", "\\'").replace(":", "\\:")

    # For long text, wrap at ~28 chars
    words = text.split()
    lines: list[str] = []
    current = ""
    for w in words:
        if len(current) + len(w) + 1 > 28 and current:
            lines.append(current.strip())
            current = w + " "
        else:
            current += w + " "
    if current.strip():
        lines.append(current.strip())
    wrapped = r"\n".join(_esc(l) for l in lines)

    line_count = len(lines)
    font_size = FONT_SIZE_PT if line_count <= 2 else int(FONT_SIZE_PT * 0.8)

    drawtext = (
        f"drawtext=fontfile='{font_path}':"
        f"text='{wrapped}':"
        f"fontcolor=0x{fg_color.lstrip('#')}:"
        f"fontsize={font_size}:"
        f"x=(w-text_w)/2:y=(h-text_h)/2:"
        f"line_spacing=12"
    )

    cmd = [
        "ffmpeg", "-y", "-hide_banner", "-loglevel", "error",
        "-f", "lavfi",
        "-i", f"color=c=0x{bg_color.lstrip('#')}:s={WIDTH}x{HEIGHT}:r={FPS}:d={duration}",
        "-vf", drawtext,
        "-c:v", "libx264", "-preset", "fast", "-crf", "18",
        "-t", str(duration),
        "-an",
        str(out_path),
    ]
    _run(cmd)


def _extract_clip(
    audio_path: Path,
    clip_in: str,
    clip_out: str,
    out_path: Path,
) -> None:
    """Extract an audio clip and wrap it as a black-video MP4."""
    cmd = [
        "ffmpeg", "-y", "-hide_banner", "-loglevel", "error",
        "-ss", clip_in,
        "-to", clip_out,
        "-i", str(audio_path),
        # Black video, same resolution
        "-f", "lavfi", "-i", f"color=black:s={WIDTH}x{HEIGHT}:r={FPS}",
        "-map", "1:v", "-map", "0:a",
        "-c:v", "libx264", "-preset", "fast", "-crf", "18",
        "-c:a", "aac", "-b:a", "128k",
        "-shortest",
        str(out_path),
    ]
    _run(cmd)


def _make_black_frame(duration: float, out_path: Path) -> None:
    cmd = [
        "ffmpeg", "-y", "-hide_banner", "-loglevel", "error",
        "-f", "lavfi",
        "-i", f"color=black:s={WIDTH}x{HEIGHT}:r={FPS}:d={duration}",
        "-c:v", "libx264", "-preset", "fast", "-crf", "18",
        "-an",
        str(out_path),
    ]
    _run(cmd)


def _concat_clips(clip_paths: list[Path], out_path: Path) -> None:
    with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as flist:
        for p in clip_paths:
            flist.write(f"file '{p}'\n")
        flist_path = flist.name
    try:
        cmd = [
            "ffmpeg", "-y", "-hide_banner", "-loglevel", "error",
            "-f", "concat", "-safe", "0",
            "-i", flist_path,
            "-c:v", "libx264", "-preset", "fast", "-crf", "18",
            "-c:a", "aac", "-b:a", "128k",
            "-movflags", "+faststart",
            str(out_path),
        ]
        _run(cmd)
    finally:
        os.unlink(flist_path)


# ─── Main ──────────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Build the 30-sec Geaboc cold-open MP4."
    )
    parser.add_argument("audio", help="Path to the unified edited audio (MP3/WAV)")
    parser.add_argument("--ufo",       nargs=2, metavar=("IN", "OUT"))
    parser.add_argument("--copeland",  nargs=2, metavar=("IN", "OUT"))
    parser.add_argument("--tomb",      nargs=2, metavar=("IN", "OUT"))
    parser.add_argument("--daughters", nargs=2, metavar=("IN", "OUT"))
    parser.add_argument("--pivot",     nargs=2, metavar=("IN", "OUT"))
    args = parser.parse_args()

    audio_path = Path(args.audio).expanduser().resolve()
    if not audio_path.exists():
        print(f"ERROR: audio not found: {audio_path}")
        sys.exit(1)

    # Check ffmpeg
    if subprocess.run(["which", "ffmpeg"], capture_output=True).returncode != 0:
        print("ERROR: ffmpeg not on PATH.  brew install ffmpeg")
        sys.exit(1)

    font_path = _find_font()
    print(f"Font: {font_path}")

    # ── Gather timecodes ──────────────────────────────────────────────────
    # Priority: CLI args > timecodes JSON > error
    tc_json_path = audio_path.parent / f"{audio_path.stem}_timecodes.json"
    tc_json: dict = {}
    if tc_json_path.exists():
        tc_json = json.loads(tc_json_path.read_text("utf-8")).get("timecodes", {})

    cli_overrides: dict[str, tuple[str, str]] = {}
    if args.ufo:       cli_overrides["ufo"]       = tuple(args.ufo)
    if args.copeland:  cli_overrides["copeland"]  = tuple(args.copeland)
    if args.tomb:      cli_overrides["tomb"]       = tuple(args.tomb)
    if args.daughters: cli_overrides["daughters"] = tuple(args.daughters)
    if args.pivot:     cli_overrides["pivot"]      = tuple(args.pivot)

    timecodes: dict[str, dict] = {}
    for pid, _, _, _ in CARD_ORDER:
        if pid in cli_overrides:
            tin, tout = cli_overrides[pid]
            timecodes[pid] = {"clip_in": tin, "clip_out": tout}
        elif pid in tc_json:
            timecodes[pid] = tc_json[pid]
        else:
            print(f"ERROR: no timecode for phrase '{pid}'.")
            print(f"  Run find_phrases.py first, or supply --{pid} IN OUT on the CLI.")
            sys.exit(1)

    # Look up card text from JSON or defaults
    DEFAULT_CARDS = {
        "ufo":       "CONGRESUL A DECLASIFICAT 46 DE VIDEOCLIPURI",
        "copeland":  "COPELAND: «TU EȘTI DUMNEZEU.»",
        "tomb":      "BETHEL: DORM PE MORMINTE.",
        "daughters": "FETIȚELE MOARTE — AU APĂRUT DUMINICA.",
        "pivot":     "ȘI O FEMEIE A PREZIS TOT — DE 170 DE ANI.",
    }

    stem = audio_path.stem.replace("_Unified", "").replace("_unified", "")
    out_dir = audio_path.parent
    final_out = out_dir / f"{stem}_ColdOpen_30sec.mp4"

    print(f"\nBuilding cold-open → {final_out.name}\n")

    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        parts: list[Path] = []

        for i, (pid, bg, fg, _is_pivot) in enumerate(CARD_ORDER):
            tc = timecodes[pid]
            clip_in  = tc["clip_in"]
            clip_out = tc["clip_out"]
            card_text = (
                tc.get("card_text_ro")
                or tc.get("card_text")
                or DEFAULT_CARDS[pid]
            )

            print(f"  [{i+1}/5] {pid}  {clip_in} → {clip_out}")
            print(f"          Card: {card_text}")

            # Extract audio clip (with black video backing)
            clip_mp4 = tmp_path / f"clip_{i:02d}_{pid}.mp4"
            _extract_clip(audio_path, clip_in, clip_out, clip_mp4)

            # Generate matching text card
            dur_sec = float(
                tc.get("clip_duration")
                or _ts_to_sec(clip_out) - _ts_to_sec(clip_in)
            )
            card_mp4 = tmp_path / f"card_{i:02d}_{pid}.mp4"
            _make_text_card_ffmpeg(card_text, dur_sec, bg, fg, font_path, card_mp4)

            # Overlay text card on the audio clip
            combined_mp4 = tmp_path / f"combined_{i:02d}_{pid}.mp4"
            _overlay(clip_mp4, card_mp4, combined_mp4)

            parts.append(combined_mp4)

        # Black frame retention reset
        black_mp4 = tmp_path / "black_frame.mp4"
        _make_black_frame(BLACK_FRAME_DURATION, black_mp4)
        parts.append(black_mp4)

        # Concatenate all parts
        print(f"\n  Concatenating {len(parts)} parts…")
        _concat_clips(parts, final_out)

    # Print summary
    try:
        result = _run(
            ["ffprobe", "-v", "error", "-show_entries", "format=duration",
             "-of", "default=noprint_wrappers=1:nokey=1", str(final_out)],
            check=False,
        )
        dur = float(result.stdout.strip()) if result.stdout.strip() else 0
    except Exception:
        dur = 0

    print(f"\n{'='*60}")
    print(f"  ✅  Cold-open built: {final_out.name}")
    print(f"      Duration: {dur:.1f}s")
    print(f"      Resolution: {WIDTH}×{HEIGHT}  |  {FPS}fps  |  H.264 + AAC 128k")
    print(f"\n  ▶ In FCP: drag to timeline position 0:00 on the main storyline")
    print(f"            press W to INSERT (pushes sermon back ~{dur:.0f}s)")
    print(f"{'='*60}\n")


def _ts_to_sec(ts: str) -> float:
    """HH:MM:SS.mmm → float seconds."""
    parts = ts.split(":")
    h, m = int(parts[0]), int(parts[1])
    s = float(parts[2])
    return h * 3600 + m * 60 + s


def _overlay(base_mp4: Path, card_mp4: Path, out_path: Path) -> None:
    """Overlay the text card (video only) onto the base clip."""
    cmd = [
        "ffmpeg", "-y", "-hide_banner", "-loglevel", "error",
        "-i", str(base_mp4),
        "-i", str(card_mp4),
        "-filter_complex",
        "[0:v][1:v]overlay=0:0[v]",
        "-map", "[v]",
        "-map", "0:a?",
        "-c:v", "libx264", "-preset", "fast", "-crf", "18",
        "-c:a", "aac", "-b:a", "128k",
        str(out_path),
    ]
    _run(cmd)


if __name__ == "__main__":
    main()
