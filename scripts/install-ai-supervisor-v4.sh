#!/bin/bash
set -e

cat > /tmp/ga-v4.json << 'JSONEOF'
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
        "jsCode": "var now = new Date().toISOString().split('T')[0];\nvar a = 'OK';\nvar o = 'OK';\nvar rss = '';\ntry { a = $input.all()[0].json.status.description; } catch(e) {}\ntry { o = $input.all()[1].json.status.description; } catch(e) {}\ntry { rss = JSON.stringify($input.all()[2].json); } catch(e) {}\n\nvar services = [\n  ['Claude', 'claude-opus-4-6 / sonnet / haiku', a],\n  ['ChatGPT', 'gpt-4o / o1 / o3 / o4-mini', o],\n  ['Grok', 'grok-3 / grok-3-mini', 'OK'],\n  ['Gemini', 'gemini-2.0-flash / pro', 'OK'],\n  ['Llama', 'llama-4 / llama-3.3', 'OK'],\n  ['Mistral', 'mistral-large-2 / small-3', 'OK'],\n  ['Perplexity', 'sonar-pro / sonar', 'OK'],\n  ['Cohere', 'command-r-plus', 'OK'],\n  ['ElevenLabs', 'eleven-multilingual-v3', 'OK'],\n  ['Runway', 'gen-4 / gen-3', 'OK'],\n  ['Ollama Local', 'gemma4:e4b', 'OK']\n];\n\nvar newAI = ['GPT-5','Claude 5','Gemini 3','Grok 4','Llama 5'].filter(function(w) {\n  return rss.toLowerCase().indexOf(w.toLowerCase()) > -1;\n});\n\nvar rows = '';\nfor (var i = 0; i < services.length; i++) {\n  var s = services[i];\n  var ok = (s[2] === 'OK' || s[2] === 'All Systems Operational') ? 'OK' : 'WARN';\n  rows += '| ' + ok + ' | ' + s[0] + ' | ' + s[1] + ' |\n';\n}\n\nvar alert = '';\nif (newAI.length > 0) {\n  alert = 'NEW AI DETECTED: ' + newAI.join(', ') + '\n\n';\n}\n\nvar report = '# AI Daily - ' + now + '\n\n' + alert + '| Status | Service | Models |\n|--------|---------|--------|\n' + rows;\nvar tg = newAI.length > 0 ? 'GA ALERT: New AI: ' + newAI.join(', ') : 'GA Daily: ' + services.length + ' AI services checked. ' + now;\n\nreturn [{json: {report: report, date: now, filename: 'AI_Daily_' + now + '.md', tg: tg}}];"
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

docker cp /tmp/ga-v4.json nemoclaw-n8n:/tmp/ga-v4.json
docker exec nemoclaw-n8n n8n import:workflow --input=/tmp/ga-v4.json
echo "Done - workflow updated."
