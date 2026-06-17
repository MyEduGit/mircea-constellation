---
cssClasses: [dashboard, wide-page]
type: dashboard
vault: UrantiPedia
created_at: 2026-05-14
updated_at: 2026-05-14T00:00:00+1000
total_captures: 0
---

# UrantiPedia: Mission Control

> Perpetual capture vault: every AI session, decision, output, and proof archived in full. Never summarised. Never lost.

---

## System Status

<!-- AUTO-STATUS-START -->
| Field | Value |
|:---|:---|
| Last capture run |: |
| Total .md files |, |
| Vault size |: |
| Sync: Google Drive |, |
| Sync: iCloud |: |
| Sync: External SSD |, |
| Host device |: |
<!-- AUTO-STATUS-END -->

---

## Source Health

<!-- AUTO-SOURCES-START -->
| Source | Inbox Folder | Files | Last Captured |
|:---|:---|---:|:---|
| Claude Code | `00_Inbox/Claude` |, |, |
| ChatGPT | `00_Inbox/ChatGPT` |, |, |
| Council / n8n | `00_Inbox/n8n` |, |, |
| Telegram | `00_Inbox/Telegram` |, |, |
| Terminal | `00_Inbox/Terminal` |, |, |
| AI Drops | `00_Inbox/AI_Captures` |, |, |
| OpenClaw | `00_Inbox/OpenClaw` |, |, |
| NemoClaw | `00_Inbox/NemoClaw` |, |, |
<!-- AUTO-SOURCES-END -->

---

## Quick Navigation

| Section | Link | Purpose |
|:---|:---|:---|
| Master Index | [[04_Backups_Index/PERPETUAL_CAPTURE_INDEX\|Capture Index]] | All captures, all runs |
| Inbox | [[00_Inbox/\|00_Inbox]] | All incoming captures |
| System Map | [[01_System/SYSTEM_MAP\|System Map]] | Architecture + wiring |
| Projects | [[02_Projects/\|02_Projects]] | Active work |
| Workflows | [[03_Workflows/\|03_Workflows]] | Automation docs |
| Archive | [[99_Archive/\|99_Archive]] | Retired notes |

---

## Recent Captures

<!-- AUTO-RECENT-START -->
_No captures recorded yet. Run `setup/perpetual-capture/capture.py` to populate._
<!-- AUTO-RECENT-END -->

---

## Today's Captures

```dataview
TABLE source, priority, topic
FROM "00_Inbox"
WHERE date(created_at) = date(today)
SORT created_at DESC
LIMIT 50
```

_Requires the Dataview Obsidian plugin. Static fallback above is auto-updated by `capture.py`._

---

## Cloud Sync Status

| Target | Path | Last Sync |
|:---|:---|:---|
| Google Drive | `gdrive:UrantiPedia` |, |
| iCloud | `icloud:Documents/Obsidian/UrantiPedia` |, |
| External SSD | auto-detected or `$PERPETUAL_CAPTURE_SSD_PATH` |, |
| GitHub Repo | `vault/` in `myedugit/mircea-constellation` |, |
| GitHub Pages | `https://myedugit.github.io/mircea-constellation/vault.html` | live |

---

## Vault Structure

```
~/Obsidian/UrantiPedia/
├── DASHBOARD.md              ← you are here
├── 00_Inbox/                 ← all captures land here first
│ ├── Claude/ : Claude Code JSONL sessions
│ ├── ChatGPT/ : ChatGPT exports
│ ├── n8n/ : Council / n8n execution logs
│ ├── Telegram/ : Telegram chat exports
│ ├── Terminal/ : shell history snapshots
│ ├── AI_Captures/ : manual drops (.txt / .md)
│ ├── OpenClaw/ : OpenClaw ingest logs
│ ├── NemoClaw/ : NemoClaw / Cognee logs
│ └── Proof/ : verification artifacts
├── 01_System/                ← system config + architecture
│   └── SYSTEM_MAP.md
├── 02_Projects/              ← active project notes
├── 03_Workflows/             ← automation + runbook docs
├── 04_Backups_Index/         ← master index + stats
│   └── PERPETUAL_CAPTURE_INDEX.md
└── 99_Archive/               ← retired / completed notes
```

---

## Activation

```bash
# First time only: scaffold vault + start 15-min capture loop
bash setup/perpetual-capture/scaffold-vault.sh
bash setup/cloud-backup/install.sh      # fill ~/.cloud-backup/.env first
bash setup/perpetual-capture/install.sh # registers macOS launchd / Linux cron

# Manual single run
python3 setup/perpetual-capture/capture.py

# Manual cloud sync
bash setup/perpetual-capture/sync-all.sh
```

---

## Backup Sources in Detail

### Claude Code
Scans `~/.claude/projects/**/*.jsonl` for session transcripts. Each JSONL file becomes a capture note with full raw content preserved.

### ChatGPT
Reads `~/Downloads/conversations.json` (official export) and `~/Downloads/ChatGPT-*.html` files.

### Council / n8n
Reads `~/.council-keys/logs/*.json`: execution logs from the Council of Seven AI seats running via n8n.

### Telegram
Reads `~/Downloads/Telegram Desktop/ChatExport_*/result.json`: official Telegram Desktop chat exports.

### Terminal
Captures the last 500 lines of `~/.bash_history` and `~/.zsh_history`. Detects changes by SHA-256 of the tail.

### AI Drops
Watches `00_Inbox/AI_Captures/`: drop any `.txt` or `.md` file here and it will be captured and indexed automatically.

---

_Auto-updated by `capture.py` every 15 minutes via launchd (macOS) or cron (Linux). Never edit the `AUTO-*` sections manually, they will be overwritten._
