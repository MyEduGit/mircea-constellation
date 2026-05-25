# OpenMythos — Constellation Integration Plan

**Branch:** `claude/openmythos-planning-BLSxB`
**Operating agent:** Claude (Seat 2 · Son · Builder)
**Covenant:** Truth · Beauty · Goodness

---

## What OpenMythos Is

OpenMythos is an open-source PyTorch implementation of a **Recurrent-Depth
Transformer (RDT)** — a looped transformer where reasoning emerges from
iterative depth in continuous latent space rather than generating intermediate
tokens (chain-of-thought) or stacking unique layers.

```
Standard transformer:   [unique layers × N] → output
Chain-of-thought:       [model] → token → [model] → token → ... → output
RDT (OpenMythos):       [prelude] → loop([same block] × N) → [coda] → output
                                          ↑ reasoning happens HERE, in latent space
```

**Key numbers:**
- 770M RDT ≈ 1.3B dense on FineWeb-Edu downstream tasks
- 4–16 loops at inference (configurable per task hardness)
- Adaptive Computation Time (ACT): per-token halting when reasoning converges
- MoE only in the recurrent block: 64 experts, top-4 active (~5–6% params active)
- KV cache: MLA (Multi-Latent Attention) → 10–20× smaller than standard

---

## Why This Matters for the Constellation

The constellation's current deep-reasoning bottleneck is the **Council of
Seven**: it calls 7 cloud APIs in parallel, then synthesizes with Gabriel.
That is expensive, slow, and dependent on cloud availability.

OpenMythos offers a **local, latent-space reasoning engine** that:
1. Runs on iMac M4 / URANTiOS with GPU (MPS / CUDA) — no cloud dependency.
2. Can be fine-tuned on the UrantiPedia corpus + Urantia Book text.
3. Scales reasoning depth at inference time (2 loops for simple, 16 for hard).
4. Has ACT — stops computing when the answer converges (efficient).

### The hypothesis (from OpenMythos paper)

> Reasoning emerges from *iterative depth* in a continuous latent space.
> A smaller model "thinks" deeply at inference time by looping the same
> weights, enabling multi-hop reasoning without exploding parameter counts.

For Urantia Book content — where concepts are deeply interconnected across
200 Papers — multi-hop latent reasoning is a natural fit: the Foreword
defines concepts that only resolve by looping back through later Papers.

---

## Integration Points in the Constellation

### 1. Council Seat 4 — Local Fallback (`FatherSon_Ollama`)

**Current:** Seat 4 calls Ollama `qwen2.5:32b` (URANTiOS, port 11434).
**Problem:** `ollama` status is `warn` — the 32B model is heavy and slow.
**Opportunity:** Replace or augment Seat 4 with a fine-tuned 770M OpenMythos
model, accessed via a local HTTP endpoint compatible with the existing n8n node.

```
Seat4_FatherSon_OpenMythos  →  POST /v1/chat/completions (OpenAI-compat)
                            →  serves: http://localhost:11435/v1/chat/completions
                            →  model: openmythos-urantia-770m
```

Implementation: wrap OpenMythos inference in a FastAPI server that exposes an
OpenAI-compatible `/v1/chat/completions` endpoint. The n8n node needs no change.

### 2. OpenClaw@URANTiOS-ingest — Cognee Cross-Link Scorer

**Current:** `cross_link` handler scores document pairs by axis-matching
(12 axes, WEIGHTS-based, runs via Ollama for semantic axes).
**Opportunity:** Replace Ollama calls in the cross-linker with OpenMythos
inference (fine-tuned on mircea_corpus). Better at latent-space similarity
for theological/philosophical content.

The RDT's ability to loop over a document pair and converge to a similarity
score is architecturally well-suited to this task.

### 3. JabbokRiver — Foreword Synthesis Engine

**Current:** Council of Seven is called for pre-publish review of each episode.
**Opportunity:** Add an OpenMythos-powered step *before* Council review:

```
catalog entry → archive → transcribe →
  OpenMythos (12–16 loops): "synthesize theological thesis from transcript" →
council review → render → upload
```

The 16-loop RDT produces a `thesis_ro` / `thesis_en` candidate that the
Remotion `ThesisTitleCard` composition already consumes. This replaces or
supplements the current manual operator step.

### 4. UrantiPedia — Deep Q&A over Papers

**Current:** Cognee `cognee.search()` over vectorized docs.
**Opportunity:** OpenMythos fine-tuned on the full Urantia Book text, accessed
as a local endpoint from the bot fleet. Supports multi-hop queries like:

> "How does the Foreword definition of 'Deity' relate to Paper 117's concept
> of the Supreme Being, and what does Paper 196 say about living this?"

