# Obsidian Sync Options – Explored April 2026 (for Mircea)

**Current situation:** Vault lives on iMac M4. We want it on OpenClaw + iPhone + MacBook Pro M1 with zero drift.

## Best options ranked

| Rank | Method | Cost | Real-time? | iOS friendly? | Difficulty |
|------|--------|------|------------|---------------|------------|
| 1 | **Self-hosted LiveSync** (CouchDB) | Free | Yes | Excellent | Medium |
| 2 | **Syncthing** | Free | Yes | Good | Easy |
| 3 | **Obsidian Git plugin** | Free | Manual | Good | Easy |
| 4 | Official Obsidian Sync | $8/mo | Yes | Excellent | Very easy |
| 5 | Remotely Save + Nextcloud | Free | Yes | Good | Medium |

**Recommendation:** Run **Self-hosted LiveSync (CouchDB)** on OpenClaw.  
n8n can then write notes instantly, and your iMac/iPhone sync in real time.

**Setup command (run in terminal on OpenClaw):**
```bash
cd ~ && docker compose up -d couchdb livesync
```

**Backup plan:** Also enable Obsidian Git plugin + push to mircea-constellation repo.
