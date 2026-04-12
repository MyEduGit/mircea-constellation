#!/bin/bash
set -e
cd /home/mircea/nemoclaw

echo "Step 1: Enabling n8n REST API..."
cat > docker-compose.override.yml << 'EOF'
services:
  n8n:
    environment:
      - N8N_SECURE_COOKIE=false
      - N8N_API_KEY=openclaw-ga-2026
EOF

echo "Step 2: Restarting n8n..."
docker compose restart n8n

echo "Waiting 15 seconds for n8n to start..."
sleep 15

echo "Step 3: Importing AI Supervisor workflow..."
RESP=$(curl -s -o /tmp/import-result.json -w "%{http_code}" \
  -X POST "http://localhost:5678/api/v1/workflows" \
  -H "X-N8N-API-KEY: openclaw-ga-2026" \
  -H "Content-Type: application/json" \
  -d @/tmp/ai-supervisor-v2.json)

if [ "$RESP" = "200" ] || [ "$RESP" = "201" ]; then
  echo "SUCCESS: AI Universe Supervisor imported into n8n!"
  echo "It will run daily at 8am and send Telegram reports."
else
  echo "Status: $RESP"
  cat /tmp/import-result.json
  echo ""
  echo "Workflow is at /tmp/ai-supervisor-v2.json if you want to import manually."
fi
