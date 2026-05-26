# OmniQuery — Phase 2 Handoff Card

> Date: 2026-05-26
> Phase: 2 — Backend API
> Status: FIXED_PENDING_REAUDIT — Codex findings resolved, local-only, not deployed

---

## Codex Findings Resolved (2026-05-26)

Codex audit returned 5 issues. All resolved:

| # | Finding | Resolution |
|---|---------|------------|
| 1 | Host could be overridden to 0.0.0.0 | `config._resolve_host()` rejects any non-localhost `OMNIQUERY_HOST` (allows only `127.0.0.1`/`localhost`/`::1`) and raises at startup. `main.py` entry point binds via validated `HOST`. |
| 2 | `.env` ignore coverage unproven | Added `omniquery/.gitignore` with `backend/.env`. Verified: `git check-ignore` confirms `.env` ignored, `.env.example` stays tracked. |
| 3 | Request schema too loose | `QueryRequest` now uses `extra="forbid"` (rejects unknown fields), trims input, rejects whitespace-only at schema level, enforces `max_length=4000`. |
| 4 | Raw provider exceptions leaked to callers | Responses now return sanitized codes only: `provider_unavailable`, `timeout`, `invalid_response`, `synthesis_unavailable`. Raw detail logged internally via `logging` only. |
| 5 | `python-dotenv==1.0.1` vulnerable | Upgraded to `python-dotenv==1.2.2`, resolving CVE-2026-28684 / GHSA-mf9w-mj56-hr94. |

### Validation performed
- `python -m py_compile` on all backend modules — pass
- venv import of `main`, `council`, `models`, `config` — pass
- Schema tests: unknown-field reject, whitespace reject, trim, over-length reject — pass
- `OMNIQUERY_HOST=0.0.0.0` rejected at import — pass
- `git check-ignore` for `.env` (ignored) and `.env.example` (tracked) — pass
- Full `run_council` with no keys: only sanitized error codes returned, no raw text leak — pass

---

## Phase 2 Closeout

| Item | Status |
|------|--------|
| Backend API built | Yes |
| Bound to 127.0.0.1 | Yes — hardcoded in .env.example, enforced in run command |
| No frontend served | Yes — Phase 3 only |
| No deployment | Yes — local run only |
| No secrets in code | Yes — all keys via .env |
| .env excluded from git | Yes — rule `backend/.env` in `omniquery/.gitignore` (verified via git check-ignore) |
| Localhost-only binding | Enforced — non-127.0.0.1 OMNIQUERY_HOST rejected at startup |
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
| `omniquery/.gitignore` | Ignores `backend/.env`; keeps `.env.example` tracked |

---

## Endpoints

| Method | Path | Response |
|--------|------|---------|
| GET | /health | `{ status, version, council, seats }` |
| POST | /query | `{ query, gabriel_synthesis, seat_responses, response_count, council, omniquery_version }` |

---

## Request Schema (POST /query)

Strict — unknown fields rejected, query trimmed, whitespace-only rejected, max 4000 chars.

```json
{ "query": "string (1–4000 chars after trim)" }
```

## Response Schema (POST /query)

Errors are sanitized to stable codes only — no raw exception text is returned.
Error codes: `provider_unavailable`, `timeout`, `invalid_response`, `synthesis_unavailable`.

```json
{
  "query": "string",
  "gabriel_synthesis": "string | null",
  "synthesis_status": "ok | error",
  "synthesis_error": "null | synthesis_unavailable",
  "seat_responses": [
    { "seat": "Father", "model": "gpt-4o",        "provider": "openai",    "response": "string", "status": "ok|error", "error": "null|<code>" },
    { "seat": "Son",    "model": "claude-opus-4-7", "provider": "anthropic", "response": "string", "status": "ok|error", "error": "null|<code>" },
    { "seat": "Spirit", "model": "grok-3",         "provider": "xai",       "response": "string", "status": "ok|error", "error": "null|<code>" }
  ],
  "response_count": 3,
  "council": "Force-of-Three (Father/GPT · Son/Claude · Spirit/Grok)",
  "omniquery_version": "phase2-v1.0"
}
```

---

## Setup & Run

Binding is localhost-only and enforced in code. Run via the entry point below
(do not pass `--host`; the validated host comes from config).

```bash
cd omniquery/backend
cp .env.example .env
# Edit .env — fill OPENAI_API_KEY, ANTHROPIC_API_KEY, XAI_API_KEY
# Verify CLAUDE_MODEL is a valid Anthropic model ID before running
pip install -r requirements.txt
python main.py
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
