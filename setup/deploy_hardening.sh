#!/usr/bin/env bash
# ================================================================
# OpenClaw Fleet Hardening — Full Remote Deployment
# Run FROM IMAC (you need SSH key access to VPS):
#   bash setup/deploy_hardening.sh
#
# What this does:
#   1. Backs up current config on VPS
#   2. Deploys SOUL.md to ~/.openclaw/workspace/
#   3. Runs fleet_diagnostic.sh — shows current state
#   4. Runs fleet_repair.sh — fixes common issues
#   5. Runs fleet_harden.sh — UFW, SSH, permissions
#   6. Installs fleet_backup.sh + weekly cron
#   7. Runs final verification
# ================================================================
set -uo pipefail

CYAN='\033[0;36m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; RED='\033[0;31m'; BOLD='\033[1m'; NC='\033[0m'
info() { echo -e "${CYAN}▶${NC} $*"; }
ok()   { echo -e "${GREEN}✓${NC} $*"; }
warn() { echo -e "${YELLOW}⚠${NC}  $*"; }
err()  { echo -e "${RED}✗${NC} $*"; exit 1; }
section() { echo -e "\n${BOLD}${CYAN}============================================================${NC}"; echo -e "${BOLD}${CYAN}  $*${NC}"; echo -e "${BOLD}${CYAN}============================================================${NC}"; }

OPENCLAW_HOST="root@46.225.51.30"
REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SETUP_DIR="$REPO_DIR/setup"

echo ""
section "OpenClaw Fleet Hardening — Full Deploy"
echo "  VPS: $OPENCLAW_HOST"
echo "  Repo: $REPO_DIR"
echo "  Time: $(date '+%Y-%m-%d %H:%M:%S')"
echo ""

# ── Pre-flight ────────────────────────────────────────────────────
info "Pre-flight: checking SSH connectivity..."
if ! ssh -o ConnectTimeout=10 -o BatchMode=yes "$OPENCLAW_HOST" 'exit' 2>/dev/null; then
  err "Cannot reach $OPENCLAW_HOST — check SSH keys and VPS status"
fi
ok "SSH OK"

# ── Step 1: Backup current config on VPS ─────────────────────────
section "Step 1 — Backup current VPS config"
ssh "$OPENCLAW_HOST" << 'SSHEOF'
set -uo pipefail
BACKUP_DIR="$HOME/openclaw-backup-$(date +%Y%m%d-%H%M%S)"
mkdir -p "$BACKUP_DIR"
[[ -f ~/.openclaw/config.json ]]   && cp ~/.openclaw/config.json "$BACKUP_DIR/"   && echo "✓ config.json backed up"
[[ -f ~/.openclaw/config.yaml ]]   && cp ~/.openclaw/config.yaml "$BACKUP_DIR/"   && echo "✓ config.yaml backed up"
[[ -d ~/.openclaw/workspace/ ]]    && cp -r ~/.openclaw/workspace/ "$BACKUP_DIR/" && echo "✓ workspace backed up"
[[ -d ~/.openclaw/memories/ ]]     && cp -r ~/.openclaw/memories/ "$BACKUP_DIR/"  && echo "✓ memories backed up"
echo "Backup saved to: $BACKUP_DIR"
ls -lah "$BACKUP_DIR"
SSHEOF

# ── Step 2: Deploy SOUL.md ────────────────────────────────────────
section "Step 2 — Deploy SOUL.md"
if [[ ! -f "$SETUP_DIR/SOUL.md" ]]; then
  err "SOUL.md not found at $SETUP_DIR/SOUL.md"
fi

ssh "$OPENCLAW_HOST" 'mkdir -p ~/.openclaw/workspace'
scp "$SETUP_DIR/SOUL.md" "$OPENCLAW_HOST:~/.openclaw/workspace/SOUL.md"
ssh "$OPENCLAW_HOST" 'chmod 644 ~/.openclaw/workspace/SOUL.md && echo "✓ SOUL.md deployed to ~/.openclaw/workspace/"'

# ── Step 3: Deploy config template (if no config exists) ──────────
section "Step 3 — Config template check"
CONFIG_EXISTS=$(ssh "$OPENCLAW_HOST" '[[ -f ~/.openclaw/config.json ]] && echo yes || echo no' 2>/dev/null)
if [[ "$CONFIG_EXISTS" == "no" ]]; then
  warn "No config.json found on VPS — deploying template"
  scp "$SETUP_DIR/openclaw_config_template.json" "$OPENCLAW_HOST:~/.openclaw/config.json"
  warn "IMPORTANT: Edit ~/.openclaw/config.json on the VPS to fill in all REPLACE_WITH_* values"
  echo "  Required values:"
  echo "    gateway.auth.token      → openssl rand -hex 32"
  echo "    model.apiKey            → Anthropic API key"
  echo "    channels.telegram.botToken → MirNeMoClaw_bot token"
  echo "    agent.identityMap       → Wife's Telegram ID"
else
  ok "config.json already exists on VPS (not overwriting)"
  echo "  → Review: ssh $OPENCLAW_HOST 'cat ~/.openclaw/config.json'"
fi

# ── Step 4: Run fleet diagnostic ─────────────────────────────────
section "Step 4 — Fleet diagnostic"
ssh "$OPENCLAW_HOST" 'bash -s' < "$SETUP_DIR/fleet_diagnostic.sh" 2>&1

# ── Step 5: Run fleet repair ──────────────────────────────────────
section "Step 5 — Fleet repair"
ssh "$OPENCLAW_HOST" 'bash -s' < "$SETUP_DIR/fleet_repair.sh" 2>&1

# ── Step 6: Run fleet hardening ───────────────────────────────────
section "Step 6 — Security hardening"
ssh "$OPENCLAW_HOST" 'bash -s' < "$SETUP_DIR/fleet_harden.sh" 2>&1

# ── Step 7: Install backup script + cron ─────────────────────────
section "Step 7 — Install backup script"
scp "$SETUP_DIR/fleet_backup.sh" "$OPENCLAW_HOST:~/openclaw-backup.sh"
ssh "$OPENCLAW_HOST" << 'SSHEOF'
chmod +x ~/openclaw-backup.sh
# Add weekly cron if not already present
if crontab -l 2>/dev/null | grep -q 'openclaw-backup'; then
  echo "✓ Backup cron already installed"
else
  (crontab -l 2>/dev/null; echo "0 2 * * 0 bash $HOME/openclaw-backup.sh >> $HOME/openclaw-backups/backup.log 2>&1") | crontab -
  echo "✓ Backup cron installed (Sundays at 02:00)"
fi
crontab -l | grep openclaw
SSHEOF

# ── Step 8: Final verification ────────────────────────────────────
section "Step 8 — Final verification"
ssh "$OPENCLAW_HOST" << 'SSHEOF'
echo ""
echo "=== OPENCLAW DOCTOR ==="
openclaw doctor 2>&1 || echo "(openclaw doctor failed)"

echo ""
echo "=== GATEWAY STATUS ==="
openclaw gateway status 2>&1 || echo "(gateway status failed)"

echo ""
echo "=== CHANNEL PROBE ==="
openclaw channels status --probe 2>&1 || echo "(channel probe failed)"

echo ""
echo "=== GATEWAY BIND ==="
ss -ltnp | grep 18789 || echo "(port 18789 not listening)"

echo ""
echo "=== UFW STATUS ==="
ufw status 2>/dev/null | head -20 || echo "(ufw not available)"

echo ""
echo "=== DOCKER CONTAINERS ==="
docker ps --format 'table {{.Names}}\t{{.Status}}\t{{.Ports}}' 2>/dev/null || echo "(docker not available)"

echo ""
echo "=== OLLAMA ==="
curl -fsS --max-time 4 http://127.0.0.1:11434/api/tags | python3 -c "
import sys, json
d = json.load(sys.stdin)
models = [m['name'] for m in d.get('models', [])]
print('Models loaded:', ', '.join(models) if models else '(none)')
" 2>/dev/null || echo "(Ollama not responding)"
SSHEOF

# ── Final checklist ───────────────────────────────────────────────
echo ""
section "COMPLETION CHECKLIST"
cat << 'CHECKLIST'

  Review each item on the VPS. If any is red, check the output above.

  [ ] All openclaw systemd units active
  [ ] Docker containers running (nemoclaw-n8n, openclaw-gateway, openclaw-ingest)
  [ ] Ollama responding on :11434
  [ ] Gateway listening on 127.0.0.1:18789 (NOT 0.0.0.0)
  [ ] `openclaw doctor` — all green
  [ ] `openclaw channels status --probe` — Telegram connected
  [ ] UFW enabled (SSH + Tailscale; nginx only if needed)
  [ ] SOUL.md deployed to ~/.openclaw/workspace/SOUL.md
  [ ] config.json hardened (no REPLACE_WITH_* values remaining)
  [ ] Backup script installed at ~/openclaw-backup.sh
  [ ] Backup cron scheduled (Sundays 02:00)

  Manual steps still needed:
  [ ] MirNeMoClaw_bot: send /status in Telegram to verify response < 3s
  [ ] NanoClaw: send /status in Telegram to verify response < 3s
  [ ] Fill in ~/.openclaw/config.json REPLACE_WITH_* values if not done
  [ ] Tailscale: install on MacBook + iPhone for full mesh
  [ ] Disable root SSH only AFTER confirming non-root sudo user works

CHECKLIST

echo "  Deploy script complete — $(date '+%Y-%m-%d %H:%M:%S')"
echo ""
