# Daily Book Publishing Pipeline

```
STATUS:    ✅ DEPLOYED
SCHEDULE:  06:00 UTC daily (GitHub Actions cron)
ENGINE:    URANTiOS BookWriter v1.1.0
SOURCE:    URANTiOS/bookwriter + urantia-book/ corpus (197 papers)
OUTPUT:    PhD-Triune-Monism/07_Generated_Books/Books/
NOTIFY:    Telegram (LobsterBot) + Notion dashboard
THEMES:    52 curated (rotating, ~52 days per cycle)
GOVERNANCE: Truth · Beauty · Goodness — Lucifer Test
BRANCH:    claude/daily-book-publishing-zeI2A
```

## Architecture

```
┌──────────────────────────────────────────────────┐
│  GitHub Actions Cron (06:00 UTC daily)        │
│  .github/workflows/daily-book-publish.yml     │
└───────────────────────┬──────────────────────────┘
                        │
           ┌───────────┴────────────┐
           │  URANTiOS BookWriter   │
           │  python -m bookwriter  │
           │  daily                 │
           └────┬──────┬──────┬────┘
                │      │      │
     ┌───────┴┐  ┌──┴───┐  ┌┴───────┐
     │ PhD     │  │ Tele- │  │ Notion  │
     │ Vault   │  │ gram  │  │ Log     │
     └─────────┘  └──────┘  └────────┘
```

## Theme Rotation (52 themes)

Stored in `URANTiOS/bookwriter/daily_themes.json`. Each theme produces
a 8–12 chapter book grounded in The Urantia Book with paragraph-level
citations. Themes cover the full scope of the revelation:

1. The Nature of God the Father
2. The Eternal Son and the Spirit of Truth
3. The Infinite Spirit and the Ministry of Mind
4. The Paradise Trinity and Triune Unity
5. … (48 more themes)

## Required Secrets (GitHub Actions)

| Secret | Purpose |
|--------|--------|
| `ANTHROPIC_API_KEY` | Claude API for book generation |
| `CROSS_REPO_PAT` | Push generated books to PhD-Triune-Monism |
| `TELEGRAM_BOT_TOKEN` | LobsterBot notifications |
| `TELEGRAM_CHAT_ID` | Target chat for notifications |
| `NOTION_API_KEY` | Notion dashboard logging (optional) |
| `NOTION_DAILY_DB_ID` | Notion database ID (optional) |

## Manual Trigger

The workflow can be triggered manually from GitHub Actions with
an optional theme override and dry-run flag:

```
gh workflow run daily-book-publish.yml --ref claude/daily-book-publishing-zeI2A
```

Or locally:

```bash
cd URANTiOS
pipeline/daily-publish.sh
pipeline/daily-publish.sh --dry-run
pipeline/daily-publish.sh --theme "The Faith of Jesus"
```

## Repos Involved

| Repo | Role |
|------|------|
| URANTiOS | Engine + cron workflow + theme rotation + state |
| PhD-Triune-Monism | Output vault (07_Generated_Books/) |
| lobsterbot | Telegram notification script |
| mircea-constellation | Pipeline registration + status (this file) |

---

*Truth · Beauty · Goodness*
