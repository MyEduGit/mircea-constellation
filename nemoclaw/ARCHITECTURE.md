# NemoClaw Architecture

## What is NemoClaw?

NemoClaw is the **job board orchestrator** for the Mircea Constellation. It watches a folder for job files (`.md`), runs them through a pipeline, and records proof of every action.

Think of it like a postal sorting office: letters arrive in the inbox, get stamped, delivered, and filed.

---

## System Map

```
┌──────────────────────────────────────────────────────────┐
│                        YOUR MAC                          │
│                                                          │
│  Obsidian Vault                                          │
│  ~/Obsidian/UrantiPedia/System/NemoClaw/Jobs/            │
│    00_INBOX/        ◄── drop .md job files here          │
│    10_CREWAI_DISPATCH/  (copies for CrewAI Studio)       │
│    20_CLAUDE_CODE_EXECUTE/  (copies for local claude)    │
│    40_RESULTS/      ◄── claude -p output lands here      │
│    80_PROOF/proof.log  ◄── every step timestamped        │
│    90_ARCHIVE/      ◄── processed jobs stored here       │
│    DASHBOARD.md     ◄── auto-updated after each job      │
│                                                          │
│  NemoClaw Dispatcher (Python)                            │
│  nemoclaw/dispatcher.py  ← polls INBOX every 10s        │
│    ├─ job_parser.py  → reads .md job metadata            │
│    ├─ worker_claude.py → calls `claude -p` headlessly    │
│    ├─ proof.py       → appends to proof.log              │
│    └─ dashboard.py   → updates status.json + DASHBOARD   │
│                                                          │
│  launchd service (always-on)                             │
│  ~/Library/LaunchAgents/com.mircea.nemoclaw.plist        │
└──────────────────────────┬───────────────────────────────┘
                           │ git push (on job complete)
                           ▼
┌──────────────────────────────────────────────────────────┐
│                      GITHUB                              │
│  myedugit/mircea-constellation                           │
│    status.json  ◄── nemoclaw counts updated              │
│    index.html   ◄── constellation map (reads status.json)│
│                                                          │
│  GitHub Actions → deploys to GitHub Pages automatically  │
└──────────────────────────┬───────────────────────────────┘
                           │ cloud agents watch same repo
                           ▼
┌──────────────────────────────────────────────────────────┐
│                   CREWAI STUDIO (cloud)                  │
│  NemoClaw Job Board Orchestrator crew                    │
│    Flow Orchestrator  → reads jobs from 10_CREWAI_DISPATCH│
│    Task Executor      → runs complex multi-step tasks    │
│    Proof Auditor      → verifies outputs meet spec       │
└──────────────────────────────────────────────────────────┘
```

---

## Pipeline Steps

| Step | Folder | What happens |
|------|--------|--------------|
| 1. Arrive | `00_INBOX/` | You drop a `.md` job file here |
| 2. Dispatch | `10_CREWAI_DISPATCH/` | Copy sent to CrewAI Studio crew |
| 3. Execute | `20_CLAUDE_CODE_EXECUTE/` | `claude -p` runs the job locally |
| 4. Results | `40_RESULTS/` | Output `.md` file written here |
| 5. Proof | `80_PROOF/proof.log` | Every step timestamped and recorded |
| 6. Archive | `90_ARCHIVE/` | Original job filed away |
| 7. Done | `00_INBOX/job.md.done` | Sentinel file prevents re-processing |

---

## Job File Format

```markdown
# My Job Title

- Task: Write a summary of Paper 1 of the Urantia Book
- Priority: high
- Output: markdown
- Tags: urantia, summary
```

---

## Running the Dispatcher

```bash
# One-shot (process inbox once)
python3 -m nemoclaw.dispatcher

# Watch mode (poll every 10 seconds)
python3 -m nemoclaw.dispatcher --watch
```

---

## CrewAI Relationship

- **Local dispatcher** = Python script, no CrewAI dependency, runs on your Mac
- **CrewAI Studio** = cloud service that runs the multi-agent crew independently
- Jobs are copied to `10_CREWAI_DISPATCH/` so CrewAI Studio agents can pick them up
- The two systems work in parallel — local is fast, cloud is powerful
