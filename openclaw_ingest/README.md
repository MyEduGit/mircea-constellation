# OpenClaw@URANTiOS-ingest

**Truthful label:** deployable scaffold with first real handler (`ingest_normalize`).
Four of the five canonical handlers are declared but stubbed pending follow-up PR.

Singular primary role: **controlled execution** (ingestion sub-role).
Does not observe, remediate, adjudicate, explain, or bundle evidence — those
belong to NemoClaw / Fireclaw / LuciferiClaw / VisualUrantiClaw / Paperclip
respectively. This module emits evidence *records* on every handler call, but
the binding contract belongs to Paperclip once it ships.

UrantiOS governed — Truth, Beauty, Goodness.

---

## Canonical sentence

> NemoClaw sees. VisualUrantiClaw explains. Fireclaw reacts to technical
> faults. LuciferiClaw adjudicates intent and mandate violation.
> **OpenClaw instances execute.** Paperclip preserves the evidence.

`OpenClaw@URANTiOS-ingest` is one instance of the OpenClaw class; the bot-fleet
instance at `46.225.51.30` is the other. Same role, different sub-scopes.

---

## Topology

Target host: **URANTiOS** (204.168.143.98 — CCX23 · 16 GB · 160 GB).

Chosen to co-locate ingestion with the already-provisioned Cognee datastore:

```
OpenClaw@URANTiOS-ingest  ──►  cognee.add()  ──►  ~/.cognee/data (host)
                                                    ├── LanceDB (vectors)
                                                    └── Kuzu (graph)
                                                        ▲
                       Ollama (native, port 11434) ─────┘   fastembed (384d)
```

Zero network hop: the container bind-mounts the host's `~/.cognee/data`
directory and reaches host Ollama via `host.docker.internal:host-gateway`.

---

## Allowlist — the canonical boundary

```python
ALLOWED_HANDLERS = {
    "ingest_normalize",      # REAL — first handler
    "categorise_by_axes",    # stub
    "cross_link",            # stub
    "governance_check",      # stub
    "export_urantipedia",    # stub
    "smoke_test",            # bootstrap
}
```

Anything outside this set is **rejected** with an evidence record stamped
`status: rejected`. No free-form shell. No `--command` escape hatch.

---

## Install + run

One-command install on the URANTiOS server (assumes the repo is cloned
at `~/mircea-constellation`, same pattern as Fireclaw / LuciferiClaw):

```bash
ssh mircea@204.168.143.98
cd ~/mircea-constellation
bash setup/openclaw_ingest_install.sh
```

The installer:
1. Discovers the invoker's UID/GID via `id -u` / `id -g` (no hardcoding).
2. Creates `/opt/openclaw-data/` and `~/.cognee/data/` with correct ownership.
3. Writes `openclaw_ingest/.env` with `HOST_UID`, `HOST_GID`, `DATASET_NAME`.
4. Runs `docker compose up --build -d` from the `openclaw_ingest/` directory.
5. Verifies the container is healthy.

### Verify

```bash
docker logs openclaw-ingest --tail 30
curl -s http://127.0.0.1:8080/health | python3 -m json.tool
ls -l /opt/openclaw-data/evidence/         # smoke_test wrote an evidence file
```

`/health` returns `cognee_ready: true|false` honestly. If `false`, Cognee
init failed (most common cause: Ollama not reachable from the container).

---

## Invoke a handler

The only way to run handlers is the `POST /tasks` endpoint (local-only, bound
to `127.0.0.1:8080`):

```bash
curl -s -X POST http://127.0.0.1:8080/tasks \
    -H 'Content-Type: application/json' \
    -d '{"handler": "ingest_normalize", "payload": {}}' \
  | python3 -m json.tool
```

Allowlisted handlers that are stubs return `status: not_implemented` with a
`reason` field — honest, not silent success.

---

## Ingest your first batch

```bash
# Drop any number of *.jsonl files into the ingestion inbox
cp ~/claude-code-export/*.jsonl /opt/openclaw-data/ingest/chatcode/

# Trigger
curl -sX POST http://127.0.0.1:8080/tasks \
    -H 'Content-Type: application/json' \
    -d '{"handler": "ingest_normalize", "payload": {}}'
```

`ingest_normalize` will, for each file:

1. Read UTF-8 content.
2. Compute `sha256(content)` (deterministic across processes — not Python's hash()).
3. Call `await cognee.add(content, dataset_name=DATASET_NAME, node_set=[...])`.
4. **Move** the file to `/data/ingested/chatcode/` so it cannot be re-ingested.
5. Write an evidence record with payload/result sha256 hashes.

Failures are reported honestly: `status: partial` if some files succeeded and
some didn't, with a per-file error list.

---

## Configuration surface

| Env var                 | Default                              | Purpose                                    |
|-------------------------|--------------------------------------|--------------------------------------------|
| `CLAW_NAME`             | `OpenClaw@URANTiOS-ingest`           | Logged on every record                     |
| `DATASET_NAME`          | `mircea_corpus`                      | Cognee dataset (not hardcoded)             |
| `LOG_LEVEL`             | `INFO`                               |                                            |
| `COGNEE_MODE`           | `local`                              | Passed to `cognee_config.init(mode=...)`   |
| `COGNEE_OLLAMA_ENDPOINT`| `http://host.docker.internal:11434`  | From inside container → host Ollama        |
| `COGNEE_DATA_ROOT`      | `/home/openclaw/.cognee/data`        | Bind-mounted to host `~/.cognee/data`      |

---

## What this is **not** yet

- Not a full ingestion pipeline — four handlers are stubs.
- Not hardened beyond what is actually proven. No Fireclaw integration
  beyond the shared evidence directory convention.
- Not Paperclip-integrated — this module emits evidence records; Paperclip
  will later bind, bundle, and preserve them under its own contract.
- Not a replacement for the existing `OpenClaw@Hetzy-bots` at 46.225.51.30.
  Two instances; same class; different sub-scopes.

Follow-up PR will implement `categorise_by_axes` (the 12-axis classifier),
then `cross_link`, then `governance_check`, then `export_urantipedia`.
