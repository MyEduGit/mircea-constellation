"""Channel-overlay tests for scribeclaw.youtube_metadata.

Two contracts:
  1. Without channel_slug, behavior is bit-identical to the pre-channel
     implementation (preserves the deterministic evidence-hash contract
     enforced by scribeclaw/main.py).
  2. With channel_slug + series, the channel footer is appended, the
     channel/series tags are deduped onto the auto-derived tag list, and
     the first title candidate is prefixed with series_title_prefix.

Run from the repo root:
  python -m scribeclaw.tests.test_channels
"""
from __future__ import annotations

import asyncio
import json
import os
import sys
import tempfile
from pathlib import Path

# Allow `python -m scribeclaw.tests.test_channels` from the repo root.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from scribeclaw.youtube import youtube_metadata  # noqa: E402


_FAKE_SEGMENTS = {
    "language": "ro",
    "segments": [
        {"start": 0.0,   "end": 3.5,  "text": "Bună seara, frați și surori."},
        {"start": 3.5,   "end": 9.0,  "text": "Astăzi vorbim despre religia lui Isus."},
        {"start": 9.0,   "end": 18.0, "text": "Religia lui Isus nu este religia despre Isus."},
        {"start": 65.0,  "end": 72.0, "text": "Tatăl ne cheamă să facem voia Lui."},
        {"start": 130.0, "end": 138.0,"text": "Credința lui Isus transformă inimile."},
    ],
}


def _seed_data_root(data_root: Path, stem: str) -> None:
    d = data_root / "transcripts" / stem
    d.mkdir(parents=True, exist_ok=True)
    (d / "segments.clean.json").write_text(
        json.dumps(_FAKE_SEGMENTS, ensure_ascii=False), encoding="utf-8"
    )


def _seed_channels_root(channels_root: Path) -> None:
    ch = channels_root / "jabbokriver"
    ch.mkdir(parents=True, exist_ok=True)
    (ch / "channel.json").write_text(json.dumps({
        "slug": "jabbokriver",
        "footer": "JabbokRiver Productions · Religia LUI Isus, nu religia DESPRE Isus.",
        "tags": ["JabbokRiver", "religia lui Isus", "Emanoil Geaboc"],
        "series_title_prefix": "JabbokRiver — ",
    }), encoding="utf-8")
    (ch / "series.json").write_text(json.dumps({
        "religia-lui-vs-religia-despre-isus": {
            "tags": ["Paper 196", "credinta lui Isus"],
        },
    }), encoding="utf-8")


def test_no_channel_slug_preserves_legacy_shape(data_root: Path) -> None:
    """Footer absent unless explicitly provided; tags purely auto-derived."""
    _seed_data_root(data_root, "no-channel")
    result = asyncio.run(youtube_metadata({"stem": "no-channel"}, data_root))
    assert result["status"] == "success", result
    desc = (data_root / "youtube" / "no-channel" / "description.txt").read_text(encoding="utf-8")
    assert not desc.endswith("JabbokRiver Productions · Religia LUI Isus, nu religia DESPRE Isus."), \
        "no-channel-slug must NOT auto-attach channel footer"
    titles = result["title_candidates"]
    assert all(not t.startswith("JabbokRiver — ") for t in titles), \
        "no-channel-slug must NOT prefix titles"
    print("OK  no_channel_slug_preserves_legacy_shape")


def test_explicit_channel_footer_still_works(data_root: Path) -> None:
    """The pre-existing channel_footer parameter must still be honored."""
    _seed_data_root(data_root, "explicit-footer")
    result = asyncio.run(youtube_metadata(
        {"stem": "explicit-footer", "channel_footer": "Custom footer XYZ"},
        data_root,
    ))
    assert result["status"] == "success", result
    desc = (data_root / "youtube" / "explicit-footer" / "description.txt").read_text(encoding="utf-8")
    assert desc.endswith("Custom footer XYZ"), desc[-200:]
    print("OK  explicit_channel_footer_still_works")


def test_channel_slug_applies_overlay(data_root: Path, channels_root: Path) -> None:
    """channel_slug + series → footer attached, tags deduped, title prefixed."""
    _seed_data_root(data_root, "with-channel")
    os.environ["CHANNELS_ROOT"] = str(channels_root)
    try:
        result = asyncio.run(youtube_metadata({
            "stem": "with-channel",
            "channel_slug": "jabbokriver",
            "series": "religia-lui-vs-religia-despre-isus",
        }, data_root))
    finally:
        os.environ.pop("CHANNELS_ROOT", None)

    assert result["status"] == "success", result
    desc = (data_root / "youtube" / "with-channel" / "description.txt").read_text(encoding="utf-8")
    assert desc.endswith("JabbokRiver Productions · Religia LUI Isus, nu religia DESPRE Isus."), \
        f"footer missing; tail={desc[-200:]!r}"

    tags_lower = {t.lower() for t in result["tags"]}
    # tags returned by handler are top-10 — channel/series tags may or may
    # not appear in the top-10 sample. Re-read the persisted full tag list.
    bundle = json.loads((data_root / "youtube" / "with-channel" / "bundle.json").read_text(encoding="utf-8"))
    full_tags_lower = {t.lower() for t in bundle["tags"]}
    for required in ("jabbokriver", "religia lui isus", "emanoil geaboc", "paper 196"):
        assert required in full_tags_lower, f"missing channel/series tag: {required!r} (got {full_tags_lower})"

    assert bundle["title_candidates"][0].startswith("JabbokRiver — "), \
        f"title prefix missing; got {bundle['title_candidates'][0]!r}"

    # Dedup invariant: no tag appears twice (case-insensitive).
    seen: set[str] = set()
    for t in bundle["tags"]:
        k = t.lower()
        assert k not in seen, f"duplicate tag {t!r}"
        seen.add(k)

    print("OK  channel_slug_applies_overlay")


def main() -> int:
    with tempfile.TemporaryDirectory() as data_dir, tempfile.TemporaryDirectory() as channels_dir:
        data_root = Path(data_dir)
        channels_root = Path(channels_dir)
        _seed_channels_root(channels_root)
        test_no_channel_slug_preserves_legacy_shape(data_root)
        test_explicit_channel_footer_still_works(data_root)
        test_channel_slug_applies_overlay(data_root, channels_root)
    print("\nAll channel tests passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
