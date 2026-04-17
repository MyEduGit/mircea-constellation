#!/usr/bin/env bash
# ================================================================
# FireClaw Boot — Mircea Constellation
# UrantiOS governed — Truth, Beauty, Goodness
#
# Usage:
#   bash setup/fireclaw/boot.sh            # run in foreground (default)
#   bash setup/fireclaw/boot.sh install    # install as launchd (mac) / systemd (linux)
#   bash setup/fireclaw/boot.sh status     # show health
#   bash setup/fireclaw/boot.sh stop       # stop the daemon
# ================================================================
set -euo pipefail

CYAN='\033[0;36m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; RED='\033[0;31m'; NC='\033[0m'
info()  { echo -e "${CYAN}▶${NC} $*"; }
ok()    { echo -e "${GREEN}✓${NC} $*"; }
warn()  { echo -e "${YELLOW}⚠${NC}  $*"; }
err()   { echo -e "${RED}✗${NC} $*"; }

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
DAEMON="$SCRIPT_DIR/fireclaw.py"
PORT="${FIRECLAW_PORT:-8797}"
BIND="${FIRECLAW_BIND:-127.0.0.1}"
FORWARD="${FIRECLAW_FORWARD:-http://46.225.51.30/webhook/fireclaw}"

cmd="${1:-run}"

need_python() {
  if ! command -v python3 >/dev/null 2>&1; then
    err "python3 not found — install it first (brew install python3 / apt-get install python3)"
    exit 1
  fi
}

run_fg() {
  need_python
  info "FireClaw foreground on $BIND:$PORT → $FORWARD"
  FIRECLAW_PORT="$PORT" FIRECLAW_BIND="$BIND" FIRECLAW_FORWARD="$FORWARD" \
    exec python3 "$DAEMON"
}

status() {
  if curl -fsS "http://$BIND:$PORT/health" >/tmp/fireclaw_health.json 2>/dev/null; then
    ok "FireClaw is UP"
    cat /tmp/fireclaw_health.json
    echo
  else
    warn "FireClaw not responding on $BIND:$PORT"
  fi
}

install_launchd() {
  need_python
  local plist="$HOME/Library/LaunchAgents/com.urantios.fireclaw.plist"
  mkdir -p "$(dirname "$plist")"
  cat > "$plist" <<PLIST
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN"
  "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>Label</key><string>com.urantios.fireclaw</string>
  <key>ProgramArguments</key>
  <array>
    <string>/usr/bin/env</string>
    <string>python3</string>
    <string>$DAEMON</string>
  </array>
  <key>EnvironmentVariables</key>
  <dict>
    <key>FIRECLAW_PORT</key><string>$PORT</string>
    <key>FIRECLAW_BIND</key><string>$BIND</string>
    <key>FIRECLAW_FORWARD</key><string>$FORWARD</string>
  </dict>
  <key>RunAtLoad</key><true/>
  <key>KeepAlive</key><true/>
  <key>StandardOutPath</key><string>$HOME/.fireclaw/stdout.log</string>
  <key>StandardErrorPath</key><string>$HOME/.fireclaw/stderr.log</string>
</dict>
</plist>
PLIST
  mkdir -p "$HOME/.fireclaw"
  launchctl unload "$plist" 2>/dev/null || true
  launchctl load "$plist"
  ok "FireClaw installed as launchd agent: com.urantios.fireclaw"
  sleep 1
  status
}

install_systemd() {
  need_python
  local svc="$HOME/.config/systemd/user/fireclaw.service"
  mkdir -p "$(dirname "$svc")" "$HOME/.fireclaw"
  cat > "$svc" <<UNIT
[Unit]
Description=FireClaw hot-line daemon (UrantiOS)
After=network-online.target

[Service]
Type=simple
Environment=FIRECLAW_PORT=$PORT
Environment=FIRECLAW_BIND=$BIND
Environment=FIRECLAW_FORWARD=$FORWARD
ExecStart=/usr/bin/env python3 $DAEMON
Restart=always
RestartSec=3

[Install]
WantedBy=default.target
UNIT
  systemctl --user daemon-reload
  systemctl --user enable --now fireclaw.service
  ok "FireClaw installed as systemd --user service: fireclaw.service"
  sleep 1
  status
}

do_install() {
  case "$(uname -s)" in
    Darwin) install_launchd ;;
    Linux)  install_systemd ;;
    *)      err "unsupported OS: $(uname -s)"; exit 1 ;;
  esac
}

do_stop() {
  case "$(uname -s)" in
    Darwin)
      launchctl unload "$HOME/Library/LaunchAgents/com.urantios.fireclaw.plist" 2>/dev/null || true
      ok "FireClaw (launchd) stopped"
      ;;
    Linux)
      systemctl --user stop fireclaw.service 2>/dev/null || true
      ok "FireClaw (systemd) stopped"
      ;;
  esac
}

case "$cmd" in
  run|fg|foreground) run_fg ;;
  install)           do_install ;;
  status)            status ;;
  stop)              do_stop ;;
  *) err "unknown command: $cmd"; echo "usage: $0 {run|install|status|stop}"; exit 2 ;;
esac
