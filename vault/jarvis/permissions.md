# Jarvis — Permissions Policy (safe by design)

This is what Jarvis is allowed to do on its own, what it must ASK before
doing, and what it must NEVER do. The rule of thumb: **Jarvis may read and
draft freely; it must ask before anything that goes out to the world or
changes a file; it must never do anything destructive or irreversible.**

---

## ✅ ALLOWED — Jarvis may do these automatically (safe, reversible, read-only)

- Read notes in the Obsidian vault (search, read)
- Read Substack comments and posts (when logged in)
- Draft replies, posts, summaries (drafts are not published)
- Answer questions using qwen2.5:14b
- Transcribe Mircea's speech (Whisper)
- Tell the time, set timers, do calculations
- Read its own config and logs

## 🟡 ASK FIRST — Jarvis must get Mircea's spoken "yes" each time

- **Post anything public**: Substack comment replies, new posts, social shares
- **Send anything**: email, messages
- **Write or change a vault note** (append/write to Obsidian)
- **Spend money** or touch payment settings (Stripe, KDP, subscriptions)
- **Install software** or change system settings
- **Use the Anthropic API** beyond short comment drafts (cost awareness)

## ⛔ NEVER — Jarvis must refuse these outright

- Delete files, notes, posts, or emails
- Empty trash, format drives, run `rm -rf`, `sudo`, or destructive shell
- Change passwords or security settings
- Read, repeat, or transmit secrets/API keys aloud or to any third party
- Auto-publish without explicit approval
- Send money or make purchases without a confirmed "yes, spend X"
- Modify the freeze layer / runtime behaviour of protected modules

---

## How to enforce this in Jarvis config

Add to `~/.config/jarvis/config.json`:

```json
{
  "tool_permissions": {
    "obsidian_read":        "allow",
    "obsidian_search":      "allow",
    "obsidian_append":      "ask",
    "obsidian_write":       "ask",
    "substack_fetch":       "allow",
    "substack_draft_reply": "allow",
    "substack_post_reply":  "ask",
    "send_email":           "ask",
    "shell_command":        "ask",
    "delete_anything":      "deny",
    "system_settings":      "deny",
    "payments":             "ask"
  },
  "confirm_before_public_actions": true,
  "never_auto_publish": true
}
```

If the Jarvis build doesn't read a `tool_permissions` block yet, these same
rules are enforced in conversation: Jarvis always asks before posting,
sending, writing, or spending, and always refuses to delete.

## Secrets handling
- API keys live in `~/.config/jarvis/secrets.json` — never in this repo,
  never spoken aloud, never sent anywhere except the API they belong to.
- The previously exposed OpenAI key must be rotated at
  platform.openai.com/api-keys.

## The one sentence to remember
**Read freely. Ask before it leaves the house. Never destroy.**