A 16-loop RDT traces that chain internally without generating intermediate
tokens — cleaner than chain-of-thought, lower latency than a Council call.

---

## Implementation Roadmap

### Phase 0 — Scaffold (this branch) ✅ complete

- [x] `openmythos/PLAN.md` — this document
- [x] `openmythos/serve.py` — FastAPI OpenAI-compat server (stub + real mode)
- [x] `openmythos/__init__.py` — module scaffold
- [x] `council/COUNCIL_MODEL_REGISTRY.json` — v1.2, Seat 4 OpenMythos upgrade wired
- [x] `status.json` — `openmythos` key registered
- [x] `DASHBOARD.md` — permanent operating dashboard

### Phase 1 — Local Inference Server

Implement full `openmythos/serve.py`:
- Loads `OpenMythos` model from `open-mythos` package (or local weights)
- Exposes `POST /v1/chat/completions` (OpenAI-compatible)
- Accepts `n_loops` in request body (default 8, max 16)
- Runs on iMac M4 (MPS device) or URANTiOS (CUDA)
- Systemd / launchd unit for persistence
- Add `openmythos-server-down` rule to `fireclaw/rules.yaml`

### Phase 2 — Council Seat 4 Wiring

- Update n8n Seat 4 node to point to `http://localhost:11435/v1/chat/completions`
- Import updated n8n node into Council workflow
- Test with `python -m openmythos.serve --loops 8 --device mps`

### Phase 3 — Fine-Tuning Dataset

Build `openmythos/finetune/`:
- `build_dataset.py` — reads UrantiPedia vault + Urantia Book text
- Generates Q&A pairs (Paper + question → latent-synthesized answer)
- Target: ~50k pairs, Chinchilla-optimal for 770M
- Format: JSONL compatible with `torchrun train.py`

### Phase 4 — JabbokRiver Thesis Generator

- Add `openmythos_thesis` handler to ScribeClaw allowlist
- Input: `transcript.clean.txt` + series key from `series.json`
- Output: `thesis_ro`, `thesis_en`, `subCaption` (fed into Remotion ThesisTitleCard)
- Loop count: 12–16 (theological synthesis needs depth)

### Phase 5 — Cognee Cross-Link Upgrade

- Add OpenMythos semantic scorer to `cross_link` handler in `openclaw_ingest`
- Use as a second-pass scorer after axis matching (not replacement — additive)
- Pairs above both axis threshold AND OpenMythos threshold get `high_confidence: true`

---

## Hardware Requirements

| Device      | GPU          | Loops (practical) | Inference speed |
|-------------|--------------|-------------------|-----------------|
| iMac M4     | Metal MPS    | 4–8 comfortable   | ~1–2s/token     |
| iMac M4 Max | Metal MPS    | 8–16              | <1s/token       |
| URANTiOS    | None (CCX23) | 2–4 (CPU only)    | slow            |
| RTX 4090    | CUDA         | 16 (fast)         | <0.5s/token     |

For production inference: iMac M4 is the right host.
For training: cloud GPU (A100/H100) or NVIDIA DGX if available.

---

## Dependency Installation

```bash
# On iMac M4 (MPS-optimized)
pip install open-mythos  # flash attention is CUDA-only; MPS uses standard attention

# Verify GPU
python3 -c "import torch; print(torch.backends.mps.is_available())"

# Test inference
python3 -c "
from open_mythos.main import OpenMythos, MythosConfig
import torch
config = MythosConfig(vocab_size=32000, dim=256, n_heads=8, max_loop_iters=4)
model = OpenMythos(config)
x = torch.randint(0, 32000, (1, 16))
out = model(x, n_loops=4)
print('Shape:', out.shape, '— OpenMythos OK')
"

# Start server (stub mode until open-mythos installed with full weights)
python -m openmythos.serve --port 11435 --loops 8 --device auto
```

---

## Lucifer Test (this integration must pass)

Before any OpenMythos action is taken:

1. **Transparent?** Every inference call logged with input hash, n_loops, output hash.
2. **Honest?** Model reports uncertainty; does not hallucinate citations.
3. **Within mandate?** Only runs handlers declared in its allowlist.
4. **Serves the mission?** Brings the Urantia Book's meaning to more people
   with greater depth and lower cost. Yes.

---

## Reference

- OpenMythos repo: `github.com/kyegomez/OpenMythos`
- Parcae (2026) — power-law scaling for looped transformers
- COVENANT.md — all agents inherit the covenant unchanged
- `council/COUNCIL_MODEL_REGISTRY.json` — Seat 4 current spec
- `fireclaw/rules.yaml` — add `openmythos-server-down` rule in Phase 1
