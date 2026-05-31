# Jarvis — one-time setup on NemoClaw

## Step 1 — Smarter brain (qwen2.5:14b)

Open Terminal, paste:

```bash
cp ~/jarvis/vault/jarvis/config-qwen.json ~/.config/jarvis/config.json
```

Or do it manually: open `~/.config/jarvis/config.json` and change
`"chat_model"` to `"qwen2.5:14b"`.

---

## Step 2 — Auto-start on login (no terminal needed)

Copy the launchd service file then load it:

```bash
cp ~/mircea-constellation/vault/jarvis/com.mircea.jarvis.plist \
   ~/Library/LaunchAgents/com.mircea.jarvis.plist

launchctl load ~/Library/LaunchAgents/com.mircea.jarvis.plist
```

From now on Jarvis starts automatically every time you log in.
The face window will appear after ~30 seconds (desktop load delay).

**Stop Jarvis:**
```bash
launchctl unload ~/Library/LaunchAgents/com.mircea.jarvis.plist
```

**Start Jarvis (without rebooting):**
```bash
launchctl load ~/Library/LaunchAgents/com.mircea.jarvis.plist
```

**View logs:**
```bash
tail -f ~/Library/Logs/jarvis.log
```

---

## Step 3 — Restart now to see the new angelic face

```bash
pkill -f "desktop_app/app.py"
cd ~/jarvis && bash scripts/run_desktop_app.sh
```

---

## Step 4 — Give Jarvis its memory seed

Once Jarvis is running, say:

> "Jarvis, remember: I am Mircea G. Matthews, age 70, living in Melbourne,
> Australia. My life's work is the Urantia Book — a 2097-page revelation of
> cosmic truth. I publish the newsletter 'A Third Story' on Substack, write
> books under the pen name Mircea G. Matthews, and my mission is to help
> ordinary people encounter the God who personally indwells them. You are
> my assistant for writing, research, scheduling, and income. You have
> access to my Obsidian vault where all my notes live."

---

## What Jarvis can do for you now

| Say this | Jarvis does this |
|---|---|
| "Search my notes for Melchizedek" | Searches Obsidian vault |
| "Read my note on light and life" | Opens that note aloud |
| "Write a note: [title] — [content]" | Saves to Obsidian |
| "What day is it?" / "Set a timer" | System queries |
| "Help me write a paragraph about…" | Uses qwen2.5:14b brain |
| "Summarise my Urantia notes on…" | RAG over your vault |
