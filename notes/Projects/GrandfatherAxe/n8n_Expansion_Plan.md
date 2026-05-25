# n8n Expansion Plan for Grandfather's Axe

**Goal:** Turn the existing n8n on OpenClaw into the brain of GA (hourly tracking, charts, Obsidian logging).

## Immediate capabilities we add this week
1. **Hourly GA Session Logger** – Cron trigger → reads recent activity → generates Mermaid timeline → writes to Obsidian.
2. **Idea Inbox** – Webhook from Claude/iPhone → captures drift ideas automatically.
3. **Behavior Mirror** – Analyses your patterns (Trigger/Reaction) and sends plain-language report.
4. **Mermaid Chart Generator** – Auto-creates daily/weekly timelines with clickable rabbit-hole links.
5. **Obsidian Write Node** – Direct save to vault (via Local REST API or file sync).

## How to activate (in n8n)
1. Open n8n → http://localhost:5678
2. Create new workflow → name it **GA-Hourly-Logger**
3. Add **Schedule Trigger** (every hour)
4. Add **HTTP Request** node to pull logs
5. Add **AI Agent** node (Claude) to analyse drift
6. Add **Markdown** node to build Mermaid chart
7. Save note to Obsidian

**Next action:** Say "Start n8n GA workflow" to get the full JSON to import in one click.
