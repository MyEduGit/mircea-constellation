# Diagram-On-Completion (DOC)

A Claude Code rule + skill + hooks that auto-archives every completed "job"
as a Mermaid diagram plus full chat transcript into a standalone Obsidian
vault, Notion, and GitHub.

## Install (one command, on your iMac/Mac)

```bash
cd ~/path/to/mircea-constellation
./setup/claude-doc/install.sh
```

Idempotent — safe to re-run.

## What it installs

| Destination | Purpose |
|---|---|
| `~/Documents/Obsidian/Jobs/` | Standalone Obsidian vault (local source of truth) |
| `~/.claude/CLAUDE.md` | Appends the DOC rule (marker-guarded, appended once) |
| `~/.claude/skills/diagram-on-completion.md` | The `/doc` skill |
| `~/.claude/hooks/doc-reminder.sh` | Stop hook — nudges Claude if a job wasn't archived |
| `~/.claude/hooks/doc-verify.sh` | SessionStart hook — verifies vault + git + mmdc |
| `~/.claude/settings.json` | Hooks merged in (via `jq`, preserves your existing keys) |
| `@mermaid-js/mermaid-cli` (global npm) | `mmdc` for SVG/PNG export (optional) |

## How it runs

1. At **session start**, `doc-verify.sh` prints a readiness report.
2. You do work as normal.
3. When a job completes, Claude invokes `/doc` (per the rule in `CLAUDE.md`).
4. `/doc`:
   - Builds a Mermaid diagram of the work
   - Writes `job.md` + `diagram.*` to the vault
   - Mirrors to Notion ("Sovereign Dashboard" parent)
   - Commits to `myedugit/mircea-constellation` under `/jobs/YYYY-MM-DD/<slug>/`
   - Drafts a Gmail summary if opted in
   - Replies with a ✓/✗ report
5. If Claude forgets, **Stop hook** nudges with a blocking reminder.

## Opt-outs

- Silence the Stop-hook reminder for a non-job session:
  `touch ~/.claude/.doc-markers/none`
- Per-project override: add a project `CLAUDE.md` changing the GitHub repo
  or Notion parent (must still archive to Obsidian).

## Optional Zapier fan-out

Create a Zapier "Catch Hook" zap. Save the URL in `~/.claude/doc.env`:

```
ZAPIER_DOC_HOOK=https://hooks.zapier.com/hooks/catch/....
```

The `/doc` skill POSTs job metadata JSON to that URL after every archive.

## Files in this package

```
setup/claude-doc/
├── README.md                            (this file)
├── install.sh                           (one-shot installer)
├── rule.md                              (the CLAUDE.md block)
├── settings.snippet.json                (for manual merge if jq absent)
├── skills/
│   └── diagram-on-completion.md         (the /doc skill)
└── hooks/
    ├── doc-reminder.sh                  (Stop hook)
    └── doc-verify.sh                    (SessionStart hook)
```

## Uninstall

```bash
# Remove the appended block between marker tags
sed -i.bak '/# \[\[DOC-RULE v1\]\]/,/<!-- end DOC-RULE v1 -->/d' ~/.claude/CLAUDE.md
rm -f ~/.claude/skills/diagram-on-completion.md
rm -f ~/.claude/hooks/doc-reminder.sh ~/.claude/hooks/doc-verify.sh
# Then edit ~/.claude/settings.json to remove the two hook entries
# The vault at ~/Documents/Obsidian/Jobs/ is NOT deleted automatically.
```
