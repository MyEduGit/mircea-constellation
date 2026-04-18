# AI Universe Tracker — Grandfather's Axe

**Purpose:** GA supervises all AI services Mircea uses, tracking status, new models, and daily updates.

## AI Services Under Supervision

| Service | Provider | Models (April 2026) | Paid? | Best for |
|---------|----------|-------------------|-------|----------|
| **Claude** | Anthropic | claude-opus-4-6, claude-sonnet-4-6, claude-haiku-4-5 | Yes | Deep reasoning, code, long documents |
| **ChatGPT** | OpenAI | gpt-4o, o1, o3, o4-mini | Yes | General tasks, images, browsing |
| **Grok** | xAI | grok-3, grok-3-mini | Yes | Real-time web, X/Twitter data |
| **Gemini** | Google | gemini-2.0-flash, gemini-1.5-pro | Free+Paid | Google Workspace integration |
| **Llama** | Meta | llama-4, llama-3.3 | Free/Open | Local/private use |
| **Mistral** | Mistral AI | mistral-large-2, mistral-small | Free+Paid | European privacy, fast responses |
| **Perplexity** | Perplexity | sonar-pro, sonar | Free+Paid | Web search + AI answers |
| **Cohere** | Cohere | command-r-plus, command-r | Free+Paid | Enterprise search |
| **Ollama** | Local | gemma4:e4b | Free | Local, private, offline |

## Daily Report
GA checks all services every morning at 8am and saves a report to:
`Resources/AI_Daily_Report_YYYY-MM-DD.md`

## Status Pages
- Anthropic: https://status.anthropic.com
- OpenAI: https://status.openai.com
- Google: https://status.cloud.google.com

## How to add a new AI service
1. Tell GA: "Add [Service Name] to AI supervisor"
2. GA updates this note + the n8n workflow automatically

**Tag:** #ga #ai-supervisor #ai-universe
