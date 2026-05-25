#!/bin/bash
# Run this on your Mac to set up hourly Obsidian auto-sync from GitHub
set -e

OBSIDIAN="/Users/mircea8me.com/Obsidian/UrantiPedia"
BRANCH="claude/debug-n8n-docker-o7zRE"
RAW="https://raw.githubusercontent.com/MyEduGit/mircea-constellation/${BRANCH}/notes"
SCRIPT="/Users/mircea8me.com/.openclaw-sync.sh"
PLIST="/Users/mircea8me.com/Library/LaunchAgents/com.openclaw.obsidian-sync.plist"

echo "Setting up Obsidian auto-sync..."

# Create sync script
cat > "$SCRIPT" << 'SYNCEOF'
#!/bin/bash
OBSIDIAN="/Users/mircea8me.com/Obsidian/UrantiPedia"
BRANCH="claude/debug-n8n-docker-o7zRE"
RAW="https://raw.githubusercontent.com/MyEduGit/mircea-constellation/${BRANCH}/notes"

mkdir -p "$OBSIDIAN/Systems/OpenClaw"
mkdir -p "$OBSIDIAN/Projects/GrandfatherAxe"
mkdir -p "$OBSIDIAN/Resources"
mkdir -p "$OBSIDIAN/Guides"

curl -sf "$RAW/Systems/OpenClaw/n8n_Deployment.md" -o "$OBSIDIAN/Systems/OpenClaw/n8n_Deployment.md"
curl -sf "$RAW/Systems/OpenClaw/SSH_Access_Guide.md" -o "$OBSIDIAN/Systems/OpenClaw/SSH_Access_Guide.md"
curl -sf "$RAW/Systems/OpenClaw/Obsidian_Sync_Options_2026.md" -o "$OBSIDIAN/Systems/OpenClaw/Obsidian_Sync_Options_2026.md"
curl -sf "$RAW/Projects/GrandfatherAxe/Vision_and_Scope.md" -o "$OBSIDIAN/Projects/GrandfatherAxe/Vision_and_Scope.md"
curl -sf "$RAW/Projects/GrandfatherAxe/GA_Session_001_Log.md" -o "$OBSIDIAN/Projects/GrandfatherAxe/GA_Session_001_Log.md"
curl -sf "$RAW/Projects/GrandfatherAxe/GA_Session_Logging_Format_Refined.md" -o "$OBSIDIAN/Projects/GrandfatherAxe/GA_Session_Logging_Format_Refined.md"
curl -sf "$RAW/Projects/GrandfatherAxe/n8n_Expansion_Plan.md" -o "$OBSIDIAN/Projects/GrandfatherAxe/n8n_Expansion_Plan.md"
curl -sf "$RAW/Projects/GrandfatherAxe/Obsidian_Plugins_for_GA.md" -o "$OBSIDIAN/Projects/GrandfatherAxe/Obsidian_Plugins_for_GA.md"
curl -sf "$RAW/Projects/GrandfatherAxe/Obsidian_Themes_for_Dyslexia.md" -o "$OBSIDIAN/Projects/GrandfatherAxe/Obsidian_Themes_for_Dyslexia.md"
curl -sf "$RAW/Projects/GrandfatherAxe/Obsidian_Dyslexia_Plugins.md" -o "$OBSIDIAN/Projects/GrandfatherAxe/Obsidian_Dyslexia_Plugins.md"
curl -sf "$RAW/Resources/OpenClaw_Full_System_Architecture.md" -o "$OBSIDIAN/Resources/OpenClaw_Full_System_Architecture.md"
curl -sf "$RAW/Guides/Apple_Passwords_Management.md" -o "$OBSIDIAN/Guides/Apple_Passwords_Management.md"
curl -sf "$RAW/Resources/Access_Booklet.md" -o "$OBSIDIAN/Resources/Access_Booklet.md"

# Also sync AI daily reports if they exist
for f in $(curl -sf "https://api.github.com/repos/MyEduGit/mircea-constellation/contents/notes/Resources?ref=${BRANCH}" 2>/dev/null | grep -o '"name":"AI_Daily[^"]*"' | cut -d'"' -f4); do
  curl -sf "$RAW/Resources/$f" -o "$OBSIDIAN/Resources/$f" 2>/dev/null
done

echo "$(date): Obsidian sync complete" >> /tmp/openclaw-sync.log
SYNCEOF

chmod +x "$SCRIPT"

# Create launchd plist for hourly sync
cat > "$PLIST" << PLISTEOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.openclaw.obsidian-sync</string>
    <key>ProgramArguments</key>
    <array>
        <string>/bin/bash</string>
        <string>$SCRIPT</string>
    </array>
    <key>StartInterval</key>
    <integer>3600</integer>
    <key>RunAtLoad</key>
    <true/>
    <key>StandardOutPath</key>
    <string>/tmp/openclaw-sync.log</string>
    <key>StandardErrorPath</key>
    <string>/tmp/openclaw-sync-error.log</string>
</dict>
</plist>
PLISTEOF

# Load the launchd job
launchctl unload "$PLIST" 2>/dev/null || true
launchctl load "$PLIST"

echo "SUCCESS: Obsidian auto-sync installed!"
echo "Notes will sync from GitHub to Obsidian every hour."
echo "First sync running now..."
bash "$SCRIPT"
echo "Done! Check Obsidian for your notes."
