"""Tests for the Geaboc Subtitle Console.

Covers the pure logic — everything that can be verified without a Mac, an
AssemblyAI key, or a network connection. The macOS dialog and Keychain
layers are thin subprocess wrappers and are exercised by the installer's
--self-test instead.

Stdlib only, matching scribeclaw/tests/. Run from the repo root:

    python3 geaboc_subtitle_console/tests/test_geaboc_console.py
"""
from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from geaboc_console import (  # noqa: E402
    build_whatsapp_announcement,
    build_youtube_metadata,
    extract_youtube_id,
    fix_romanian,
    fmt_duration,
    fmt_timestamp,
    normalize_segments,
    normalize_youtube_url,
    reflow_paragraphs,
    render_srt,
    render_vtt,
    split_into_cues,
    suggest_chapters,
    validate_code,
    wrap_caption,
    write_outputs,
)

_FAILURES: list[str] = []
_PASSES = 0


def check(condition: bool, label: str) -> None:
    global _PASSES
    if condition:
        _PASSES += 1
    else:
        _FAILURES.append(label)


def check_raises(fn, exc_type, label: str) -> None:
    try:
        fn()
    except exc_type:
        check(True, label)
        return
    except Exception as exc:  # wrong exception type is still a failure
        check(False, f"{label} (raised {exc.__class__.__name__})")
        return
    check(False, f"{label} (did not raise)")


# ── Episode codes ───────────────────────────────────────────────────────

def test_codes() -> None:
    check(validate_code("C0086") == "C0086", "plain code accepted")
    check(validate_code("  C0086  ") == "C0086", "code is trimmed")
    check(validate_code("geaboc-003") == "geaboc-003", "slug code accepted")

    # A bad code must never be able to write outside the output folder.
    for bad in ["", "   ", "../C0086", "/etc/passwd", "C0086/sub", "..",
                "C0086;rm -rf /", "C 0086\nrm"]:
        check_raises(lambda b=bad: validate_code(b), ValueError,
                     f"rejects code {bad!r}")


# ── Timestamps ──────────────────────────────────────────────────────────

def test_timestamps() -> None:
    check(fmt_timestamp(0, ",") == "00:00:00,000", "zero timestamp")
    check(fmt_timestamp(1.5, ",") == "00:00:01,500", "fractional seconds")
    check(fmt_timestamp(3661.25, ",") == "01:01:01,250", "hour rollover")
    check(fmt_timestamp(3661.25, ".") == "01:01:01.250", "vtt separator")
    check(fmt_timestamp(-5, ",") == "00:00:00,000", "negative clamps to zero")
    # 999.9995 s rounds up to 1000000 ms — must roll into the seconds field,
    # not print as ,1000.
    check(fmt_timestamp(59.9999, ",") == "00:01:00,000", "millisecond rounding")

    check(fmt_duration(0) == "0:00:00", "zero duration")
    check(fmt_duration(754) == "0:12:34", "minutes and seconds")
    check(fmt_duration(3661) == "1:01:01", "hours")


# ── Segment normalization ───────────────────────────────────────────────

def test_segments() -> None:
    payload = {"sentences": [
        {"start": 0, "end": 3200, "text": "Bună seara."},
        {"start": 3200, "end": 9000, "text": "  Astăzi vorbim.  "},
        {"start": 9000, "end": 9500, "text": "   "},
    ]}
    segs = normalize_segments(payload)
    check(len(segs) == 2, "blank sentences dropped")
    check(segs[0]["start"] == 0.0 and segs[0]["end"] == 3.2,
          "milliseconds converted to seconds")
    check(segs[1]["text"] == "Astăzi vorbim.", "text is stripped")
    check([s["id"] for s in segs] == [0, 1], "ids are contiguous after drops")

    fallback = normalize_segments({"sentences": []}, "Doar text.")
    check(len(fallback) == 1 and fallback[0]["text"] == "Doar text.",
          "falls back to whole-text transcript")
    check(normalize_segments({"sentences": []}, "   ") == [],
          "empty fallback yields no segments")


# ── Romanian orthography ────────────────────────────────────────────────

