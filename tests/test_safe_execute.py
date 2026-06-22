"""Tests for the safe_execute boundary — rejections are allowlisted."""
from __future__ import annotations

import asyncio
import types


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


def test_rejects_unlisted_handler():
    _stub_web_deps()
    from scribeclaw import main

    r = asyncio.run(main.safe_execute("definitely_not_a_handler", {}))
    assert r["status"] == "rejected"
    assert r["handler"] == "definitely_not_a_handler"
    assert "not in ScribeClaw allowlist" in r["error"]


def test_smoke_test_returns_success():
    _stub_web_deps()
    from scribeclaw import main

    r = asyncio.run(main.safe_execute("smoke_test", {}))
    assert r["status"] == "success"
    assert r["handler"] == "smoke_test"
    # _probe_runtime's keys must all be present regardless of the
    # sandbox's actual capabilities.
    for key in ("ffmpeg_on_path", "faster_whisper_installed",
                "httpx_installed", "assemblyai_key_set"):
        assert key in r, f"missing probe key: {key}"


def test_handler_crash_returns_structured_error():
    _stub_web_deps()
    from scribeclaw import main

    # Inject a deliberately-raising handler into the dispatch table for
    # one call. We restore it afterwards so the invariant stays intact.
    async def boom(payload):
        raise RuntimeError("intentional")

    original = main._HANDLERS["smoke_test"]
    main._HANDLERS["smoke_test"] = lambda p: boom(p)
    try:
        r = asyncio.run(main.safe_execute("smoke_test", {}))
    finally:
        main._HANDLERS["smoke_test"] = original

    assert r["status"] == "error"
    assert r["handler"] == "smoke_test"
    assert "intentional" in r["error"]
