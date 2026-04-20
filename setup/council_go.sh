#!/usr/bin/env bash
# Council Go — pulls all models + wires all n8n seats in one shot.
# Run once from iMac: bash setup/council_go.sh
#
# Does everything:
#   1. Pulls qwen3:8b, qwen2.5-coder:7b, mistral:7b on URANTiOS (if not already there)
#   2. Wires all 8 seats in n8n to free local Ollama
#   3. Reports final status

set -e
URANTIOS="root@204.168.143.98"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

G="\033[32m"; C="\033[36m"; Y="\033[33m"; R="\033[31m"; B="\033[1m"; E="\033[0m"
ok()   { echo -e "${G}✓${E} $*"; }
info() { echo -e "${C}▶${E} $*"; }
warn() { echo -e "${Y}⚠${E} $*"; }
err()  { echo -e "${R}✗${E} $*" >&2; exit 1; }

echo -e "\n${B}╔══════════════════════════════════════════════════╗${E}"
echo -e "${B}║   COUNCIL OF SEVEN — FULL DEPLOY                ║${E}"
echo -e "${B}║   Pull models + Wire all seats — \$0.00/run      ║${E}"
echo -e "${B}╚══════════════════════════════════════════════════╝${E}\n"

# Credentials
N8N_EMAIL="${N8N_EMAIL:-mircea8@me.com}"
if [ -z "$N8N_PASSWORD" ]; then
  read -rsp "n8n password: " N8N_PASSWORD; echo
fi
export N8N_EMAIL N8N_PASSWORD

# ── STEP 1: Pull models on URANTiOS ────────────────────────────────────────
echo -e "\n${B}STEP 1/2 — Pull free models on URANTiOS${E}"
echo -e "${Y}(skips models already installed)${E}\n"

ssh -o ConnectTimeout=15 -o StrictHostKeyChecking=no "$URANTIOS" '
MODELS="qwen3:8b qwen2.5-coder:7b mistral:7b"
for model in $MODELS; do
  if ollama list 2>/dev/null | grep -q "^${model}"; then
    echo "  ✓ $model already installed"
  else
    echo "  ▶ Pulling $model ..."
    ollama pull "$model" && echo "  ✓ $model done"
  fi
done
echo ""
echo "  Installed models:"
ollama list
' || err "SSH to URANTiOS failed. Check: ssh $URANTIOS"

echo ""
ok "Models ready on URANTiOS\n"

# ── STEP 2: Wire all seats in n8n ──────────────────────────────────────────
echo -e "${B}STEP 2/2 — Wire all 8 seats in n8n${E}\n"

python3 "$SCRIPT_DIR/fix_council_complete.py"

echo -e "\n${B}╔══════════════════════════════════════════════════╗${E}"
echo -e "${G}║   COUNCIL DEPLOYED — ALL SEATS LIVE — \$0.00     ║${E}"
echo -e "${B}╚══════════════════════════════════════════════════╝${E}"
echo ""
echo "  n8n UI  → http://46.225.51.30"
echo "  Ollama  → http://204.168.143.98:11434"
echo ""
echo -e "${C}  Open n8n, ask the Council a question, watch all 7 seats respond.${E}\n"
