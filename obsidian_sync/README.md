# obsidian_sync — Claude → Obsidian → (iCloud + Google Drive)

Pipeline that copies conversation content from Anthropic tools into an Obsidian
vault, which then syncs to both iCloud (native) and Google Drive (rclone).

## What is and isn't automated

| Source | Past | Present / future |
|---|---|---|
| **claude.ai** (web chat) | Request export ZIP (manual click), then `import_claude_export.py` | Request a fresh export periodically (same pipeline, idempotent) — or install a browser extension (out of scope) |
| **Claude Code** (terminal) | `export_claude_code.py` — scans `~/.claude/projects/*.jsonl` | `SessionEnd` hook → `session_end_hook.sh` |
| **Cowork / VS Code Claude** | Same harvester if it writes to `~/.claude/projects` — otherwise point `--projects-root` at the correct dir | Same hook config if supported by the tool |
| **iCloud backup** | Automatic (vault lives in iCloud) | Automatic |
| **Google Drive backup** | `sync_to_gdrive.sh` (rclone, one-way mirror) | Run on a cron or from the SessionEnd hook |

The honest truth: there is no public API to pull live claude.ai conversations.
The two options are (a) browser extension, or (b) periodic re-export — which
is fine because `import_claude_export.py` is idempotent (updates only files
whose `updated_at` changed).

## One-time setup

```bash
# 1. Clone this repo on the Mac (if not already).
git clone https://github.com/MyEduGit/mircea-constellation ~/mircea-constellation

# 2. Create the target folders inside the Obsidian vault.
VAULT="$HOME/Library/Mobile Documents/iCloud~md~obsidian/Documents/Urantia-Vault"
mkdir -p "$VAULT/Claude-Archive/claude-chat"
mkdir -p "$VAULT/Claude-Archive/claude-code"
mkdir -p "$VAULT/Claude-Archive/cowork"
mkdir -p "$VAULT/Claude-Archive/claude-code-vscode"

# 3. Install rclone and configure a Google Drive remote named "gdrive".
brew install rclone
rclone config   # n → gdrive → drive → follow browser auth → name it "gdrive"

# 4. (Optional) test the remote is working.
rclone lsd gdrive:
```

## Backfill past Claude Code sessions

```bash
python3 ~/mircea-constellation/obsidian_sync/export_claude_code.py \
    "$HOME/Library/Mobile Documents/iCloud~md~obsidian/Documents/Urantia-Vault/Claude-Archive/claude-code"
```

Re-running is safe — files are only rewritten if their last timestamp changed.

## Backfill past claude.ai chats

1. Go to [claude.ai → Settings → Privacy → Export Data](https://claude.ai/settings/data-privacy-controls) and request the export.
2. When the email arrives, download the ZIP **within 24 hours** (links expire).
3. Run:

```bash
python3 ~/mircea-constellation/obsidian_sync/import_claude_export.py \
    ~/Downloads/data-2026-04-21-*.zip \
    "$HOME/Library/Mobile Documents/iCloud~md~obsidian/Documents/Urantia-Vault/Claude-Archive/claude-chat"
```

## Real-time Claude Code capture (SessionEnd hook)

Make the hook executable, then wire it into `~/.claude/settings.json`:

```bash
chmod +x ~/mircea-constellation/obsidian_sync/session_end_hook.sh
```

Add to `~/.claude/settings.json` (merge if the file already has `hooks`):

```json
{
  "hooks": {
    "SessionEnd": [
      {
        "hooks": [
          {
            "type": "command",
            "command": "/Users/YOU/mircea-constellation/obsidian_sync/session_end_hook.sh"
          }
        ]
      }
    ]
  }
}
```

Optional env vars (in the hook script or your shell rc):

| Variable | Default |
|---|---|
| `OBSIDIAN_SYNC_REPO` | `$HOME/mircea-constellation` |
| `OBSIDIAN_CLAUDE_CODE_DIR` | `.../Urantia-Vault/Claude-Archive/claude-code` |
| `GDRIVE_REMOTE` | *(empty — set to `gdrive:Claude-Archive` to mirror after every session)* |

## Google Drive backup

```bash
~/mircea-constellation/obsidian_sync/sync_to_gdrive.sh
```

Or schedule it (LaunchAgent / cron). The script is a one-way `rclone copy`
(no `--delete-*`), so a bad local delete never propagates to Google Drive.

## File layout in the vault

```
Urantia-Vault/Claude-Archive/
├── claude-chat/
│   └── 2026-04-13-Become-tub-on-the-following-...-ab12cd34.md
├── claude-code/
│   └── 2026-04-20-fix-your-clock-its-fuzzy-candy-6H3Kc...md
├── cowork/
└── claude-code-vscode/
```

Every file carries YAML frontmatter (`source`, `title`, `uuid`/`session_id`,
`created_at`/`first_timestamp`, `updated_at`/`last_timestamp`, counts) so
downstream tools (Qdrant indexer, Cognee, search) can filter cleanly.

## Verification

The two Python scripts have a test suite in `tests/` that exercises them
against synthetic Claude.ai and Claude Code inputs:

```bash
cd ~/mircea-constellation && python3 -m unittest discover obsidian_sync/tests
```