def test_romanian() -> None:
    # Turkish cedilla → Romanian comma-below.
    check(fix_romanian("fraţi şi surori") == "frați și surori",
          "cedilla converted to comma-below")
    check(fix_romanian("ŞTIINŢA") == "ȘTIINȚA", "uppercase cedilla converted")
    check(fix_romanian("două  spaţii") == "două spații", "double space collapsed")
    check(fix_romanian("cuvânt , apoi") == "cuvânt, apoi", "space before comma")
    # Missing diacritics are NOT invented — that needs a human.
    check(fix_romanian("frati si surori") == "frati si surori",
          "unaccented text left alone, never guessed")

    paras = reflow_paragraphs([
        {"text": "Prima frază. A doua frază."},
        {"text": "A treia frază."},
    ])
    check(len(paras) == 3, "reflow splits on sentence boundaries")
    check(paras[0] == "Prima frază.", "first paragraph intact")


# ── Caption wrapping ────────────────────────────────────────────────────

def test_wrapping() -> None:
    check(wrap_caption("") == [], "empty text yields no lines")
    check(wrap_caption("scurt") == ["scurt"], "short text is one line")

    long_text = ("Astăzi vorbim despre credința lui Isus așa cum este ea "
                 "prezentată în Evanghelie și despre ce înseamnă pentru noi")
    lines = wrap_caption(long_text)
    check(all(len(ln) <= 42 for ln in lines), "every line within 42 characters")
    check(" ".join(lines) == long_text, "no words lost or duplicated in wrap")

    # A single unbreakable token is kept whole rather than chopped mid-word.
    giant = "Nebuchadnezzarrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrr"
    check(wrap_caption(giant) == [giant], "over-long word kept intact")


def test_cues() -> None:
    segments = [
        {"id": 0, "start": 0.0, "end": 3.0, "text": "Bună seara."},
        {"id": 1, "start": 3.0, "end": 30.0, "text": (
            "Astăzi vorbim despre credința lui Isus așa cum este ea "
            "prezentată în Evanghelie și despre ce înseamnă ea pentru "
            "fiecare dintre noi în viața de zi cu zi.")},
    ]
    cues = split_into_cues(segments)

    check(len(cues) > len(segments), "long sentence split into several cues")
    check(all(len(c["text"].splitlines()) <= 2 for c in cues),
          "no cue exceeds two lines")
    check(all(len(ln) <= 42 for c in cues for ln in c["text"].splitlines()),
          "no cue line exceeds 42 characters")

    # Timing must stay inside the parent sentence and never run backwards.
    check(all(c["end"] >= c["start"] for c in cues), "no cue ends before it starts")
    check(all(cues[i]["end"] <= cues[i + 1]["start"] + 1e-6
              for i in range(len(cues) - 1)), "cues do not overlap")
    check(abs(cues[-1]["end"] - 30.0) < 1e-6,
          "last cue ends exactly at the segment end")
    check(abs(cues[0]["start"] - 0.0) < 1e-6, "first cue starts at zero")

    # No text is lost in the split.
    joined = " ".join(c["text"].replace("\n", " ") for c in cues)
    original = " ".join(s["text"] for s in segments)
    check(" ".join(joined.split()) == " ".join(original.split()),
          "cue split preserves every word")

    check(split_into_cues([{"start": 0, "end": 1, "text": "   "}]) == [],
          "blank segment produces no cue")


# ── Subtitle rendering ──────────────────────────────────────────────────

def test_rendering() -> None:
    cues = [{"start": 0.0, "end": 2.5, "text": "Bună seara."},
            {"start": 2.5, "end": 5.0, "text": "A doua\nlinie."}]

    srt = render_srt(cues)
    lines = srt.splitlines()
    check(lines[0] == "1", "srt cue numbering starts at 1")
    check(lines[1] == "00:00:00,000 --> 00:00:02,500", "srt timing line")
    check(lines[2] == "Bună seara.", "srt text line")
    check(lines[3] == "", "blank line between srt cues")
    check(lines[4] == "2", "second cue numbered")

    vtt = render_vtt(cues)
    check(vtt.startswith("WEBVTT\n"), "vtt header present")
    check("00:00:00.000 --> 00:00:02.500" in vtt, "vtt uses dot separator")
    check("-->" in vtt and "," not in vtt.split("\n")[2], "vtt has no comma timings")


