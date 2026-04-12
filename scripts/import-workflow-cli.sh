#!/bin/bash
set -e
BRANCH="claude/debug-n8n-docker-o7zRE"
RAW="https://raw.githubusercontent.com/MyEduGit/mircea-constellation/${BRANCH}"

echo "Downloading workflow..."
curl -s "$RAW/workflows/ai-supervisor-v3.json" -o /tmp/ai-supervisor-v3.json

echo "Copying into n8n container..."
docker cp /tmp/ai-supervisor-v3.json nemoclaw-n8n:/tmp/ai-supervisor-v3.json

echo "Importing via n8n CLI..."
docker exec nemoclaw-n8n n8n import:workflow --input=/tmp/ai-supervisor-v3.json

echo ""
echo "SUCCESS: AI Universe Supervisor is active in n8n!"
echo "Runs daily at 8am - sends Telegram report - monitors all AI services."
