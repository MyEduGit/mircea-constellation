# NemoClaw Observer

Mission-control dashboard agent for the Mircea / JRP stack. Monitors five
layers (VPS, local, agents, LLMs, connected apps) and produces a
Telegram-ready Markdown dashboard plus a PostgreSQL append-only log.

## Quickstart

```bash
cd nemoclaw_observer
cp config.env.example .env         # then edit secrets
./run.sh                           # one-shot, printed to stdout
./run.sh telegram                  # post to Telegram
./run.sh loop telegram             # run every 6h forever
```

`run.sh` is idempotent: it creates `.venv/`, installs `requirements.txt`,
and seeds `.env` from the example on first run.

## Database

Apply the schema once to the VPS PostgreSQL:

```bash
psql -h 46.225.51.30 -U postgres amep_schema_v1 -f schema.sql
```

This creates `nemoclaw_dashboard_log` plus the
`nemoclaw_latest_status` and `nemoclaw_recent_alerts` views.

## n8n cron

Import `n8n_cron_workflow.json` into the n8n instance on Hetzy and activate
it. The workflow calls `observer.py telegram` every 6 hours.

## Systemd (persistent VPS run)

Copy `nemoclaw-observer.service` to `/etc/systemd/system/` and:

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now nemoclaw-observer
sudo systemctl status nemoclaw-observer
journalctl -u nemoclaw-observer -f
```

## Manual invocation

```bash
python3 observer.py              # print dashboard
python3 observer.py telegram     # push to Telegram
python3 observer.py json         # raw JSON of checks
python3 observer.py silent       # store only, return string
```

## Layers monitored

| Layer | Checks |
|---|---|
| VPS (46.225.51.30) | n8n, PostgreSQL, Redis, Qdrant |
| Local (iMac M4)   | Ollama + required models |
| Apps              | Telegram bot (`@Hetzy_PhD_bot`) |
| LLM spend         | Z.ai GLM-5.1 cap ($5/mo, warn at 80%) |

## Companion

The Telegram `/dashboard` and `/status` command handlers live in the
**lobsterbot** repo at `nemoclaw_observer/telegram_handler.py`.
