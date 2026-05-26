# OmniQuery Backend — Phase 2

Local-only FastAPI wrapper around the Force-of-Three Council.

## Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | /health | Service health check |
| POST | /query | Run a query through the Force-of-Three |

### POST /query

```json
Request:  { "query": "What is the nature of truth?" }

Response: {
  "query": "What is the nature of truth?",
  "gabriel_synthesis": "...",
  "seat_responses": [
    { "seat": "Father", "model": "gpt-4o",      "provider": "openai",    "response": "...", "status": "ok" },
    { "seat": "Son",    "model": "claude-opus-4-7", "provider": "anthropic", "response": "...", "status": "ok" },
    { "seat": "Spirit", "model": "grok-3",       "provider": "xai",       "response": "...", "status": "ok" }
  ],
  "response_count": 3,
  "council": "Force-of-Three (Father/GPT · Son/Claude · Spirit/Grok)",
  "omniquery_version": "phase2-v1.0"
}
```

## Setup

```bash
cd omniquery/backend
cp .env.example .env
# Edit .env with real API keys
pip install -r requirements.txt
```

## Run

Binding is **localhost-only and enforced in code**. Use the entry point —
do not pass `--host`. A non-localhost `OMNIQUERY_HOST` is rejected at startup.

```bash
cd omniquery/backend
python main.py
```

Verify:
```bash
curl http://127.0.0.1:8741/health
curl -X POST http://127.0.0.1:8741/query \
     -H "Content-Type: application/json" \
     -d '{"query": "What is truth?"}'
```

## Constraints

- Binds to `127.0.0.1` only — not exposed to network
- No frontend served here (Phase 3)
- No deployment to production (requires explicit Mircea approval)
- All API keys via `.env` only — never in code
- `continueOnFail` equivalent: failed seats return `status: "error"` and do not abort the request

## Model ID Note

The Son seat uses `CLAUDE_MODEL` (default `claude-opus-4-7`), which is **provisional**.
Verify against official Anthropic API docs before live test.
Override via `.env`: `CLAUDE_MODEL=claude-3-5-sonnet-latest`