# ── YouTube link hygiene ────────────────────────────────────────────────

def test_youtube_links() -> None:
    expected = "ZKbWtcBfjQU"
    forms = [
        "https://youtu.be/ZKbWtcBfjQU",
        "https://www.youtube.com/watch?v=ZKbWtcBfjQU",
        "http://youtube.com/watch?v=ZKbWtcBfjQU",
        "www.youtube.com/watch?v=ZKbWtcBfjQU",
        "youtu.be/ZKbWtcBfjQU",
        "https://www.youtube.com/live/ZKbWtcBfjQU",
        "https://www.youtube.com/shorts/ZKbWtcBfjQU",
        "https://www.youtube.com/embed/ZKbWtcBfjQU",
        "https://www.youtube-nocookie.com/embed/ZKbWtcBfjQU",
        "ZKbWtcBfjQU",
    ]
    for form in forms:
        check(extract_youtube_id(form) == expected, f"extracts id from {form}")

    # The three reported defects, as regression tests.
    check(normalize_youtube_url("https://youtu.be/ZKbWtcBfjQU?t=42")
          == "https://youtu.be/ZKbWtcBfjQU",
          "start-time parameter stripped — video starts at the beginning")
    check(normalize_youtube_url(
        "https://youtu.be/ZKbWtcBfjQU?si=AbC123XyZ&t=1907")
        == "https://youtu.be/ZKbWtcBfjQU",
        "share-tracking and start-time both stripped")
    check(normalize_youtube_url(
        "https://www.youtube.com/watch?v=ZKbWtcBfjQU&list=PL123&index=4")
        == "https://youtu.be/ZKbWtcBfjQU",
        "playlist parameters stripped")
    check(normalize_youtube_url("  https://youtu.be/ZKbWtcBfjQU  ")
          == "https://youtu.be/ZKbWtcBfjQU", "surrounding whitespace ignored")

    for bad in ["", "not a link", "https://vimeo.com/12345",
                "https://youtu.be/", "https://www.youtube.com/watch?v=short",
                "https://example.com/watch?v=ZKbWtcBfjQU"]:
        check(extract_youtube_id(bad) is None, f"no id extracted from {bad!r}")
        check_raises(lambda b=bad: normalize_youtube_url(b), ValueError,
                     f"refuses to build a link from {bad!r}")


# ── WhatsApp announcement ───────────────────────────────────────────────

def test_whatsapp() -> None:
    text = build_whatsapp_announcement(
        title="Credința lui Isus",
        url="https://youtu.be/ZKbWtcBfjQU?si=track&t=1907",
        host="Dr. Emanoil Geaboc",
        summary="O predică despre religia LUI Isus.",
        duration_sec=3725)

    # "still pastes unformatted" — no Markdown may survive into WhatsApp.
    for markdown in ["**", "##", "__", "](", "<http", "```"]:
        check(markdown not in text, f"no markdown {markdown!r} in output")
    check(text.startswith("*Credința lui Isus*"),
          "title uses WhatsApp bold, not markdown")
    check("_Dr. Emanoil Geaboc_" in text, "host uses WhatsApp italic")
    check("\n" in text, "real line breaks, not escaped ones")
    check("\\n" not in text, "no literal backslash-n in output")

    # "the link does not work" / "it does not start at the beginning".
    check("https://youtu.be/ZKbWtcBfjQU" in text, "clean link present")
    check("t=1907" not in text and "si=track" not in text,
          "no start-time or tracking parameters in the announcement")

    # The URL must sit alone on its line or WhatsApp will not auto-link it.
    url_lines = [ln for ln in text.splitlines() if "youtu.be" in ln]
    check(len(url_lines) == 1, "exactly one link line")
    check(url_lines[0].strip() == "https://youtu.be/ZKbWtcBfjQU",
          "link is bare on its own line")

    check("1:02:05" in text, "duration rendered")
    check(text.endswith("\n"), "trailing newline for clean paste")

    minimal = build_whatsapp_announcement(
        "T", "https://youtu.be/ZKbWtcBfjQU", "")
    check("Durata" not in minimal, "duration omitted when unknown")
    check_raises(
        lambda: build_whatsapp_announcement("T", "broken", "H"),
        ValueError, "announcement refuses a link it cannot clean")


