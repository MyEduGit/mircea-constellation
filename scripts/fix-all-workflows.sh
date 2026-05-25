#!/bin/bash
# fix-all-workflows.sh — Diagnose and fix all n8n workflows
set -e

CONTAINER="nemoclaw-n8n"
COMPOSE_DIR="/home/mircea/nemoclaw"

echo "========================================"
echo "  OpenClaw n8n Workflow Fixer"
echo "========================================"

# Step 1: Show all node types across all workflows
echo ""
echo "--- All node types in all workflows ---"
docker exec nemoclaw-postgres psql -U mircea -d nemoclaw -t -A -c "
SELECT DISTINCT jsonb_array_elements(nodes)->>'type' as node_type
FROM workflow_entity
ORDER BY 1;
" 2>/dev/null

# Step 2: Show node types per workflow
echo ""
echo "--- Node types per workflow ---"
docker exec nemoclaw-postgres psql -U mircea -d nemoclaw -t -c "
SELECT
  name,
  jsonb_agg(DISTINCT jsonb_array_elements(nodes)->>'type') as node_types
FROM workflow_entity
GROUP BY name
ORDER BY name;
" 2>/dev/null

# Step 3: Show NanoClaw Dashboard full JSON
echo ""
echo "--- NanoClaw Dashboard full node list ---"
docker exec nemoclaw-postgres psql -U mircea -d nemoclaw -t -c "
SELECT jsonb_pretty(nodes)
FROM workflow_entity
WHERE name='NanoClaw Dashboard';
" 2>/dev/null

# Step 4: Find non-standard node types (possible community nodes)
echo ""
echo "--- Non-standard / community node types ---"
docker exec nemoclaw-postgres psql -U mircea -d nemoclaw -t -A -c "
SELECT DISTINCT jsonb_array_elements(nodes)->>'type' as node_type
FROM workflow_entity
WHERE jsonb_array_elements(nodes)->>'type' NOT LIKE 'n8n-nodes-base.%'
AND jsonb_array_elements(nodes)->>'type' NOT LIKE '@n8n/%'
ORDER BY 1;
" 2>/dev/null

echo ""
echo "========================================"
echo "  Paste the output above to Claude"
echo "========================================"
