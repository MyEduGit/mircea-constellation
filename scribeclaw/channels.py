"""Channel-aware helpers for scribeclaw.

A "channel" is a content-publishing destination (e.g. JabbokRiverProductions)
described declaratively under `<repo>/channels/<slug>/`. The youtube_metadata
handler may opt-in to channel branding by passing `channel_slug` (and
optionally `series`) in its payload.

Configuration discovery:
  1. env CHANNELS_ROOT, if set
  2. <scribeclaw_pkg>/../channels/  (the in-repo location)

All loaders are pure functions — they read JSON, return dicts, and never
mutate global state. This preserves the deterministic evidence-hash
contract enforced by scribeclaw/main.py.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any


def channels_root() -> Path:
    env = os.getenv("CHANNELS_ROOT", "").strip()
    if env:
        return Path(env)
    # scribeclaw/channels.py → repo_root/channels
    return Path(__file__).resolve().parent.parent / "channels"


def load_channel(slug: str, root: Path | None = None) -> dict[str, Any] | None:
    base = (root or channels_root()) / slug / "channel.json"
    if not base.exists():
        return None
    return json.loads(base.read_text(encoding="utf-8"))


def load_series(slug: str, root: Path | None = None) -> dict[str, Any]:
    base = (root or channels_root()) / slug / "series.json"
    if not base.exists():
        return {}
    return json.loads(base.read_text(encoding="utf-8"))


def apply_channel(
    channel: dict[str, Any],
    series: dict[str, Any] | None,
    title_candidates: list[str],
    tags: list[str],
    explicit_footer: str | None,
) -> tuple[list[str], list[str], str | None]:
    """Return (titles, tags, footer) with channel + series overlays applied.

    - Title candidates: prepend the channel's `series_title_prefix` to the
      first candidate when a valid series is supplied. Other candidates
      are left untouched (operators may pick a different title).
    - Tags: append channel-level tags AND series tags, deduped while
      preserving the original frequency-derived order.
    - Footer: explicit payload footer wins; otherwise channel.footer.
    """
    new_titles = list(title_candidates)
    if series and new_titles:
        prefix = channel.get("series_title_prefix") or ""
        if isinstance(prefix, str) and prefix and not new_titles[0].startswith(prefix):
            new_titles[0] = f"{prefix}{new_titles[0]}"

    seen: set[str] = set()
    new_tags: list[str] = []
    for t in tags:
        key = t.lower()
        if key in seen:
            continue
        seen.add(key)
        new_tags.append(t)
    for t in list(channel.get("tags") or []) + list((series or {}).get("tags") or []):
        if not isinstance(t, str):
            continue
        key = t.lower()
        if key in seen:
            continue
        seen.add(key)
        new_tags.append(t)

    footer = explicit_footer
    if not footer:
        ch_footer = channel.get("footer")
        if isinstance(ch_footer, str) and ch_footer.strip():
            footer = ch_footer

    return new_titles, new_tags, footer
