# Mircea Constellation — Architecture

**UrantiOS governed — Truth, Beauty, Goodness.**

This repository hosts a set of cooperating services — "the
constellation" — each with a single canonical role. Every service
follows the same shape (allowlisted handlers, evidence records on every
call, local-only HTTP surface, Docker-compose deployment) so a new
module can be added without changing the rest.

---

## Canonical sentence

> NemoClaw sees. VisualUrantiClaw explains. Fireclaw reacts to
> technical faults. LuciferiClaw adjudicates intent and mandate
> violation. **OpenClaw instances execute.** Paperclip preserves the
> evidence.

Each word is a role, not a wish — when two services appear to overlap,
the canonical sentence settles jurisdiction. If a module does more than
one of these things, it's doing one thing wrong.

---

## Modules on `main`

| Module              | Role (singular)                            | Status                                        |
|---------------------|--------------------------------------------|-----------------------------------------------|
| `fireclaw/`         | Remediate technical faults                 | Ships: rules.yaml → actions; 5 real handlers  |
| `lucifericlaw/`     | Adjudicate intent & mandate violations     | Ships: trial / sentencing / scripture engine  |
| `openclaw_ingest/`  | Controlled execution (ingest sub-role)     | Scaffold + one real handler (`ingest_normalize`); 4 stubs |
| `scribeclaw/`       | Controlled execution (media sub-role)      | Scaffold + AssemblyAI; see `scribeclaw/README.md` |

`cognee_config.py` at repo root is a shared library (Ollama/Cognee
config) — not a service, not governed by the canonical sentence, just
a single source of truth the execution services import.

> ⚠️ **`NemoClaw` / `VisualUrantiClaw` / `Paperclip`** are named in the
> canonical sentence but do not yet live in this repo. When they ship,
> update this table first — the sentence is the contract.

---

## Shared conventions

These hold across every module. If you're adding a fifth claw, match
them exactly.

### 1. Allowlisted handlers

Every service exposes a `POST /tasks` endpoint whose body is a handler
name plus a payload dict:

```json
{ "handler": "smoke_test", "payload": {} }
```

The handler name is checked against a `frozenset` allowlist. Anything
outside the set is **rejected** with an evidence record — no free-form
shell, no `--command` escape. The dispatch table and the allowlist are
held in lockstep by an `assert`:

```python
assert set(_HANDLERS) == set(ALLOWED_HANDLERS), \
    "dispatch table must match ALLOWED_HANDLERS exactly"
```

This is the canonical boundary. Any PR that adds a handler touches both
sides or it crashes at import time.

### 2. Evidence records on every call

Every handler invocation (success, failure, rejection) emits a JSON
record to `{DATA_ROOT}/evidence/evidence_<ms_epoch>_<handler>.json`:

```json
{
  "claw": "...",
  "version": "...",
  "handler": "...",
  "payload_sha256": "…canonical json hash…",
  "result_sha256": "…canonical json hash…",
  "ts_epoch": 1234567890.12,
  "ts_iso":   "2026-04-16T…",
  "urantios_governed": true
}
```

The hashes are canonicalised JSON so the same inputs always produce the
same record. This module emits evidence; **Paperclip** (not yet
shipped) will own the bundling/preservation contract once it lands.

### 3. Local-only HTTP surface

Services bind to `0.0.0.0` inside the container but publish only to
`127.0.0.1` on the host via Docker's port mapping
(`"127.0.0.1:<port>:<port>"`). Nothing is externally reachable by
default.

Port assignments:

| Module              | Host port              |
|---------------------|------------------------|
| openclaw_ingest     | `127.0.0.1:8080`       |
| scribeclaw          | `127.0.0.1:8081`       |

New services claim the next free port and document it here before
merging.

### 4. One-command install

Every module ships:

- `<module>/Dockerfile`
- `<module>/docker-compose.yml`
- `setup/<module>_install.sh` — idempotent, discovers UID/GID, writes
  a mode-600 `.env`, brings the stack up.

The installer never runs as root and never `curl | sh`es anything.
Host data dirs live under `/opt/<module>-data/` and are owned by the
invoking user.

### 5. Honest failure modes

- A handler that can't run **refuses** with a structured error object
  (e.g. `{"status": "error", "error": "ffmpeg_not_on_path", "hint": ...}`).
- A handler that is a stub returns `{"status": "not_implemented"}` —
  never silent success.
- A rejected (unlisted) handler returns `{"status": "rejected"}` plus
  an evidence record stamped the same way.
- Probes (`/health`, `smoke_test`) report capabilities truthfully
  (`ffmpeg_on_path: false`, `cognee_ready: false`, …) rather than
  hiding them behind a green light.

The rule: **silent success is worse than loud failure**.

---

## Data flow across the constellation

```text
  Operator → POST /tasks ─┐
                          ▼
                   scribeclaw      media pipeline
                          ▼
                   openclaw_ingest Cognee (LanceDB + Kuzu)
                          │
          ┌───────────────┼──────────────────┐
          ▼               ▼                  ▼
     fireclaw        lucifericlaw        (Paperclip)
     reacts to       adjudicates         preserves
     technical       intent/mandate      evidence
     faults          violations          bundles
                                         (not shipped)
```

Arrows are logical, not network. Each service owns its own evidence
directory; a future Paperclip will cross-reference them.

---

## Adding a new module

1. **Name it.** The suffix is `…claw` when it executes, `…ingest` /
   `…bundler` / etc. when its role is distinct. The module name must
   make its role obvious from the canonical sentence.
2. **Stub it with the real shape.** `__init__.py`, `main.py`,
   `Dockerfile`, `docker-compose.yml`, `setup/<name>_install.sh`,
   `README.md`. Mirror an existing module — divergence costs more than
   it saves.
3. **Pick one real handler.** Don't ship five stubs and call it a
   platform. Ship one handler that actually does the work; stub the
   rest honestly (`status: not_implemented`).
4. **Wire the allowlist invariant.** The `assert set(_HANDLERS) ==
   set(ALLOWED_HANDLERS)` line is non-negotiable.
5. **Add the README entry.** Every claim in the README must be
   verifiable by reading the code or running the module. No aspirational
   tense.
6. **Update `ARCHITECTURE.md`** (this file) — port, role, canonical
   sentence alignment.

UrantiOS governed — Truth, Beauty, Goodness.
