#!/usr/bin/env bash
# ================================================================
# CLAWS BOOT + COUNCIL DEPLOY — Mircea Constellation
# UrantiOS governed — Truth · Beauty · Goodness
#
# Run from iMac Terminal:
#   bash <(curl -fsSL https://raw.githubusercontent.com/MyEduGit/mircea-constellation/claude/count-claws-NrqRh/setup/claws_boot.sh)
# ================================================================
set -eo pipefail

CYAN='\033[0;36m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; RED='\033[0;31m'; BOLD='\033[1m'; NC='\033[0m'
info()  { echo -e "${CYAN}▶${NC} $*"; }
ok()    { echo -e "${GREEN}✓${NC} $*"; }
warn()  { echo -e "${YELLOW}⚠${NC}  $*"; }
err()   { echo -e "${RED}✗${NC} $*"; }
header(){ echo -e "\n${BOLD}$*${NC}"; }

OPENCLAW="root@46.225.51.30"
URANTIOS="root@204.168.143.98"
WORKFLOW_URL="https://raw.githubusercontent.com/MyEduGit/mircea-constellation/claude/count-claws-NrqRh/council/council_of_seven_v1.n8n.json"
Z_AI_KEY=""
OPENCLAW_OK=false
URANTIOS_OK=false

header "================================================="
header "  CLAWS BOOT + COUNCIL DEPLOY"
header "  Truth · Beauty · Goodness"
header "================================================="

# ── 1. SSH connectivity ──────────────────────────────────────────
info "[1/6] Checking SSH connectivity..."

if ssh -o ConnectTimeout=6 -o BatchMode=yes $OPENCLAW 'exit' 2>/dev/null; then
  ok "OpenClaw (46.225.51.30) — reachable"
  OPENCLAW_OK=true
else
  err "OpenClaw unreachable — check: ssh root@46.225.51.30"
fi

if ssh -o ConnectTimeout=6 -o BatchMode=yes $URANTIOS 'exit' 2>/dev/null; then
  ok "URANTiOS (204.168.143.98) — reachable"
  URANTIOS_OK=true
else
  warn "URANTiOS unreachable — skipping URANTiOS steps"
fi

# ── 2. Fix NemoClaw — expose n8n via nginx ───────────────────────
info "[2/6] Fixing NemoClaw — nginx reverse proxy for n8n..."
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
echo "nginx: OK"
SSHEOF
  ok "NemoClaw — n8n now accessible at http://46.225.51.30"
else
  warn "Skipping NemoClaw fix (SSH unavailable)"
fi

# ── 3. Prompt for Z.ai API key (Seat 6 — you have it) ───────────
echo ""
echo -e "${BOLD}[3/6] Council of Seven — Seat 6 (Z.ai / GLM)${NC}"
echo "      Key exists. Enter it now to wire Seat 6 automatically."
echo "      (Press Enter to skip — paste manually in n8n later)"
echo ""
echo -n "      Z.ai API key: "
read -r Z_AI_KEY
echo ""

# ── 4. Download, patch, and import workflow into n8n ─────────────
info "[4/6] Deploying Council of Seven workflow..."
if $OPENCLAW_OK; then
  # Download workflow JSON from GitHub
  if ! curl -fsSL "$WORKFLOW_URL" -o /tmp/council_workflow.json; then
    warn "Could not download workflow from GitHub — skipping import"
    OPENCLAW_OK=false
  fi
fi

if $OPENCLAW_OK && [ -f /tmp/council_workflow.json ]; then
  WORKFLOW_FILE="/tmp/council_workflow.json"

  # Patch in Z.ai key if provided
  if [ -n "$Z_AI_KEY" ]; then
    python3 - "$Z_AI_KEY" << 'PYEOF'
import sys, json
key = sys.argv[1]
with open('/tmp/council_workflow.json') as f:
    content = f.read()
patched = content.replace('REPLACE_WITH_Z_AI_API_KEY', key)
with open('/tmp/council_workflow_patched.json', 'w') as f:
    f.write(patched)
print("Z.ai key patched into Seat6_SonSpirit_GLM")
PYEOF
    WORKFLOW_FILE="/tmp/council_workflow_patched.json"
  else
    warn "No key entered — Seat 6 needs manual key after import"
  fi

  # Copy workflow into the n8n container and import via CLI
  ssh $OPENCLAW 'docker exec -i nemoclaw-n8n sh -c "cat > /tmp/council_workflow.json"' < "$WORKFLOW_FILE"
  ssh $OPENCLAW 'docker exec nemoclaw-n8n n8n import:workflow --input=/tmp/council_workflow.json 2>&1'
  ok "Council of Seven workflow imported into n8n"
  rm -f /tmp/council_workflow_patched.json
fi

# ── 5. Full container status ─────────────────────────────────────
info "[5/6] Container status..."
echo ""
echo "--- OpenClaw (46.225.51.30) ---"
if $OPENCLAW_OK; then
  ssh $OPENCLAW 'docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"' || true
fi
echo ""
echo "--- URANTiOS (204.168.143.98) ---"
if $URANTIOS_OK; then
  ssh $URANTIOS 'docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"' || true
fi

# ── 6. Open n8n ──────────────────────────────────────────────────
info "[6/6] Opening NemoClaw in browser..."
sleep 2
open "http://46.225.51.30" 2>/dev/null || echo "  → Open manually: http://46.225.51.30"

echo ""
header "================================================="
header "  COUNCIL OF SEVEN — STATUS"
header "================================================="
if [ -n "$Z_AI_KEY" ]; then
  echo -e "${GREEN}  Seat 6 (Son-Spirit / GLM):       KEY WIRED ✓${NC}"
else
  echo -e "${YELLOW}  Seat 6 (Son-Spirit / GLM):       paste key in n8n${NC}"
fi
echo -e "${YELLOW}  Seat 4 (Father-Son / Gemma):     ollama pull gemma3 on URANTiOS${NC}"
echo -e "${YELLOW}  Seats 1,2,3,5,7:                 API keys needed${NC}"
echo ""
echo -e "${GREEN}  n8n UI: http://46.225.51.30${NC}"
echo -e "${BOLD}  → Workflows → Council of Seven Master Spirits v1${NC}"
echo -e "${BOLD}  → Click 'Execute Workflow' to test${NC}"
header "================================================="
echo ""
