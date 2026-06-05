#!/usr/bin/env bash
# =============================================================================
# NemoClaw Observer — n8n workflow import via REST API
# No browser / UI required.
#
# Prerequisites:
#   - n8n running at http://46.225.51.30:5678
#   - n8n API key (Settings → API → Create API Key in the n8n UI)
#
# Usage:
#   N8N_API_KEY=your_key bash n8n_import.sh
# OR set N8N_API_KEY in your .env and run:
#   source /opt/nemoclaw/.env && bash /opt/nemoclaw/nemoclaw_observer/n8n_import.sh
# =============================================================================
set -euo pipefail

INSTALL_DIR="/opt/nemoclaw"
WORKFLOW_FILE="$INSTALL_DIR/nemoclaw_observer/n8n_cron_workflow.json"
N8N_URL="http://46.225.51.30:5678"

GREEN='\033[0;32m'; YELLOW='\033[1;33m'; RED='\033[0;31m'; NC='\033[0m'
ok()   { echo -e "${GREEN}[OK]${NC} $*"; }
warn() { echo -e "${YELLOW}[WARN]${NC} $*"; }
fail() { echo -e "${RED}[FAIL]${NC} $*"; exit 1; }

# ── Validate ──────────────────────────────────────────────────────────────────
[ -z "${N8N_API_KEY:-}" ] && fail "N8N_API_KEY is not set. Get it from n8n UI → Settings → API → Create API Key"
[ -f "$WORKFLOW_FILE" ]  || fail "Workflow file not found: $WORKFLOW_FILE — run deploy.sh first"
command -v curl &>/dev/null || fail "curl is required"

echo ""
echo "============================================="
echo " NemoClaw Observer — n8n Workflow Import"
echo "============================================="
echo ""

# ── Check n8n is reachable ────────────────────────────────────────────────────
echo "Checking n8n at $N8N_URL ..."
if ! curl -sf "$N8N_URL/healthz" &>/dev/null; then
  warn "n8n healthz check failed — trying anyway"
else
  ok "n8n is reachable"
fi

# ── Import workflow ───────────────────────────────────────────────────────────
echo ""
echo "Importing workflow from $WORKFLOW_FILE ..."

RESPONSE=$(curl -s -w "\n%{http_code}" \
  -X POST "$N8N_URL/api/v1/workflows" \
  -H "X-N8N-API-KEY: $N8N_API_KEY" \
  -H "Content-Type: application/json" \
  -d @"$WORKFLOW_FILE")

HTTP_CODE=$(echo "$RESPONSE" | tail -1)
BODY=$(echo "$RESPONSE" | head -1)

if [ "$HTTP_CODE" != "200" ] && [ "$HTTP_CODE" != "201" ]; then
  echo "Response: $BODY"
  fail "Import failed (HTTP $HTTP_CODE). Check your N8N_API_KEY and that n8n is running."
fi

WORKFLOW_ID=$(echo "$BODY" | python3 -c "import sys,json; print(json.load(sys.stdin).get('id','unknown'))" 2>/dev/null || echo "unknown")
ok "Workflow imported (id=$WORKFLOW_ID)"

# ── Activate workflow ─────────────────────────────────────────────────────────
echo ""
echo "Activating workflow $WORKFLOW_ID ..."

if [ "$WORKFLOW_ID" = "unknown" ]; then
  warn "Could not extract workflow ID — activate manually in n8n UI"
else
  ACT_RESPONSE=$(curl -s -w "\n%{http_code}" \
    -X PATCH "$N8N_URL/api/v1/workflows/$WORKFLOW_ID" \
    -H "X-N8N-API-KEY: $N8N_API_KEY" \
    -H "Content-Type: application/json" \
    -d '{"active": true}')

  ACT_CODE=$(echo "$ACT_RESPONSE" | tail -1)
  if [ "$ACT_CODE" = "200" ]; then
    ok "Workflow activated — cron will fire every 6 hours"
  else
    warn "Activation call returned HTTP $ACT_CODE — check n8n UI to confirm active status"
  fi
fi

# ── Test webhook endpoint ─────────────────────────────────────────────────────
echo ""
echo "Testing manual webhook trigger..."
WEBHOOK_RESP=$(curl -s -o /dev/null -w "%{http_code}" "$N8N_URL/webhook/nemoclaw-dashboard" || echo "000")
if [ "$WEBHOOK_RESP" = "200" ]; then
  ok "Webhook endpoint responding at $N8N_URL/webhook/nemoclaw-dashboard"
else
  warn "Webhook returned HTTP $WEBHOOK_RESP — it becomes active after first cron trigger"
fi

echo ""
echo "============================================="
echo " n8n import done."
echo "============================================="
echo ""
echo "  Workflow ID : $WORKFLOW_ID"
echo "  Schedule    : every 6 hours"
echo "  Webhook     : $N8N_URL/webhook/nemoclaw-dashboard"
echo "  Verify      : open n8n UI → Workflows → NemoClaw Observer"
echo ""
