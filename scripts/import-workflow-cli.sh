#!/bin/bash
# Import n8n workflow using the n8n built-in CLI (no API key needed)
set -e

BRANCH="claude/debug-n8n-docker-o7zRE"
RAW="https://raw.githubusercontent.com/MyEduGit/mircea-constellation/${BRANCH}"

echo "Downloading workflow..."
curl -s "$RAW/workflows/ai-supervisor-v2.json" -o /tmp/ai-supervisor-v2.json

echo "Copying workflow into n8n container..."
docker cp /tmp/ai-supervisor-v2.json nemoclaw-n8n:/tmp/ai-supervisor-v2.json

echo "Importing via n8n CLI..."
docker exec nemoclaw-n8n n8n import:workflow --input=/tmp/ai-supervisor-v2.json

echo ""
echo "SUCCESS: AI Universe Supervisor is now in n8n!"
echo "It runs daily at 8am and sends Telegram reports."
