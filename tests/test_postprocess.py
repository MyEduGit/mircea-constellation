"""Unit tests for scribeclaw.postprocess — deterministic RO diacritics
normaliser and punctuation spacer."""
from __future__ import annotations

from scribeclaw.postprocess import _fix_text


def test_cedilla_lowercase_to_comma_below():
    # ş U+015F → ș U+0219  |  ţ U+0163 → ț U+021B
    assert _fix_text("acesta fiinţa puţinuluI sfaturi ști") == "acesta ființa puținuluI sfaturi ști"


def test_cedilla_uppercase_to_comma_below():
    assert _fix_text("ŞCOALA ŢĂRII") == "ȘCOALA ȚĂRII"


def test_double_space_collapsed():
    assert _fix_text("foo    bar") == "foo bar"


def test_space_before_punct_removed():
    assert _fix_text("foo , bar ; baz !") == "foo, bar; baz!"


def test_trimmed():
    assert _fix_text("   hi   ") == "hi"


def test_mixed():
    src = "Astăzi  ,  ŞI voi fi fericit ."
    assert _fix_text(src) == "Astăzi, ȘI voi fi fericit."
