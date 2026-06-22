# OmniQuery — Phase Roadmap

> Phase 1 is complete. This document defines what comes next.
> No phase begins without mircea8 approval.

---

## Phase Overview

| Phase | Name | Status | Trigger |
|-------|------|--------|---------|
| 1 | Force-of-Three Council Workflow | **COMPLETE** | — |
| 2 | Backend API | Not started | Phase 1 tested in n8n |
| 3 | Frontend UI | Not started | Phase 2 API running |
| 4 | Audit & Routing | Not started | Phase 3 UI live |

---

## Phase 1 — Complete

**Deliverables:**
- `omniquery/n8n_workflows/omniquery_phase1_council_workflow.json`
- `omniquery/docs/HANDOFF_PHASE_1.md`
- `docs/omniquery/OMNIQUERY_ALL_ON_ONE.md`
- Directory skeleton

**Phase 2 trigger condition:**
- Phase 1 workflow imported into n8n
- At least one seat key configured and returning live response
- mircea8 signals Phase 2 start

---

## Phase 2 — Backend API

**Goal:** Wrap the Force-of-Three in a callable API so other tools can query OmniQuery without opening n8n manually.

**Proposed stack:** FastAPI (Python) or Express (Node.js)

**Endpoint:**
```
POST /query
Body: { "query": "..." }
Response: { "gabriel_synthesis": "...", "seat_responses": [...] }
```

**Deliverables:**
- `omniquery/backend/main.py` (or `index.js`)
- `omniquery/backend/requirements.txt` (or `package.json`)
- `omniquery/backend/README.md`

**Constraints:**
- Config via environment variables only
- No hardcoded keys
- Does not replace the n8n workflow — calls it via n8n webhook, or replicates the HTTP calls directly

---

## Phase 3 — Frontend UI

**Goal:** A single-page query interface for direct use without CLI or n8n.

**Proposed stack:** Plain HTML + JS, or minimal React component

**Interface:**
- Input: text field for the query
- Output: Gabriel synthesis (prominent) + collapsible seat responses
- Status: which seats responded, which failed

**Deliverables:**
- `omniquery/frontend/index.html`
- `omniquery/frontend/app.js`
- `omniquery/frontend/style.css`

**Constraints:**
- No framework unless mircea8 approves
- No API keys in frontend code
- Calls Phase 2 backend only

---

## Phase 4 — Audit & Routing

**Goal:** Every query is logged and routing becomes intelligent.

**Audit log:**
- Each execution writes to `omniquery/audit/YYYY-MM-DD.jsonl`
- Fields: timestamp, query, response_count, gabriel_synthesis, seat_responses, latency_ms

**Routing:**
- Direct query (single seat) for speed when full council is not needed
- Full Force-of-Three for weighted or philosophical queries
- Routing decision: keyword-based or configurable

**Deliverables:**
- `omniquery/audit/` (populated by Phase 4 logger)
- `omniquery/backend/router.py`
- `omniquery/backend/audit_logger.py`

---

## Future Generations Note

If you are a future Claude Code session picking up this work:

1. Read `docs/omniquery/OMNIQUERY_ALL_ON_ONE.md` first — it is the canonical doctrine.
2. Check `omniquery/docs/HANDOFF_PHASE_1.md` for the last known state.
3. Do not start a new phase without checking with mircea8.
4. Do not admit Gemini. Do not replace Force-of-Three. Do not expose secrets.
5. Gabriel speaks last. Always.
