# OmniQuery — Phase 2 Handoff Card

> Date: 2026-05-26
> Phase: 2 — Backend API
> Status: COMPLETE — local-only, not deployed

---

## Phase 2 Closeout

| Item | Status |
|------|--------|
| Backend API built | Yes |
| Bound to 127.0.0.1 | Yes — hardcoded in .env.example, enforced in run command |
| No frontend served | Yes — Phase 3 only |
| No deployment | Yes — local run only |
| No secrets in code | Yes — all keys via .env |
| .env excluded from git | Yes — omniquery/backend/.env in .gitignore |
| Phase 3 | BLOCKED — waiting for Mircea "PHASE 3 GO" |

---

## Files Created

| File | Description |
|------|-------------|
| `omniquery/backend/main.py` | FastAPI app — /health + /query endpoints |
| `omniquery/backend/council.py` | Force-of-Three + Gabriel async logic |
| `omniquery/backend/models.py` | Pydantic request/response schemas |
| `omniquery/backend/config.py` | Environment variable config |
| `omniquery/backend/requirements.txt` | Python dependencies |
| `omniquery/backend/.env.example` | Key template (no real values) |
| `omniquery/backend/README.md` | Setup and run instructions |

---

## Endpoints

| Method | Path | Response |
|--------|------|---------|
| GET | /health | `{ status, version, council, seats }` |
| POST | /query | `{ query, gabriel_synthesis, seat_responses, response_count, council, omniquery_version }` |

---

## Response Schema (POST /query)

```json
{
  "query": "string",
  "gabriel_synthesis": "string",
  "seat_responses": [
    { "seat": "Father", "model": "gpt-4o",       "provider": "openai",    "response": "string", "status": "ok|error" },
    { "seat": "Son",    "model": "claude-opus-4-7", "provider": "anthropic", "response": "string", "status": "ok|error" },
    { "seat": "Spirit", "model": "grok-3",        "provider": "xai",       "response": "string", "status": "ok|error" }
  ],
  "response_count": 3,
  "council": "Force-of-Three (Father/GPT · Son/Claude · Spirit/Grok)",
  "omniquery_version": "phase2-v1.0"
}
```

---

## Setup & Run

```bash
cd omniquery/backend
cp .env.example .env
# Edit .env — fill OPENAI_API_KEY, ANTHROPIC_API_KEY, XAI_API_KEY
# Verify CLAUDE_MODEL is a valid Anthropic model ID before running
pip install -r requirements.txt
uvicorn main:app --host 127.0.0.1 --port 8741
```

Test:
```bash
curl http://127.0.0.1:8741/health
curl -X POST http://127.0.0.1:8741/query \
     -H "Content-Type: application/json" \
     -d '{"query": "What is the nature of truth, beauty, and goodness?"}'
```

---

## Claude Model ID — Still Provisional

`claude-opus-4-7` in config.py and .env.example is **provisional**.
Override via `CLAUDE_MODEL` in `.env` at deployment time.
Do not treat as confirmed until verified against official Anthropic docs or live API.

---

## Constraints Honoured

| Constraint | Status |
|------------|--------|
| Bind to 127.0.0.1 only | ✓ |
| No frontend | ✓ Phase 3 only |
| No deployment | ✓ |
| No browser storage | ✓ |
| No secrets in code | ✓ |
| .env.example only | ✓ |
| .env excluded by .gitignore | ✓ |
| POST /query endpoint | ✓ |
| GET /health endpoint | ✓ |
| Strict Council response schema | ✓ |
| Do not admit Gemini | ✓ |
| Do not replace Force-of-Three | ✓ |

---

## Phase 3 Trigger Condition

Phase 3 (Frontend UI) begins when:
1. Phase 2 backend runs locally and /health returns 200
2. At least one seat returns a live response via /query
3. Mircea signals "PHASE 3 GO"
