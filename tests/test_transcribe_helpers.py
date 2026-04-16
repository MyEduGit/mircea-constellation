"""Unit tests for the pure helpers in scribeclaw.transcribe.

The handler itself needs faster-whisper + a model; not tested here.
The helpers below are the serialization primitives everything else
relies on — they must be stable."""
from __future__ import annotations

from pathlib import Path

import pytest

from scribeclaw.transcribe import _format_ts, _write_srt, _write_vtt


def test_format_ts_srt_zero():
    assert _format_ts(0.0) == "00:00:00,000"


def test_format_ts_vtt_zero():
    assert _format_ts(0.0, ".") == "00:00:00.000"


def test_format_ts_mixed():
    # 3723.456 = 1h 2m 3s 456ms
    assert _format_ts(3723.456) == "01:02:03,456"


def test_format_ts_rounds_ms_up():
    # 1.9995 s -> 2000 ms rounded
    assert _format_ts(1.9995) == "00:00:02,000"


def test_write_srt(tmp_path: Path):
    segs = [
        {"start": 0.0, "end": 1.5, "text": "hello"},
        {"start": 1.5, "end": 3.0, "text": "world"},
    ]
    out = tmp_path / "x.srt"
    _write_srt(segs, out)
    content = out.read_text(encoding="utf-8")
    assert "1\n00:00:00,000 --> 00:00:01,500\nhello" in content
    assert "2\n00:00:01,500 --> 00:00:03,000\nworld" in content


def test_write_vtt_header(tmp_path: Path):
    out = tmp_path / "x.vtt"
    _write_vtt([{"start": 0.0, "end": 1.0, "text": "hi"}], out)
    content = out.read_text(encoding="utf-8")
    assert content.startswith("WEBVTT")
    assert "00:00:00.000 --> 00:00:01.000" in content


@pytest.mark.parametrize("sec,expected", [
    (0.0, "00:00:00,000"),
    (59.999, "00:00:59,999"),
    (60.0, "00:01:00,000"),
    (3600.0, "01:00:00,000"),
])
def test_format_ts_boundaries(sec, expected):
    assert _format_ts(sec) == expected
