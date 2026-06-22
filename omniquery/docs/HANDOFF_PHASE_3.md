# OmniQuery — Phase 3 Handoff Card

> Date: 2026-05-26
> Phase: 3 — Frontend UI
> Status: BUILT_LOCAL — local-only React/Vite UI built, not deployed, not audited

> **PHASE 3 — LOCAL UI ONLY.** Not for deployment. Not for production hosting.
> This UI exists solely to drive the Phase 2 backend on a local machine.

---

## What was built

A single-page React/Vite interface for the existing Phase 2 Force-of-Three
backend. It provides:

- A query input (textarea, trimmed, max 4000 chars — matches backend schema).
- Gabriel's synthesis, shown prominently at the top of the results.
- Three seat cards — Father/GPT · Son/Claude · Spirit/Grok — each showing
  model, provider, and response or sanitized error.
- A seat tally ("N/3 seats responded").
- Error states rendered as the backend's **sanitized error codes only**
  (`provider_unavailable`, `timeout`, `invalid_response`,
  `synthesis_unavailable`), each with a short fixed gloss. No raw provider
  text is expected or rendered.

---

## How it reaches the backend (localhost only)

The browser never calls the backend directly. The Vite dev server binds to
`127.0.0.1:5273` and proxies `/api/*` to the Phase 2 backend at
`127.0.0.1:8741`, server-side. Every hop stays on localhost and the backend
CORS config is left **untouched** (no backend modification was required).

```
browser ──> 127.0.0.1:5273 (Vite dev server) ──proxy──> 127.0.0.1:8741 (backend)
```

---

## Files created

| File | Description |
|------|-------------|
| `omniquery/frontend/package.json` | Scripts + React/Vite deps |
| `omniquery/frontend/vite.config.js` | Localhost bind + `/api` → `127.0.0.1:8741` proxy |
| `omniquery/frontend/index.html` | App shell (noindex/nofollow) |
| `omniquery/frontend/src/main.jsx` | React entry point |
| `omniquery/frontend/src/App.jsx` | Query form, results, seat cards, sanitized errors |
| `omniquery/frontend/src/styles.css` | Styling |
| `omniquery/frontend/.gitignore` | Ignores `node_modules/`, `dist/`, `.vite/` |
| `omniquery/frontend/README.md` | Local-only setup and run instructions |

Backend files: **unchanged.**

---

## Run (local only)

```bash
# Terminal 1 — backend (Phase 2)
cd omniquery/backend
python main.py            # listens on 127.0.0.1:8741

# Terminal 2 — frontend (Phase 3)
cd omniquery/frontend
npm install
npm run dev               # serves on http://127.0.0.1:5273
```

Open `http://127.0.0.1:5273` in a local browser.

---

## Validation performed

| Check | Result |
|-------|--------|
| `npm install` | pass (62 packages) |
| `npm run build` (production compile) | pass — 31 modules transformed |
| Dev server binds to `127.0.0.1:5273` | pass |
| Dev server serves SPA | pass (HTTP 200) |
| `/api` proxy targets `127.0.0.1:8741` | pass (ECONNREFUSED while backend down — proxy wired correctly) |
| Live `/query` round-trip | **not run** — backend not started (no keys; out of scope) |

The full query→synthesis flow was **not** exercised end-to-end because the
backend was not started (no API keys present, and starting it is out of
scope). The UI's network-error path is what surfaces when the backend is
down.

---

## Constraints honoured

| Constraint | Status |
|------------|--------|
| Local-only (dev server binds `127.0.0.1`, never `0.0.0.0`) | ✓ |
| No deployment | ✓ |
| No production hosting | ✓ |
| No API keys in frontend | ✓ — keys remain in backend `.env` |
| No browser storage of secrets | ✓ — no localStorage/sessionStorage/cookies |
| Frontend calls backend at `127.0.0.1` only | ✓ — via dev-server proxy |
| Query input shown | ✓ |
| Force-of-Three seat responses shown | ✓ |
| Gabriel synthesis shown | ✓ — prominent |
| Error states use sanitized codes only | ✓ |
| "Phase 3 local UI only" warning in README/HANDOFF | ✓ |
| Do not admit Gemini | ✓ — seats fixed at Father/Son/Spirit |
| Do not replace Force-of-Three | ✓ |
| Backend unchanged (except if required) | ✓ — not required, untouched |
| Do not start Phase 4 | ✓ |

---

## Status

- **Phase 3 = BUILT_LOCAL** (not deployed, not audited).
- **Phase 4 = LOCKED.**
- `next_trigger = PHASE 3 VERIFY` — awaiting review (Antigravity / Codex) and
  Mircea's gate before any further phase.

Stopping here. No deployment. No Phase 4.
