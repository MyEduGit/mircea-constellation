# Session Overview — UOS / CrewAI / NemoClaw / OpenClaw / Preservation

Date: Thursday, 30 April 2026 — AEST
Device: iMAC_M4
Repository: /Users/mircea8me.com/mircea-constellation
Branch: claude/fix-issue-D6j6B

## Verified Pipeline

Stage 1: CrewAI / crew_engine orchestration
Stage 2: NemoClaw
Stage 3: OpenClaw visibility
Stage 4: Preservation

## Verified Facts

- pipeline/run.sh exists and runs.
- preservation/run.sh exists and runs.
- setup/preservation_install.sh exists.
- .githooks/post-commit exists.
- Local bare mirror exists at ~/backups/mircea-constellation.git.
- GitHub branch pushed: claude/fix-issue-D6j6B.
- Latest verified commit before this note: 23238a7.
- Obsidian app found at /Applications/Obsidian.app.
- Local UrantiPedia vault found at ~/Obsidian/UrantiPedia.
- iCloud Obsidian vaults found.
- iCloud backup folder found/created at ~/Library/Mobile Documents/com~apple~CloudDocs/UOS_Backups.

## Remaining Gaps

- crew_engine is currently a verified placeholder, not a full CrewAI clone.
- OpenClaw is currently visibility-checked by folder presence, not full execution.
- External SSD/offline immutable backup is not yet verified.
- Google Drive mirror is not yet verified.
- Restore test is not yet verified.

## Rule Going Forward

No component is accepted because an AI says it exists.

Accepted only when iMAC_M4 proves:

1. file exists
2. command runs
3. output is shown
4. proof is logged
5. backup exists
6. restore path is known
