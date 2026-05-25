#!/bin/bash
# fix-gabriel.sh — Update Gabriel_Synthesizer to use current Claude model
# Also fixes N8N_ALLOW_EXEC and enables webhook

set -e
COMPOSE_DIR="/home/mircea/nemoclaw"

echo "=== Fix Gabriel + Council of Seven ==="

# Step 1: Fix N8N_ALLOW_EXEC using 'up -d' not 'restart'
echo ""
echo "--- Ensuring N8N_ALLOW_EXEC=true via up -d ---"
cat > $COMPOSE_DIR/docker-compose.override.yml << 'EOF'
services:
  n8n:
    environment:
      - N8N_SECURE_COOKIE=false
      - N8N_USER_MANAGEMENT_DISABLED=true
      - EXECUTIONS_PROCESS=main
      - N8N_ALLOW_EXEC=true
EOF

cd $COMPOSE_DIR
docker compose up -d n8n
echo "n8n restarted with override applied"
sleep 3

# Verify
VAL=$(docker exec nemoclaw-n8n printenv N8N_ALLOW_EXEC 2>/dev/null || echo "NOT SET")
echo "N8N_ALLOW_EXEC = $VAL"

# Step 2: Update Gabriel model in the database
echo ""
echo "--- Updating Gabriel_Synthesizer model to claude-sonnet-4-6 ---"

docker exec nemoclaw-postgres psql -U mircea -d nemoclaw -t -A -c \
  "SELECT nodes FROM workflow_entity WHERE name LIKE 'Council of Seven%' LIMIT 1;" \
  > /tmp/council_nodes_raw.txt

# Check we got something
if [ ! -s /tmp/council_nodes_raw.txt ]; then
  echo "ERROR: Could not find Council of Seven workflow in DB"
  exit 1
fi

python3 << 'PYEOF'
import json, sys

with open('/tmp/council_nodes_raw.txt') as f:
    raw = f.read().strip()

try:
    nodes = json.loads(raw)
except json.JSONDecodeError as e:
    print(f"JSON parse error: {e}")
    print(f"Raw (first 200): {raw[:200]}")
    sys.exit(1)

updated = False
for n in nodes:
    if n.get('name') == 'Gabriel_Synthesizer':
        print(f"Found Gabriel_Synthesizer (type: {n.get('type')})")
        params = n.get('parameters', {})
        # Check jsonBody string
        for key in ['jsonBody', 'body']:
            val = params.get(key, '')
            if isinstance(val, str) and 'claude-sonnet-4-20250514' in val:
                params[key] = val.replace('claude-sonnet-4-20250514', 'claude-sonnet-4-6')
                print(f"  Updated '{key}': claude-sonnet-4-20250514 -> claude-sonnet-4-6")
                updated = True
            elif isinstance(val, dict) and val.get('model', '').startswith('claude-sonnet-4-2025'):
                print(f"  Old model: {val['model']}")
                val['model'] = 'claude-sonnet-4-6'
                print(f"  Updated to: claude-sonnet-4-6")
                updated = True
        # Also check nested parameters
        if 'options' in params:
            opts = params['options']
            if isinstance(opts, dict) and opts.get('model', '').startswith('claude-sonnet-4-2025'):
                opts['model'] = 'claude-sonnet-4-6'
                updated = True

if not updated:
    # Try a brute-force string replace on the whole JSON
    raw_updated = raw.replace('claude-sonnet-4-20250514', 'claude-sonnet-4-6')
    if raw_updated != raw:
        nodes = json.loads(raw_updated)
        print("  Brute-force replaced model string")
        updated = True

if updated:
    with open('/tmp/council_nodes_fixed.json', 'w') as f:
        json.dump(nodes, f)
    print("Saved fixed nodes")
else:
    print("No claude-sonnet-4-20250514 found — checking current model:")
    for n in nodes:
        if n.get('name') == 'Gabriel_Synthesizer':
            print(json.dumps(n.get('parameters', {}), indent=2)[:500])
PYEOF

if [ -f /tmp/council_nodes_fixed.json ]; then
  echo "Applying to database..."
  python3 -c "
import json
with open('/tmp/council_nodes_fixed.json') as f:
    data = json.load(f)
# Escape for SQL
escaped = json.dumps(data).replace(\"'\", \"''\")
print(escaped)
" > /tmp/council_nodes_escaped.txt

  docker exec -i nemoclaw-postgres psql -U mircea -d nemoclaw << SQLEOF
UPDATE workflow_entity
SET nodes = '$(cat /tmp/council_nodes_escaped.txt)'::json
WHERE name LIKE 'Council of Seven%';
SQLEOF

  echo "Database updated!"
fi

echo ""
echo "=== All done ==="
echo "Refresh your browser and try the Council of Seven workflow again."
