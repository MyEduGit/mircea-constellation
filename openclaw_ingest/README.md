# OpenClaw@URANTiOS-ingest

**Truthful label:** deployable scaffold with three real handlers
(`ingest_normalize`, `categorise_by_axes`, `cross_link`). Two of the five
canonical handlers remain declared-but-stubbed pending follow-up PR.

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
    "ingest_normalize",         # REAL — normalises raw files into Cognee
    "categorise_by_axes",       # REAL — 12-axis classifier, see axes.py
    "cross_link",               # REAL — pair-score edge emission, see axes.WEIGHTS
    "governance_check",         # stub
    "export_urantipedia",       # stub
    "smoke_test",               # bootstrap
    "subscription_subscribe",   # REAL — record subscriber in Cognee
    "subscription_unsubscribe", # REAL — append status:inactive record
    "subscription_list",        # REAL — recall subscribers from Cognee
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
| `OLLAMA_ENDPOINT`       | falls back to `COGNEE_OLLAMA_ENDPOINT` | Classifier LLM endpoint                  |
| `OLLAMA_MODEL`          | `qwen2.5:32b`                        | Classifier LLM model                       |
| `OLLAMA_TIMEOUT`        | `120`                                | Per-classification timeout (seconds)       |
| `CLASSIFY_MAX_CHARS`    | `8000`                               | Document truncation budget for classifier  |
| `CROSS_LINK_THRESHOLD`  | `5.0`                                | Minimum pair score to emit an edge         |
| `CROSS_LINK_MAX_PAIRS`  | `10000`                              | Per-invocation pair budget (O(n²) guard)   |
| `CROSS_LINK_MAX_FANOUT` | `50`                                 | Max new edges per document per run         |
| `SUBSCRIPTION_DATASET`  | `mircea_subscribers`                 | Cognee dataset for subscriber nodes        |

---

## Classify an ingested batch

After `ingest_normalize` has moved files into `ingested/chatcode/`, the
12-axis classifier can run over them:

```bash
curl -s -X POST http://127.0.0.1:8080/tasks \
    -H 'Content-Type: application/json' \
    -d '{"handler": "categorise_by_axes", "payload": {}}' \
  | python3 -m json.tool
```

For each ingested file:

1. Compute `sha256(content)`.
2. Skip if `/data/classified/{sha256}.json` already exists (idempotent).
3. Call Ollama (`OLLAMA_ENDPOINT`, `OLLAMA_MODEL`) with a strict
   JSON-only prompt listing all 12 axes and their allowed labels.
4. Validate the response against the closed label sets in `axes.py`.
   Missing or out-of-vocabulary labels are coerced to `"unclear"` and
   the coercions are recorded in `validation_errors`.
5. Write the full record (sha, per-axis labels, validation errors,
   model name, timestamp) to `/data/classified/{sha256}.json`.

Honest failure: if Ollama is unreachable the handler aborts the batch
and returns `status: error` (or `status: partial` if some files already
classified before the outage).

The axes themselves live in [`axes.py`](./axes.py) — first draft,
grounded in UrantiOS Three Values + PhD Triune Monism + corpus-practical
metadata. Edit there; the handler reads straight from that list.

## Cross-link a classified batch

Once documents are in `/data/classified/`, `cross_link` scores every
unordered pair and emits edges above the threshold:

```bash
curl -s -X POST http://127.0.0.1:8080/tasks \
    -H 'Content-Type: application/json' \
    -d '{"handler": "cross_link", "payload": {}}' \
  | python3 -m json.tool

# Override knobs per call (all optional):
#   {"handler": "cross_link",
#    "payload": {"threshold": 6.0, "max_pairs": 500, "max_fanout": 20}}
```

Algorithm per pair `(a, b)` with `sha_a < sha_b`:

1. Skip if `/data/linked/{sha_a}__{sha_b}.json` already exists
   (idempotent — safe to re-run).
2. Skip if either document has `lucifer_test == "flagged"`. Iniquitous
   docs produce **zero** edges in either direction.
3. Compute `score = Σ WEIGHTS[axis]` over axes where labels match AND
   the label is not in `NONPOSITIVE_LABELS` (so `serves_self ↔
   serves_self` and `absent ↔ absent` don't reinforce). Polarity-only —
   see [`axes.py`](./axes.py).
4. Skip if either node has already hit `max_fanout` this run (protects
   hub-docs from runaway fan-out).
5. Emit `/data/linked/{sha_a}__{sha_b}.json` with `score`, `axes_matched`
   (per-axis weight breakdown), `threshold`, timestamp.
6. If Cognee is ready, also `cognee.add` a synthetic edge-content node
   tagged with both shas so the graph sees the relationship. Cognee
   failures are recorded per-pair in `errors`; they don't abort the run.

`O(n²)` guard: `max_pairs` caps the per-invocation budget; the response
includes `pairs_unseen` for honest reporting of what wasn't scored.

Edge weights live in [`axes.WEIGHTS`](./axes.py). Tune there.

## Manage subscribers

Subscribers live in a separate Cognee dataset (`SUBSCRIPTION_DATASET`,
default `mircea_subscribers`), tagged via `node_set` so the bot fleet,
Urantipedia, and scribeclaw can recall them through the same
`cognee.search()` surface used for the corpus.

Append-only: an unsubscribe writes a new `status:inactive` record rather
than deleting the original — matches the module's evidence-trail
discipline. Identifiers are hashed to `identifier_sha256` before storage
so the Cognee graph never holds raw email addresses or Telegram chat IDs.

Subscribe:

```bash
curl -s -X POST http://127.0.0.1:8080/tasks \
    -H 'Content-Type: application/json' \
    -d '{"handler": "subscription_subscribe",
         "payload": {"channel": "newsletter",
                     "identifier": "reader@example.com",
                     "tags": ["urantia_daily", "phd_updates"]}}' \
  | python3 -m json.tool
```

Valid `channel` values: `newsletter`, `telegram`, `bot_fleet`. `tags` is
optional; each tag is stored as a `tag:{name}` node-set entry.

List subscribers on one channel (or all when `channel` is omitted):

```bash
curl -s -X POST http://127.0.0.1:8080/tasks \
    -H 'Content-Type: application/json' \
    -d '{"handler": "subscription_list",
         "payload": {"channel": "newsletter"}}' \
  | python3 -m json.tool
```

Unsubscribe (append `status:inactive`):

```bash
curl -s -X POST http://127.0.0.1:8080/tasks \
    -H 'Content-Type: application/json' \
    -d '{"handler": "subscription_unsubscribe",
         "payload": {"identifier": "reader@example.com"}}' \
  | python3 -m json.tool
```

Honest failures: missing/invalid payload fields return
`status: error, error: invalid_channel|missing_identifier|invalid_tags`;
if Cognee is down every subscription handler short-circuits with
`error: cognee_not_ready` and leaves an evidence record.

## What this is **not** yet

- Not a full ingestion pipeline — two handlers are still stubs.
- Not hardened beyond what is actually proven. No Fireclaw integration
  beyond the shared evidence directory convention.
- Not Paperclip-integrated — this module emits evidence records; Paperclip
  will later bind, bundle, and preserve them under its own contract.
- Not a replacement for the existing `OpenClaw@Hetzy-bots` at 46.225.51.30.
  Two instances; same class; different sub-scopes.

Follow-up PR will implement `governance_check`, then `export_urantipedia`.
