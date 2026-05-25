#!/usr/bin/env bash
# ================================================================
# OpenClaw Fleet Hardening — Phase 4
# Run ON the server:  ssh root@46.225.51.30 'bash -s' < setup/fleet_harden.sh
# Idempotent — safe to re-run.
# WARNING: Do NOT disable root SSH until a non-root sudo user exists!
# ================================================================
set -uo pipefail

CYAN='\033[0;36m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; RED='\033[0;31m'; BOLD='\033[1m'; NC='\033[0m'
info() { echo -e "${CYAN}▶${NC} $*"; }
ok()   { echo -e "${GREEN}✓${NC} $*"; }
warn() { echo -e "${YELLOW}⚠${NC}  $*"; }
err()  { echo -e "${RED}✗${NC} $*"; }
section() { echo -e "\n${BOLD}${CYAN}=== $* ===${NC}"; }

echo ""
echo -e "${BOLD}=================================================${NC}"
echo -e "${BOLD}  OpenClaw Fleet Hardening — $(date '+%Y-%m-%d %H:%M:%S %Z')${NC}"
echo -e "${BOLD}=================================================${NC}"

# ── HARDEN 1: UFW Firewall ────────────────────────────────────────
section "HARDEN 1 — UFW Firewall"
if ! command -v ufw &>/dev/null; then
  info "Installing ufw..."
  apt-get update -qq && apt-get install -y ufw -qq
fi

ufw --force reset 2>/dev/null || true
ufw default deny incoming
ufw default allow outgoing
ufw allow 22/tcp comment 'SSH'
ufw allow 41641/udp comment 'Tailscale'
# n8n is proxied via nginx on 80; keep 80/443 open only if nginx is in use
if systemctl is-active nginx &>/dev/null; then
  ufw allow 80/tcp comment 'nginx-n8n'
  ufw allow 443/tcp comment 'nginx-ssl'
  ok "nginx detected — port 80/443 allowed"
fi
ufw --force enable
ok "UFW enabled"
ufw status verbose

# ── HARDEN 2: Tailscale ───────────────────────────────────────────
section "HARDEN 2 — Tailscale"
if command -v tailscale &>/dev/null; then
  ok "Tailscale already installed: $(tailscale ip -4 2>/dev/null || echo '(not connected)')"
else
  warn "Tailscale not installed"
  echo "  → To install: curl -fsSL https://tailscale.com/install.sh | sh"
  echo "  → Then: tailscale up"
  echo "  → Also install on MacBook and iPhone for full mesh"
fi

# ── HARDEN 3: Verify gateway on loopback only ─────────────────────
section "HARDEN 3 — Gateway bind address"
if ss -ltnp 2>/dev/null | grep -q '0\.0\.0\.0:18789'; then
  err "SECURITY RISK: gateway is listening on 0.0.0.0:18789"
  echo "  → Fix: set gateway.bind = '127.0.0.1' in ~/.openclaw/config.json"
  echo "  → Then: openclaw gateway restart"
elif ss -ltnp 2>/dev/null | grep -q '127\.0\.0\.1:18789'; then
  ok "Gateway correctly bound to loopback only (127.0.0.1:18789)"
else
  warn "Gateway port 18789 not detected — check if gateway is running"
fi

# ── HARDEN 4: SSH hardening ───────────────────────────────────────
section "HARDEN 4 — SSH hardening"
SSHD=/etc/ssh/sshd_config

# Check root login status
ROOT_LOGIN=$(grep -E '^PermitRootLogin' "$SSHD" 2>/dev/null | awk '{print $2}' || echo "unknown")
echo "  Current PermitRootLogin: $ROOT_LOGIN"

# Check if there's a non-root sudo user before recommending root lock
SUDO_USERS=$(grep -vE '^(root|#)' /etc/sudoers 2>/dev/null | grep -c 'ALL' || getent group sudo 2>/dev/null | cut -d: -f4)
if [[ -n "$SUDO_USERS" && "$SUDO_USERS" != "0" ]]; then
  warn "Root SSH is $ROOT_LOGIN — non-root sudo user exists"
  echo "  → To disable root SSH (ONLY when non-root login is confirmed working):"
  echo "     sed -i 's/^PermitRootLogin.*/PermitRootLogin no/' /etc/ssh/sshd_config"
  echo "     systemctl restart sshd"
else
  warn "Root SSH is $ROOT_LOGIN — no non-root sudo user detected, keeping root SSH enabled for safety"
fi

# Ensure password auth is disabled (key-only)
if grep -qE '^PasswordAuthentication yes' "$SSHD" 2>/dev/null; then
  warn "PasswordAuthentication is YES — disabling..."
  sed -i 's/^PasswordAuthentication yes/PasswordAuthentication no/' "$SSHD"
  systemctl reload sshd 2>/dev/null || true
  ok "Password authentication disabled (key-only)"
elif grep -qE '^PasswordAuthentication no' "$SSHD" 2>/dev/null; then
  ok "Password authentication already disabled"
else
  warn "PasswordAuthentication not explicitly set — recommend adding: PasswordAuthentication no"
fi

# ── HARDEN 5: Fail2ban ────────────────────────────────────────────
section "HARDEN 5 — Fail2ban"
if command -v fail2ban-server &>/dev/null; then
  ok "fail2ban already installed"
  systemctl is-active fail2ban &>/dev/null && ok "fail2ban running" || (systemctl start fail2ban && ok "fail2ban started")
else
  info "Installing fail2ban..."
  apt-get install -y fail2ban -qq 2>/dev/null && systemctl enable --now fail2ban && ok "fail2ban installed and running" \
    || warn "fail2ban install failed — non-critical"
fi

# ── HARDEN 6: Docker socket permissions ───────────────────────────
section "HARDEN 6 — Docker socket permissions"
if [[ -S /var/run/docker.sock ]]; then
  SOCK_PERMS=$(stat -c '%a' /var/run/docker.sock)
  SOCK_GROUP=$(stat -c '%G' /var/run/docker.sock)
  echo "  Docker socket: mode=$SOCK_PERMS, group=$SOCK_GROUP"
  if [[ "$SOCK_PERMS" == "660" && "$SOCK_GROUP" == "docker" ]]; then
    ok "Docker socket permissions look correct"
  else
    warn "Unexpected docker socket permissions — review access"
  fi
fi

# ── HARDEN 7: Verify no world-writable openclaw files ─────────────
section "HARDEN 7 — Openclaw config permissions"
if [[ -f ~/.openclaw/config.json ]]; then
  PERMS=$(stat -c '%a' ~/.openclaw/config.json)
  if [[ "$PERMS" -le 600 ]]; then
    ok "~/.openclaw/config.json permissions: $PERMS (good)"
  else
    warn "~/.openclaw/config.json permissions: $PERMS — tightening to 600"
    chmod 600 ~/.openclaw/config.json
    ok "Fixed to 600"
  fi
fi
if [[ -f ~/.openclaw/workspace/SOUL.md ]]; then
  ok "SOUL.md exists"
else
  warn "SOUL.md not deployed to ~/.openclaw/workspace/"
  echo "  → Run deploy_hardening.sh to place it"
fi

# ── SUMMARY ──────────────────────────────────────────────────────
section "HARDENING SUMMARY"
echo ""
echo "  ✓ UFW firewall configured (SSH + Tailscale only by default)"
echo "  ✓ Gateway bind address verified"
echo "  ✓ SSH password auth hardening checked"
echo "  ✓ fail2ban checked"
echo ""
echo "  Remaining manual steps:"
echo "  1. Tailscale: connect Mircea's MacBook and iPhone"
echo "  2. Root SSH: disable after confirming non-root sudo access"
echo "  3. MirNeMoClaw_bot: send /status in Telegram to verify"
echo ""
