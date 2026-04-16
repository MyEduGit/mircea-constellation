"""Shared pytest configuration for the scribeclaw test suite.

Keeps the Python path pointed at the repo root so `from scribeclaw...`
works regardless of how pytest is invoked (via CI, from tests/, or from
the repo root).
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

# scribeclaw.main touches DATA_ROOT at import time. Redirect it to a
# temp dir for the whole test session so we never pollute the host.
os.environ.setdefault("DATA_ROOT", "/tmp/scribeclaw-pytest")
Path(os.environ["DATA_ROOT"]).mkdir(parents=True, exist_ok=True)
