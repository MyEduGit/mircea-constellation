"""Unit tests for scribeclaw.assemblyai pure helpers."""
from __future__ import annotations

from scribeclaw.assemblyai import _fmt_ts, _normalize_segments


def test_fmt_ts_comma():
    assert _fmt_ts(0.0, ",") == "00:00:00,000"


def test_fmt_ts_dot():
    assert _fmt_ts(1.234, ".") == "00:00:01.234"


def test_normalize_segments_with_sentences():
    payload = {"sentences": [
        {"start": 0, "end": 1500, "text": " Salut! "},
        {"start": 1500, "end": 3000, "text": "Ce faci?"},
    ]}
    segs = _normalize_segments(payload, "fallback")
    assert len(segs) == 2
    assert segs[0] == {"id": 0, "start": 0.0, "end": 1.5,
                       "text": "Salut!", "words": None}
    assert segs[1]["text"] == "Ce faci?"


def test_normalize_segments_empty_sentences_uses_fallback():
    segs = _normalize_segments({"sentences": []}, "full body text")
    assert len(segs) == 1
    assert segs[0]["text"] == "full body text"


def test_normalize_segments_empty_both():
    segs = _normalize_segments({}, "   ")
    assert segs == []
