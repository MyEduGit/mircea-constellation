#!/usr/bin/env bash
# ================================================================
# OpenClaw Fleet Diagnostic — Phase 1
# Run ON the server:  ssh root@46.225.51.30 'bash -s' < setup/fleet_diagnostic.sh
# Or from claws_boot:  ssh root@46.225.51.30 < setup/fleet_diagnostic.sh
# ================================================================
set -uo pipefail

CYAN='\033[0;36m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; RED='\033[0;31m'; BOLD='\033[1m'; NC='\033[0m'
ok()   { echo -e "${GREEN}✓${NC} $*"; }
warn() { echo -e "${YELLOW}⚠${NC}  $*"; }
err()  { echo -e "${RED}✗${NC} $*"; }
section() { echo -e "\n${BOLD}${CYAN}=== $* ===${NC}"; }

echo ""
echo -e "${BOLD}=================================================${NC}"
echo -e "${BOLD}  OpenClaw Fleet Diagnostic — $(date '+%Y-%m-%d %H:%M:%S %Z')${NC}"
echo -e "${BOLD}=================================================${NC}"
echo ""

section "HOST"
hostname && date

section "DISK"
df -hP / | awk 'NR==2{
  used=$5+0
  printf "  %s used, %s free (of %s)\n", $5, $4, $2
  if (used >= 95) print "  ✗ CRITICAL: disk nearly full — fix this first"
  else if (used >= 80) print "  ⚠  WARNING: disk above 80%"
  else print "  ✓ disk OK"
}'

section "MEMORY"
free -h | awk '/^Mem:/{printf "  %s used / %s total\n", $3, $2}'

section "LOAD"
uptime

section "OPENCLAW"
if command -v openclaw &>/dev/null; then
  ok "openclaw found at $(command -v openclaw)"
  openclaw --version 2>&1 || true
else
  err "openclaw NOT IN PATH"
  echo "  → Try: npm list -g openclaw"
  echo "  → Or:  which openclaw; ls /usr/local/bin/openclaw"
fi

section "NODE"
node --version 2>&1 && ok "node OK" || err "node not found"

section "DOCKER"
if command -v docker &>/dev/null; then
  docker ps --format 'table {{.Names}}\t{{.Status}}\t{{.Ports}}' 2>&1
  echo ""
  echo "  --- stopped containers ---"
  docker ps -a --filter status=exited --format 'table {{.Names}}\t{{.Status}}' 2>&1 || true
else
  err "docker not available"
  echo "  → Fix: apt install -y docker.io && systemctl enable --now docker"
fi

section "OPENCLAW DOCTOR"
openclaw doctor 2>&1 || err "openclaw doctor failed"

section "GATEWAY STATUS"
openclaw gateway status 2>&1 || err "gateway status failed"

section "CHANNEL PROBE"
openclaw channels status --probe 2>&1 || err "channel probe failed"

section "PROCESSES"
ps aux | grep -iE 'openclaw|n8n|telegram|gateway|ollama' | grep -v grep || warn "no matching processes running"

section "PORTS"
echo "  Checking :5678 (n8n), :18789 (openclaw-gateway), :18810, :11434 (ollama)"
ss -ltnp | grep -E ':5678|:18789|:18810|:11434' || warn "none of the expected ports listening"

section "GATEWAY BIND ADDRESS"
if ss -ltnp | grep -q '0\.0\.0\.0:18789'; then
  err "SECURITY RISK: gateway listening on 0.0.0.0:18789 (exposed to internet)"
  echo "  → Fix: set gateway.bind to 127.0.0.1 in config.json, restart gateway"
elif ss -ltnp | grep -q '127\.0\.0\.1:18789'; then
  ok "gateway correctly bound to loopback only"
else
  warn "gateway port 18789 not detected"
fi

section "SYSTEMD UNITS"
systemctl list-units --type=service --all --no-legend '*openclaw*' 2>/dev/null \
  | while read -r unit _load active sub desc; do
      if [[ "$active" == "active" ]]; then ok "$unit — $active ($sub)"
      else err "$unit — $active ($sub)"
      fi
    done || warn "no openclaw systemd units found"

section "OLLAMA"
if curl -fsS --max-time 5 http://127.0.0.1:11434/api/tags &>/dev/null; then
  ok "Ollama responding on :11434"
  curl -fsS --max-time 5 http://127.0.0.1:11434/api/tags | python3 -c "
import sys, json
try:
  data = json.load(sys.stdin)
  models = [m['name'] for m in data.get('models', [])]
  print('  Models:', ', '.join(models) if models else '(none loaded)')
except: pass
" 2>/dev/null || true
else
  err "Ollama not responding on :11434"
  echo "  → Fix: systemctl restart ollama"
  echo "  → Synthesis Scholar and Nebadon will be dead until Ollama is up"
fi

section "TELEGRAM REACHABILITY"
if curl -fsS --max-time 8 https://api.telegram.org &>/dev/null; then
  ok "api.telegram.org reachable"
else
  err "api.telegram.org UNREACHABLE"
  echo "  → Check: ufw status | grep -E '80|443|OUT'"
  echo "  → Check: cat /etc/resolv.conf"
fi

section "UFW FIREWALL"
ufw status verbose 2>/dev/null || warn "ufw not installed or not active"

section "STALE LOCK FILES"
STALE=0
while IFS= read -r lockfile; do
  pid=$(cat "$lockfile" 2>/dev/null)
  if [[ -n "$pid" ]] && ! kill -0 "$pid" 2>/dev/null; then
    err "Stale lock: $lockfile (pid $pid is dead)"
    STALE=$((STALE+1))
  fi
done < <(find /var/lib/openclaw -name 'run.lock' 2>/dev/null)
[[ $STALE -eq 0 ]] && ok "no stale lock files"

section "DISK USAGE TOP 10"
du -sh /var/lib/docker /var/log /tmp /root 2>/dev/null | sort -rh | head -10 || true

section "SUMMARY"
echo ""
echo "  VPS: $(hostname) / $(curl -fsS --max-time 4 https://api.ipify.org 2>/dev/null || echo '(ip check failed)')"
echo "  Date: $(date '+%Y-%m-%d %H:%M:%S %Z')"
echo ""
echo "  Next step: run setup/fleet_repair.sh on any issues found above."
echo ""
