# Download and Install Claude Cowork for Mac

Runbook for installing Claude Cowork on macOS and correcting a stale product description that still called Cowork a "beta / research preview."

## Context

As of April 2026, **Cowork** is a first-party Anthropic product ("Claude Cowork" — agentic AI for knowledge work), shipped inside the Claude desktop app for macOS. There is no separate "coworkos" installer; Cowork is accessed from the Claude macOS app sidebar once signed in on an eligible paid plan.

Goal: get Cowork running on a Mac so it can be used for agentic file/task automation and plugins outside of the Claude Code CLI.

## Prerequisites

- macOS (Cowork is Mac-only today; Windows support is planned).
- A paid Claude plan: **Pro, Max, Team, or Enterprise**. Free accounts cannot open Cowork.
- Admin rights to drag an app into `/Applications`.

## Steps

1. **Download the Claude desktop app for Mac**
   - Visit <https://claude.com/download> in a browser on the Mac.
   - Download the macOS `.dmg` (the page auto-detects Apple Silicon vs Intel).

2. **Install the app**
   - Open the downloaded `.dmg`.
   - Drag **Claude** into the **Applications** folder.
   - Eject the disk image.

3. **Launch and sign in**
   - Open **Claude** from `/Applications` (or Spotlight).
   - Sign in with the account that holds the Pro/Max/Team/Enterprise subscription.

4. **Enable Cowork**
   - In the Claude app sidebar, click **Cowork**.
   - If prompted, grant the filesystem / accessibility permissions Cowork requests — required for it to act on local files and apps.

5. **(Optional) Update an existing install**
   - If Claude is already installed, use **Claude → Check for Updates…** from the menu bar, or re-download from <https://claude.com/download> and replace the app in `/Applications`.

## Verification

- Claude app opens without errors and the top-left shows the signed-in account.
- A **Cowork** entry is visible in the left sidebar and opens a Cowork workspace when clicked.
- In the Cowork workspace, a new session can read a test file (e.g., on the Desktop) — confirming the filesystem permission grant worked.
- Help Center reference if anything is off: <https://support.claude.com/en/articles/13345190-get-started-with-claude-cowork>.

## Correction to the stale product blurb

The older description is wrong in two ways:

- "Cowork (beta / research preview)" — it is positioned as a shipping product for paid plans, not a research preview.
- "A desktop tool for non-developers to automate file and task management" — Cowork is pitched as "Claude Code power for knowledge work," usable by developers and non-developers alike, and supports plugins (MCPs, skills, tools).

## Sources

- [Download Claude](https://claude.com/download)
- [Claude Cowork product page](https://claude.com/product/cowork)
- [Claude Cowork (Anthropic)](https://www.anthropic.com/product/claude-cowork)
- [Get started with Claude Cowork (Help Center)](https://support.claude.com/en/articles/13345190-get-started-with-claude-cowork)
