# Fireclaw — Remediation & Incident-Response Layer

> **Canonical claw map:**
> NemoClaw sees · **Fireclaw reacts** · OpenClaw runs · NanoClaw serves at the edge · Paperclip preserves the evidence

Fireclaw is the intervention layer that turns observed faults into
controlled, auditable corrective action. It does not execute workloads
(that is OpenClaw), it does not watch (that is NemoClaw), and it does
not bundle evidence (that is Paperclip). It owns one job: **decide and
act when something is broken, then prove what it did.**

Governance: UrantiOS — Truth, Beauty, Goodness.

---

## Responsibilities (and only these)

- Restart dead services (systemd, docker, n8n workflows)
- Disable misbehaving workflows
- Quarantine bots with repeated failures
- Failover from broken local path → fallback path
- Write incident logs with proof (request/response, exit codes, timestamps)
- Escalate to human review (Telegram) when recovery fails or thresholds cross

## Non-responsibilities

- ✗ Not a general executor (use OpenClaw)
- ✗ Not a dashboard or status surface (use NemoClaw)
- ✗ Not a Telegram bot wrapper (use NanoClaw / UrantiPedia Agent)
- ✗ Not an artifact bundler (use Paperclip — once specified)

---

## Architecture

```
   ┌────────────┐    signals    ┌──────────────┐   actions   ┌────────────┐
   │ NemoClaw   │ ─────────────►│              │────────────►│ OpenClaw / │
   │ (observer) │               │   Fireclaw   │             │  systemd / │
   └────────────┘               │  (this repo) │             │  n8n / etc │
   ┌────────────┐    direct     │              │   alerts    └────────────┘
   │ HTTP probes│ ─────────────►│              │────────────► Telegram
   └────────────┘               └──────┬───────┘
                                       │ append-only
                                       ▼
                               incident_log (jsonl + optional PG)
```

Inputs (any combination):
1. **NemoClaw status row** — `nemoclaw_latest_status` view if Postgres is wired
2. **status.json** — local file written by other layers
3. **Direct probe** — TCP port / HTTP `/health` / process check

Outputs:
1. **Action invocation** — restart / disable / quarantine / failover
2. **Incident record** — `~/.fireclaw/incidents.jsonl` (append-only)
3. **Telegram escalation** — only when `escalate: true` AND threshold crossed

---

## Files

| File                          | Purpose                                                  |
|-------------------------------|----------------------------------------------------------|
| `fireclaw.py`                 | Main daemon. Loads rules, evaluates, acts, logs.         |
| `actions.py`                  | Action primitives (restart, disable, quarantine, alert). |
| `signals.py`                  | Signal collectors (HTTP, file, NemoClaw view).           |
| `rules.yaml`                  | Declarative rules (condition → action). Edit freely.     |
| `schema.sql`                  | Optional Postgres append-only incident log.              |
| `fireclaw.service`            | systemd unit (loop mode every 60s).                      |
| `../setup/fireclaw_install.sh`| Idempotent installer (venv + deps + smoke test).         |

---

## Run

### One-shot (dry-run — no actions taken, just evaluate)

```bash
cd ~/mircea-constellation
python3 -m fireclaw.fireclaw --dry-run --once
```

### One-shot (execute matching actions)

```bash
python3 -m fireclaw.fireclaw --execute --once
```

### Loop (production)

```bash
python3 -m fireclaw.fireclaw --execute --loop --interval 60
```

### Install (iMac M4 / URANTiOS)

```bash
bash setup/fireclaw_install.sh
```

The installer creates `~/.fireclaw-env`, installs deps, runs an
import-only smoke test, and prints next steps. It does **not**
auto-enable the systemd unit — that step is explicit.

### Enable as a service (Linux only)

```bash
sudo cp fireclaw/fireclaw.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now fireclaw.service
journalctl -u fireclaw -f
```

---

## Rules

`rules.yaml` is the single source of truth for what Fireclaw will do.
Each rule has the shape:

```yaml
- id: lobsterbot-down
  description: "Restart lobsterbot if its health probe fails 3 cycles."
  signal:
    kind: http               # http | tcp | file | nemoclaw
    url: http://localhost:8081/health
    expect_status: 200
  condition:
    consecutive_failures: 3
    cooldown_seconds: 600    # don't re-fire within 10 min of last action
  action:
    kind: restart_systemd    # restart_systemd | disable_n8n | quarantine | failover | alert_only
    target: lobsterbot.service
    host: localhost
  escalate:
    on_action_failure: true
    on_repeated_trigger: 3   # alert if rule fires N times in 24h
```

Fireclaw refuses to take any action not declared in `rules.yaml`. New
remediation paths require an explicit rule and a deliberate edit.

## Lucifer Test (every action must pass)

Before Fireclaw acts, it self-checks:

1. **Transparent?** Action is logged with full input, output, exit code.
2. **Honest?** If the action fails, the failure is reported — not hidden.
3. **Within mandate?** Action matches a declared rule. No improvisation.
4. **Serves the mission?** Restart serves uptime; quarantine serves safety.

If any answer is "no", Fireclaw aborts and escalates instead.

## Incident log

Every evaluation cycle appends one JSONL row per fired rule to
`~/.fireclaw/incidents.jsonl`:

```json
{"ts":"2026-04-15T19:30:00+10:00","rule":"lobsterbot-down","signal":{"kind":"http","ok":false,"detail":"connection refused"},"action":{"kind":"restart_systemd","target":"lobsterbot.service","executed":true,"exit_code":0,"duration_ms":842},"escalated":false}
```

Optional Postgres mirror via `schema.sql` (table `fireclaw_incidents`,
append-only, with convenience views `fireclaw_recent_incidents` and
`fireclaw_open_alerts`).

---

## Status surface

Fireclaw is itself a node on the constellation map and reports into
`status.json` under the `fireclaw` key:

```json
"fireclaw": { "status": "ok", "last_cycle": "2026-04-15T19:30:00Z", "incidents_24h": 0 }
```

Statuses: `ok` (no incidents), `warn` (incidents fired but recovered),
`error` (open escalation), `offline` (daemon not running).

---

## Future — Paperclip integration

When Paperclip ships, every Fireclaw incident will trigger a Paperclip
bundle (logs + before/after status snapshots + action transcript) and
attach it to the incident row. Until then, the JSONL log is the audit
trail.
