#!/usr/bin/env bash
# Pull qwen3:8b on URANTiOS for Seat 4 (Father-Son)
# Run from iMac: bash <(curl -fsSL ...)

G="\033[32m"; C="\033[36m"; Y="\033[33m"; B="\033[1m"; E="\033[0m"

echo -e "\n${B}=== Pulling qwen3:8b on URANTiOS (Seat 4) ===${E}"
echo -e "${Y}This will take a few minutes — model is ~5GB${E}\n"

ssh -o ConnectTimeout=10 root@204.168.143.98 '
    echo "▶ Starting ollama pull qwen3:8b..."
    ollama pull qwen3:8b
    echo ""
    echo "▶ Installed models:"
    ollama list
    echo ""
    echo "▶ Testing qwen3:8b..."
    ollama run qwen3:8b "Reply in one sentence: what is the Trinity?" --nowordwrap 2>/dev/null | head -3
'

echo -e "\n${G}✓ Done. Seat 4 (qwen3:8b) ready on URANTiOS.${E}\n"
