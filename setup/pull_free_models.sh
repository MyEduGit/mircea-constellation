#!/usr/bin/env bash
# Pull all free Council models on URANTiOS via SSH.
# Replaces paid/depleted seats with local Ollama models.
#
# Seat 3  (Spirit)       → qwen3:8b      — broad reasoning, context, integration
# Seat 6  (Son-Spirit)   → qwen2.5-coder:7b — code specialist, engineering precision
# Seat 7  (Trinity)      → mistral:7b    — creative horizon, outer awareness
# Seat 4  (Father-Son)   → gemma4:e4b    — already installed ✓
# Seat 5  (Father-Spirit)→ deepseek-r1:7b — already installed ✓
#
# Usage (from iMac):
#   bash setup/pull_free_models.sh

URANTIOS="root@204.168.143.98"
G="\033[32m"; C="\033[36m"; Y="\033[33m"; R="\033[31m"; B="\033[1m"; E="\033[0m"

echo -e "\n${B}=== Pulling Free Council Models on URANTiOS ===${E}"
echo -e "${C}Server: 204.168.143.98 (URANTiOS / Hetzner Helsinki)${E}"
echo -e "${Y}This may take 10-20 minutes — ~12GB total download${E}\n"

ssh -o ConnectTimeout=15 "$URANTIOS" '
set -e
echo "▶ Currently installed models:"
ollama list
echo ""

# Seat 3: Spirit — broad knowledge, contextual integration
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "▶ Seat 3 (Spirit) — pulling qwen3:8b ..."
if ollama list | grep -q "qwen3:8b"; then
    echo "  ✓ qwen3:8b already installed — skipping"
else
    ollama pull qwen3:8b
    echo "  ✓ qwen3:8b installed"
fi
echo ""

# Seat 6: Son-Spirit — engineering, code specialist
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "▶ Seat 6 (Son-Spirit) — pulling qwen2.5-coder:7b ..."
if ollama list | grep -q "qwen2.5-coder:7b"; then
    echo "  ✓ qwen2.5-coder:7b already installed — skipping"
else
    ollama pull qwen2.5-coder:7b
    echo "  ✓ qwen2.5-coder:7b installed"
fi
echo ""

# Seat 7: Trinity — outer awareness, creative horizon
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "▶ Seat 7 (Trinity) — pulling mistral:7b ..."
if ollama list | grep -q "mistral:7b"; then
    echo "  ✓ mistral:7b already installed — skipping"
else
    ollama pull mistral:7b
    echo "  ✓ mistral:7b installed"
fi
echo ""

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "▶ Quick smoke test — all new models:"
echo ""

echo "── qwen3:8b (Seat 3 / Spirit):"
ollama run qwen3:8b "Reply in one sentence: what is universal mind?" --nowordwrap 2>/dev/null | head -2
echo ""

echo "── qwen2.5-coder:7b (Seat 6 / Son-Spirit):"
ollama run qwen2.5-coder:7b "Reply in one sentence: what is a Python generator?" --nowordwrap 2>/dev/null | head -2
echo ""

echo "── mistral:7b (Seat 7 / Trinity):"
ollama run mistral:7b "Reply in one sentence: what lies at the edge of the known universe?" --nowordwrap 2>/dev/null | head -2
echo ""

echo "▶ All installed models:"
ollama list
'

echo -e "\n${G}✓ All free models ready on URANTiOS.${E}"
echo -e "${C}Next: run wire_all_free_seats.py to connect them to n8n${E}\n"
