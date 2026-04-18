#!/bin/bash
cd /home/mircea/nemoclaw

cat > docker-compose.override.yml << 'EOF'
services:
  n8n:
    environment:
      - N8N_SECURE_COOKIE=false
      - N8N_USER_MANAGEMENT_DISABLED=true
      - N8N_DIAGNOSTICS_ENABLED=false
      - N8N_PERSONALIZATION_ENABLED=false
EOF

docker compose restart n8n
echo "Waiting for n8n to restart..."
sleep 12
echo "Done. Open http://localhost:5678 - no email needed now."
