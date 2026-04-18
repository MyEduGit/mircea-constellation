# Mircea's Access Booklet – Simple Guide

## To access n8n
1. Open Mac terminal
2. Run: `ssh -L 5678:localhost:5678 root@46.225.51.30`
3. Keep terminal open
4. Open Chrome or Firefox
5. Go to: http://localhost:5678
6. Login: mircea / (Apple Passwords → OpenClaw n8n)

## To access Hetzner server
1. Open Mac terminal
2. Run: `ssh root@46.225.51.30`
3. You are now on the server

## Server files location
- n8n config: `/home/mircea/nemoclaw/`
- Main compose file: `/home/mircea/nemoclaw/docker-compose.yml`
- Bot config: `/home/mircea/nemoclaw/bot.env`

## Emergency: if n8n stops
```bash
ssh root@46.225.51.30
cd /home/mircea/nemoclaw
docker compose up -d
```
