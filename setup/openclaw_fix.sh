#!/usr/bin/env bash
# ================================================================
# OpenClaw Fix — Expose NemoClaw n8n via nginx
# Run ON the server: ssh root@46.225.51.30 'bash -s' < openclaw_fix.sh
# Or remotely:       ssh root@46.225.51.30 < openclaw_fix.sh
# ================================================================
set -euo pipefail

CYAN='\033[0;36m'; GREEN='\033[0;32m'; RED='\033[0;31m'; NC='\033[0m'
info() { echo -e "${CYAN}▶${NC} $*"; }
ok()   { echo -e "${GREEN}✓${NC} $*"; }
err()  { echo -e "${RED}✗${NC} $*"; exit 1; }

echo ""
echo "================================================="
echo "  OpenClaw Fix — NemoClaw n8n Exposure"
echo "================================================="
echo ""

info "[1/4] Installing nginx..."
apt-get update -qq 2>/dev/null
apt-get install -y nginx -qq 2>/dev/null
ok "nginx installed"

info "[2/4] Writing n8n reverse proxy config..."
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
nginx -t || err "nginx config invalid"
ok "nginx configured"

info "[3/4] Enabling & restarting nginx..."
systemctl enable nginx --quiet
systemctl restart nginx
ok "nginx running"

info "[4/4] Opening firewall..."
ufw allow 80/tcp 2>/dev/null || true
ufw allow 443/tcp 2>/dev/null || true
ok "ports 80 and 443 open"

echo ""
echo "================================================="
echo "  NemoClaw n8n is now accessible at:"
echo "  http://46.225.51.30"
echo "================================================="
echo ""
echo "Container status:"
docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"
echo ""
