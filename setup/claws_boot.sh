#!/usr/bin/env bash
# ================================================================
# CLAWS BOOT — Bootstrap all Claws from iMac M4
# UrantiOS governed — Truth · Beauty · Goodness
#
# Run from iMac Terminal:
#   bash <(curl -fsSL https://raw.githubusercontent.com/MyEduGit/mircea-constellation/claude/count-claws-NrqRh/setup/claws_boot.sh)
# ================================================================
set -euo pipefail

CYAN='\033[0;36m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; RED='\033[0;31m'; BOLD='\033[1m'; NC='\033[0m'
info()  { echo -e "${CYAN}▶${NC} $*"; }
ok()    { echo -e "${GREEN}✓${NC} $*"; }
warn()  { echo -e "${YELLOW}⚠${NC}  $*"; }
err()   { echo -e "${RED}✗${NC} $*"; }

OPENCLAW="root@46.225.51.30"
URANTIOS="root@204.168.143.98"

echo ""
echo -e "${BOLD}=================================================${NC}"
echo -e "${BOLD}  CLAWS BOOT — Mircea Constellation${NC}"
echo -e "${BOLD}  Truth · Beauty · Goodness${NC}"
echo -e "${BOLD}=================================================${NC}"
echo ""

# ── 1. SSH connectivity ──────────────────────────────────────────────────────
info "[1/5] Checking SSH connectivity..."
OPENCLAW_OK=false
URANTIOS_OK=false

if ssh -o ConnectTimeout=6 -o BatchMode=yes $OPENCLAW 'exit' 2>/dev/null; then
  ok "OpenClaw (46.225.51.30) — reachable"
  OPENCLAW_OK=true
else
  err "OpenClaw unreachable — check SSH keys"
fi

if ssh -o ConnectTimeout=6 -o BatchMode=yes $URANTIOS 'exit' 2>/dev/null; then
  ok "URANTiOS (204.168.143.98) — reachable"
  URANTIOS_OK=true
else
  warn "URANTiOS unreachable — skipping URANTiOS steps"
fi

# ── 2. Fix NemoClaw — expose n8n via nginx ───────────────────────────────────
info "[2/5] Fixing NemoClaw — exposing n8n on port 80..."
if $OPENCLAW_OK; then
  ssh $OPENCLAW << 'SSHEOF'
apt-get update -qq 2>/dev/null
apt-get install -y nginx -qq 2>/dev/null
rm -f /etc/nginx/sites-enabled/default
cat > /etc/nginx/sites-enabled/n8n.conf << 'NGINXEOF'
server {
    listen 80;
    server_name _;
    client_max_body_size 50M;
    location / {
        proxy_pass http://127.0.0.1:5678;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_buffering off;
        proxy_read_timeout 300;
    }
}
NGINXEOF
nginx -t && systemctl enable nginx --quiet && systemctl restart nginx
ufw allow 80/tcp 2>/dev/null || true
ufw allow 443/tcp 2>/dev/null || true
echo "NemoClaw nginx: OK"
SSSHEOF
  ok "NemoClaw fixed — n8n now on port 80"
else
  warn "Skipping NemoClaw fix (SSH unavailable)"
fi

# ── 3. Check NanoClaw on URANTiOS ────────────────────────────────────────────
info "[3/5] Checking NanoClaw on URANTiOS..."
if $URANTIOS_OK; then
  ssh $URANTIOS 'docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"'
else
  warn "URANTiOS unreachable — NanoClaw check skipped"
fi

# ── 4. Full container status ─────────────────────────────────────────────────
info "[4/5] Full container status..."
echo ""
echo "--- OpenClaw (46.225.51.30) ---"
if $OPENCLAW_OK; then
  ssh $OPENCLAW 'docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"'
fi
echo ""
echo "--- URANTiOS (204.168.143.98) ---"
if $URANTIOS_OK; then
  ssh $URANTIOS 'docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"'
fi

# ── 5. Open n8n in browser ───────────────────────────────────────────────────
info "[5/5] Opening NemoClaw (n8n) in browser..."
sleep 1
open "http://46.225.51.30" 2>/dev/null && ok "Browser opened" || echo "  → Open manually: http://46.225.51.30"

echo ""
echo -e "${BOLD}=================================================${NC}"
echo -e "${BOLD}  ALL CLAWS STATUS${NC}"
echo -e "${GREEN}  NemoClaw (n8n):   http://46.225.51.30${NC}"
echo -e "${CYAN}  NanoClaw:         Telegram @nanoclaw_openclaw_bot${NC}"
echo -e "${CYAN}  OpenClaw bots:    Check your Telegram fleet${NC}"
echo -e "${YELLOW}  InstantlyClaw:    → Build next inside n8n${NC}"
echo -e "${YELLOW}  FireClaw:         → Build next inside n8n${NC}"
echo -e "${BOLD}=================================================${NC}"
echo ""