# ── Metadata worksheet ──────────────────────────────────────────────────

def test_metadata() -> None:
    segments = [
        {"id": 0, "start": 0.0, "end": 5.0, "text": "Bună seara."},
        {"id": 1, "start": 310.0, "end": 315.0, "text": "Al doilea punct."},
        {"id": 2, "start": 640.0, "end": 645.0, "text": "Al treilea punct."},
    ]
    chapters = suggest_chapters(segments)
    check(chapters[0].startswith("00:00"), "first chapter is 00:00 as YouTube requires")
    check(len(chapters) == 3, "a chapter mark roughly every five minutes")
    check(suggest_chapters([])[0].startswith("00:00"), "empty input still yields 00:00")

    meta = build_youtube_metadata("C0086", segments, 754.0, "Dr. Emanoil Geaboc")
    check("C0086" in meta, "code appears in the worksheet")
    check("0:12:34" in meta, "duration appears")
    check("C0086.srt" in meta, "points at the subtitle file to upload")
    # It must not invent an editorial title.
    title_section = meta.split("## Title")[1].split("##")[0]
    check(title_section.strip().endswith(")"),
          "title is left blank for the operator, not fabricated")


# ── Full output folder ──────────────────────────────────────────────────

def test_write_outputs() -> None:
    raw = {"id": "abc123", "status": "completed", "language_code": "ro",
           "audio_duration": 754.0, "text": "Bună seara. Fraţi şi surori."}
    segments = normalize_segments({"sentences": [
        {"start": 0, "end": 3000, "text": "Bună seara."},
        {"start": 3000, "end": 9000, "text": "Fraţi şi surori."},
    ]})

    with tempfile.TemporaryDirectory() as tmp:
        out = Path(tmp) / "C0086"
        summary = write_outputs(out, "C0086", raw, segments)

        for name in ["assemblyai.raw.json", "segments.json", "transcript.srt",
                     "transcript.vtt", "transcript.txt", "segments.clean.json",
                     "transcript.clean.txt", "C0086.srt", "C0086.vtt",
                     "youtube_metadata.txt", "RUN.json"]:
            check((out / name).exists(), f"wrote {name}")

        # scribeclaw compatibility: segments.json keeps the agreed shape.
        seg_data = json.loads((out / "segments.json").read_text(encoding="utf-8"))
        for key in ["language", "duration", "model", "segments", "source",
                    "assemblyai_id"]:
            check(key in seg_data, f"segments.json carries {key}")
        check(seg_data["source"] == "assemblyai", "source recorded as assemblyai")
        check(seg_data["segments"][0]["start"] == 0.0, "segment timings in seconds")

        # The clean copy is corrected; the verbatim copy is not touched.
        clean = (out / "transcript.clean.txt").read_text(encoding="utf-8")
        verbatim = (out / "transcript.txt").read_text(encoding="utf-8")
        check("frați și surori" in clean.lower(), "clean transcript is corrected")
        check("Fraţi şi surori." in verbatim, "verbatim transcript is preserved")

        check(summary["engine"] == "assemblyai", "run record names the engine")
        check(summary["assemblyai_id"] == "abc123", "run record keeps the job id")
        check(summary["duration_human"] == "0:12:34", "run record has readable duration")

        run = json.loads((out / "RUN.json").read_text(encoding="utf-8"))
        check("api_key" not in json.dumps(run).lower().replace("assemblyai_id", ""),
              "run record contains no key material")

        # Idempotent: a re-run over the same folder must not fail.
        write_outputs(out, "C0086", raw, segments)
        check(True, "second run over an existing folder succeeds")


def main() -> int:
    for fn in [test_codes, test_timestamps, test_segments, test_romanian,
               test_wrapping, test_cues, test_rendering, test_youtube_links,
               test_whatsapp, test_metadata, test_write_outputs]:
        fn()

    print(f"{_PASSES} checks passed, {len(_FAILURES)} failed")
    if _FAILURES:
        print("\nFAILED:")
        for label in _FAILURES:
            print(f"  ✗ {label}")
        return 1
    print("All checks passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
