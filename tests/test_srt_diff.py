"""Tests for scribeclaw.srt_diff."""
from __future__ import annotations

import asyncio
from pathlib import Path

from scribeclaw.srt_diff import srt_diff

A = """1
00:00:00,000 --> 00:00:03,000
Postul Pavel.

2
00:00:03,000 --> 00:00:06,000
Unchanged cue.
"""

B_TEXT_CHANGED = """1
00:00:00,000 --> 00:00:03,000
Apostolul Pavel.

2
00:00:03,000 --> 00:00:06,000
Unchanged cue.
"""

B_TIMING_SHIFTED = """1
00:00:00,500 --> 00:00:03,500
Postul Pavel.

2
00:00:03,500 --> 00:00:06,500
Unchanged cue.
"""


def _write(root: Path, name: str, content: str) -> Path:
    p = root / "x" / name
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(content, encoding="utf-8")
    return p


def test_text_changed(tmp_path: Path):
    _write(tmp_path, "a.srt", A)
    _write(tmp_path, "b.srt", B_TEXT_CHANGED)
    r = asyncio.run(srt_diff({"a": "x/a.srt", "b": "x/b.srt"}, tmp_path))
    assert r["status"] == "success"
    assert r["changes_total"] == 1
    assert r["changes_by_kind"] == {"text_changed": 1}


def test_timing_shifted_detected(tmp_path: Path):
    _write(tmp_path, "a.srt", A)
    _write(tmp_path, "b.srt", B_TIMING_SHIFTED)
    r = asyncio.run(srt_diff({"a": "x/a.srt", "b": "x/b.srt",
                              "tolerance_ms": 50}, tmp_path))
    assert r["status"] == "success"
    # Two cues shifted by 500ms -> timing_shifted for each.
    assert r["changes_by_kind"].get("timing_shifted", 0) == 2


def test_identical_srts_have_zero_changes(tmp_path: Path):
    _write(tmp_path, "a.srt", A)
    _write(tmp_path, "b.srt", A)
    r = asyncio.run(srt_diff({"a": "x/a.srt", "b": "x/b.srt"}, tmp_path))
    assert r["changes_total"] == 0
    assert r["changes_by_kind"] == {}


def test_traversal_blocked(tmp_path: Path):
    r = asyncio.run(srt_diff({"a": "/etc/passwd", "b": "/etc/hosts"}, tmp_path))
    assert r["status"] == "error"
    assert r["error"] == "path_outside_data_root"


def test_missing_args(tmp_path: Path):
    r = asyncio.run(srt_diff({"a": "x.srt"}, tmp_path))
    assert r["status"] == "error"
    assert r["error"] == "a_and_b_required"
