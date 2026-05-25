# n8n Persistent Deployment on OpenClaw

**Server:** OpenClaw (46.225.51.30) – Nuremberg  
**Date created:** April 2026  
**Status:** Running (confirmed via Hetzner console)

## Quick Access
- URL: http://46.225.51.30:5678
- Username: `mircea`
- Password: (see your Apple Passwords → "OpenClaw — n8n")

## How it was set up (one-time commands)

```bash
mkdir -p ~/openclaw-n8n
cd ~/openclaw-n8n
docker stop n8n 2>/dev/null; docker rm n8n 2>/dev/null
docker compose up -d
```

## Folder on server
`/home/mircea/nemoclaw/`

## What it does
- Survives reboot (`restart: unless-stopped`)
- Data stored in `./data` folder
- Basic auth protects the web UI

**Next step:** Build Grandfather's Axe hourly bot inside n8n.
