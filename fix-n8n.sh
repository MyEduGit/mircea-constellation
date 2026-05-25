#!/bin/bash
set -e
cd /home/mircea/nemoclaw
cat > docker-compose.override.yml << 'EOF'
services:
  n8n:
    environment:
      - N8N_SECURE_COOKIE=false
EOF
echo "Override file created."
docker compose down
docker compose up -d
echo "n8n restarted. Open http://localhost:5678 in Chrome/Firefox."
