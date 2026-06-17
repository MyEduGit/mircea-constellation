---
type: system-map
vault: UrantiPedia
updated_at: 2026-05-14
---

# System Map: Mircea Constellation

Full architecture of the perpetual capture + cloud backup pipeline.

---

## Data Flow

```
  ┌─────────────────────────────────────────────────────────┐
  │                   DATA SOURCES                          │
  │                                                         │
  │  Claude Code  ChatGPT  Council/n8n  Telegram  Terminal  │
  │      │            │         │           │        │      │
  └──────┼────────────┼─────────┼───────────┼────────┼──────┘
         │            │         │           │        │
         └────────────┴─────────┴───────────┴────────┘
                               │
                     capture.py (every 15 min)
                               │
                    ┌──────────▼──────────┐
                    │  ~/Obsidian/        │
                    │  UrantiPedia/       │
                    │  (local vault)      │
                    └──────────┬──────────┘
                               │
              ┌────────────────┼────────────────┐
              │                │                │
     ┌────────▼────────┐  ┌────▼────┐  ┌────────▼────────┐
     │  Google Drive   │  │ iCloud  │  │  External SSD   │
     │  gdrive:        │  │ icloud: │  │  (auto-detect)  │
     │  UrantiPedia    │  │ DAV     │  │                 │
     └─────────────────┘  └─────────┘  └─────────────────┘
              │
     ┌────────▼────────────────────────────────────────────┐
     │  Google Docs (upload-to-gdocs.py)                   │
     │  ObsidianJobs/ + AnthropicData/                     │
 │ anyoneWithLink reader: no login required │
     └─────────────────────────────────────────────────────┘

  GitHub repo: vault/ directory → GitHub Pages → vault.html
  Public URL: https://myedugit.github.io/mircea-constellation/vault.html
```

---

## Components

| Component | Location | Trigger | Purpose |
|:---|:---|:---|:---|
| `capture.py` | `setup/perpetual-capture/` | every 15 min | Multi-source ingestion engine |
| `sync-all.sh` | `setup/perpetual-capture/` | after capture | rclone → GDrive + iCloud + SSD |
| `export-anthropic.py` | `setup/cloud-backup/` | on demand | Claude JSONL + Council → Obsidian |
| `sync-obsidian.sh` | `setup/cloud-backup/` | on demand | rclone all 3 vaults |
| `upload-to-gdocs.py` | `setup/cloud-backup/` | on demand | Markdown → Google Docs (public) |
| `backup-all.sh` | `setup/cloud-backup/` | Stop hook | Master orchestrator |
| `cloud-backup.yml` | `.github/workflows/` | 03:00 UTC daily | CI-driven full pipeline |
| `vault.html` | repo root | always | Public web vault browser |
| launchd plist | `setup/perpetual-capture/launchd/` | macOS boot | 15-min capture daemon |

---

## Vaults

| Vault | Local Path | GDrive | iCloud |
|:---|:---|:---|:---|
| UrantiPedia (perpetual) | `~/Obsidian/UrantiPedia/` | `gdrive:UrantiPedia` | `icloud:Documents/Obsidian/UrantiPedia` |
| Jobs | `~/Documents/Obsidian/Jobs/` | `gdrive:ObsidianJobs` | `icloud:Documents/Obsidian/Jobs` |
| Anthropic-Data | `~/Documents/Obsidian/Anthropic-Data/` | `gdrive:AnthropicData` | `icloud:Documents/Obsidian/Anthropic-Data` |

---

## Credentials

All credentials live in `~/.cloud-backup/.env` (chmod 600, never committed).

| Variable | Purpose |
|:---|:---|
| `GDRIVE_SA_FILE` | Path to Google service account JSON |
| `GDRIVE_CLIENT_ID` / `GDRIVE_CLIENT_SECRET` | OAuth alternative to SA |
| `GDOCS_JOBS_FOLDER_ID` | Drive folder ID for Google Docs uploads |
| `APPLE_ID` | Apple ID for iCloud WebDAV |
| `APPLE_APP_PASSWORD` | App-specific password (appleid.apple.com) |
| `ICLOUD_DAV_URL` | WebDAV shard, e.g. `https://p62-dav.icloud.com` |

GitHub Action secrets: `GDRIVE_SA_JSON`, `APPLE_ID`, `APPLE_APP_PASSWORD`, `ICLOUD_DAV_URL`, `GDOCS_JOBS_FOLDER_ID`

---

## Public Access

All data is accessible without login via:

- **Vault browser**: `https://myedugit.github.io/mircea-constellation/vault.html`
- **Dashboard**: loads `vault/DASHBOARD.md` by default
- **Google Docs**: `anyoneWithLink` reader on all uploaded documents
- **Raw markdown**: GitHub public API, `https://api.github.com/repos/MyEduGit/mircea-constellation/contents/vault/`

---

## Failure Modes

| Failure | Detection | Response |
|:---|:---|:---|
| Vault missing | `capture.py` exits 1 | Run `scaffold-vault.sh` |
| rclone missing | `sync-all.sh` exits 1 | Run `setup/cloud-backup/install.sh` |
| GDrive remote absent | warns, non-fatal | Configure via `rclone config` |
| iCloud remote absent | warns, non-fatal | Fill `.env` + re-run `install.sh` |
| GDocs auth failure | prints error, exits 1 | Check `GDRIVE_SA_FILE` in `.env` |
| launchd not loaded |, | Run `setup/perpetual-capture/install.sh` |

---

_Part of `myedugit/mircea-constellation`. See [[DASHBOARD]] to return to Mission Control._
