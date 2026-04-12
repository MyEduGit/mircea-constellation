# HANDOVER — Claude Code Session
# Date: 2026-04-12
# Project: OpenClaw / NemoClaw — Hetzner VPS + n8n

---

## SYSTEM STATE

### Server
- **Host**: Hetzner VPS `ubuntu-4gb-nbg1-1`
- **IP**: `46.225.51.30`
- **SSH**: `ssh root@46.225.51.30`
- **SSH Tunnel for n8n**: `ssh -L 5678:localhost:5678 root@46.225.51.30`

### Docker Stack (`/home/mircea/nemoclaw/`)
- `nemoclaw-n8n` — n8n v2.13.3, port 5678
- `nemoclaw-postgres` — PostgreSQL, DB: `nemoclaw`, user: `mircea`, pass: `mircea8`
- `nemoclaw-redis` — Redis
- `nemoclaw-paperclip` — Node.js proof service (port 3101 internal)
- `nemoclaw-bot` — Telegram bot

### n8n Access
- **Local**: `http://localhost:5678` (via SSH tunnel)
- **Public**: `https://n8n.urantipedia.org`
- **Login**: `mircea8@me.com` / `mircea8`

### docker-compose.override.yml (current)
```yaml
services:
  n8n:
    environment:
      - N8N_SECURE_COOKIE=false
      - N8N_USER_MANAGEMENT_DISABLED=true
      - EXECUTIONS_PROCESS=main
      - N8N_ALLOW_EXEC=true
```

### Obsidian Vault
- **Mac path**: `/Users/mircea8me.com/Obsidian/UrantiPedia/`
- **iCloud path**: `/Users/mircea8me.com/Library/Mobile Documents/com~apple~CloudDocs/UrantiPedia/`
- **GitHub repo**: `myedugit/mircea-constellation` branch `claude/debug-n8n-docker-o7zRE`

---

## COMPLETED THIS SESSION

1. Fixed n8n Safari cookie error (N8N_SECURE_COOKIE=false)
2. Set n8n credentials: mircea8@me.com / mircea8
3. Fixed N8N_ALLOW_EXEC=true (Execute Command nodes now work)
4. Imported GA AI Universe Supervisor workflow (monitors AI services daily at 8am)
5. Imported OpenClaw Health Check workflow
6. Pushed 13 Obsidian notes to GitHub
7. Set up Mac hourly Obsidian auto-sync (launchd)
8. Updated Gabriel_Synthesizer model: claude-sonnet-4-20250514 → claude-sonnet-4-6
9. Rebuilt Council of Seven v2 (see PENDING #1)

---

## PENDING TASKS

### Step 1 — Run Council of Seven rebuild on server
```bash
# In SSH server terminal:
curl -s https://raw.githubusercontent.com/MyEduGit/mircea-constellation/claude/debug-n8n-docker-o7zRE/scripts/rebuild-council-v2.sh | bash
```
This deletes the old broken workflow and imports a clean v2 with:
- Webhook ENABLED
- All 7 seats with continueOnFail
- Gabriel uses claude-sonnet-4-6
- Seat4 Ollama uses server IP (172.17.0.1:11434) not Mac IP

### Step 2 — Enter API keys in n8n
Open each seat node and replace placeholder with real key:

| Node | Placeholder | Where to get key |
|------|------------|------------------|
| Seat1_OpenAI | ENTER_OPENAI_KEY_HERE | platform.openai.com |
| Seat2_Anthropic | ENTER_ANTHROPIC_KEY_HERE | console.anthropic.com |
| Seat3_Gemini | ENTER_GEMINI_KEY_HERE (in URL) | aistudio.google.com |
| Seat4_Gemma4_Local | no key needed | Ollama on server |
| Seat5_DeepSeek | ENTER_DEEPSEEK_KEY_HERE | platform.deepseek.com |
| **Seat6_GLM** | **ENTER_GLM_KEY_HERE** | **User already paid — get from open.bigmodel.cn** |
| Seat7_Grok | ENTER_GROK_KEY_HERE | console.x.ai |
| Gabriel_Synthesizer | ENTER_ANTHROPIC_KEY_HERE | console.anthropic.com |

**Priority**: Seat6_GLM first (user already has Z.ai subscription)

### Step 3 — Install Ollama on server (optional, for Seat4)
```bash
# On server:
curl -fsSL https://ollama.ai/install.sh | sh
ollama pull gemma2
# Verify:
curl http://localhost:11434/api/tags
```

### Step 4 — Test Council of Seven
1. Open n8n → Council of Seven Master Spirits v2
2. Click Execute workflow
3. When waiting, run from Mac terminal:
```bash
curl -X POST "http://localhost:5678/webhook-test/council-of-seven" \
  -H "Content-Type: application/json" \
  -d '{"prompt": "What is the nature of consciousness?"}'
```
4. Gabriel should return synthesized answer

### Step 5 — Remaining workflows to check
- NanoClaw Dashboard (executeCommand nodes — should work now with N8N_ALLOW_EXEC=true)
- Paperclip v1 Proof Ping (POST to nemoclaw-paperclip container)
- Stage 4 — Nebadon Heartbeat
- Stage 5 — Telegram Triggers

---

## WORKFLOW INVENTORY

| Workflow | Status | Notes |
|----------|--------|-------|
| Council of Seven v2 | ⚠️ Needs server rebuild script | Step 1 above |
| GA AI Universe Supervisor | ✅ Published | Runs daily 8am |
| OpenClaw Health Check | ✅ Imported | Test after N8N_ALLOW_EXEC |
| NanoClaw Dashboard | ⚠️ Needs test | executeCommand nodes |
| Paperclip v1 Proof Ping | ⚠️ Needs test | POST to paperclip:3101 |
| Stage 4 — Nebadon Heartbeat | ✅ Published | Hourly heartbeat |
| Stage 5 — Telegram (Nebadon) | ✅ Published | Telegram trigger |
| Stage 5 — Telegram (Hetzy PhD) | ✅ Published | Telegram trigger |
| Stage 5 — Error Handler | ✅ Published | |

---

## API KEYS TO OBTAIN

Priority order:
1. **GLM/Z.ai** — already paid, get from open.bigmodel.cn/usercenter/apikeys
2. **Anthropic** — console.anthropic.com/settings/keys
3. **Google Gemini** — aistudio.google.com (free tier)
4. **DeepSeek** — platform.deepseek.com (load $5)
5. **OpenAI** — platform.openai.com
6. **Grok** — console.x.ai

---

## GITHUB REPO

Repo: `myedugit/mircea-constellation`
Branch: `claude/debug-n8n-docker-o7zRE`

Key scripts:
- `scripts/rebuild-council-v2.sh` — rebuild Council of Seven
- `scripts/fix-gabriel.sh` — update Gabriel model
- `scripts/verify-and-fix.sh` — verify N8N_ALLOW_EXEC
- `scripts/setup-mac-autosync.sh` — Mac hourly Obsidian sync
- `notes/` — 13 Obsidian notes
- `CLAUDE.md` — proactive instructions for future sessions
