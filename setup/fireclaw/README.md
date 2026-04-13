# FireClaw

The constellation's **hot line** — a tiny, dependency-free Python daemon that
accepts urgent signals from local agents (iPhone Shortcuts, iMac menubar,
LobsterBot, Claude Code sessions) and forwards them to the NemoClaw n8n
webhook on OpenClaw.

> UrantiOS governed — **Truth · Beauty · Goodness**.
> FireClaw only relays; it does not decide. The Council decides.

## Place in the constellation

| Claw      | Role                                           | Where                   |
| --------- | ---------------------------------------------- | ----------------------- |
| OpenClaw  | Hetzner execution node — n8n + nginx           | `root@46.225.51.30`     |
| NemoClaw  | n8n instance on OpenClaw                       | container `nemoclaw-n8n`|
| NanoClaw  | Edge fleet of small bots                       | various                 |
| URANTiOS  | Ontology / data-plane server                   | `root@204.168.143.98`   |
| **FireClaw** | **Local hot-line forwarder** (this repo)   | **`127.0.0.1:8797`**    |

## Quick start

```bash
# Foreground (for testing)
bash setup/fireclaw/boot.sh run

# Install as a persistent service (launchd on macOS, systemd --user on Linux)
bash setup/fireclaw/boot.sh install

# Check health
bash setup/fireclaw/boot.sh status

# Stop the service
bash setup/fireclaw/boot.sh stop
```

## Fire a signal

```bash
curl -s -X POST http://127.0.0.1:8797/fire \
  -H 'Content-Type: application/json' \
  -d '{"source": "imac-menubar", "severity": "high", "message": "council convene"}'
```

Response:

```json
{"ok": true, "forwarded": true, "id": "8d1..."}
```

## Environment

| Var                 | Default                                   | Notes                     |
| ------------------- | ----------------------------------------- | ------------------------- |
| `FIRECLAW_PORT`     | `8797`                                    |                           |
| `FIRECLAW_BIND`     | `127.0.0.1`                               | loopback-only by default  |
| `FIRECLAW_FORWARD`  | `http://46.225.51.30/webhook/fireclaw`    | NemoClaw n8n webhook      |
| `FIRECLAW_TOKEN`    | *(unset)*                                 | if set, required on `/fire` |
| `FIRECLAW_LOG`      | `~/.fireclaw/fireclaw.log`                |                           |

## The Lucifer Test

- **Transparent?** Every request is logged with id, source, severity, forwarded.
- **Honest?** `/health` reports both forwarded and failed counts.
- **In mandate?** FireClaw forwards; it does not invent actions.
- **Serves the mission?** Yes — it cuts latency between "something is wrong"
  and the Council hearing it.
