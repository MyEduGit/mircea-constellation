#!/usr/bin/env bash
# ================================================================
# OpenClaw Fleet Repair — Phase 2
# Run ON the server:  ssh root@46.225.51.30 'bash -s' < setup/fleet_repair.sh
# Idempotent — safe to re-run.
# ================================================================
set -uo pipefail

CYAN='\033[0;36m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; RED='\033[0;31m'; BOLD='\033[1m'; NC='\033[0m'
info() { echo -e "${CYAN}▶${NC} $*"; }
ok()   { echo -e "${GREEN}✓${NC} $*"; }
warn() { echo -e "${YELLOW}⚠${NC}  $*"; }
err()  { echo -e "${RED}✗${NC} $*"; }
section() { echo -e "\n${BOLD}${CYAN}=== $* ===${NC}"; }

FIXED=0
WARNED=0

echo ""
echo -e "${BOLD}=================================================${NC}"
echo -e "${BOLD}  OpenClaw Fleet Repair — $(date '+%Y-%m-%d %H:%M:%S %Z')${NC}"
echo -e "${BOLD}=================================================${NC}"

# ── FIX 1: Disk space ────────────────────────────────────────────
section "FIX 1 — Disk space check"
DISK_PCT=$(df -P / | awk 'NR==2{print $5+0}')
echo "  Disk usage: ${DISK_PCT}%"
if [[ $DISK_PCT -ge 85 ]]; then
  warn "Disk above 85% — running cleanup..."
  docker system prune -f 2>/dev/null && ok "docker prune done" || warn "docker prune skipped"
  journalctl --vacuum-size=100M 2>/dev/null && ok "journal vacuumed" || warn "journal vacuum skipped"
  apt-get autoremove -y -qq 2>/dev/null && ok "apt autoremove done" || warn "apt autoremove skipped"
  find /tmp -type f -mtime +7 -delete 2>/dev/null && ok "old /tmp files removed" || true
  NEW_PCT=$(df -P / | awk 'NR==2{print $5+0}')
  echo "  Disk after cleanup: ${NEW_PCT}%"
  FIXED=$((FIXED+1))
else
  ok "Disk OK (${DISK_PCT}% used)"
fi

# ── FIX 2: Stale lock files ───────────────────────────────────────
section "FIX 2 — Stale lock files"
STALE=0
while IFS= read -r lockfile; do
  pid=$(cat "$lockfile" 2>/dev/null)
  if [[ -n "$pid" ]] && ! kill -0 "$pid" 2>/dev/null; then
    err "Removing stale lock: $lockfile (pid $pid dead)"
    rm -f "$lockfile"
    STALE=$((STALE+1))
    FIXED=$((FIXED+1))
  fi
done < <(find /var/lib/openclaw -name 'run.lock' 2>/dev/null)
[[ $STALE -eq 0 ]] && ok "no stale locks"

# ── FIX 3: Docker containers ─────────────────────────────────────
section "FIX 3 — Docker containers"
if ! command -v docker &>/dev/null; then
  warn "Docker not installed — installing..."
  apt-get update -qq && apt-get install -y docker.io -qq
  systemctl enable --now docker
  ok "Docker installed and started"
  FIXED=$((FIXED+1))
fi

# Try to start known stopped containers
for CNAME in nemoclaw-n8n openclaw-gateway openclaw-ingest; do
  if docker ps -a --format '{{.Names}}' | grep -q "^${CNAME}$"; then
    STATUS=$(docker inspect --format '{{.State.Status}}' "$CNAME" 2>/dev/null)
    if [[ "$STATUS" != "running" ]]; then
      warn "$CNAME is $STATUS — starting..."
      docker start "$CNAME" && ok "$CNAME started" || err "Failed to start $CNAME — check: docker logs $CNAME"
      FIXED=$((FIXED+1))
    else
      ok "$CNAME is running"
    fi
  else
    warn "$CNAME not found — may need docker compose up"
  fi
done

# Try docker compose if containers are missing
COMPOSE_FILE=$(find / -maxdepth 6 -name 'docker-compose*.yml' -path '*openclaw*' 2>/dev/null | head -1)
if [[ -n "$COMPOSE_FILE" ]]; then
  info "Found compose file: $COMPOSE_FILE"
  echo "  → If containers are missing, run: cd $(dirname "$COMPOSE_FILE") && docker compose up -d"
else
  warn "No openclaw docker-compose.yml found"
fi

# ── FIX 4: Systemd units ─────────────────────────────────────────
section "FIX 4 — Systemd units"
FAILED_UNITS=$(systemctl list-units --type=service --all --no-legend '*openclaw*' 2>/dev/null \
  | awk '$3 != "active" {print $1}')
if [[ -z "$FAILED_UNITS" ]]; then
  ok "All openclaw systemd units active (or none registered)"
else
  for UNIT in $FAILED_UNITS; do
    warn "Unit $UNIT is not active — resetting and restarting..."
    systemctl reset-failed "$UNIT" 2>/dev/null || true
    systemctl restart "$UNIT" 2>/dev/null \
      && ok "$UNIT restarted" \
      || err "$UNIT restart failed — check: journalctl -u $UNIT -n 50 --no-pager"
    FIXED=$((FIXED+1))
  done
fi

# ── FIX 5: Ollama ────────────────────────────────────────────────
section "FIX 5 — Ollama"
if ! curl -fsS --max-time 5 http://127.0.0.1:11434/api/tags &>/dev/null; then
  warn "Ollama not responding — restarting..."
  systemctl restart ollama 2>/dev/null && sleep 5 || warn "systemctl restart ollama failed"
  if curl -fsS --max-time 8 http://127.0.0.1:11434/api/tags &>/dev/null; then
    ok "Ollama is now responding"
    FIXED=$((FIXED+1))
  else
    err "Ollama still not responding — check: journalctl -u ollama -n 50 --no-pager"
    WARNED=$((WARNED+1))
  fi
else
  ok "Ollama responding"
fi

# ── FIX 6: OpenClaw gateway ──────────────────────────────────────
section "FIX 6 — OpenClaw gateway"
if command -v openclaw &>/dev/null; then
  GW_STATUS=$(openclaw gateway status 2>&1)
  if echo "$GW_STATUS" | grep -qi 'running\|ok\|up'; then
    ok "Gateway is running"
  else
    warn "Gateway not running — restarting..."
    openclaw gateway restart 2>&1 && sleep 8 || warn "gateway restart command failed"
    openclaw gateway status 2>&1 | head -5
    FIXED=$((FIXED+1))
  fi
else
  warn "openclaw not in PATH — skipping gateway check"
  echo "  → Try: npm list -g openclaw; npm install -g openclaw"
  WARNED=$((WARNED+1))
fi

# ── FIX 7: Telegram reachability ─────────────────────────────────
section "FIX 7 — Telegram reachability"
if curl -fsS --max-time 8 https://api.telegram.org &>/dev/null; then
  ok "Telegram API reachable"
else
  err "Telegram API UNREACHABLE — checking firewall..."
  ufw status 2>/dev/null || true
  echo "  → Check: ufw allow out 443/tcp && ufw allow out 80/tcp"
  echo "  → Check: cat /etc/resolv.conf (need working DNS)"
  WARNED=$((WARNED+1))
fi

# ── FIX 8: Channel probe ─────────────────────────────────────────
section "FIX 8 — Channel probe (after fixes)"
if command -v openclaw &>/dev/null; then
  sleep 3
  openclaw channels status --probe 2>&1 | head -20 || warn "channel probe failed"
else
  warn "openclaw not available — skipping channel probe"
fi

# ── SUMMARY ──────────────────────────────────────────────────────
section "SUMMARY"
echo ""
echo "  Fixes applied:  $FIXED"
echo "  Warnings left:  $WARNED"
echo ""
if [[ $WARNED -gt 0 ]]; then
  echo "  Action required — review warnings above."
else
  ok "All automated repairs complete."
fi
echo "  Next: run setup/fleet_harden.sh to apply security hardening."
echo ""
