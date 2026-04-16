"""The core invariant: dispatch table and allowlist stay in lockstep.

main.py already asserts this at module-import time, but having it as an
explicit test means regressions show up in CI with a readable failure
instead of a traceback at first-use."""
from __future__ import annotations

import types


def _stub_web_deps():
    """Provide minimal stubs for fastapi / uvicorn so scribeclaw.main
    can be imported without needing the actual packages installed on
    the CI runner's minimal image."""
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


def test_dispatch_matches_allowlist():
    _stub_web_deps()
    from scribeclaw import main

    assert set(main._HANDLERS) == set(main.ALLOWED_HANDLERS), (
        "allowlist / dispatch divergence\n"
        f"  handlers={sorted(main._HANDLERS)}\n"
        f"  allowed ={sorted(main.ALLOWED_HANDLERS)}"
    )


def test_allowlist_contains_smoke_test():
    _stub_web_deps()
    from scribeclaw import main

    assert "smoke_test" in main.ALLOWED_HANDLERS
