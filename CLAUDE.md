# Claude Code Instructions — mircea-constellation

## WHO THIS IS FOR
This repo belongs to Mircea (age 70). He builds Grandfather's Axe (GA) — a personal AI supervision system.

## PROACTIVE RULES (do these WITHOUT being asked)

### 1. AI Universe Auto-Update
At the start of EVERY session:
- Check `notes/Projects/GrandfatherAxe/AI_Universe_Tracker.md` for the current list of AI services
- Compare against known 2026 AI providers: Anthropic, OpenAI, Google, xAI, Meta, Mistral, Cohere, Perplexity, Stability AI, Midjourney, ElevenLabs, Runway, and any others released since August 2025
- If ANY new models or services are missing from the tracker, update the file and push to GitHub automatically
- Announce to Mircea: "I found X new AI services and added them to your tracker."

### 2. n8n Workflow Auto-Update
- If new AI services are added to the tracker, also update `workflows/ai-supervisor.json` to include them in the daily status check
- Push the updated workflow to GitHub
- Remind Mircea to re-import the workflow into n8n (one paste command)

### 3. Obsidian Sync
- All notes go under `notes/` in this repo
- Mircea's Obsidian vault: `/Users/mircea8me.com/Obsidian/UrantiPedia/`
- Auto-sync script: `notes/sync-to-obsidian.sh`
- After pushing notes, remind Mircea to run the sync if not already automatic

### 4. Memory Continuity
- Mircea has memory challenges. Always summarise where we left off at the start of each session.
- Check `notes/Projects/GrandfatherAxe/GA_Session_001_Log.md` and the latest `AI_Daily_Report_*.md` for context.
- If the last session log is more than 24 hours old, create a new one.

### 5. Server Details (always available)
- Server: `root@46.225.51.30` (Hetzner, Nuremberg)
- n8n: `http://localhost:5678` (via SSH tunnel `ssh -L 5678:localhost:5678 root@46.225.51.30`)
- n8n login: `mircea` / check Apple Passwords
- Docker folder: `/home/mircea/nemoclaw/`
- n8n API key: in `/home/mircea/nemoclaw/bot.env`

## DEVELOPMENT BRANCH
Always commit to: `claude/debug-n8n-docker-o7zRE`

## COMMUNICATION STYLE
- Mircea is 70, has dyslexia and memory challenges
- Use simple, short sentences
- Use big clear headings
- Always say what you just did AND what to do next
- Never assume he remembers previous sessions
- Always give copy-paste commands, never just describe them
