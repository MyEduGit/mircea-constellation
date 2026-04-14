<!--
  Diagram-On-Completion (DOC) — Claude Code rule
  Source: myedugit/mircea-constellation @ setup/claude-doc/rule.md
  Install: appended to ~/.claude/CLAUDE.md by setup/claude-doc/install.sh
-->

## Rule: Diagram-On-Completion (DOC)

**Trigger.** Every time a "job" is completed. A job = any discrete task the user
asked for that reached a conclusion (code shipped, question answered, plan
produced, research delivered, PR merged, decision made). If a single session
contains several jobs, DOC runs once per job.

**A job is not "done" until DOC has executed successfully.** If any required
step fails, retry once; then report which mirrors succeeded and which didn't.
Never silently skip archival.

### Required sequence

0. **VERIFY BEFORE DISPLAY (hard gate).** No Mermaid diagram may be shown to
   the user, written to disk, committed, or mirrored until it has been
   rendered by `setup/claude-doc/scripts/verify-diagram.sh` with exit code
   0. "Rendered" means: mmdc produced an SVG AND the log contains no
   "Parse error" AND the SVG itself does not contain the "Syntax error in
   text" bomb glyph (mmdc exits 0 even on bad sources, so grep the log and
   the SVG). This gate is non-negotiable. If verification is not possible
   (mmdc missing, no network), **do not display a diagram at all** —
   describe the structure in prose and say so.

   Quoting rule: quote every label with `[...]` that contains any of
   `@ # ( ) : — , / \` or Unicode punctuation. Safest default: quote all
   labels. Unquoted labels with `@` (e.g. email addresses) are the most
   common cause of the "Syntax error" bomb.

1. **Generate a diagram of the work done.**
   - Default: **Mermaid** (flowchart / sequence / state — choose the type that
     fits the job). Include: inputs, decisions, actions taken, tools/MCPs used,
     artifacts produced, outcome.
   - Fallback: if Mermaid is insufficient (visual/spatial/branded output
     needed), use the Canva MCP (`generate-design-structured`) and attach the
     thumbnail + shortlink.
   - Every control in the rendered diagram MUST work: zoom, pan,
     **expand arrows**, collapse, fullscreen, +/− zoom, copy-as-image,
     copy-as-source, download SVG/PNG, export-to-PDF. Regenerate until all
     controls work. Do not ship a diagram with broken expand arrows.

2. **Archive to the Obsidian vault (primary store).**
   - Vault: `~/Documents/Obsidian/Jobs/` (standalone vault)
   - Path: `Jobs/YYYY-MM-DD/<job-slug>/`
   - Files to write (use the `Write` tool):
     - `job.md` — frontmatter + summary + full chat transcript that produced
       the job. Link to `diagram.md` with a wikilink.
     - `diagram.md` — Mermaid source in a fenced ```mermaid block, plus
       embedded `![[diagram.svg]]`.
     - `diagram.mmd` — raw Mermaid source (for copy-source control).
     - `diagram.svg` and `diagram.png` — rendered exports.
     - `assets/` — any Canva thumbnails, screenshots, referenced files.
   - `job.md` frontmatter MUST include: `date`, `slug`, `outcome`,
     `tools_used`, `repo` (if any), `notion_url`, `github_url`.

3. **Mirror to Notion** via `notion-create-pages`, as a child page of
   **"Sovereign Dashboard — ProlegomenaOS Infrastructure"**
   (id `3328525a-b5a0-815d-886c-d5488593aa3d`). Embed the diagram and put the
   full chat transcript inside a toggle block titled "Transcript".

4. **Mirror to GitHub** — commit the full folder to
   `myedugit/mircea-constellation` at `/jobs/YYYY-MM-DD/<job-slug>/` via
   `mcp__github__push_files` (single atomic commit). Commit message:
   `job: <slug> — <one-line outcome>`.

5. **Interaction affordances on every archived diagram page.**
   Each `job.md` MUST include, at the bottom, a working "Controls" section
   with:
   - **Copy Mermaid source** — fenced code block + wikilink to `diagram.mmd`
   - **Copy rendered image** — wikilink to `diagram.png`
   - **Export bundle** — link to a `bundle.zip` containing `diagram.svg`,
     `diagram.png`, `diagram.mmd`, `job.md`, and the chat transcript
   - **Open in Obsidian** — `obsidian://open?vault=Jobs&file=...` deep link
   - **Open in Notion** — direct URL
   - **Open in GitHub** — direct URL to the committed folder
   - Paste target: instructions for dropping an image/text onto the card to
     append to `assets/` and auto-link in `job.md`.

6. **Optional fan-out** (only when opted in for the job):
   - **Gmail draft** — `gmail_create_draft` addressed to
     `mirceamatthews@gmail.com`, subject `Job: <slug>`, body = summary +
     links, attach `bundle.zip`.
   - **Slack** — skipped by default (no channel configured). Enable per-job
     with user opt-in.
   - **Zapier** — skipped by default. When a catch-hook URL is configured in
     `~/.claude/doc.env` as `ZAPIER_DOC_HOOK`, POST the job metadata JSON.

### Report format

After archival, reply with a single fenced block:

```
✓ Obsidian: <vault-relative path>
✓ Notion:   <url>
✓ GitHub:   <url>
  diagram:  <preview or first 10 lines of Mermaid>
```

If any line begins with `✗` instead of `✓`, the user knows that mirror failed.

### Failure handling

- Retry each destination once on failure.
- If Notion or GitHub auth is missing, continue with the remaining
  destinations and flag the missing one.
- If the local vault path does not exist, create it on first run and warn
  once.
- Never abandon a job mid-archive. Partial archival with a truthful report is
  always preferred over silent skip.

### Scope note

This rule is **global** (lives in `~/.claude/CLAUDE.md`). A per-project
`CLAUDE.md` may override the GitHub repo or the Notion parent, but MUST
retain the Obsidian archival step.
