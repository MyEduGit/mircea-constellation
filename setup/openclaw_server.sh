#!/usr/bin/env bash
# OpenClaw Server Setup — Mircea Constellation (Mission Control Dashboard)
# Target host: Hetzner CPX22 — 46.225.51.30 (Nuremberg, DE), user: mircea
# UrantiOS governed — Truth, Beauty, Goodness
#
# Deploys the static mission-control dashboard (index.html + status.json) on
# OpenClaw behind nginx on port 18789. Idempotent: safe to re-run.
#
# Usage (on OpenClaw as user `mircea`):
#   curl -fsSL https://raw.githubusercontent.com/myedugit/mircea-constellation/main/setup/openclaw_server.sh | bash
#   # or, after cloning:
#   bash setup/openclaw_server.sh

set -euo pipefail

CYAN='\033[0;36m'; GREEN='\033[0;32m'; RED='\033[0;31m'; YELLOW='\033[1;33m'; NC='\033[0m'
info()  { echo -e "${CYAN}[INFO]${NC}  $*"; }
ok()    { echo -e "${GREEN}[OK]${NC}    $*"; }
warn()  { echo -e "${YELLOW}[WARN]${NC}  $*"; }
fail()  { echo -e "${RED}[FAIL]${NC}  $*"; exit 1; }

REPO_URL="https://github.com/myedugit/mircea-constellation.git"
REPO_DIR="${HOME}/mircea-constellation"
WEB_ROOT="/var/www/constellation"
NGINX_SITE="/etc/nginx/sites-available/constellation"
NGINX_LINK="/etc/nginx/sites-enabled/constellation"
PORT="18789"

echo ""
echo "================================================="
echo "  OpenClaw Server Setup — Mission Control"
echo "  Host: 46.225.51.30  Port: ${PORT}"
echo "  Governed by: Truth · Beauty · Goodness"
echo "================================================="
echo ""

# ── 0. Sanity ───────────────────────────────────────────────────────────────
[ "$(id -un)" != "root" ] || fail "Do not run as root. Run as 'mircea'; the script uses sudo where needed."
command -v sudo >/dev/null || fail "sudo is required."

# ── 1. APT packages ─────────────────────────────────────────────────────────
info "[1/5] Installing system packages (nginx, git, rsync, jq)..."
sudo apt-get update -qq
sudo DEBIAN_FRONTEND=noninteractive apt-get install -y -qq nginx git rsync jq curl ca-certificates
ok "Packages installed."

# ── 2. Clone / refresh repo ─────────────────────────────────────────────────
info "[2/5] Syncing repo to ${REPO_DIR}..."
if [ ! -d "${REPO_DIR}/.git" ]; then
  git clone "${REPO_URL}" "${REPO_DIR}"
  ok "Cloned."
else
  git -C "${REPO_DIR}" pull --ff-only || warn "Could not fast-forward — leaving working tree as-is."
  ok "Repo up to date."
fi

# ── 3. Deploy static assets ─────────────────────────────────────────────────
info "[3/5] Deploying static assets to ${WEB_ROOT}..."
sudo mkdir -p "${WEB_ROOT}"
sudo rsync -a --delete \
  --include='index.html' \
  --include='status.json' \
  --include='*.css' \
  --include='*.js' \
  --include='assets/***' \
  --exclude='*' \
  "${REPO_DIR}/" "${WEB_ROOT}/"
sudo chown -R www-data:www-data "${WEB_ROOT}"
ok "Assets deployed."

# ── 4. nginx site ───────────────────────────────────────────────────────────
info "[4/5] Configuring nginx on port ${PORT}..."
sudo tee "${NGINX_SITE}" >/dev/null << NGINXEOF
# Mircea's Constellation — governed by UrantiOS (Truth, Beauty, Goodness)
server {
    listen ${PORT};
    listen [::]:${PORT};
    server_name _;

    root ${WEB_ROOT};
    index index.html;

    # status.json is refreshed often — no-cache so the dashboard sees updates.
    location = /status.json {
        add_header Cache-Control "no-store, no-cache, must-revalidate";
        try_files \$uri =404;
    }

    location / {
        try_files \$uri \$uri/ =404;
    }

    access_log /var/log/nginx/constellation.access.log;
    error_log  /var/log/nginx/constellation.error.log;
}
NGINXEOF

sudo ln -sf "${NGINX_SITE}" "${NGINX_LINK}"
sudo nginx -t
sudo systemctl reload nginx || sudo systemctl restart nginx
ok "nginx reloaded."

# ── 5. Firewall (ufw, if present) ───────────────────────────────────────────
info "[5/5] Opening port ${PORT} (if ufw active)..."
if command -v ufw >/dev/null && sudo ufw status | grep -q "Status: active"; then
  sudo ufw allow "${PORT}/tcp" || true
  ok "ufw rule added."
else
  warn "ufw not active — skipping. Ensure Hetzner firewall allows tcp/${PORT}."
fi

# ── Proof ───────────────────────────────────────────────────────────────────
info "Verifying..."
if curl -fsS "http://127.0.0.1:${PORT}/status.json" >/dev/null; then
  ok "Dashboard reachable locally: http://127.0.0.1:${PORT}/"
else
  warn "Local probe failed — check /var/log/nginx/constellation.error.log"
fi

echo ""
echo "================================================="
echo "  OpenClaw Mission Control Online"
echo "================================================="
echo ""
echo "  Public URL: http://46.225.51.30:${PORT}/"
echo "  Web root:   ${WEB_ROOT}"
echo "  nginx site: ${NGINX_SITE}"
echo ""
echo "  Refresh status.json from the repo (cron-friendly):"
echo "    bash ${REPO_DIR}/setup/openclaw_server.sh"
echo ""
echo "  UrantiOS governed — Truth, Beauty, Goodness"
echo ""
