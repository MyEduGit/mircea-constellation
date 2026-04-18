#!/bin/bash
# Run this on your Mac to copy all notes to Obsidian
# Usage: bash sync-to-obsidian.sh

OBSIDIAN="/Users/mircea8me.com/Obsidian/UrantiPedia"
BRANCH="claude/debug-n8n-docker-o7zRE"
RAW="https://raw.githubusercontent.com/MyEduGit/mircea-constellation/${BRANCH}/notes"

mkdir -p "$OBSIDIAN/Systems/OpenClaw"
mkdir -p "$OBSIDIAN/Projects/GrandfatherAxe"
mkdir -p "$OBSIDIAN/Resources"
mkdir -p "$OBSIDIAN/Guides"

curl -s "$RAW/Systems/OpenClaw/n8n_Deployment.md" -o "$OBSIDIAN/Systems/OpenClaw/n8n_Deployment.md"
curl -s "$RAW/Systems/OpenClaw/SSH_Access_Guide.md" -o "$OBSIDIAN/Systems/OpenClaw/SSH_Access_Guide.md"
curl -s "$RAW/Systems/OpenClaw/Obsidian_Sync_Options_2026.md" -o "$OBSIDIAN/Systems/OpenClaw/Obsidian_Sync_Options_2026.md"
curl -s "$RAW/Projects/GrandfatherAxe/Vision_and_Scope.md" -o "$OBSIDIAN/Projects/GrandfatherAxe/Vision_and_Scope.md"
curl -s "$RAW/Projects/GrandfatherAxe/GA_Session_001_Log.md" -o "$OBSIDIAN/Projects/GrandfatherAxe/GA_Session_001_Log.md"
curl -s "$RAW/Projects/GrandfatherAxe/GA_Session_Logging_Format_Refined.md" -o "$OBSIDIAN/Projects/GrandfatherAxe/GA_Session_Logging_Format_Refined.md"
curl -s "$RAW/Projects/GrandfatherAxe/n8n_Expansion_Plan.md" -o "$OBSIDIAN/Projects/GrandfatherAxe/n8n_Expansion_Plan.md"
curl -s "$RAW/Projects/GrandfatherAxe/Obsidian_Plugins_for_GA.md" -o "$OBSIDIAN/Projects/GrandfatherAxe/Obsidian_Plugins_for_GA.md"
curl -s "$RAW/Projects/GrandfatherAxe/Obsidian_Themes_for_Dyslexia.md" -o "$OBSIDIAN/Projects/GrandfatherAxe/Obsidian_Themes_for_Dyslexia.md"
curl -s "$RAW/Projects/GrandfatherAxe/Obsidian_Dyslexia_Plugins.md" -o "$OBSIDIAN/Projects/GrandfatherAxe/Obsidian_Dyslexia_Plugins.md"
curl -s "$RAW/Resources/OpenClaw_Full_System_Architecture.md" -o "$OBSIDIAN/Resources/OpenClaw_Full_System_Architecture.md"
curl -s "$RAW/Guides/Apple_Passwords_Management.md" -o "$OBSIDIAN/Guides/Apple_Passwords_Management.md"
curl -s "$RAW/Resources/Access_Booklet.md" -o "$OBSIDIAN/Resources/Access_Booklet.md"

echo "Done! 13 notes saved to Obsidian."
