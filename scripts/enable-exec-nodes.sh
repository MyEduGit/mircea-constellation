#!/bin/bash
cd /home/mircea/nemoclaw

cat > docker-compose.override.yml << 'EOF'
services:
  n8n:
    environment:
      - N8N_SECURE_COOKIE=false
      - N8N_USER_MANAGEMENT_DISABLED=true
      - EXECUTIONS_PROCESS=main
      - N8N_ALLOW_EXEC=true
EOF

docker compose restart n8n
echo "Waiting for n8n..."
sleep 12
echo "Done. Execute Command nodes are now enabled."
