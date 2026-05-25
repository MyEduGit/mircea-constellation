#!/usr/bin/env python3
"""
cognee_config.py — Cognee Configuration for NemoClaw Integration
Mircea's Constellation / UrantiOS governed — Truth, Beauty, Goodness

This file configures Cognee 1.0 for the iMac M4 controller node.
It supports two modes:
  1. LOCAL:  Ollama on iMac M4 (fully offline, private)
  2. REMOTE: Ollama on URANTiOS server (204.168.143.98)

Usage:
    import cognee_config
    cognee_config.init()              # auto-detects local vs remote Ollama
    cognee_config.init(mode="local")  # force local Ollama
    cognee_config.init(mode="remote") # force URANTiOS Ollama

After init(), use Cognee normally:
    await cognee.remember("data")
    await cognee.recall("query")
"""
import os

import cognee

# ── Defaults ────────────────────────────────────────────────────────────────

OLLAMA_LOCAL = "http://localhost:11434"
OLLAMA_REMOTE = "http://204.168.143.98:11434"
OLLAMA_MODEL = "ollama/qwen2.5:32b"

EMBEDDING_PROVIDER = "fastembed"
EMBEDDING_MODEL = "BAAI/bge-small-en-v1.5"
EMBEDDING_DIMENSIONS = 384

GRAPH_DB = "kuzu"
VECTOR_DB = "lancedb"

DATASET_URANTIA = "urantia_book"
DATASET_PHD = "phd_triune_monism"
DATASET_NEMOCLAW = "nemoclaw_memory"


def _check_ollama(endpoint: str, timeout: float = 2.0) -> bool:
    """Check if Ollama is reachable at the given endpoint."""
    import urllib.request
    try:
        req = urllib.request.Request(f"{endpoint}/api/tags", method="GET")
        with urllib.request.urlopen(req, timeout=timeout):
            return True
    except Exception:
        return False


def init(mode: str = "auto", verbose: bool = True):
    """
    Initialize Cognee for NemoClaw / iMac M4.

    Parameters
    ----------
    mode : str
        "local"  — use Ollama on localhost:11434
        "remote" — use Ollama on URANTiOS (204.168.143.98:11434)
        "auto"   — try local first, fall back to remote
    verbose : bool
        Print config summary when True.
    """
    # ── Resolve Ollama endpoint ─────────────────────────────────────
    endpoint = None

    if mode == "local":
        endpoint = OLLAMA_LOCAL
    elif mode == "remote":
        endpoint = OLLAMA_REMOTE
    elif mode == "auto":
        if _check_ollama(OLLAMA_LOCAL):
            endpoint = OLLAMA_LOCAL
            mode = "local"
        elif _check_ollama(OLLAMA_REMOTE):
            endpoint = OLLAMA_REMOTE
            mode = "remote"
        else:
            endpoint = OLLAMA_LOCAL
            mode = "local (offline — Ollama not detected)"

    # Allow env var override
    endpoint = os.environ.get("COGNEE_OLLAMA_ENDPOINT", endpoint)

    # ── LLM config ──────────────────────────────────────────────────
    model = os.environ.get("COGNEE_LLM_MODEL", OLLAMA_MODEL)
    cognee.config.set_llm_provider("ollama")
    cognee.config.set_llm_model(model)
    cognee.config.set_llm_endpoint(endpoint)
    cognee.config.set_llm_api_key("ollama")

    # ── Embedding config (local fastembed — no API key needed) ──────
    cognee.config.set_embedding_provider(EMBEDDING_PROVIDER)
    cognee.config.set_embedding_model(EMBEDDING_MODEL)
    cognee.config.set_embedding_dimensions(EMBEDDING_DIMENSIONS)

    # ── Storage paths ───────────────────────────────────────────────
    data_root = os.environ.get(
        "COGNEE_DATA_ROOT",
        os.path.expanduser("~/.cognee/data"),
    )
    cognee.config.data_root_directory(data_root)

    if verbose:
        print(f"Cognee {cognee.__version__} configured for NemoClaw")
        print(f"  Mode:      {mode}")
        print(f"  LLM:       {model} @ {endpoint}")
        print(f"  Embedding: {EMBEDDING_PROVIDER} / {EMBEDDING_MODEL}")
        print(f"  Data root: {data_root}")
        print()

    return {
        "mode": mode,
        "endpoint": endpoint,
        "model": model,
        "version": cognee.__version__,
    }


if __name__ == "__main__":
    info = init()
    print("Config test complete.")
    print(f"  Cognee version: {info['version']}")
    print(f"  Ollama mode:    {info['mode']}")
    print(f"  Endpoint:       {info['endpoint']}")
