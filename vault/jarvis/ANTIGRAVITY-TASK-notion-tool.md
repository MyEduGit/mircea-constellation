# Antigravity Task — Build the Notion tool for Jarvis

Goal: let Jarvis read Mircea's Notion workspace — especially the 90-Day
Income Plan — so it can answer questions and turn plans into action lists.
Follow `permissions.md` exactly (read freely; ASK before writing/changing).

## What to build

Create `src/jarvis/tools/builtin/notion.py` (mirror `obsidian.py`), register
in `registry.py`:

1. **`searchNotion(query)`** — search pages/databases via the Notion API
   (`POST https://api.notion.com/v1/search`). Return titles + page ids.
2. **`readNotionPage(page_id)`** — fetch a page's blocks
   (`GET /v1/blocks/{id}/children`), return readable text.
3. **`appendNotionBlock(page_id, text)`** — ASK-FIRST. Append a paragraph.
   Never delete or overwrite existing blocks.

## Auth
- Notion integration token in `~/.config/jarvis/secrets.json` →
  `notion_token`. Header: `Authorization: Bearer <token>`,
  `Notion-Version: 2022-06-28`.
- Mircea must share the relevant pages with the integration in Notion
  (Notion → page → ... → Connections → add the integration).

## Permission rules
- search/read → run freely. append → require explicit "yes". Never delete.
- Never print the token. Never commit secrets.

## Tests
- `tests/test_notion_tools.py` mocking the Notion API: search shape, read
  parses blocks, append requires approval. All green.

## Acceptance
- "Jarvis, pull up my 90-Day Income Plan" → reads it back.
- "Turn it into a prioritised action list with done items crossed off" →
  Jarvis uses qwen2.5:14b (or Claude) to summarise the read content.
