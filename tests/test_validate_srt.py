"""Tests for scribeclaw.validate_srt — shape and classification only.

These are async handlers; we drive them directly via asyncio.run."""
from __future__ import annotations

import asyncio
from pathlib import Path

from scribeclaw.validate_srt import validate_srt

GOOD = """1
00:00:00,000 --> 00:00:03,000
Salut.

2
00:00:03,000 --> 00:00:06,500
A doua cue.
"""

OVERLAP = """1
00:00:00,000 --> 00:00:05,000
A.

2
00:00:03,000 --> 00:00:06,000
B.
"""

OUT_OF_ORDER = """1
00:00:10,000 --> 00:00:15,000
A.

2
00:00:03,000 --> 00:00:06,000
B.
"""

END_BEFORE_START = """1
00:00:10,000 --> 00:00:05,000
A.
"""


def _run(path: Path):
    return asyncio.run(validate_srt({"srt_path": str(path.relative_to(path.parents[1]))},
                                    path.parents[1]))


def _write(tmp_path: Path, content) -> Path:
    target = tmp_path / "t" / "x.srt"
    target.parent.mkdir(parents=True, exist_ok=True)
    if isinstance(content, bytes):
        target.write_bytes(content)
    else:
        target.write_text(content, encoding="utf-8")
    return target


def _codes(entries):
    return [e["code"] for e in entries]


def test_good_srt_passes(tmp_path: Path):
    r = _run(_write(tmp_path, GOOD))
    assert r["status"] == "success"
    assert r["cues"] == 2
    assert r["errors"] == []
    assert r["warnings"] == []


def test_overlap_is_warning(tmp_path: Path):
    r = _run(_write(tmp_path, OVERLAP))
    assert r["status"] == "success"  # overlap is soft
    assert "overlap" in _codes(r["warnings"])


def test_out_of_order_is_error(tmp_path: Path):
    r = _run(_write(tmp_path, OUT_OF_ORDER))
    assert r["status"] == "error"
    assert "out_of_order" in _codes(r["errors"])


def test_end_before_start_is_error(tmp_path: Path):
    r = _run(_write(tmp_path, END_BEFORE_START))
    assert r["status"] == "error"
    assert "end_before_start" in _codes(r["errors"])


def test_not_utf8_is_error(tmp_path: Path):
    r = _run(_write(tmp_path, b"1\n00:00:00,000 --> 00:00:05,000\n\xe9\n"))
    assert r["status"] == "error"
    assert r["error"] == "not_utf8"


def test_utf8_bom_is_accepted_and_reported(tmp_path: Path):
    r = _run(_write(tmp_path, "\ufeff" + GOOD))
    assert r["status"] == "success"
    assert r["has_utf8_bom"] is True


def test_traversal_blocked(tmp_path: Path):
    # Absolute path that escapes data_root → refused.
    r = asyncio.run(validate_srt({"srt_path": "/etc/passwd"}, tmp_path))
    assert r["status"] == "error"
    assert r["error"] == "srt_path_outside_data_root"
