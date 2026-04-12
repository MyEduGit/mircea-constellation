#!/bin/bash
# probe-db.sh — Inspect actual n8n database schema

echo "=== Tables in nemoclaw DB ==="
docker exec nemoclaw-postgres psql -U mircea -d nemoclaw -t -c "\dt"

echo ""
echo "=== Columns in workflow_entity ==="
docker exec nemoclaw-postgres psql -U mircea -d nemoclaw -t -c "
SELECT column_name, data_type
FROM information_schema.columns
WHERE table_name = 'workflow_entity'
ORDER BY ordinal_position;
"

echo ""
echo "=== First workflow name and raw nodes sample ==="
docker exec nemoclaw-postgres psql -U mircea -d nemoclaw -t -c "
SELECT name, left(nodes::text, 300)
FROM workflow_entity
LIMIT 3;
"
