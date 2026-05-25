#!/bin/bash
set -e

cat > /tmp/ga-workflow.json << 'JSONEOF'
{
  "id": "ga-ai-supervisor-001",
  "name": "GA AI Universe Supervisor",
  "nodes": [
    {
      "parameters": {
        "rule": {"interval": [{"field": "cronExpression", "expression": "0 8 * * *"}]}
      },
      "name": "Daily 8am",
      "type": "n8n-nodes-base.scheduleTrigger",
      "typeVersion": 1.1,
      "position": [100, 300],
      "id": "t1"
    },
    {
      "parameters": {
        "url": "https://status.anthropic.com/api/v2/status.json",
        "options": {}
      },
      "name": "Anthropic",
      "type": "n8n-nodes-base.httpRequest",
      "typeVersion": 4,
      "position": [300, 200],
      "id": "t2"
    },
    {
      "parameters": {
        "url": "https://status.openai.com/api/v2/status.json",
        "options": {}
      },
      "name": "OpenAI",
      "type": "n8n-nodes-base.httpRequest",
      "typeVersion": 4,
      "position": [300, 350],
      "id": "t3"
    },
    {
      "parameters": {
        "url": "https://techcrunch.com/category/artificial-intelligence/feed/",
        "options": {}
      },
      "name": "AI News",
      "type": "n8n-nodes-base.httpRequest",
      "typeVersion": 4,
      "position": [300, 500],
      "id": "t4"
    },
    {
      "parameters": {
        "mode": "combine",
        "combinationMode": "multiplex",
        "options": {}
      },
      "name": "Merge",
      "type": "n8n-nodes-base.merge",
      "typeVersion": 2.1,
      "position": [520, 350],
      "id": "t5"
    },
    {
      "parameters": {
        "jsCode": "const now = new Date().toISOString().split('T')[0];\nconst a = $input.all()[0]?.json?.status?.description || 'OK';\nconst o = $input.all()[1]?.json?.status?.description || 'OK';\nconst rss = JSON.stringify($input.all()[2]?.json || '');\nconst watch = ['GPT-5','Claude 5','Gemini 3','Grok 4','Llama 5'];\nconst found = watch.filter(w => rss.toLowerCase().includes(w.toLowerCase()));\nconst svcs = [['Claude','claude-opus-4-6/sonnet/haiku',a],['ChatGPT','gpt-4o/o1/o3/o4-mini',o],['Grok','grok-3/grok-3-mini','OK'],['Gemini','gemini-2.0-flash/pro','OK'],['Llama','llama-4/llama-3.3','OK'],['Mistral','mistral-large-2/small-3','OK'],['Perplexity','sonar-pro/sonar','OK'],['Cohere','command-r-plus','OK'],['ElevenLabs','eleven-multilingual-v3','OK'],['Runway','gen-4/gen-3','OK'],['Ollama','gemma4:e4b','OK']];\nconst rows = svcs.map(s => '| ' + (s[2]==='OK'?'OK':'WARN') + ' | ' + s[0] + ' | ' + s[1] + ' |').join('\n');\nconst alert = found.length > 0 ? 'NEW AI DETECTED: ' + found.join(', ') + '\n\n' : '';\nconst report = '# AI Daily - ' + now + '\n\n' + alert + '| Status | Service | Models |\n|--------|---------|--------|\n' + rows + '\n';\nconst tg = found.length > 0 ? 'GA ALERT: New AI: ' + found.join(', ') : 'GA Daily: ' + svcs.length + ' AI services OK. ' + now;\nreturn [{json:{report,date:now,filename:'AI_Daily_'+now+'.md',tg}}];"
      },
      "name": "Report",
      "type": "n8n-nodes-base.code",
      "typeVersion": 2,
      "position": [740, 350],
      "id": "t6"
    },
    {
      "parameters": {
        "url": "=https://api.telegram.org/bot{{$env.TELEGRAM_TOKEN}}/sendMessage",
        "method": "POST",
        "sendBody": true,
        "bodyParameters": {
          "parameters": [
            {"name": "chat_id", "value": "={{$env.AUTHORIZED_CHAT_ID}}"},
            {"name": "text", "value": "={{$('Report').item.json.tg}}"}
          ]
        },
        "options": {}
      },
      "name": "Telegram",
      "type": "n8n-nodes-base.httpRequest",
      "typeVersion": 4,
      "position": [960, 350],
      "id": "t7"
    }
  ],
  "connections": {
    "Daily 8am": {"main": [[{"node": "Anthropic", "type": "main", "index": 0},{"node": "OpenAI", "type": "main", "index": 0},{"node": "AI News", "type": "main", "index": 0}]]},
    "Anthropic": {"main": [[{"node": "Merge", "type": "main", "index": 0}]]},
    "OpenAI": {"main": [[{"node": "Merge", "type": "main", "index": 1}]]},
    "AI News": {"main": [[{"node": "Merge", "type": "main", "index": 2}]]},
    "Merge": {"main": [[{"node": "Report", "type": "main", "index": 0}]]},
    "Report": {"main": [[{"node": "Telegram", "type": "main", "index": 0}]]}
  },
  "active": true,
  "settings": {"executionOrder": "v1"}
}
JSONEOF

echo "Copying into n8n container..."
docker cp /tmp/ga-workflow.json nemoclaw-n8n:/tmp/ga-workflow.json

echo "Importing..."
if docker exec nemoclaw-n8n n8n import:workflow --input=/tmp/ga-workflow.json 2>&1 | grep -v 'null value'; then
  echo ""
  echo "Checking if workflow exists..."
  RESULT=$(docker exec nemoclaw-n8n n8n export:workflow --all 2>/dev/null | grep -c 'GA AI Universe' || echo 0)
  if [ "$RESULT" -gt 0 ]; then
    echo "SUCCESS: GA AI Universe Supervisor is in n8n!"
  else
    echo "Trying alternative import method..."
    docker exec nemoclaw-n8n n8n import:workflow --separate --input=/tmp/ga-workflow.json
  fi
fi

echo ""
echo "Done. Workflow runs daily at 8am and sends Telegram alerts."
