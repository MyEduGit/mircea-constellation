# Antigravity Task: Build the Substack comment-reply tool for Jarvis

Mircea wants Jarvis to handle Substack comments automatically:
**Jarvis fetches comments → Claude drafts the reply → Mircea approves → Jarvis posts.**
Build this now. Full design is in `automate-comments.md`; permissions in
`permissions.md`. Follow both exactly.

## What to build

Create `src/jarvis/tools/builtin/substack.py` (mirror the structure of the
existing `obsidian.py`) with three tools, and register them in `registry.py`:

1. **`fetchSubstackComments(post_slug)`**
   - Resolve slug → post id via
     `GET https://mirceamatthews.substack.com/api/v1/posts/by-slug/<slug>`
   - Get comments via `GET .../api/v1/post/<id>/comments?all=true`
   - Send Mircea's browser cookies (read from Safari/Chrome cookie store, or
     a `substack_cookie` value in `~/.config/jarvis/secrets.json`)
   - Track handled comment ids in `~/.config/jarvis/substack_seen.json`;
     return only NEW comments.

2. **`draftCommentReply(comment_body, commenter_name, post_excerpt)`**
   - Call the Anthropic API (model `claude-sonnet-4-6`, max_tokens 300)
   - System prompt = full contents of `vault/jarvis/answering-comments.md`
   - API key from `~/.config/jarvis/secrets.json` → `anthropic_api_key`
   - Return the draft text only. NEVER post here.

3. **`postSubstackReply(post_id, parent_id, body)`**
   - `POST .../api/v1/post/<post_id>/comment` with `{body, parent_id}`
   - Only callable AFTER Mircea approves (see permissions).

## Permission rules (from permissions.md, enforce in code)
- `fetchSubstackComments`, `draftCommentReply` → run freely
- `postSubstackReply` → require explicit approval flag; never auto-post
- Never delete comments. Never store the API key in the repo or logs.
- Log every draft + posted reply to `~/.config/jarvis/substack_log.md`

## Wiring
- Add config keys to `config.py` Settings (add `substack_seen_path`, reuse
  secrets.json for keys).
- Register the three tools in `registry.py`.
- Add unit tests `tests/test_substack_tools.py` (mock HTTP + Anthropic),
  covering: new-comment filtering, draft call shape, post requires approval,
  refuse-to-post without approval. All tests must pass.

## Acceptance
- `pytest tests/test_substack_tools.py` green
- Voice flow works: "Jarvis, any new comments?" → reads them → "I'd reply: …
  post it?" → "post it" → posted.
- No key ever printed or committed.

When done, write a short walkthrough and tell Mircea it's ready to test on Post 1
(slug: `a-third-story-about-where-we-came`).
