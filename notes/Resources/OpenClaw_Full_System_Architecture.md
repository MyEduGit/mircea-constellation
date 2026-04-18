# OpenClaw — Full System Architecture

```mermaid
flowchart TB
    M[Mircea] --> iMac[iMac M4]
    iMac --> T[Terminal SSH]
    iMac --> CC[Claude Code]
    iMac --> OB[Obsidian Vault]
    iMac --> AP[Apple Passwords]
    T --> OC[OpenClaw 46.225.51.30]
    OC --> DC[Docker]
    DC --> N8N[n8n :5678]
    DC --> Bot[Telegram Bot]
    DC --> PG[Postgres]
    DC --> RD[Redis]
    N8N --> GA[Grandfather's Axe Workflows]
    GA --> OB
    OC --> LS[LiveSync CouchDB]
    LS --> OB
```

## Infrastructure

| Component | Location | Status |
|-----------|----------|--------|
| iMac M4 | Local macOS | Active |
| Hetzner Server | ubuntu-4gb-nbg1-1 | Active |
| n8n | Docker / port 5678 | Running |
| Obsidian | /Users/mircea8me.com/Obsidian/ | Local |
| GitHub | myedugit/mircea-constellation | Active |

**Current status:** n8n confirmed running. GA hourly bot is next.
