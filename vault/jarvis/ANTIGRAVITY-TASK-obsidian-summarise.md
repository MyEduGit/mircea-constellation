# Antigravity Task — Add summarise/RAG over Obsidian for Jarvis

The Obsidian read/search/write/append tools already exist (`obsidian.py`).
This task adds the ability to **summarise and answer questions across many
notes at once** (lightweight RAG), so Jarvis can use Mircea's life's work.

## What to build

Extend `src/jarvis/tools/builtin/obsidian.py` (or a new `obsidian_rag.py`):

1. **`summariseObsidianNotes(query, max_notes=8)`**
   - Use existing search to find the most relevant notes for `query`
   - Read their contents (truncate each to ~2000 chars)
   - Send the bundle to the chat model (qwen2.5:14b, or Claude
     `claude-sonnet-4-6` if `anthropic_api_key` present) with a prompt:
     "Answer the question using ONLY these notes; cite note titles."
   - Return a grounded answer with the note titles it used.

2. **Optional `buildObsidianIndex()`** — a simple keyword/embedding index
   cached at `~/.config/jarvis/obsidian_index.json` to speed up search on
   large vaults. Skip if the vault is small.

## Permission rules (permissions.md)
- Read-only over the vault → run freely. No writes here.
- If using Claude, it's a paid API call → fine for this read task, but log it.

## Tests
- `tests/test_obsidian_rag.py`: search→read→summarise pipeline with mocked
  model; verify it only uses provided notes and returns cited titles.

## Acceptance
- "Jarvis, summarise everything I've written about the Thought Adjuster" →
  pulls the relevant notes and gives a grounded, cited answer in Mircea's
  knowledge.
