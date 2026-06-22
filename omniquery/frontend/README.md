# OmniQuery Frontend — Phase 3

> **PHASE 3 — LOCAL UI ONLY.**
> Not for deployment. Not for production hosting. This UI exists to drive the
> Phase 2 backend on your own machine and nothing more.

A single-page React/Vite interface for the Force-of-Three Council backend.
It shows a query box, the three seat responses (Father/GPT · Son/Claude ·
Spirit/Grok), and Gabriel's synthesis. Errors are surfaced only as the
backend's sanitized error codes — no raw provider text.

## How it talks to the backend (localhost only)

The browser never calls the backend directly. The Vite dev server binds to
`127.0.0.1:5273` and proxies `/api/*` to the Phase 2 backend at
`127.0.0.1:8741`. Every hop stays on localhost, and the backend's CORS config
is left untouched.

```
browser ──> 127.0.0.1:5273 (Vite dev server) ──proxy──> 127.0.0.1:8741 (backend)
```

## Run (local only)

1. Start the Phase 2 backend first (separate terminal):

   ```bash
   cd ../backend
   python main.py        # listens on 127.0.0.1:8741
   ```

2. Start this UI:

   ```bash
   cd omniquery/frontend
   npm install
   npm run dev           # serves on http://127.0.0.1:5273
   ```

3. Open `http://127.0.0.1:5273` in a local browser.

## Constraints honoured

- Local-only: dev server binds to `127.0.0.1`, never `0.0.0.0`.
- No deployment, no production hosting.
- No API keys in the frontend — all keys live in the backend `.env`.
- No browser storage of secrets (no localStorage/sessionStorage/cookies).
- Calls the backend at `127.0.0.1` only, via the dev-server proxy.
- Force-of-Three is fixed: Father / Son / Spirit. Gemini is not admitted.
- Error states display sanitized codes only (`provider_unavailable`,
  `timeout`, `invalid_response`, `synthesis_unavailable`).

## Files

| File | Purpose |
|------|---------|
| `index.html` | App shell (noindex/nofollow) |
| `vite.config.js` | Localhost bind + `/api` → `127.0.0.1:8741` proxy |
| `src/main.jsx` | React entry point |
| `src/App.jsx` | Query form, results, seat cards, sanitized error rendering |
| `src/styles.css` | Styling |
| `package.json` | Scripts and dependencies |
| `.gitignore` | Ignores `node_modules/`, `dist/`, `.vite/` |

## Not in scope

- No deployment / hosting config.
- No Phase 4 work.
- No backend changes (the proxy keeps the backend untouched).
