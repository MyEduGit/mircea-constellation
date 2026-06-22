"""Unit tests for scribeclaw.youtube pure helpers."""
from __future__ import annotations

from scribeclaw.youtube import (
    _build_chapters,
    _build_tags,
    _title_candidates,
    _ts_chapter,
)


def test_ts_chapter_no_hours():
    assert _ts_chapter(65.0) == "1:05"
    assert _ts_chapter(5.5) == "0:05"


def test_ts_chapter_with_hours():
    assert _ts_chapter(3723.0) == "1:02:03"


def test_title_candidates_basic():
    txt = "Primul gând. Al doilea gând. Un al treilea."
    cands = _title_candidates(txt)
    assert cands[0] == "Primul gând"
    assert len(cands) <= 3


def test_title_candidates_truncation():
    long = "A" * 200 + "."
    cands = _title_candidates(long, limit=50)
    assert len(cands[0]) <= 50


def test_title_candidates_fallback_when_empty():
    assert _title_candidates("") == ["Video"]


def test_build_tags_skips_stopwords_and_dedupes():
    txt = ("Dumnezeu este iubire. Dumnezeu este iubire. Mântuitorul "
           "este viața noastră.")
    tags = _build_tags(txt, extra_stop=set(), top_n=5)
    # 'este' and 'noastra' (stop-like) shouldn't appear, words >= 3 chars
    assert "este" not in tags
    assert "dumnezeu" in tags


def test_build_tags_respects_extra_stopwords():
    txt = "apple apple apple banana cherry"
    tags = _build_tags(txt, extra_stop={"apple"}, top_n=3)
    assert "apple" not in tags
    assert "banana" in tags


def test_build_chapters_floor_of_three():
    # Single segment -> no chapters generated.
    segs = [{"start": 0.0, "end": 60.0, "text": "Hello."}]
    assert _build_chapters(segs, min_gap_sec=30) == []


def test_build_chapters_first_zero_prepended():
    segs = [
        {"start": 30.0, "end": 60.0, "text": "A sentence here."},
        {"start": 100.0, "end": 130.0, "text": "Another sentence."},
        {"start": 200.0, "end": 230.0, "text": "Third sentence."},
    ]
    chs = _build_chapters(segs, min_gap_sec=30)
    assert len(chs) >= 3
    assert chs[0]["start"] == 0.0
    assert chs[0]["title"] == "Introducere"
