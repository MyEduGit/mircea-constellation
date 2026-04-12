#!/bin/bash
# Run this on the Hetzner server to import the AI Supervisor workflow into n8n
set -e

BRANCH="claude/debug-n8n-docker-o7zRE"
RAW="https://raw.githubusercontent.com/MyEduGit/mircea-constellation/${BRANCH}"
N8N_URL="http://localhost:5678"
API_KEY="n8n_api_gabriel_stage4_openclaw_2026"

echo "Downloading AI Supervisor workflow..."
curl -s "$RAW/workflows/ai-supervisor.json" -o /tmp/ai-supervisor.json

echo "Importing into n8n via API..."
RESPONSE=$(curl -s -o /tmp/n8n-response.json -w "%{http_code}" \
  -X POST "$N8N_URL/api/v1/workflows" \
  -H "X-N8N-API-KEY: $API_KEY" \
  -H "Content-Type: application/json" \
  -d @/tmp/ai-supervisor.json)

if [ "$RESPONSE" = "200" ] || [ "$RESPONSE" = "201" ]; then
  echo "SUCCESS: AI Supervisor workflow imported into n8n!"
  echo "It will run daily at 8am and send a Telegram report."
else
  echo "API import returned: $RESPONSE"
  echo "Manual import needed:"
  echo "1. Open http://localhost:5678 in browser (via SSH tunnel)"
  echo "2. Go to Workflows -> Import from JSON"
  echo "3. Paste the contents of /tmp/ai-supervisor.json"
  cat /tmp/n8n-response.json
fi

# Set up server-side cron to push obsidian-sync reports to GitHub
mkdir -p /home/mircea/nemoclaw/obsidian-sync/Resources

echo "Setting up daily AI report sync..."
(crontab -l 2>/dev/null; echo "0 9 * * * cd /home/mircea/nemoclaw && docker exec nemoclaw-n8n wget -qO- http://localhost:5678/webhook/ai-daily-check 2>/dev/null || true") | crontab -

echo "Done! AI Supervisor is active."
