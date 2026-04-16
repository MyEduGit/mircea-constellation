"""Tests for scribeclaw.session_status."""
from __future__ import annotations

import asyncio
import types
from pathlib import Path


def _stub_web_deps():
    import sys
    if "fastapi" not in sys.modules:
        fa = types.ModuleType("fastapi")
        fa.Body = lambda *a, **k: None

        class FA:
            def __init__(self, **kw):
                pass

            def get(self, *a, **k):
                return lambda fn: fn

            def post(self, *a, **k):
                return lambda fn: fn

        fa.FastAPI = FA
        sys.modules["fastapi"] = fa
    if "uvicorn" not in sys.modules:
        uv = types.ModuleType("uvicorn")
        uv.run = lambda *a, **k: None
        sys.modules["uvicorn"] = uv


def _seed_stem(root: Path, stem: str, stages: dict[str, bool]):
    t = root / "transcripts" / stem
    y = root / "youtube" / stem
    t.mkdir(parents=True, exist_ok=True)
    y.mkdir(parents=True, exist_ok=True)
    if stages.get("segments"):
        (t / "segments.json").write_text("{}")
    if stages.get("cleaned"):
        (t / "segments.clean.json").write_text("{}")
    if stages.get("cues"):
        (t / "cues.json").write_text("{}")
    if stages.get("bundle"):
        (y / "bundle.json").write_text("{}")
    if stages.get("thumbnail"):
        (y / "thumbnail.jpg").write_bytes(b"\xff\xd8\xff")
    if stages.get("uploaded"):
        (y / "upload.result.json").write_text("{}")


def test_empty_data_root(tmp_path: Path):
    _stub_web_deps()
    from scribeclaw.session_status import session_status

    r = asyncio.run(session_status({}, tmp_path))
    assert r["status"] == "success"
    assert r["stems_total"] == 0
    assert r["stems_uploaded"] == 0
    # next_actions should include the 6 readiness items (all missing).
    assert len(r["next_actions"]) >= 1


def test_half_done_stem(tmp_path: Path):
    _stub_web_deps()
    from scribeclaw.session_status import session_status

    _seed_stem(tmp_path, "c0069", {"segments": True, "cleaned": True})
    r = asyncio.run(session_status({}, tmp_path))
    assert r["stems_total"] == 1
    assert r["stems_uploaded"] == 0
    # Per-stem advice should mention the first missing stage (cues).
    actions_blob = "\n".join(r["next_actions"])
    assert "c0069" in actions_blob


def test_fully_processed_stem_counts_as_uploaded(tmp_path: Path):
    _stub_web_deps()
    from scribeclaw.session_status import session_status

    _seed_stem(tmp_path, "done", {
        "segments": True, "cleaned": True, "cues": True,
        "bundle": True, "thumbnail": True, "uploaded": True,
    })
    r = asyncio.run(session_status({}, tmp_path))
    assert r["stems_total"] == 1
    assert r["stems_uploaded"] == 1


def test_markdown_file_written(tmp_path: Path):
    _stub_web_deps()
    from scribeclaw.session_status import session_status

    _seed_stem(tmp_path, "x", {"segments": True})
    r = asyncio.run(session_status({}, tmp_path))
    md = Path(r["outputs"][0])
    js = Path(r["outputs"][1])
    assert md.exists()
    assert js.exists()
    assert md.suffix == ".md"
    assert js.suffix == ".json"
    body = md.read_text(encoding="utf-8")
    assert "Session Status" in body
    assert "Operator readiness" in body
    assert "Pipeline progress" in body
