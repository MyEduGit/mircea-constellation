#!/usr/bin/env bash
# =============================================================================
# NemoClaw Observer — One-shot VPS deploy script
# Run this on 46.225.51.30 as the user that runs your bots.
#
# Usage:
#   curl -sSL https://raw.githubusercontent.com/MyEduGit/mircea-constellation/claude/nemoclaw-observer-dashboard-sfT8m/nemoclaw_observer/deploy.sh | bash
# OR clone first and run locally:
#   bash /opt/nemoclaw/nemoclaw_observer/deploy.sh
# =============================================================================
set -euo pipefail

BRANCH="claude/nemoclaw-observer-dashboard-sfT8m"
INSTALL_DIR="/opt/nemoclaw"
REPO_URL="https://github.com/MyEduGit/mircea-constellation.git"
ENV_FILE="$INSTALL_DIR/.env"

GREEN='\033[0;32m'; YELLOW='\033[1;33m'; RED='\033[0;31m'; NC='\033[0m'
ok()   { echo -e "${GREEN}[OK]${NC} $*"; }
warn() { echo -e "${YELLOW}[WARN]${NC} $*"; }
fail() { echo -e "${RED}[FAIL]${NC} $*"; exit 1; }

echo ""
echo "============================================="
echo " NemoClaw Observer — VPS Deploy"
echo "============================================="
echo ""

# ── Step 1: Clone or update ───────────────────────────────────────────────────
if [ -d "$INSTALL_DIR/.git" ]; then
  echo "Updating existing install at $INSTALL_DIR ..."
  git -C "$INSTALL_DIR" fetch origin
  git -C "$INSTALL_DIR" checkout "$BRANCH"
  git -C "$INSTALL_DIR" pull origin "$BRANCH"
  ok "Repo updated"
else
  echo "Fresh clone into $INSTALL_DIR ..."
  git clone -b "$BRANCH" "$REPO_URL" "$INSTALL_DIR"
  ok "Repo cloned"
fi

# ── Step 2: Python dependencies ───────────────────────────────────────────────
echo ""
echo "Installing Python dependencies..."
pip3 install -q -r "$INSTALL_DIR/nemoclaw_observer/requirements.txt"
ok "Python deps installed (requests, psycopg2-binary, redis)"

# ── Step 3: .env setup ────────────────────────────────────────────────────────
echo ""
if [ ! -f "$ENV_FILE" ]; then
  cp "$INSTALL_DIR/nemoclaw_observer/config.env.example" "$ENV_FILE"
  warn ".env created at $ENV_FILE"
  echo ""
  echo "  *** ACTION REQUIRED — fill in these values in $ENV_FILE:"
  echo ""
  echo "    PG_DSN=postgresql://postgres:YOUR_PASSWORD@46.225.51.30:5432/amep_schema_v1"
  echo "    TELEGRAM_TOKEN=your_bot_token_from_BotFather"
  echo "    TELEGRAM_CHAT=828807562"
  echo ""
  echo "  Then re-run this script: bash $INSTALL_DIR/nemoclaw_observer/deploy.sh"
  echo ""
  exit 0
fi
ok ".env already exists — loading"

# Load env vars
set -a
# shellcheck disable=SC1090
source "$ENV_FILE"
set +a

# ── Step 4: Database schema ───────────────────────────────────────────────────
echo ""
echo "Applying database schema to PostgreSQL..."
if command -v psql &>/dev/null; then
  psql "$PG_DSN" -f "$INSTALL_DIR/nemoclaw_observer/schema.sql" \
    && ok "Schema applied — nemoclaw_dashboard_log table ready" \
    || warn "Schema apply failed — check PG_DSN in .env and try manually:"
  echo "  psql \"$PG_DSN\" -f $INSTALL_DIR/nemoclaw_observer/schema.sql"
else
  warn "psql not found — apply schema manually:"
  echo "  psql \"$PG_DSN\" -f $INSTALL_DIR/nemoclaw_observer/schema.sql"
fi

# ── Step 5: Smoke test ────────────────────────────────────────────────────────
echo ""
echo "Running smoke test (print mode — no Telegram, no DB write)..."
echo "--------------------------------------------------------------"
cd "$INSTALL_DIR"
python3 nemoclaw_observer/observer.py
echo "--------------------------------------------------------------"
ok "Smoke test complete"

# ── Step 6: Next steps ────────────────────────────────────────────────────────
echo ""
echo "============================================="
echo " Deploy complete. Two steps remain:"
echo "============================================="
echo ""
echo "  1. Import n8n workflow (run this next):"
echo "     bash $INSTALL_DIR/nemoclaw_observer/n8n_import.sh"
echo ""
echo "  2. Wire /dashboard into hetzy_phd.py (run this next):"
echo "     python3 $INSTALL_DIR/nemoclaw_observer/hetzy_phd_patch.py /path/to/hetzy_phd.py"
echo ""
echo "  Full dashboard test (posts to Telegram):"
echo "     cd $INSTALL_DIR && python3 nemoclaw_observer/observer.py telegram"
echo ""
