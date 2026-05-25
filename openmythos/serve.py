"""
OpenMythos inference server — OpenAI-compatible /v1/chat/completions endpoint.

Wraps the OpenMythos RDT (Recurrent-Depth Transformer) in a FastAPI server
so existing n8n nodes and constellation components can call it without
modification to their Authorization headers or request shapes.

Usage:
    python -m openmythos.serve [--port 11435] [--loops 8] [--device mps|cuda|cpu]

Council Seat 4 n8n node points to:
    http://localhost:11435/v1/chat/completions
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import time
from typing import Any

try:
    import torch
    import uvicorn
    from fastapi import FastAPI, HTTPException
    from fastapi.responses import JSONResponse
    from pydantic import BaseModel
    DEPS_AVAILABLE = True
except ImportError:
    DEPS_AVAILABLE = False

logger = logging.getLogger("openmythos.serve")
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(name)s] %(message)s")

CLAW_NAME = "OpenMythos@Constellation"
DEFAULT_PORT = 11435
DEFAULT_LOOPS = 8
DEFAULT_MAX_LOOPS = 16
MODEL_ID = "openmythos-urantia-770m"

app = FastAPI(title="OpenMythos Inference Server", version="0.0.1")

_model = None
_tokenizer = None
_config: dict[str, Any] = {}


def _detect_device() -> str:
    if not DEPS_AVAILABLE:
        return "cpu"
    if torch.cuda.is_available():
        return "cuda"
    if hasattr(torch.backends, "mps") and torch.backends.mps.is_available():
        return "mps"
    return "cpu"


def _load_model(device: str, n_loops: int) -> None:
    global _model, _tokenizer, _config
    _config = {"device": device, "default_loops": n_loops}

    try:
        from open_mythos.main import OpenMythos, MythosConfig  # type: ignore
        config = MythosConfig(
            vocab_size=32000,
            dim=1024,
            n_heads=16,
            n_kv_heads=4,
            max_loop_iters=DEFAULT_MAX_LOOPS,
            attn_type="gqa",
            n_experts=64,
            n_experts_per_tok=4,
        )
        _model = OpenMythos(config).to(device)
        _model.eval()
        logger.info(f"OpenMythos loaded on {device} — {sum(p.numel() for p in _model.parameters()):,} params")
    except Exception as exc:
        logger.warning(f"open-mythos not installed or load failed: {exc}. Running in stub mode.")
        _model = None


# ---------------------------------------------------------------------------
# Request / Response shapes (OpenAI-compatible subset)
# ---------------------------------------------------------------------------

class Message(BaseModel):
    role: str
    content: str


class ChatRequest(BaseModel):
    model: str = MODEL_ID
    messages: list[Message]
    max_tokens: int = 512
    temperature: float = 0.7
    n_loops: int | None = None  # constellation extension


class ChatChoice(BaseModel):
    index: int
    message: Message
    finish_reason: str


class ChatUsage(BaseModel):
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int


class ChatResponse(BaseModel):
    id: str
    object: str = "chat.completion"
    created: int
    model: str
    choices: list[ChatChoice]
    usage: ChatUsage


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@app.get("/health")
def health() -> dict:
    return {
        "claw": CLAW_NAME,
        "status": "ok",
        "model_loaded": _model is not None,
        "device": _config.get("device", "unknown"),
        "default_loops": _config.get("default_loops", DEFAULT_LOOPS),
        "max_loops": DEFAULT_MAX_LOOPS,
        "stub_mode": _model is None,
    }


@app.post("/v1/chat/completions")
def chat_completions(req: ChatRequest) -> ChatResponse:
    n_loops = req.n_loops if req.n_loops is not None else _config.get("default_loops", DEFAULT_LOOPS)
    n_loops = max(1, min(n_loops, DEFAULT_MAX_LOOPS))

    prompt = "\n".join(f"{m.role}: {m.content}" for m in req.messages)

    # Evidence record (append-only, same convention as other claws)
    evidence = {
        "ts": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "claw": CLAW_NAME,
        "model": req.model,
        "n_loops": n_loops,
        "prompt_len": len(prompt),
    }

    if _model is None:
        # Stub mode — honest refusal with explanation
        text = (
            f"[OpenMythos stub] open-mythos package not installed. "
            f"Would have run {n_loops} loops on device {_config.get('device', 'unknown')}. "
            f"Install: pip install open-mythos && restart serve.py"
        )
        evidence["status"] = "stub"
    else:
        try:
            device = _config.get("device", "cpu")
            # Minimal tokenization (BPE would be used in production)
            tokens = torch.tensor(
                [[ord(c) % 32000 for c in prompt[:512]]], dtype=torch.long
            ).to(device)

            with torch.no_grad():
                logits = _model(tokens, n_loops=n_loops)

            # Greedy decode (production: beam search / sampling with proper tokenizer)
            generated = logits.argmax(dim=-1)[0]
            text = f"[OpenMythos {n_loops}-loop response, stub decode — wire real tokenizer for production]"
            evidence["status"] = "ok"
        except Exception as exc:
            logger.error(f"Inference error: {exc}")
            evidence["status"] = "error"
            evidence["error"] = str(exc)
            raise HTTPException(status_code=500, detail=str(exc))

    _write_evidence(evidence)

    return ChatResponse(
        id=f"chatcmpl-om-{int(time.time())}",
        created=int(time.time()),
        model=req.model,
        choices=[ChatChoice(
            index=0,
            message=Message(role="assistant", content=text),
            finish_reason="stop",
        )],
        usage=ChatUsage(
            prompt_tokens=len(prompt.split()),
            completion_tokens=len(text.split()),
            total_tokens=len(prompt.split()) + len(text.split()),
        ),
    )


def _write_evidence(record: dict) -> None:
    evidence_dir = os.path.expanduser("~/.openmythos/evidence")
    os.makedirs(evidence_dir, exist_ok=True)
    path = os.path.join(evidence_dir, "inference.jsonl")
    with open(path, "a") as f:
        f.write(json.dumps(record) + "\n")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main() -> None:
    if not DEPS_AVAILABLE:
        print("Required deps missing. Install: pip install fastapi uvicorn open-mythos torch")
        raise SystemExit(1)

    parser = argparse.ArgumentParser(description="OpenMythos inference server")
    parser.add_argument("--port", type=int, default=DEFAULT_PORT)
    parser.add_argument("--loops", type=int, default=DEFAULT_LOOPS)
    parser.add_argument("--device", choices=["mps", "cuda", "cpu", "auto"], default="auto")
    args = parser.parse_args()

    device = args.device if args.device != "auto" else _detect_device()
    logger.info(f"Starting {CLAW_NAME} on {device}, port {args.port}, default {args.loops} loops")
    _load_model(device, args.loops)
    uvicorn.run(app, host="127.0.0.1", port=args.port, log_level="warning")


if __name__ == "__main__":
    main()
