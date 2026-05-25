#!/bin/bash
# Fixed server setup script
BRANCH="claude/debug-n8n-docker-o7zRE"
RAW="https://raw.githubusercontent.com/MyEduGit/mircea-constellation/${BRANCH}"

# Use correct server path
DIR="/home/mircea/nemoclaw/obsidian-reports"
mkdir -p "$DIR" 2>/dev/null || mkdir -p "/root/obsidian-reports" && DIR="/root/obsidian-reports"

echo "Report folder: $DIR"

# Download workflow JSON
curl -s "$RAW/workflows/ai-supervisor-v2.json" -o /tmp/ai-supervisor-v2.json
echo "Workflow downloaded to /tmp/ai-supervisor-v2.json"

# Try n8n API import (try both basic auth and API key)
RESP=$(curl -s -o /tmp/n8n-resp.json -w "%{http_code}" \
  -X POST "http://localhost:5678/api/v1/workflows" \
  -H "Content-Type: application/json" \
  -u "mircea:mircea8" \
  -d @/tmp/ai-supervisor-v2.json 2>/dev/null)

if [ "$RESP" = "200" ] || [ "$RESP" = "201" ]; then
  echo "SUCCESS: Workflow imported into n8n!"
else
  echo "Auto-import not available (status: $RESP)"
  echo ""
  echo "=== ONE MANUAL STEP NEEDED ==="
  echo "1. Open http://localhost:5678 in Chrome/Firefox"
  echo "2. Click the + button -> Import from JSON"
  echo "3. Run this to get the JSON to paste:"
  echo "   cat /tmp/ai-supervisor-v2.json"
fi

# Set up daily cron for reports
(crontab -l 2>/dev/null | grep -v ai-report; echo "0 8 * * * curl -s http://localhost:5678/webhook/ai-daily 2>/dev/null") | crontab -

echo "Done."
