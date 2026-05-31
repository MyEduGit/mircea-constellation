# Jarvis — Automating Substack Comment Replies (the relay)

## Why this design
Claude in the cloud is the best writer, but Substack **bot-blocks** cloud
servers (HTTP 999). Jarvis runs on Mircea's iMac, logged into Substack with
his own browser session — so Jarvis CAN read comments that cloud Claude can't.

So the labour is split:

```
  Jarvis (local, has login)        Claude (best writer)         Mircea
  ─────────────────────────        ────────────────────         ──────
  1. fetch new comments      ──►    2. draft reply in his   ──►  3. approve
     from Substack                     voice (Anthropic API)        & post
```

Jarvis fetches and posts (it's authenticated); Claude writes; Mircea has the
final say. Nothing is published without Mircea's yes.

---

## Step 1 — Jarvis fetches comments

Substack exposes a JSON comments API that works WHEN called from Mircea's
logged-in machine (cookies present). For a post with slug `a-third-story`:

```
GET https://mirceamatthews.substack.com/api/v1/posts/by-slug/a-third-story
        → returns the post id
GET https://mirceamatthews.substack.com/api/v1/post/<id>/comments?all=true
        → returns every comment: { id, body, name, date, parent_id }
```

Jarvis should send the browser cookie jar (Safari/Chrome) with the request.
Store the highest `comment id` already handled in
`~/.config/jarvis/substack_seen.json` so only NEW comments are processed.

## Step 2 — Claude drafts the reply (Anthropic API)

For each new comment, Jarvis calls the Anthropic API with:
- The comment text
- The post excerpt it's responding to
- The voice + recipe from `answering-comments.md` (system prompt)

Recommended model: **claude-sonnet-4-6** (great writing, fast, cheap enough
for short replies). System prompt = the contents of `answering-comments.md`.

Pseudo-call:
```
POST https://api.anthropic.com/v1/messages
{
  "model": "claude-sonnet-4-6",
  "max_tokens": 300,
  "system": "<contents of answering-comments.md>",
  "messages": [
    {"role": "user", "content":
      "Post excerpt: <…>\n\nReader (Jane): <comment>\n\nDraft Mircea's reply."}
  ]
}
```

## Step 3 — Mircea approves

Jarvis presents each draft out loud / in the face window:
> "Jane wrote: '<comment>'. I'd reply: '<draft>'. Post it, edit, or skip?"

- **"Post it"** → Jarvis POSTs the reply via Substack's comment API
- **"Edit"** → Mircea dictates a change, Jarvis re-drafts
- **"Skip"** → marks it seen, no reply

Posting a reply (authenticated):
```
POST https://mirceamatthews.substack.com/api/v1/post/<id>/comment
{ "body": "<reply text>", "parent_id": <comment id> }
```

---

## How to build it (one new Jarvis tool)

Add a tool file `src/jarvis/tools/builtin/substack.py` with three functions,
registered in `registry.py` (same pattern as `obsidian.py`):

1. `fetchSubstackComments(post_slug)` → list of unhandled comments
2. `draftCommentReply(comment, post_excerpt)` → calls Anthropic API
3. `postSubstackReply(post_id, parent_id, body)` → posts after approval

Keep the Anthropic API key in `~/.config/jarvis/secrets.json` (NOT in the
repo, NOT in chat — the last key got exposed and must be rotated).

## Safety rules (non-negotiable)
- **Never auto-post.** Always require Mircea's explicit "post it".
- Hostile/strange comments → flag, suggest a brief thank-you or skip.
- Rate-limit: handle a few comments per run, not a flood.
- Log every drafted + posted reply to `~/.config/jarvis/substack_log.md`.

---

## Until this is built — the manual relay (works today)
Mircea pastes a comment into the Claude session; Claude drafts the reply;
Mircea posts it. Same quality, just hand-carried instead of automated.
This is the fallback whenever the tool isn't running.
