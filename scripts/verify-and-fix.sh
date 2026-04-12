#!/bin/bash
# verify-and-fix.sh — Verify N8N_ALLOW_EXEC and check all services

COMPOSE_DIR="/home/mircea/nemoclaw"

echo "=== Checking N8N_ALLOW_EXEC ==="
VAL=$(docker exec nemoclaw-n8n printenv N8N_ALLOW_EXEC 2>/dev/null || echo "NOT SET")
echo "N8N_ALLOW_EXEC = $VAL"

if [ "$VAL" != "true" ]; then
  echo ">>> NOT SET — adding it now..."
  cd $COMPOSE_DIR

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
  echo ">>> n8n restarted with N8N_ALLOW_EXEC=true"
else
  echo "OK - already set"
fi

echo ""
echo "=== All running Docker containers ==="
docker ps --format 'table {{.Names}}\t{{.Status}}\t{{.Ports}}'

echo ""
echo "=== Checking for Paperclip container ==="
if docker ps | grep -q paperclip; then
  echo "Paperclip is RUNNING"
  docker ps | grep paperclip
else
  echo "Paperclip is NOT running"
  echo "Checking if image exists..."
  docker images | grep paperclip || echo "No paperclip image found"
fi

echo ""
echo "=== Checking installed n8n community packages ==="
docker exec nemoclaw-postgres psql -U mircea -d nemoclaw -t -c "
SELECT package_name, installed_version FROM installed_packages;
" 2>/dev/null || echo "(none)"

echo ""
echo "=== Done ==="
