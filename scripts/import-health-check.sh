#!/bin/bash
set -e

cat > /tmp/health-check.json << 'JSONEOF'
{
  "id": "openclaw-health-check-001",
  "name": "OpenClaw Health Check",
  "nodes": [
    {
      "parameters": {},
      "id": "n1",
      "name": "Manual Trigger",
      "type": "n8n-nodes-base.manualTrigger",
      "typeVersion": 1,
      "position": [240, 304]
    },
    {
      "parameters": {
        "command": "docker ps --format '{{.Names}} | {{.Status}}' | grep nemoclaw || echo 'no-containers'"
      },
      "id": "n2",
      "name": "Docker PS",
      "type": "n8n-nodes-base.executeCommand",
      "typeVersion": 1,
      "position": [480, 160]
    },
    {
      "parameters": {
        "command": "ls -t $HOME/.openclaw/paperclip/proofs/$(date +%Y-%m-%d)/ 2>/dev/null | head -5 || echo 'no-proofs-today'"
      },
      "id": "n3",
      "name": "Latest Proofs",
      "type": "n8n-nodes-base.executeCommand",
      "typeVersion": 1,
      "position": [480, 304]
    },
    {
      "parameters": {
        "command": "printf 'RAM: %s\\n' \"$(free -h | awk '/Mem/{print $3\"/\"$2}')\"; printf 'Disk: %s\\n' \"$(df -h / | tail -1 | awk '{print $3\"/\"$2\" (\"$5\")\"}')\" "
      },
      "id": "n4",
      "name": "RAM and Disk",
      "type": "n8n-nodes-base.executeCommand",
      "typeVersion": 1,
      "position": [480, 448]
    },
    {
      "parameters": {
        "command": "curl -sf http://127.0.0.1:11434/api/tags | python3 -c \"import sys,json; [print(m['name']) for m in json.load(sys.stdin)['models']]\" 2>/dev/null || echo 'ollama-unreachable'"
      },
      "id": "n5",
      "name": "Ollama Models",
      "type": "n8n-nodes-base.executeCommand",
      "typeVersion": 1,
      "position": [480, 592]
    },
    {
      "parameters": {
        "jsCode": "var ts = new Date().toISOString();\nvar labels = ['containers','proofs','system','ollama'];\nvar all = $input.all();\nvar results = [];\nfor (var i = 0; i < all.length; i++) {\n  var out = all[i].json.stdout || all[i].json.stderr || 'no output';\n  results.push('=== ' + (labels[i] || i) + ' ===\\n' + out);\n}\nreturn [{ json: { report: results.join('\\n\\n'), generated: ts } }];"
      },
      "id": "n6",
      "name": "Format Report",
      "type": "n8n-nodes-base.code",
      "typeVersion": 2,
      "position": [768, 384]
    }
  ],
  "connections": {
    "Manual Trigger": {
      "main": [[{"node": "Docker PS", "type": "main", "index": 0},{"node": "Latest Proofs", "type": "main", "index": 0},{"node": "RAM and Disk", "type": "main", "index": 0},{"node": "Ollama Models", "type": "main", "index": 0}]]
    },
    "Docker PS": {"main": [[{"node": "Format Report", "type": "main", "index": 0}]]},
    "Latest Proofs": {"main": [[{"node": "Format Report", "type": "main", "index": 0}]]},
    "RAM and Disk": {"main": [[{"node": "Format Report", "type": "main", "index": 0}]]},
    "Ollama Models": {"main": [[{"node": "Format Report", "type": "main", "index": 0}]]}
  },
  "active": false,
  "settings": {"executionOrder": "v1"}
}
JSONEOF

docker cp /tmp/health-check.json nemoclaw-n8n:/tmp/health-check.json
docker exec nemoclaw-n8n n8n import:workflow --input=/tmp/health-check.json
echo "Done! OpenClaw Health Check imported."
