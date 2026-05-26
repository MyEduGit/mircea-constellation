# OmniQuery — Model ID Verification Report

> Date: 2026-05-26
> Scope: OmniQuery Phase 1 (n8n workflow) + Phase 2 (FastAPI backend) model IDs
> Method: Official provider documentation and public release announcements
> Live credentials used: No
> Backend started: No
> Workflow imported: No

---

> **Resolution update (2026-05-26):** The Spirit-seat patch recommended below
> has been applied — `grok-3` → `grok-4.3` across all OmniQuery artifacts, and
> the stale `claude-opus-4-5-20251001` reference corrected to `claude-opus-4-7`
> in the doctrine and notion-export. The findings below are preserved as the
> original point-in-time record. Account access for `claude-opus-4-7` must
> still be verified before any live use.

## Verdict Summary

| Seat | Role | Model ID in use | Status | Action required |
|------|------|-----------------|--------|-----------------|
| Father | OpenAI / chat | `gpt-4o` | **VALID** (API) | None immediately — see note |
| Son | Anthropic / chat | `claude-opus-4-7` | **CONFIRMED VALID** | Remove "provisional" flag |
| Spirit | xAI / chat | `grok-3` | **RETIRED May 15 2026** | **Update to `grok-4.3`** |
| Gabriel | OpenAI / synthesis | `gpt-4o` | **VALID** (API) | None immediately — see note |

---

## Findings by seat

### Father — `gpt-4o` (OpenAI)

- `gpt-4o` was removed from the ChatGPT web interface (February 2026) and
  from ChatGPT Enterprise/Edu custom GPTs (April 3, 2026).
- **The API model ID `gpt-4o` remains available with no changes at this
  time.** OpenAI's deprecation notices explicitly distinguish ChatGPT
  interface retirement from API availability.
- Newer flagship models exist (`gpt-4.1`, `gpt-5.5`). OpenAI has signalled
  upcoming API shutdowns for older models in 2026 but has not published a
  specific shutdown date for `gpt-4o` in the API at this writing.
- **Verdict: VALID for current API use.** Flag for future review before live
  deployment — recommend Mircea's approval before upgrading to `gpt-4.1` or
  `gpt-5.5`, which would change the seat lineage cost and behaviour.
- Proposed action: **No change now.** Monitor OpenAI deprecation schedule.

---

### Son — `claude-opus-4-7` (Anthropic)

- Model ID `claude-opus-4-7` is confirmed as the official exact API string
  for Claude Opus 4.7.
- Claude Opus 4.7 became generally available on **April 16, 2026**.
  It is the current Anthropic flagship model (an improvement on Opus 4.6 in
  advanced software engineering).
- Available on Anthropic API directly, Amazon Bedrock, Google Cloud Vertex
  AI, Microsoft Foundry, and GitHub Models.
- The "provisional" label applied throughout Phase 1 and Phase 2 is now
  **resolved**. The model ID is confirmed against official Anthropic release
  documentation.
- **Verdict: CONFIRMED VALID. Provisional flag cleared.**
- Proposed action: Remove the provisional warning from `config.py`,
  `.env.example`, `HANDOFF_PHASE_2.md`, and the n8n workflow HTTP node body
  where `CLAUDE_MODEL` is referenced. (Do not modify files in this report
  pass — record finding only.)

---

### Spirit — `grok-3` (xAI)

- **`grok-3` was retired by xAI on May 15, 2026 at 12:00 PM PT** — eleven
  days before this report.
- As of retirement, requests to the `grok-3` slug are **automatically
  redirected to `grok-4.3`** by xAI infrastructure. This means:
  - The backend will not throw an error — it silently receives Grok 4.3
    responses.
  - Pricing, context window, and reasoning behaviour differ from Grok 3.
  - The redirect is not an explicit configuration — it is invisible to callers.
- The correct explicit replacement model ID is **`grok-4.3`**.
- `grok-4.3` is xAI's current flagship: 1 M-token context window, leading
  non-hallucination rate, supports reasoning and non-reasoning modes.
  For OmniQuery's use (general chat / council reasoning), `grok-4.3` is
  the direct seat-preserving upgrade.
- **Verdict: RETIRED. The Spirit seat is silently running Grok 4.3 already
  due to the redirect; the config must be updated to make this explicit.**
- Proposed action: **Update `grok-3` → `grok-4.3`** in:
  - `omniquery/backend/config.py` (`XAI_MODEL` or inline model string)
  - `omniquery/backend/.env.example`
  - `omniquery/n8n_workflows/omniquery_phase1_council_workflow.json`
    (Spirit node HTTP body)
  - `omniquery/docs/HANDOFF_PHASE_1.md` and `HANDOFF_PHASE_2.md` tables
  - `omniquery/backend/README.md` response schema example
  - `omniquery/docs/MODEL_ID_VERIFICATION.md` (this file)
  Requires Mircea's "SPIRIT MODEL UPDATE GO" or equivalent gate before
  modifying files, consistent with the approval doctrine.

---

### Gabriel — `gpt-4o` (OpenAI, synthesis)

- Same model and same API status as the Father seat above.
- **Verdict: VALID for current API use.** Same aging caveat applies.
- Proposed action: **No change now.** Monitor alongside Father seat.

---

## Action plan (pending Mircea approval)

| Priority | Action | Files affected |
|----------|--------|----------------|
| **High** | Update Spirit seat: `grok-3` → `grok-4.3` | `config.py`, `.env.example`, n8n JSON, README, HANDOFF files |
| **High** | Remove Claude provisional flag | `config.py`, `.env.example`, `HANDOFF_PHASE_2.md` |
| **Low** | Monitor `gpt-4o` API deprecation schedule | No file change now |

---

## What was NOT done

- No API key used or printed.
- No live model call made.
- No workflow imported or activated.
- No n8n accessed.
- No backend started.
- No files modified (report only).
- Phase 4 not started.

---

## Sources consulted

- [Models overview — Claude API Docs](https://docs.anthropic.com/en/docs/about-claude/models)
- [Introducing Claude Opus 4.7 — Anthropic](https://www.anthropic.com/news/claude-opus-4-7)
- [Claude Opus 4.7 GA — GitHub Changelog](https://github.blog/changelog/2026-04-16-claude-opus-4-7-is-generally-available/)
- [May 15, 2026 Model Retirement — xAI Docs](https://docs.x.ai/developers/migration/may-15-retirement)
- [Grok 4.3 — xAI Docs](https://docs.x.ai/developers/models/grok-4.3)
- [Models — xAI Docs](https://docs.x.ai/developers/models)
- [xAI grok-3 retirement migration guide — Apiyi](https://help.apiyi.com/en/grok-4-3-release-xai-api-model-retirement-en.html)
- [xAI retired 8 Grok models May 15 — DEV Community](https://dev.to/flarecanary/xai-retired-8-grok-models-on-may-15-the-slugs-still-resolve-so-your-bill-and-output-quality-26jd)
- [Retiring GPT-4o in ChatGPT — OpenAI](https://openai.com/index/retiring-gpt-4o-and-older-models/)
- [Deprecations — OpenAI API](https://developers.openai.com/api/docs/deprecations)
- [Models — OpenAI API](https://developers.openai.com/api/docs/models)
