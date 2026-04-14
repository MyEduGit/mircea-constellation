---
name: diagram-on-completion
description: |
  Invokable as /doc. Use this skill to archive a completed "job" — generate a
  Mermaid (or Canva) diagram of the work done, write it plus the chat
  transcript to the Obsidian vault at ~/Documents/Obsidian/Jobs/, mirror to
  Notion (Sovereign Dashboard parent), commit to
  myedugit/mircea-constellation under /jobs/, and optionally draft a Gmail
  summary. Use when: the user says "archive this", "save this job", "done",
  "/doc", or when a discrete task has just reached a conclusion and the
  Diagram-On-Completion rule requires archival.
---

# /doc — Diagram-On-Completion

You are archiving a completed job. Follow the Diagram-On-Completion rule in
`~/.claude/CLAUDE.md` exactly. This skill is the canonical execution path for
that rule.

## Pre-flight

1. Determine `<job-slug>` — a lowercase, hyphenated, ≤40-char summary of the
   job (e.g. `fix-expand-arrows`, `wire-doc-rule`).
2. Determine `YYYY-MM-DD` — today's date in the user's local timezone.
3. Compose a one-line `<outcome>` — imperative past tense, e.g.
   "Wired Diagram-On-Completion rule and skill end-to-end."
4. Choose Mermaid diagram type (flowchart / sequence / state / mindmap) based
   on job shape. Default: flowchart LR.

## Execution (in order)

### 1. Build the diagram

Draft Mermaid source covering: inputs → decisions → actions → tools/MCPs
used → artifacts → outcome. Include at least one `subgraph` when the job
touches multiple systems. Validate syntax mentally before writing.

If Mermaid is genuinely insufficient, call `generate-design-structured`
(Canva MCP) and capture the thumbnail URL via `get-design-thumbnail`.

### 2. Write to Obsidian vault

Use the `Write` tool for each file. Base path:
`~/Documents/Obsidian/Jobs/<YYYY-MM-DD>/<job-slug>/`

Files:
- `job.md` (frontmatter + summary + `![[diagram.svg]]` + toggle-style
  transcript + Controls section)
- `diagram.md` (fenced ```mermaid block + embedded image)
- `diagram.mmd` (raw source)
- `diagram.svg`, `diagram.png` (render via `mmdc` if available on the user's
  PATH; fall back to inline SVG generated from the Mermaid source; if
  neither is possible, note it in `job.md` and skip PNG)
- `assets/` (create empty directory if nothing to add)

### 3. Mirror to Notion

Call `mcp__570245c3-...-notion-create-pages` with parent
`3328525a-b5a0-815d-886c-d5488593aa3d` (Sovereign Dashboard). Page title:
`Job: <job-slug> — <YYYY-MM-DD>`. Body: summary + embedded Mermaid code block
+ toggle "Transcript" containing the full chat.

Capture the returned URL for the report.

### 4. Mirror to GitHub

Stage all files produced in step 2 and commit via
`mcp__github__push_files` to `myedugit/mircea-constellation` on branch
`claude/claude-usage-guide-mtE8j` at path `jobs/<YYYY-MM-DD>/<job-slug>/`.

Commit message: `job: <job-slug> — <outcome>`.

Capture the returned commit URL for the report.

### 5. Build the Controls section

Append to `job.md`:

```markdown
## Controls

- **Copy Mermaid source** → [[diagram.mmd]]
- **Copy rendered image** → [[diagram.png]]
- **Export bundle** → [[bundle.zip]]
- **Open in Obsidian** → `obsidian://open?vault=Jobs&file=<YYYY-MM-DD>/<job-slug>/job`
- **Open in Notion** → <notion_url>
- **Open in GitHub** → <github_url>
- **Paste target** — drop images/text onto this note; they land in `assets/`
  and auto-link below.
```

### 6. Fan-out (conditional)

- **Gmail**: if the user opted in for this job OR the job is tagged
  `notify`, call `gmail_create_draft` to `mirceamatthews@gmail.com` with
  subject `Job: <slug>` and the summary + links as body.
- **Zapier**: if `~/.claude/doc.env` contains `ZAPIER_DOC_HOOK=<url>`, POST
  job metadata JSON to that URL. (Use a Bash `curl` call; do NOT read the
  secret into context.)
- **Slack**: skipped by default.

### 7. Report

Reply with:

```
✓ Obsidian: Jobs/<YYYY-MM-DD>/<job-slug>/
✓ Notion:   <url>
✓ GitHub:   <url>
  diagram:  <first 10 lines of Mermaid>
```

Replace any failed line with `✗` + one-sentence failure reason. Do not
suppress errors.

## When to refuse to archive

- The "job" has no meaningful outcome yet (still mid-task) — ask the user to
  confirm completion before archiving.
- The user explicitly said "don't archive this" for the current job.
- Archival would expose secrets from the transcript — redact first, then
  archive the redacted version and warn the user.
